import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.client_ip import get_client_ip
from app.config import settings
from app.cookies import (
    OIDC_FLOW_COOKIE_NAME,
    clear_auth_cookie,
    clear_id_token_cookie,
    clear_oidc_flow_cookie,
    set_auth_cookie,
    set_id_token_cookie,
    set_oidc_flow_cookie,
)
from app.database import get_db
from app.dependencies import (
    ensure_password_length,
    get_audit_logger,
    get_current_user,
    user_from_session_cookie,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    OidcConfig,
    OidcLoginResponse,
    UserResponse,
)
from app.services import admin_service, auth_service
from app.services.audit_service import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")


async def _get_oidc_cfg(db: AsyncSession) -> dict[str, Any] | None:
    """Load OIDC config from DB; returns None if not configured or disabled."""
    db_cfg = await admin_service.get_oidc_settings(db)
    if db_cfg and db_cfg.enabled:
        return {
            "client_id": db_cfg.client_id,
            "client_secret": db_cfg.client_secret,
            "discovery_url": db_cfg.discovery_url,
            "redirect_uri": db_cfg.redirect_uri,
            "scopes": db_cfg.scopes,
            "post_logout_redirect_uri": db_cfg.post_logout_redirect_uri,
        }
    return None


@router.get("/config", response_model=OidcConfig)
async def get_auth_config(db: AsyncSession = Depends(get_db)) -> OidcConfig:
    db_cfg = await admin_service.get_oidc_settings(db)
    if db_cfg:
        return OidcConfig(
            enabled=db_cfg.enabled,
            client_id=db_cfg.client_id if db_cfg.enabled else None,
            local_login_disabled=db_cfg.local_login_disabled,
        )
    return OidcConfig(enabled=False, client_id=None, local_login_disabled=False)


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    db_cfg = await admin_service.get_oidc_settings(db)
    local_disabled = db_cfg.local_login_disabled if db_cfg else False
    audit = AuditLogger(db, payload.username, ip=get_client_ip(request))
    if local_disabled:
        await audit.failure(
            "login",
            "auth",
            details={"detail": "Local connection is disabled. Use SSO."},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local connection is disabled. Use SSO.",
        )
    user = await auth_service.authenticate_user(db, payload.username, payload.password)
    if not user:
        await audit.failure("login", "auth")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
        )
    audit.user_id = user.id
    await audit.success("login", "auth")
    token = auth_service.create_session_token(user)
    set_auth_cookie(response, request, token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    # Logging out must always clear the cookie, even when the session has already
    # expired — hence the identity is resolved best-effort rather than required.
    user = await user_from_session_cookie(db, request)
    if user is not None:
        # Revoke the JWT server-side too: a copy of the cookie stops working.
        # This ends the user's sessions on every device.
        auth_service.revoke_sessions(user)
        db.add(user)
        await db.commit()
        audit = AuditLogger(db, user.username, user.id, get_client_ip(request))
        await audit.success("logout", "auth")

    logout_url: str | None = None
    cfg = await _get_oidc_cfg(db)
    if cfg and cfg["post_logout_redirect_uri"] and (user is None or user.is_oidc):
        id_token = request.cookies.get(settings.id_token_cookie_name)
        try:
            logout_url = await auth_service.build_oidc_logout_url(id_token, cfg)
        except Exception as exc:  # noqa: BLE001
            # A provider hiccup must never block the local logout.
            _log_oidc_error("logout url build", exc)

    clear_auth_cookie(response)
    clear_id_token_cookie(response)
    return LogoutResponse(logout_url=logout_url)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    is_account_admin = await admin_service.user_is_account_admin(db, current_user.id)  # type: ignore[arg-type]
    return UserResponse(
        id=current_user.id,  # type: ignore[arg-type]
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_oidc=current_user.is_oidc,
        is_admin=current_user.is_admin,
        is_account_admin=is_account_admin,
    )


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    if current_user.is_oidc:
        await audit.failure(
            "change_password",
            "user",
            current_user.username,
            {"detail": "SSO users cannot change their password"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO users cannot change their password",
        )
    if not current_user.hashed_password or not auth_service.verify_password(
        payload.current_password, current_user.hashed_password
    ):
        await audit.failure(
            "change_password",
            "user",
            current_user.username,
            {"detail": "Current password is incorrect"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    await ensure_password_length(
        audit, "change_password", current_user.username, payload.new_password
    )
    current_user.hashed_password = auth_service.hash_password(payload.new_password)
    # Revoke every other session; the current one gets a fresh token.
    auth_service.revoke_sessions(current_user)
    db.add(current_user)
    await db.commit()
    set_auth_cookie(response, request, auth_service.create_session_token(current_user))
    await audit.success("change_password", "user", current_user.username)


@router.get("/oidc/login", response_model=OidcLoginResponse)
async def oidc_login(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> OidcLoginResponse:
    cfg = await _get_oidc_cfg(db)
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC not configured"
        )
    url, flow_token = await auth_service.start_oidc_flow(cfg)
    set_oidc_flow_cookie(
        response,
        request,
        flow_token,
        int(auth_service.OIDC_FLOW_TTL.total_seconds()),
    )
    return OidcLoginResponse(authorization_url=url)


def _oidc_redirect(url: str) -> RedirectResponse:
    """Redirect at the end of the OIDC callback; the flow cookie is single-use."""
    redirect = RedirectResponse(url=url)
    clear_oidc_flow_cookie(redirect)
    return redirect


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request, code: str, state: str, db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    cfg = await _get_oidc_cfg(db)
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC not configured"
        )
    try:
        nonce, code_verifier = auth_service.validate_oidc_flow(
            request.cookies.get(OIDC_FLOW_COOKIE_NAME), state
        )
    except ValueError as exc:
        # Never log the query string: it carries the authorization code.
        logger.warning("OIDC state validation failed: %s", exc)
        audit = AuditLogger(db, "oidc", ip=get_client_ip(request))
        await audit.failure("login", "auth", details={"detail": "Invalid OIDC state"})
        return _oidc_redirect("/login?error=oidc_state_invalid")
    try:
        tokens = await auth_service.exchange_oidc_code(code, code_verifier, cfg)
        claims = await auth_service.verify_oidc_id_token(
            tokens.get("id_token", ""), nonce, cfg
        )
    except Exception as exc:
        _log_oidc_error("token exchange", exc)
        audit = AuditLogger(db, "oidc", ip=get_client_ip(request))
        await audit.failure(
            "login", "auth", details={"detail": "OIDC token exchange failed"}
        )
        return _oidc_redirect("/login?error=oidc_failed")
    try:
        userinfo = await auth_service.get_oidc_userinfo(tokens["access_token"], cfg)
        # OpenID Connect Core 5.3.2: the UserInfo sub must match the id_token.
        if userinfo.get("sub") != claims["sub"]:
            raise ValueError("UserInfo subject does not match the id_token")
    except Exception as exc:
        _log_oidc_error("userinfo fetch", exc)
        audit = AuditLogger(db, "oidc", ip=get_client_ip(request))
        await audit.failure(
            "login", "auth", details={"detail": "OIDC userinfo fetch failed"}
        )
        return _oidc_redirect("/login?error=oidc_failed")
    username: str = userinfo.get("preferred_username") or claims["sub"]
    try:
        email: str | None = userinfo.get("email")
        user = await auth_service.get_or_create_oidc_user(
            db,
            issuer=claims["iss"],
            subject=claims["sub"],
            username=username,
            email=email,
        )
        audit = AuditLogger(
            db, user.username, user_id=user.id, ip=get_client_ip(request)
        )
        await audit.success("login", "auth", details={"method": "oidc"})
        jwt_token = auth_service.create_session_token(user)
        redirect = _oidc_redirect("/")
        set_auth_cookie(redirect, request, jwt_token)
        set_id_token_cookie(redirect, request, tokens["id_token"])
        return redirect
    except Exception as exc:
        _log_oidc_error("user provisioning", exc)
        audit = AuditLogger(db, username or "oidc", ip=get_client_ip(request))
        await audit.failure(
            "login", "auth", details={"detail": "OIDC user provisioning failed"}
        )
        return _oidc_redirect("/login?error=oidc_failed")


def _log_oidc_error(step: str, exc: Exception) -> None:
    import httpx as _httpx

    if isinstance(exc, _httpx.HTTPStatusError):
        logger.error(
            "OIDC %s failed — HTTP %s %s — body: %s",
            step,
            exc.response.status_code,
            exc.request.url,
            exc.response.text,
        )
    else:
        logger.exception("OIDC %s failed", step)

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cookies import clear_auth_cookie, set_auth_cookie
from app.database import get_db
from app.dependencies import (
    get_audit_logger,
    get_client_ip,
    get_current_user,
    user_from_session_cookie,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    OidcConfig,
    OidcLoginResponse,
    UserResponse,
)
from app.services import admin_service, auth_service
from app.services.audit_service import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")


async def _get_oidc_cfg(db: AsyncSession) -> dict | None:
    """Load OIDC config from DB; returns None if not configured or disabled."""
    db_cfg = await admin_service.get_oidc_settings(db)
    if db_cfg and db_cfg.enabled:
        return {
            "client_id": db_cfg.client_id,
            "client_secret": db_cfg.client_secret,
            "discovery_url": db_cfg.discovery_url,
            "redirect_uri": db_cfg.redirect_uri,
            "scopes": db_cfg.scopes,
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
    token = auth_service.create_access_token({"sub": user.username})
    set_auth_cookie(response, request, token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> None:
    # Logging out must always clear the cookie, even when the session has already
    # expired — hence the identity is resolved best-effort rather than required.
    user = await user_from_session_cookie(db, request)
    if user is not None:
        audit = AuditLogger(db, user.username, user.id, get_client_ip(request))
        await audit.success("logout", "auth")
    clear_auth_cookie(response)


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
    if len(payload.new_password) < 8:
        await audit.failure(
            "change_password",
            "user",
            current_user.username,
            {"detail": "New password must contain at least 8 characters"},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must contain at least 8 characters",
        )
    current_user.hashed_password = auth_service.hash_password(payload.new_password)
    db.add(current_user)
    await db.commit()
    await audit.success("change_password", "user", current_user.username)


@router.get("/oidc/login", response_model=OidcLoginResponse)
async def oidc_login(db: AsyncSession = Depends(get_db)) -> OidcLoginResponse:
    cfg = await _get_oidc_cfg(db)
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC not configured"
        )
    url = await auth_service.build_oidc_authorization_url(cfg)
    return OidcLoginResponse(authorization_url=url)


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
        auth_service.validate_and_consume_oidc_state(state)
    except ValueError:
        logger.warning(
            "OIDC state validation failed (params: %s)", dict(request.query_params)
        )
        audit = AuditLogger(db, "oidc", ip=get_client_ip(request))
        await audit.failure("login", "auth", details={"detail": "Invalid OIDC state"})
        return RedirectResponse(url="/login?error=oidc_state_invalid")
    try:
        tokens = await auth_service.exchange_oidc_code(code, cfg)
    except Exception as exc:
        _log_oidc_error("token exchange", exc)
        audit = AuditLogger(db, "oidc", ip=get_client_ip(request))
        await audit.failure(
            "login", "auth", details={"detail": "OIDC token exchange failed"}
        )
        return RedirectResponse(url="/login?error=oidc_failed")
    try:
        userinfo = await auth_service.get_oidc_userinfo(tokens["access_token"], cfg)
    except Exception as exc:
        _log_oidc_error("userinfo fetch", exc)
        audit = AuditLogger(db, "oidc", ip=get_client_ip(request))
        await audit.failure(
            "login", "auth", details={"detail": "OIDC userinfo fetch failed"}
        )
        return RedirectResponse(url="/login?error=oidc_failed")
    try:
        username: str = userinfo.get("preferred_username") or userinfo.get("sub", "")
        email: str | None = userinfo.get("email")
        user = await auth_service.get_or_create_oidc_user(
            db, username=username, email=email
        )
        audit = AuditLogger(
            db, user.username, user_id=user.id, ip=get_client_ip(request)
        )
        await audit.success("login", "auth", details={"method": "oidc"})
        jwt_token = auth_service.create_access_token({"sub": user.username})
        redirect = RedirectResponse(url="/")
        set_auth_cookie(redirect, request, jwt_token)
        return redirect
    except Exception as exc:
        _log_oidc_error("user provisioning", exc)
        audit = AuditLogger(db, username or "oidc", ip=get_client_ip(request))
        await audit.failure(
            "login", "auth", details={"detail": "OIDC user provisioning failed"}
        )
        return RedirectResponse(url="/login?error=oidc_failed")


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

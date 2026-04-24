from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    OidcConfig,
    OidcLoginResponse,
    TokenResponse,
    UserResponse,
)
from app.services import admin_service, audit_service, auth_service

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


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    ip = request.client.host if request.client else None
    db_cfg = await admin_service.get_oidc_settings(db)
    local_disabled = db_cfg.local_login_disabled if db_cfg else False
    if local_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local connection is disabled. Use SSO.",
        )
    user = await auth_service.authenticate_user(db, payload.username, payload.password)
    if not user:
        await audit_service.log_action(
            db,
            username=payload.username,
            action="login",
            resource_type="auth",
            ip_address=ip,
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
        )
    await audit_service.log_action(
        db,
        username=user.username,
        user_id=user.id,
        action="login",
        resource_type="auth",
        ip_address=ip,
    )
    token = auth_service.create_access_token({"sub": user.username})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,  # type: ignore[arg-type]
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_oidc=current_user.is_oidc,
        is_admin=current_user.is_admin,
    )


@router.put("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    if current_user.is_oidc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO users cannot change their password",
        )
    if not current_user.hashed_password or not auth_service.verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must contain at least 8 characters",
        )
    current_user.hashed_password = auth_service.hash_password(payload.new_password)
    db.add(current_user)
    await db.commit()
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="change_password",
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=ip,
    )


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
    code: str, state: str, db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    cfg = await _get_oidc_cfg(db)
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC not configured"
        )
    try:
        tokens = await auth_service.exchange_oidc_code(code, state, cfg)
        userinfo = await auth_service.get_oidc_userinfo(tokens["access_token"], cfg)
        username: str = userinfo.get("preferred_username") or userinfo.get("sub", "")
        email: str | None = userinfo.get("email")
        user = await auth_service.get_or_create_oidc_user(
            db, username=username, email=email
        )
        jwt_token = auth_service.create_access_token({"sub": user.username})
        return RedirectResponse(url=f"/?token={jwt_token}")
    except Exception as exc:
        return RedirectResponse(url=f"/login?error=oidc_failed&detail={exc!s}")

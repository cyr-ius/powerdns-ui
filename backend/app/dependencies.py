from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_ip import get_client_ip
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services import acme_service, auth_service
from app.services.audit_service import AuditLogger

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Personal access token (PAT) issued from the user profile",
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="PersonalAccessToken",
    description="Personal access token (PAT) sent as 'Authorization: Bearer <token>'",
)


async def _user_from_pat(db: AsyncSession, token: str) -> User | None:
    key = await acme_service.verify_key(db, token)
    if key is None or key.key_type != "api":
        return None
    user = await db.get(User, key.user_id)
    return user if user is not None and user.is_active else None


def require_api_keys_enabled() -> None:
    """Guard for the PAT management endpoints when API_KEYS_ENABLED=false."""
    if not settings.api_keys_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Personal access tokens are disabled",
        )


async def user_from_session_cookie(db: AsyncSession, request: Request) -> User | None:
    """Resolve the browser session, or None when it is missing/expired/invalid.

    Browser sessions carry the JWT in the HttpOnly auth cookie set at login. It
    is never exposed to JavaScript, so there is no header-based variant.
    """
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        return None
    username: str | None = payload.get("sub")
    if username is None:
        return None
    user = await auth_service.get_user_by_username(db, username)
    return user if user is not None and user.is_active else None


async def get_current_user(
    request: Request,
    x_api_key: str | None = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )

    user = await user_from_session_cookie(db, request)
    if user is not None:
        return user

    # Fall back to a personal access token, accepted either as an
    # "Authorization: Bearer <token>" header or the legacy X-API-Key header.
    if settings.api_keys_enabled:
        for token in (
            credentials.credentials if credentials else None,
            x_api_key,
        ):
            if not token:
                continue
            user = await _user_from_pat(db, token)
            if user is not None:
                return user

    raise exc


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators",
        )
    return current_user


def get_audit_logger(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogger:
    return AuditLogger(
        db, current_user.username, current_user.id, get_client_ip(request)
    )

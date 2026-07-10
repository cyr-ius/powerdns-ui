from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
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
    description="Use API key issued by an administrator",
)


async def get_current_user(
    request: Request,
    x_api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )

    # Browser sessions carry the JWT in the HttpOnly auth cookie set at login.
    # It is never exposed to JavaScript, so there is no header-based variant.
    token = request.cookies.get(settings.auth_cookie_name)
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
            username: str | None = payload.get("sub")
            if username is not None:
                user = await auth_service.get_user_by_username(db, username)
                if user is not None and user.is_active:
                    return user
        except JWTError:
            pass

    # Fall back to API key (X-API-Key header, key_type must be "api")
    if x_api_key:
        key = await acme_service.verify_key(db, x_api_key)
        if key is not None and key.key_type == "api":
            user = await db.get(User, key.user_id)
            if user is not None and user.is_active:
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

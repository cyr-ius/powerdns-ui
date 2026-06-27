from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services import acme_service, admin_service, auth_service
from app.services.audit_service import AuditLogger

bearer_scheme = HTTPBearer(
    auto_error=False, description="JWT Bearer token in Authorization header"
)
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Use API key issued by an administrator",
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Accept the JWT from the Authorization header (API clients) or from the
    # HttpOnly auth cookie (browser sessions, set at login).
    token = (
        credentials.credentials
        if credentials
        else request.cookies.get(settings.auth_cookie_name)
    )
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


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def get_audit_logger(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogger:
    return AuditLogger(
        db, current_user.username, current_user.id, get_client_ip(request)
    )


async def get_acme_creator(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Allow super admins and account-level admins to create ACME keys."""
    if current_user.is_admin:
        return current_user
    if await admin_service.user_is_account_admin(db, current_user.id):  # type: ignore[arg-type]
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Account admin or super admin required to create ACME keys",
    )

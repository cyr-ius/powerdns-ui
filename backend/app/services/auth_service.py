import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import bcrypt
import httpx
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.models.user import User

_oidc_discovery_cache: dict | None = None


def clear_oidc_cache() -> None:
    global _oidc_discovery_cache
    _oidc_discovery_cache = None


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)  # type: ignore[no-any-return]


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.exec(select(User).where(User.username == username))  # type: ignore[call-overload]
    return result.first()


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    user = await get_user_by_username(db, username)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    password: str | None = None,
    email: str | None = None,
    is_oidc: bool = False,
    is_admin: bool = False,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password) if password else None,
        is_oidc=is_oidc,
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class OidcAccountConflictError(Exception):
    """Raised when an OIDC identity collides with an existing local account."""


async def get_or_create_oidc_user(
    db: AsyncSession, username: str, email: str | None
) -> User:
    user = await get_user_by_username(db, username)
    if user is not None:
        # The OIDC `username` (preferred_username/sub) is attacker-influenceable
        # at many IdPs and is not a trustworthy unique identifier. Refuse to log
        # in as an existing *local* account (e.g. the built-in 'admin'); only
        # accept a match against an account that was itself created via OIDC.
        if not user.is_oidc:
            raise OidcAccountConflictError(
                f"Username '{username}' is already used by a local account"
            )
        return user
    return await create_user(db, username=username, email=email, is_oidc=True)


def _oidc_cfg(override: dict | None) -> dict:
    return override or {}


async def _get_oidc_discovery(cfg: dict) -> dict:
    global _oidc_discovery_cache
    if _oidc_discovery_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(cfg["discovery_url"])
            resp.raise_for_status()
            _oidc_discovery_cache = resp.json()
    result: dict = _oidc_discovery_cache  # type: ignore[assignment]
    return result


def _generate_oidc_state() -> str:
    """Generate a short-lived signed JWT used as OIDC state parameter.

    Stateless: survives app restarts and works across multiple workers.
    """
    expire = datetime.now(UTC) + timedelta(minutes=10)
    return jwt.encode(
        {"sub": "oidc_state", "exp": expire, "nonce": secrets.token_urlsafe(16)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def validate_and_consume_oidc_state(state: str) -> None:
    """Verify the state JWT was signed by this server and has not expired."""
    try:
        payload = jwt.decode(
            state, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("sub") != "oidc_state":
            raise ValueError("Invalid OIDC state subject")
    except JWTError as exc:
        raise ValueError("Invalid or expired OIDC state") from exc


async def build_oidc_authorization_url(cfg_override: dict | None = None) -> str:
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    auth_endpoint = discovery["authorization_endpoint"]
    state = _generate_oidc_state()
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": cfg["scopes"],
        "state": state,
    }
    return f"{auth_endpoint}?{urlencode(params)}"


async def build_oidc_logout_url(
    id_token: str | None, cfg_override: dict | None = None
) -> str | None:
    """Return the provider's RP-initiated logout URL, or None if unavailable.

    The ``id_token_hint`` lets the provider know which session to terminate;
    without it (cookie lost/expired) most providers reject the request, so we
    only build the URL when we still hold the token.
    """
    cfg = _oidc_cfg(cfg_override)
    if not id_token:
        return None
    try:
        discovery = await _get_oidc_discovery(cfg)
    except httpx.HTTPError:
        return None
    end_session_endpoint = discovery.get("end_session_endpoint")
    if not end_session_endpoint:
        return None
    params = {"id_token_hint": id_token, "client_id": cfg["client_id"]}
    if cfg.get("post_logout_redirect_uri"):
        params["post_logout_redirect_uri"] = cfg["post_logout_redirect_uri"]
    return f"{end_session_endpoint}?{urlencode(params)}"


async def exchange_oidc_code(code: str, cfg_override: dict | None = None) -> dict:
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    token_endpoint = discovery["token_endpoint"]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
            },
            auth=(cfg["client_id"], cfg["client_secret"]),
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def get_oidc_userinfo(
    access_token: str, cfg_override: dict | None = None
) -> dict:
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    userinfo_endpoint = discovery["userinfo_endpoint"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

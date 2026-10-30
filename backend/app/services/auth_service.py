import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import bcrypt
import httpx
import jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.models.user import User

_oidc_discovery_cache: dict[str, Any] | None = None
_oidc_jwks_cache: jwt.PyJWKSet | None = None

# Asymmetric algorithms only: a provider's public JWKS can't verify an HMAC.
OIDC_ID_TOKEN_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512"]
OIDC_ID_TOKEN_ALGORITHMS += ["ES256", "ES384", "ES512", "EdDSA"]
# Outgoing calls to the identity provider never hang a worker.
OIDC_HTTP_TIMEOUT = 10.0
OIDC_FLOW_TTL = timedelta(minutes=10)


def clear_oidc_cache() -> None:
    global _oidc_discovery_cache, _oidc_jwks_cache
    _oidc_discovery_cache = None
    _oidc_jwks_cache = None


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_session_token(user: User) -> str:
    """Issue the session JWT of a user, bound to its current token version."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user.username,
        "uid": user.id,
        "ver": user.token_version,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def revoke_sessions(user: User) -> None:
    """Invalidate every session JWT already issued to the user.

    The caller adds the user to the session and commits.
    """
    user.token_version += 1


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.exec(select(User).where(User.username == username))
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
    db: AsyncSession,
    issuer: str,
    subject: str,
    username: str,
    email: str | None,
) -> User:
    """Return the account of an OIDC identity, creating it on first login.

    The identity is the (issuer, subject) pair: preferred_username can change or
    be reassigned at many providers, so it only names a new account.
    """
    result = await db.exec(
        select(User).where(User.oidc_issuer == issuer, User.oidc_subject == subject)
    )
    user = result.first()
    if user is not None:
        return user
    user = await get_user_by_username(db, username)
    if user is not None:
        # Accounts created before the identity was recorded are linked once, on
        # their next login. A local account (e.g. the built-in 'admin') or an
        # account already bound to another identity is never taken over.
        if not user.is_oidc or user.oidc_subject is not None:
            raise OidcAccountConflictError(
                f"Username '{username}' is already used by another account"
            )
        user.oidc_issuer = issuer
        user.oidc_subject = subject
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    user = User(
        username=username,
        email=email,
        is_oidc=True,
        oidc_issuer=issuer,
        oidc_subject=subject,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _oidc_cfg(override: dict[str, Any] | None) -> dict[str, Any]:
    return override or {}


async def _get_oidc_discovery(cfg: dict[str, Any]) -> dict[str, Any]:
    global _oidc_discovery_cache
    if _oidc_discovery_cache is None:
        async with httpx.AsyncClient(timeout=OIDC_HTTP_TIMEOUT) as client:
            resp = await client.get(cfg["discovery_url"])
            resp.raise_for_status()
            _oidc_discovery_cache = resp.json()
    return _oidc_discovery_cache


def _pkce_challenge(verifier: str) -> str:
    """Return the S256 PKCE code challenge of a code verifier (RFC 7636)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


async def start_oidc_flow(
    cfg_override: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Build the authorization URL and the signed flow token of a new login.

    The flow token holds the state, the nonce and the PKCE code verifier. It is
    kept in an HttpOnly cookie of the browser that started the login, so the
    callback is only accepted in that browser (no login CSRF), and it is signed
    so it survives restarts and works across workers.
    """
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    flow_token = jwt.encode(
        {
            "sub": "oidc_flow",
            "state": state,
            "nonce": nonce,
            "cv": code_verifier,
            "exp": datetime.now(UTC) + OIDC_FLOW_TTL,
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": cfg["scopes"],
        "state": state,
        "nonce": nonce,
        "code_challenge": _pkce_challenge(code_verifier),
        "code_challenge_method": "S256",
    }
    return f"{discovery['authorization_endpoint']}?{urlencode(params)}", flow_token


def validate_oidc_flow(flow_token: str | None, state: str) -> tuple[str, str]:
    """Check the callback state against the browser's flow token.

    Returns the expected nonce and the PKCE code verifier.
    """
    if not flow_token:
        raise ValueError("Missing OIDC flow cookie")
    try:
        payload = jwt.decode(
            flow_token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired OIDC flow cookie") from exc
    expected = payload.get("state")
    if (
        payload.get("sub") != "oidc_flow"
        or not isinstance(expected, str)
        or not hmac.compare_digest(expected.encode(), state.encode())
    ):
        raise ValueError("OIDC state mismatch")
    return payload["nonce"], payload["cv"]


async def _get_oidc_signing_key(discovery: dict[str, Any], kid: str | None) -> Any:
    """Return the provider's signing key of an id_token, from its JWKS.

    The JWKS is cached and fetched again once when the key is unknown, so a key
    rotation at the provider is picked up.
    """
    global _oidc_jwks_cache
    for refresh in (False, True):
        if refresh or _oidc_jwks_cache is None:
            async with httpx.AsyncClient(timeout=OIDC_HTTP_TIMEOUT) as client:
                resp = await client.get(discovery["jwks_uri"])
                resp.raise_for_status()
            _oidc_jwks_cache = jwt.PyJWKSet.from_dict(resp.json())
        for key in _oidc_jwks_cache.keys:
            if key.public_key_use != "enc" and (kid is None or key.key_id == kid):
                return key
    raise ValueError("Unknown OIDC signing key")


async def verify_oidc_id_token(
    id_token: str, nonce: str, cfg_override: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Verify the id_token signature and claims, and return the claims."""
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    try:
        header = jwt.get_unverified_header(id_token)
        key = await _get_oidc_signing_key(discovery, header.get("kid"))
        claims: dict[str, Any] = jwt.decode(
            id_token,
            key,
            algorithms=OIDC_ID_TOKEN_ALGORITHMS,
            audience=cfg["client_id"],
            issuer=discovery["issuer"],
            options={"require": ["iss", "sub", "aud", "exp", "iat"]},
        )
    except (jwt.PyJWTError, httpx.HTTPError) as exc:
        raise ValueError("Invalid OIDC id_token") from exc
    if isinstance(claims["aud"], list) and len(claims["aud"]) > 1:
        if claims.get("azp") != cfg["client_id"]:
            raise ValueError("Invalid OIDC id_token authorized party")
    token_nonce = claims.get("nonce")
    if not isinstance(token_nonce, str) or not hmac.compare_digest(
        token_nonce.encode(), nonce.encode()
    ):
        raise ValueError("OIDC nonce mismatch")
    return claims


async def build_oidc_logout_url(
    id_token: str | None, cfg_override: dict[str, Any] | None = None
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


async def exchange_oidc_code(
    code: str, code_verifier: str, cfg_override: dict[str, Any] | None = None
) -> dict[str, Any]:
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    token_endpoint = discovery["token_endpoint"]
    async with httpx.AsyncClient(timeout=OIDC_HTTP_TIMEOUT) as client:
        resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["redirect_uri"],
                "code_verifier": code_verifier,
            },
            auth=(cfg["client_id"], cfg["client_secret"]),
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


async def get_oidc_userinfo(
    access_token: str, cfg_override: dict[str, Any] | None = None
) -> dict[str, Any]:
    cfg = _oidc_cfg(cfg_override)
    discovery = await _get_oidc_discovery(cfg)
    userinfo_endpoint = discovery["userinfo_endpoint"]
    async with httpx.AsyncClient(timeout=OIDC_HTTP_TIMEOUT) as client:
        resp = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

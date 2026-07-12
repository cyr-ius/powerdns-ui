"""Helpers to carry the session JWT in an HttpOnly cookie.

Storing the token in an HttpOnly, SameSite=Lax cookie keeps it out of reach of
JavaScript (no `localStorage`), so an XSS flaw can no longer exfiltrate the
session token. SameSite=Lax still lets the cookie ride top-level navigations
(needed for the OIDC redirect) while blocking it on cross-site state-changing
requests, which mitigates CSRF for mutations.
"""

from fastapi import Request, Response

from app.config import settings


def _cookie_secure(request: Request) -> bool:
    """Set the ``Secure`` flag only when the request is actually over HTTPS.

    Honours ``X-Forwarded-Proto`` for TLS-terminating proxies so the cookie is
    marked secure in production, while staying usable on plain-HTTP local dev.
    """
    proto = request.headers.get("x-forwarded-proto")
    if proto:
        return proto.split(",")[0].strip().lower() == "https"
    return request.url.scheme == "https"


def set_auth_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        samesite="lax",
        path="/",
    )


def set_id_token_cookie(response: Response, request: Request, id_token: str) -> None:
    """Keep the OIDC id_token server-side only, to be replayed as id_token_hint.

    It is never read by JavaScript: the logout endpoint reads it back from the
    request and builds the provider's end_session URL itself.
    """
    response.set_cookie(
        key=settings.id_token_cookie_name,
        value=id_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        path="/",
    )


def clear_id_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.id_token_cookie_name,
        httponly=True,
        samesite="lax",
        path="/",
    )

import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.client_ip import get_client_ip
from app.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every HTTP response."""

    JSDELIVR = "https://cdn.jsdelivr.net/npm/"
    FONT_GOOGLE = "https://fonts.gstatic.com"
    GITHUB = "https://api.github.com"  # for GitHub API calls (avatars, etc.)

    # Build CSP once at class level — one directive per list entry, auditable.
    _CSP_DIRECTIVES: list[str] = [
        "default-src 'self'",
        f"script-src 'self' 'unsafe-inline' {JSDELIVR}",  # Angular requires unsafe-inline
        f"style-src 'self' 'unsafe-inline' {JSDELIVR}",  # Bootstrap inline styles
        "img-src 'self' data: https:",  # logos, QR codes base64
        f"font-src 'self' data: {FONT_GOOGLE}",  # Bootstrap Icons embedded font
        f"connect-src 'self' {GITHUB}",  # API calls + Azure endpoints
        "worker-src 'self'",  # Angular Service Worker (PWA)
        "frame-ancestors 'none'",  # replaces X-Frame-Options
    ]
    _CSP: str = "; ".join(_CSP_DIRECTIVES) + ";"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = self._CSP
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client-IP rate limiting with an in-memory sliding window.

    Every request is throttled by client IP (resolved through the trusted-proxy
    chain, so the real caller is used even behind a reverse proxy). A stricter
    window is additionally applied to the login endpoint to slow credential
    brute-forcing. Blocked requests are answered with 429 before reaching any
    route. Per-process only — front with a shared store (Redis) for multi-worker
    deployments.
    """

    def __init__(
        self,
        app,
        *,
        max_requests: int,
        window_seconds: int,
        login_max_attempts: int,
        login_window_seconds: int,
        login_path: str,
    ) -> None:
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._login_max_attempts = login_max_attempts
        self._login_window_seconds = login_window_seconds
        self._login_path = login_path
        # Sliding-window buckets keyed by "<scope>:<ip>"; global and login
        # limits live in the same store under distinct prefixes.
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        if not settings.trusted_proxies:
            logger.warning(
                "Rate limiting is enabled but no trusted_proxies are configured. "
                "Behind a reverse proxy every request will share the proxy IP as "
                "the key. Set TRUSTED_PROXIES so the real client IP is used."
            )

    def _check(self, key: str, max_hits: int, window: int) -> None:
        """Record a hit for ``key``; raise 429 once its window is full."""
        now = time.monotonic()
        hits = self._hits[key]
        cutoff = now - window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= max_hits:
            retry_after = int(window - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

    async def dispatch(self, request: Request, call_next) -> Response:
        ip = get_client_ip(request) or "unknown"
        try:
            self._check(f"ip:{ip}", self._max_requests, self._window_seconds)
            if request.method == "POST" and request.url.path == self._login_path:
                self._check(
                    f"login:{ip}",
                    self._login_max_attempts,
                    self._login_window_seconds,
                )
        except HTTPException as exc:
            return JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers=exc.headers,
            )
        return await call_next(request)

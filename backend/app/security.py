import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request, status
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


class _SlidingWindowLimiter:
    """In-memory sliding-window rate limiter keyed by an arbitrary string.

    Each key maps to a deque of monotonic timestamps. On every check the
    timestamps that have fallen out of the window are evicted and the hit is
    allowed only while the remaining count is below the limit. A throttled
    periodic sweep discards buckets that have gone idle so memory stays bounded
    as distinct client IPs churn.

    A ``threading.Lock`` guards the shared state: the check is fully synchronous
    (no ``await`` inside the critical section), so contention is negligible and
    the limiter stays correct even if the app is served with a threaded worker.
    """

    _CLEANUP_INTERVAL_S: float = 300.0

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._last_cleanup = 0.0
        # Largest window seen across checks; used as the eviction horizon so a
        # bucket is never dropped while any of its hits could still be live.
        self._max_window = 0.0

    def check(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """Record a hit for ``key`` and report whether it is allowed.

        Returns ``(allowed, retry_after)`` where ``retry_after`` is the whole
        number of seconds until the oldest recorded hit leaves the window (``0``
        when the request is allowed).
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            self._max_window = max(self._max_window, float(window_seconds))
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= max_requests:
                retry_after = int(hits[0] + window_seconds - now) + 1
                return False, max(retry_after, 1)
            hits.append(now)
            self._sweep(now)
            return True, 0

    def _sweep(self, now: float) -> None:
        """Drop idle buckets. Called under the lock, throttled to one scan per interval."""
        if now - self._last_cleanup < self._CLEANUP_INTERVAL_S:
            return
        self._last_cleanup = now
        boundary = now - self._max_window
        stale = [
            key for key, hits in self._hits.items() if not hits or hits[-1] <= boundary
        ]
        for key in stale:
            del self._hits[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client-IP rate limiting with an in-memory sliding window.

    Only ``/api/*`` routes are throttled (the SPA's static assets and the health
    probe are exempt so orchestration is never blocked). Every request is keyed
    by the real client IP (resolved through the trusted-proxy chain, so the real
    caller is used even behind a reverse proxy). A stricter, separate budget is
    applied to the login endpoint to slow credential brute-forcing. Blocked
    requests are answered with 429 before reaching any route. Per-process only —
    front with a shared store (Redis) for multi-worker deployments.
    """

    _EXEMPT_PATHS: frozenset[str] = frozenset({"/api/health"})

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
        self._limiter = _SlidingWindowLimiter()
        if not settings.trusted_proxies:
            logger.warning(
                "Rate limiting is enabled but no trusted_proxies are configured. "
                "Behind a reverse proxy every request will share the proxy IP as "
                "the key. Set TRUSTED_PROXIES so the real client IP is used."
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/api/") or path in self._EXEMPT_PATHS:
            return await call_next(request)

        ip = get_client_ip(request) or "unknown"
        bucket = "global"
        allowed, retry_after = self._limiter.check(
            f"ip:{ip}", self._max_requests, self._window_seconds
        )
        if allowed and request.method == "POST" and path == self._login_path:
            bucket = "login"
            allowed, retry_after = self._limiter.check(
                f"login:{ip}", self._login_max_attempts, self._login_window_seconds
            )

        if not allowed:
            logger.warning(
                "Rate limit exceeded: ip=%s path=%s bucket=%s", ip, path, bucket
            )
            return JSONResponse(
                {"detail": "Too many attempts. Please try again later."},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

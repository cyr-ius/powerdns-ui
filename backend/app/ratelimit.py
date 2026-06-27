"""Minimal in-memory rate limiter.

Dependency-free, single-process sliding window keyed by an arbitrary string
(typically the client IP). It is meant to slow down brute-force attempts on
authentication endpoints, not to be a distributed quota system: for a
multi-worker / multi-instance deployment, front it with a shared store.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, status


class InMemoryRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        """Record an attempt for ``key``; raise 429 once the window is full."""
        now = time.monotonic()
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.max_attempts:
            retry_after = int(self.window_seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        # Opportunistically drop fully-expired buckets to bound memory growth.
        if not hits:
            self._hits.pop(key, None)

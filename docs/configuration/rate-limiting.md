# Rate Limiting & Reverse Proxy

## In-memory rate limiter

The backend applies an **in-memory sliding-window rate limiter** to every `/api/*` route. The health probe `/api/health` is exempt so container orchestration (liveness/readiness checks) is never blocked.

Two independent budgets are enforced per client IP:

- a **global** budget — `RATE_LIMIT_MAX_REQUESTS` requests per `RATE_LIMIT_WINDOW_SECONDS`;
- a stricter **login** budget on `RATE_LIMIT_LOGIN_PATH` — `RATE_LIMIT_LOGIN_MAX_ATTEMPTS` attempts per `RATE_LIMIT_LOGIN_WINDOW_SECONDS`, to slow credential brute-forcing.

Throttled requests receive `429 Too Many Requests` with a `Retry-After` header before reaching any route handler. Idle IP buckets are swept periodically so memory usage stays bounded.

See [Environment Variables](environment-variables.md) for the full list of `RATE_LIMIT_*` settings, including how to disable the limiter entirely with `RATE_LIMIT_ENABLED=false`.

!!! warning "State is per-process"
    The limiter's state is **not shared** across workers or replicas — this is adequate for the single-container deployment PowerDNS UI targets. If you scale to multiple workers or replicas, front them with a shared store (e.g. Redis) or rely on rate limiting at the reverse proxy / load balancer level instead.

## Behind a reverse proxy

Set `TRUSTED_PROXIES` to the reverse proxy's IPs/CIDRs, e.g.:

```bash
TRUSTED_PROXIES=10.0.0.0/8,172.16.0.0/12
```

`X-Forwarded-For` is honoured **only** when the direct TCP peer matches one of these ranges; otherwise it is ignored, to prevent IP spoofing by clients that set the header themselves. When `TRUSTED_PROXIES` is left empty, all clients behind the proxy share the proxy's own IP as the rate-limit key — meaning they will all count against the same budget.

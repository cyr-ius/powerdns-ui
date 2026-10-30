# ─── Stage 1: Build Angular Frontend ──────────────────────────────────────
FROM node:26-alpine AS frontend-builder

WORKDIR /build/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Final container ─────────────────────────────────────────────
FROM python:3.14-alpine

LABEL maintainer="cyr-ius <https://github.com/cyr-ius>"
LABEL org.opencontainers.image.title="PowerDNS UI"
LABEL org.opencontainers.image.description="Powerdns UI - DNS management"
LABEL org.opencontainers.image.source="https://github.com/cyr-ius/powerdns-ui"
LABEL org.opencontainers.image.url="https://github.com/cyr-ius/powerdns-ui"
LABEL org.opencontainers.image.licenses="MIT"

RUN apk add --no-cache \
    curl \
    ca-certificates \
    su-exec \
    && addgroup -S -g 1000 powerdns-ui \
    && adduser -S -D -H -u 1000 -G powerdns-ui powerdns-ui

COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /usr/local/bin/uv

ENV UV_NO_CACHE=true
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PYTHONUNBUFFERED=1
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"
ENV PYTHONPATH=/app/backend

WORKDIR /app

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

COPY --from=frontend-builder /build/frontend/dist/frontend/browser ./frontend

COPY backend ./backend

# PowerDNS MySQL schema, pinned to a release tag and checked by its digest so
# the build is reproducible. Keep it in line with the pdns image of the compose:
# a new tag needs its new digest.
ADD --checksum=sha256:fb4a8408d69c7d25c7bd491cdcc620d6b5195a32e00ca544e0be6fdca53382a4 --chmod=644 \
    https://raw.githubusercontent.com/PowerDNS/pdns/auth-5.1.5/modules/gmysqlbackend/schema.mysql.sql \
    /var/lib/powerdns/schema.sql

RUN chmod 755 /var/lib/powerdns \
    && mkdir -p /var/lib/powerdns-ui \
    && chown powerdns-ui:powerdns-ui /var/lib/powerdns-ui

ARG VERSION
ENV APP_VERSION=${VERSION:-"1.0.0"}

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

VOLUME [ "/var/lib/powerdns-ui" ]

EXPOSE 8080/tcp

# One worker by default: the rate limiter and the OIDC caches live in the
# memory of each process. Uvicorn reads WEB_CONCURRENCY as its worker count.
ENV WEB_CONCURRENCY=1

# Starts as root only to hand an existing data volume over to powerdns-ui,
# then runs the command as powerdns-ui (see docker/entrypoint.sh).
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]

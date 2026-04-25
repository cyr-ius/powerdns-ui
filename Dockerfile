# ─── Stage 1: Build Angular Frontend ──────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend

# Install dependencies
COPY frontend/package.json ./
RUN npm install

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Final container ─────────────────────────────────────────────
FROM python:3.14-alpine

LABEL maintainer="cyr-ius <https://github.com/cyr-ius>"
LABEL org.opencontainers.image.title="PowerDNS UI"
LABEL org.opencontainers.image.description="Powerdns UI - DNS management"
LABEL org.opencontainers.image.source="https://github.com/cyr-ius/pdns-ui"
LABEL org.opencontainers.image.url="https://github.com/cyr-ius/pdns-ui"
LABEL org.opencontainers.image.licenses="MIT"

RUN apk add --no-cache \
    curl \
    supervisor \
    ca-certificates

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_NO_CACHE=true
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PYTHONUNBUFFERED=1
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"
ENV PYTHONPATH=/app/backend

WORKDIR /app

RUN --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    uv sync --frozen --no-dev

COPY --from=frontend-builder /build/frontend/dist/frontend/browser ./frontend

COPY backend ./backend

RUN mkdir -p /var/lib/powerdns \
    && curl -o /var/lib/powerdns/schema.sql https://raw.githubusercontent.com/PowerDNS/pdns/refs/heads/master/modules/gmysqlbackend/schema.mysql.sql

ARG VERSION
ENV APP_VERSION=${VERSION:-"1.0.0"}

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

VOLUME [ "/var/lib/powerdns-ui" ]

EXPOSE 8080/tcp

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]

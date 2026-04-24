# ─── FastAPI + Angular Development Image ─────────────────────────────────────────────

FROM mcr.microsoft.com/devcontainers/base:alpine

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── System dependencies (apk = gestionnaire Alpine) ────────────────────────
RUN apk add --no-cache \
    curl \
    git \
    python3 \
    nodejs \
    npm

# ── Installation de uv (gestionnaire Python ultra-rapide) ──────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Configurer uv pour installer dans le système (pas de venv par défaut)
ENV UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Angular CLI 21 + outils globaux ────────────────────────────────────────
ENV NG_CLI_ANALYTICS=ci \
    NG_FORCE_TTY=false

RUN npm install -g \
    @angular/cli@21 \
    prettier@3

USER vscode

# ── Dépendances Python via uv ───────────────────────────────────────────────
RUN uv tool install ruff \
    && uv tool install prek \
    && uv tool install alembic

# ── Default shell to bash instead of sh ─────────
ENV SHELL=/bin/bash

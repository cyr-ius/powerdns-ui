"""
Powerdns UI - FastAPI Backend
Copyright (C) 2021-2024  Cyr-ius (github.com/cyr-ius)
"""

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import async_session, init_db
from app.routers import (
    acme,
    acme_keys,
    admin,
    audit,
    auth,
    autoprimaries,
    catalogues,
    health,
    networks,
    pdns,
    server,
    tsigkeys,
    views,
)
from app.routers.acme import router_api as acme_api_router
from app.security import SecurityHeadersMiddleware
from app.services.auth_service import create_user, get_user_by_username
from app.utils import resolve_safe_path

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    async with async_session() as db:
        admin_user = await get_user_by_username(db, settings.admin_username)
        if not admin_user:
            # The admin password can no longer be supplied via configuration:
            # always generate a one-time random secret and surface it in the
            # logs so the operator can log in and change it after first login.
            password = secrets.token_urlsafe(16)
            logger.warning(
                "Generated a one-time random password for the initial '%s' "
                "account: %s — change it after first login.",
                settings.admin_username,
                password,
            )
            await create_user(
                db,
                username=settings.admin_username,
                password=password,
                is_admin=True,
            )
            logger.info("Utilisateur admin créé : %s", settings.admin_username)
        elif not admin_user.is_admin:
            admin_user.is_admin = True
            db.add(admin_user)
            await db.commit()
            logger.info(
                "Admin account promoted to super administrator : %s",
                settings.admin_username,
            )
    yield


app = FastAPI(
    title="PowerDNS UI",
    description="REST API for PowerDNS management",
    lifespan=lifespan,
    version=settings.app_version,
    openapi_url="/api/openapi.json" if settings.swagger_enabled else None,
    docs_url=None,
    redoc_url=None,
)

# ── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── API routers ───────────────────────────────────────────────────────────────
app.include_router(acme.router)
app.include_router(acme_api_router)
app.include_router(acme_keys.router)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(audit.router)
app.include_router(pdns.router)
app.include_router(catalogues.router)
app.include_router(tsigkeys.router)
app.include_router(server.router)
app.include_router(autoprimaries.router)
app.include_router(networks.router)
app.include_router(views.router)

# ── Self-hosted static assets (Swagger UI, no Internet dependency) ─────────────
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/api/static", StaticFiles(directory=static_dir), name="static")


@app.get("/api/docs", include_in_schema=False)
async def swagger_ui():
    if not settings.swagger_enabled:
        raise HTTPException(status_code=404, detail="Not Found")
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="Portalcrane API",
        swagger_js_url="/api/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/api/static/swagger/swagger-ui.css",
        swagger_favicon_url="/favicon.ico",
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "healthy", "app": "Powerdns UI", "version": settings.app_version}


# ── Serve Angular SPA (must be last) ─────────────────────────────────────────
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str) -> FileResponse:
    """
    Serve Angular static files with path traversal protection.

    Requests for existing static assets (JS, CSS, images) are served directly.
    All other paths fall back to index.html to support client-side SPA routing.
    Unknown or unsafe paths also fall back to index.html rather than 404-ing,
    letting the Angular router handle the error page.
    """

    # Resolve once at module load — avoids repeated filesystem calls per request.
    project_root = Path(__file__).resolve().parents[2]
    frontend_dist = (project_root / "frontend").resolve()
    frontend_index = frontend_dist / "index.html"

    if not frontend_index.is_file():
        logger.error("SPA index.html not found at %s", frontend_index)
        raise HTTPException(status_code=503, detail="Frontend not available.")

    safe = resolve_safe_path(full_path, frontend_dist)
    if safe is not None:
        return FileResponse(safe)

    # SPA fallback: Angular router handles unknown client-side routes.
    return FileResponse(frontend_index)

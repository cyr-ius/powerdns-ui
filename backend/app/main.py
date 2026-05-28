"""
Powerdns UI - FastAPI Backend
Copyright (C) 2021-2024  Cyr-ius (github.com/cyr-ius)
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

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

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    async with async_session() as db:
        admin_user = await get_user_by_username(db, settings.admin_username)
        if not admin_user:
            await create_user(
                db,
                username=settings.admin_username,
                password=settings.admin_password,
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
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
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

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_user
from app.models.user import User
from app.schemas.pdns import (
    CacheFlushResult,
    ConfigSetting,
    SearchResult,
    ServerInfo,
    StatisticItem,
)
from app.services import admin_service
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])

_SERVER = "/servers/localhost"


def _pdns_error(exc: httpx.HTTPStatusError) -> HTTPException:
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


# ── Accounts ─────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[str])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    if current_user.is_admin:
        accounts = await admin_service.list_accounts(db)
        return [a["name"] for a in accounts]
    return await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]


# ── Server info ───────────────────────────────────────────────────────────────


@router.get("/server", response_model=ServerInfo)
async def get_server_info() -> dict:
    try:
        return await pdns_request("GET", _SERVER)
    except httpx.HTTPStatusError as exc:
        raise _pdns_error(exc) from exc


# ── Config ────────────────────────────────────────────────────────────────────


@router.get("/config", response_model=list[ConfigSetting])
async def get_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> list:
    if not current_user.is_admin:
        await audit.failure(
            "read",
            "server_config",
            details={"detail": "Access restricted to administrators"},
        )
        raise HTTPException(
            status_code=403, detail="Access restricted to administrators"
        )
    try:
        return await pdns_request("GET", f"{_SERVER}/config")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error(exc) from exc


# ── Search ────────────────────────────────────────────────────────────────────


@router.get("/search", response_model=list[SearchResult])
async def search_data(
    q: Annotated[
        str, Query(min_length=1, description="Search term (supports * and ?)")
    ],
    max: Annotated[int, Query(ge=1, le=500)] = 100,
    object_type: Annotated[
        str | None, Query(description="Filter: all | zone | record | comment")
    ] = "all",
) -> list:
    params: dict = {"q": q, "max": max}
    if object_type and object_type != "all":
        params["object_type"] = object_type
    try:
        return await pdns_request("GET", f"{_SERVER}/search-data", params=params)
    except httpx.HTTPStatusError as exc:
        raise _pdns_error(exc) from exc


# ── Statistics ────────────────────────────────────────────────────────────────


@router.get("/statistics", response_model=list[StatisticItem])
async def get_statistics(
    statistic: Annotated[
        str | None,
        Query(
            description="Specific statistic name (e.g. 'recursor') or leave empty for all"
        ),
    ] = None,
    includerings: Annotated[bool, Query(description="Include Ring items")] = False,
) -> list:
    params: dict = {"includerings": str(includerings).lower()}
    if statistic:
        params["statistic"] = statistic
    try:
        return await pdns_request("GET", f"{_SERVER}/statistics", params=params)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            raise HTTPException(
                status_code=422, detail=f"Unknown statistic: {statistic}"
            ) from exc
        raise _pdns_error(exc) from exc


# ── Cache ─────────────────────────────────────────────────────────────────────


@router.put("/cache/flush", response_model=CacheFlushResult)
async def flush_cache(
    domain: Annotated[
        str, Query(min_length=1, description="Domain name to flush from cache")
    ],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    try:
        result = await pdns_request(
            "PUT", f"{_SERVER}/cache/flush", params={"domain": domain}
        )
        await audit.success("flush_cache", "server", domain)
        return result
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error(exc)
        await audit.failure(
            "flush_cache", "server", domain, {"detail": http_exc.detail}
        )
        raise http_exc from exc

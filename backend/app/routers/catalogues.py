import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_user
from app.models.user import User
from app.schemas.pdns import Zone, ZoneCreate, ZoneDetail
from app.services import admin_service
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api/catalogues")

_SERVER = "/servers/localhost"


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Resource not found")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


async def _get_catalog_zone(zone_id: str) -> dict:
    try:
        zone: dict = await pdns_request("GET", f"{_SERVER}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    if zone.get("kind") != "Producer":
        raise HTTPException(status_code=404, detail="Zone catalogue not found")
    return zone


# ── Catalogues ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[Zone])
async def list_catalogues(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    zones: list = await pdns_request("GET", f"{_SERVER}/zones")
    catalogs = [z for z in zones if z.get("kind") == "Producer"]
    if current_user.is_admin:
        return catalogs
    user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
    return [z for z in catalogs if (z.get("account") or "") in user_accounts]


@router.post("", response_model=ZoneDetail, status_code=201)
async def create_catalogue(
    payload: ZoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if not payload.account or payload.account not in user_accounts:
            await audit.failure(
                "create",
                "catalogue",
                payload.name,
                {
                    "detail": "You must specify an account to which you belong to create a catalogue"
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must specify an account to which you belong to create a catalogue",
            )
    data = payload.model_dump(exclude_none=True)
    data["kind"] = "Producer"
    if not data["name"].endswith("."):
        data["name"] += "."
    try:
        result = await pdns_request("POST", f"{_SERVER}/zones", json=data)
        await audit.success("create", "catalogue", data["name"])
        return result
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit.failure(
            "create", "catalogue", data["name"], {"detail": http_exc.detail}
        )
        raise http_exc from exc


@router.delete("/{zone_id}", status_code=204)
async def delete_catalogue(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    zone = await _get_catalog_zone(zone_id)
    if not current_user.is_admin:
        account = zone.get("account") or ""
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if account not in user_accounts:
            await audit.failure(
                "delete", "catalogue", zone_id, {"detail": "Access denied"}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    try:
        await pdns_request("DELETE", f"{_SERVER}/zones/{zone_id}")
        await audit.success("delete", "catalogue", zone_id)
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit.failure("delete", "catalogue", zone_id, {"detail": http_exc.detail})
        raise http_exc from exc


# ── Members ───────────────────────────────────────────────────────────────────


@router.get("/{zone_id}/members", response_model=list[Zone])
async def list_members(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    catalog = await _get_catalog_zone(zone_id)
    catalog_name: str = catalog["name"]
    zones: list = await pdns_request("GET", f"{_SERVER}/zones")
    members = [z for z in zones if z.get("catalog") == catalog_name]
    if current_user.is_admin:
        return members
    user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
    return [z for z in members if (z.get("account") or "") in user_accounts]


@router.post("/{zone_id}/members/{member_zone_id}", status_code=204)
async def add_member(
    zone_id: str,
    member_zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    catalog = await _get_catalog_zone(zone_id)
    try:
        member: dict = await pdns_request("GET", f"{_SERVER}/zones/{member_zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if (member.get("account") or "") not in user_accounts:
            await audit.failure(
                "add_member",
                "catalogue",
                zone_id,
                {"member": member_zone_id, "detail": "Access denied"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    try:
        await pdns_request(
            "PUT",
            f"{_SERVER}/zones/{member_zone_id}",
            json={
                "name": member["name"],
                "kind": member["kind"],
                "account": member.get("account") or "",
                "masters": member.get("masters") or [],
                "catalog": catalog["name"],
            },
        )
        await audit.success(
            "add_member", "catalogue", zone_id, {"member": member_zone_id}
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit.failure(
            "add_member",
            "catalogue",
            zone_id,
            {"member": member_zone_id, "detail": http_exc.detail},
        )
        raise http_exc from exc


@router.delete("/{zone_id}/members/{member_zone_id}", status_code=204)
async def remove_member(
    zone_id: str,
    member_zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    await _get_catalog_zone(zone_id)
    try:
        member: dict = await pdns_request("GET", f"{_SERVER}/zones/{member_zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if (member.get("account") or "") not in user_accounts:
            await audit.failure(
                "remove_member",
                "catalogue",
                zone_id,
                {"member": member_zone_id, "detail": "Access denied"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    try:
        await pdns_request(
            "PUT",
            f"{_SERVER}/zones/{member_zone_id}",
            json={
                "name": member["name"],
                "kind": member["kind"],
                "account": member.get("account") or "",
                "masters": member.get("masters") or [],
                "catalog": "",
            },
        )
        await audit.success(
            "remove_member", "catalogue", zone_id, {"member": member_zone_id}
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit.failure(
            "remove_member",
            "catalogue",
            zone_id,
            {"member": member_zone_id, "detail": http_exc.detail},
        )
        raise http_exc from exc


# ── Consumers ─────────────────────────────────────────────────────────────────


async def _get_consumer_zone(zone_id: str) -> dict:
    try:
        zone: dict = await pdns_request("GET", f"{_SERVER}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    if zone.get("kind") != "Consumer":
        raise HTTPException(status_code=404, detail="Consumer catalog zone not found")
    return zone


@router.get("/consumers", response_model=list[Zone])
async def list_consumers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    zones: list = await pdns_request("GET", f"{_SERVER}/zones")
    consumers = [z for z in zones if z.get("kind") == "Consumer"]
    if current_user.is_admin:
        return consumers
    user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
    return [z for z in consumers if (z.get("account") or "") in user_accounts]


@router.post("/consumers", response_model=ZoneDetail, status_code=201)
async def create_consumer(
    payload: ZoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if not payload.account or payload.account not in user_accounts:
            await audit.failure(
                "create",
                "consumer",
                payload.name,
                {
                    "detail": "You must specify an account to which you belong to create a consumer"
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must specify an account to which you belong to create a consumer",
            )
    if not payload.masters:
        await audit.failure(
            "create",
            "consumer",
            payload.name,
            {
                "detail": "At least one master server is required for a Consumer catalog zone"
            },
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one master server is required for a Consumer catalog zone",
        )
    data = payload.model_dump(exclude_none=True)
    data["kind"] = "Consumer"
    data.pop("nameservers", None)
    if not data["name"].endswith("."):
        data["name"] += "."
    try:
        result = await pdns_request("POST", f"{_SERVER}/zones", json=data)
        await audit.success("create", "consumer", data["name"])
        return result
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit.failure(
            "create", "consumer", data["name"], {"detail": http_exc.detail}
        )
        raise http_exc from exc


@router.delete("/consumers/{zone_id}", status_code=204)
async def delete_consumer(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    zone = await _get_consumer_zone(zone_id)
    if not current_user.is_admin:
        account = zone.get("account") or ""
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if account not in user_accounts:
            await audit.failure(
                "delete", "consumer", zone_id, {"detail": "Access denied"}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
    try:
        await pdns_request("DELETE", f"{_SERVER}/zones/{zone_id}")
        await audit.success("delete", "consumer", zone_id)
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit.failure("delete", "consumer", zone_id, {"detail": http_exc.detail})
        raise http_exc from exc


@router.get("/consumers/{zone_id}/members", response_model=list[Zone])
async def list_consumer_members(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    consumer = await _get_consumer_zone(zone_id)
    consumer_name: str = consumer["name"]
    zones: list = await pdns_request("GET", f"{_SERVER}/zones")
    members = [z for z in zones if z.get("catalog") == consumer_name]
    if current_user.is_admin:
        return members
    user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
    return [z for z in members if (z.get("account") or "") in user_accounts]

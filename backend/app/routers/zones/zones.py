"""Zone CRUD, records and allowed record types."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_user
from app.models.record_type import RecordType
from app.models.user import User
from app.models.zone_record_type import ZoneRecordType
from app.routers.zones.access import (
    ROLE_LEVELS,
    SERVER,
    ZoneAccess,
    pdns_error_handler,
    zone_access,
)
from app.schemas.admin import (
    UserBasicResponse,
    ZoneRecordTypesResponse,
    ZoneRecordTypesUpdate,
)
from app.schemas.pdns import PatchRRsets, Zone, ZoneCreate, ZoneDetail, ZoneUpdate
from app.services import admin_service
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request

router = APIRouter()


# ── Users (basic, for zone member management) ─────────────────────────────────
# Declared before the /{zone_id} routes, which would otherwise match "/users".


@router.get("/users", response_model=list[UserBasicResponse])
async def list_users_basic(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Any]:
    return await admin_service.list_users_basic(db)


# ── Zones ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[Zone])
async def list_zones(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Any]:
    zones: list[Any] = await pdns_request("GET", f"{SERVER}/zones")
    if current_user.is_admin:
        return zones
    user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
    return [z for z in zones if (z.get("account") or "") in user_accounts]


@router.post("", response_model=ZoneDetail, status_code=201)
async def create_zone(
    payload: ZoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if not payload.account or payload.account not in user_accounts:
            await audit.failure(
                "create",
                "zone",
                payload.name,
                {"detail": "You must specify an account to which you belong"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must specify an account to which you belong",
            )
        # Non-admin creating a zone must be at least admin of that account
        ua = await admin_service.get_user_role_for_account(
            db,
            current_user.id,  # type: ignore[arg-type]
            payload.account,
        )
        if ua is None or ROLE_LEVELS.get(str(ua.role), -1) < ROLE_LEVELS["admin"]:
            await audit.failure(
                "create",
                "zone",
                payload.name,
                {"detail": "Only administrators of an account can create zones"},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators of an account can create zones",
            )
    data = payload.model_dump(exclude_none=True)
    if not data["name"].endswith("."):
        data["name"] += "."
    zone: dict[str, Any] = await pdns_request("POST", f"{SERVER}/zones", json=data)
    await audit.success("create", "zone", data["name"])
    return zone


@router.get("/{zone_id}", response_model=ZoneDetail)
async def get_zone(access: ZoneAccess = Depends(zone_access())) -> dict[str, Any]:
    return access.zone


@router.put("/{zone_id}", status_code=204)
async def update_zone(
    zone_id: str,
    payload: ZoneUpdate,
    current_user: User = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "update")),
) -> None:
    # Prevent non-global-admins from changing the account field. The check only
    # triggers when the account is explicitly provided (model_fields_set), so a
    # per-account admin saving other settings without touching `account` is not
    # wrongly rejected, while any explicit change — including to null — is denied.
    if (
        not current_user.is_admin
        and "account" in payload.model_fields_set
        and payload.account != access.zone.get("account")
    ):
        await audit.failure(
            "update",
            "zone",
            zone_id,
            {
                "detail": "Only a global administrator can modify "
                "the account associated with a zone"
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only a global administrator can modify "
                "the account associated with a zone"
            ),
        )
    try:
        await pdns_request(
            "PUT",
            f"{SERVER}/zones/{zone_id}",
            json=payload.model_dump(exclude_none=True),
        )
        await audit.success("update", "zone", zone_id)
    except httpx.HTTPStatusError as exc:
        http_exc = pdns_error_handler(exc)
        await audit.failure("update", "zone", zone_id, {"detail": http_exc.detail})
        raise http_exc from exc


@router.delete(
    "/{zone_id}",
    status_code=204,
    dependencies=[Depends(zone_access("admin", "delete"))],
)
async def delete_zone(
    zone_id: str,
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    try:
        await pdns_request("DELETE", f"{SERVER}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc
    await audit.success("delete", "zone", zone_id)


# ── Records ───────────────────────────────────────────────────────────────────


@router.patch(
    "/{zone_id}/rrsets",
    status_code=204,
    dependencies=[Depends(zone_access("manager", "update_records"))],
)
async def patch_rrsets(
    zone_id: str,
    payload: PatchRRsets,
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    try:
        await pdns_request(
            "PATCH", f"{SERVER}/zones/{zone_id}", json=payload.model_dump()
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc
    await audit.success("update_records", "zone", zone_id)


# ── Zone Record Types ─────────────────────────────────────────────────────────


@router.get(
    "/{zone_id}/record-types",
    response_model=ZoneRecordTypesResponse,
    dependencies=[Depends(zone_access("viewer"))],
)
async def get_zone_record_types(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
) -> ZoneRecordTypesResponse:
    zone_types = await db.exec(
        select(ZoneRecordType).where(ZoneRecordType.zone_id == zone_id)
    )
    rows = zone_types.all()
    if rows:
        return ZoneRecordTypesResponse(
            types=sorted(r.record_type_name for r in rows),
            is_custom=True,
        )
    global_types = await db.exec(
        select(RecordType).where(RecordType.enabled == True).order_by(RecordType.name)  # noqa: E712
    )
    return ZoneRecordTypesResponse(
        types=[rt.name for rt in global_types.all()],
        is_custom=False,
    )


@router.put(
    "/{zone_id}/record-types",
    response_model=ZoneRecordTypesResponse,
    dependencies=[Depends(zone_access("admin"))],
)
async def set_zone_record_types(
    zone_id: str,
    payload: ZoneRecordTypesUpdate,
    db: AsyncSession = Depends(get_db),
) -> ZoneRecordTypesResponse:
    existing = await db.exec(
        select(ZoneRecordType).where(ZoneRecordType.zone_id == zone_id)
    )
    for row in existing.all():
        await db.delete(row)
    if not payload.types:
        await db.commit()
        global_types = await db.exec(
            select(RecordType)
            .where(RecordType.enabled == True)  # noqa: E712
            .order_by(RecordType.name)
        )
        return ZoneRecordTypesResponse(
            types=[rt.name for rt in global_types.all()],
            is_custom=False,
        )
    for type_name in payload.types:
        db.add(ZoneRecordType(zone_id=zone_id, record_type_name=type_name.upper()))
    await db.commit()
    return ZoneRecordTypesResponse(
        types=sorted(t.upper() for t in payload.types), is_custom=True
    )

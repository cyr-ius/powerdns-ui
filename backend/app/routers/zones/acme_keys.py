"""ACME API keys bound to a zone, reserved to the zone administrators."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_user
from app.models.user import User
from app.routers.zones.access import ZoneAccess, zone_access
from app.schemas.acme import (
    AcmeApiKeyCreated,
    AcmeApiKeyResponse,
    AcmeApiKeyUpdate,
    AcmeApiKeyZoneCreate,
)
from app.services import acme_service
from app.services.audit_service import AuditLogger

router = APIRouter()


@router.get("/{zone_id}/acme-keys", response_model=list[AcmeApiKeyResponse])
async def list_zone_acme_keys(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    access: ZoneAccess = Depends(zone_access("admin")),
) -> list[dict[str, Any]]:
    keys = await acme_service.list_zone_keys(db, access.zone.get("name", zone_id))
    return [acme_service.key_to_response(k) for k in keys]


@router.post("/{zone_id}/acme-keys", response_model=AcmeApiKeyCreated, status_code=201)
async def create_zone_acme_key(
    zone_id: str,
    payload: AcmeApiKeyZoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "create_acme_key")),
) -> dict[str, Any]:
    zone_name = access.zone.get("name", zone_id)
    key, raw = await acme_service.create_zone_key(
        db,
        zone_name,
        current_user.id,  # type: ignore[arg-type]
        payload.name,
        payload.key or None,
        payload.comment,
    )
    await audit.success("create", "acme_key", payload.name, {"zone": zone_name})
    return {**acme_service.key_to_response(key), "key": raw}


@router.patch("/{zone_id}/acme-keys/{key_id}", response_model=AcmeApiKeyResponse)
async def update_zone_acme_key(
    zone_id: str,
    key_id: int,
    payload: AcmeApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "update_acme_key")),
) -> dict[str, Any]:
    zone_name = access.zone.get("name", zone_id)
    updated = await acme_service.update_zone_key(
        db, key_id, zone_name, payload.comment, payload.name
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Clé ACME introuvable")
    await audit.success("update", "acme_key", updated.name)
    return acme_service.key_to_response(updated)


@router.delete("/{zone_id}/acme-keys/{key_id}", status_code=204)
async def delete_zone_acme_key(
    zone_id: str,
    key_id: int,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "delete_acme_key")),
) -> None:
    zone_name = access.zone.get("name", zone_id)
    deleted = await acme_service.delete_zone_key(db, key_id, zone_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Clé ACME introuvable")
    await audit.success("delete", "acme_key", str(key_id), {"zone": zone_name})

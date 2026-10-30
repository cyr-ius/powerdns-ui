"""Zone health checks open to every member of the zone's account."""

from typing import Any

from fastapi import APIRouter, Depends

from app.routers.zones.access import ZoneAccess, zone_access
from app.services import zone_check_service

router = APIRouter()


@router.get("/{zone_id}/soa-check")
async def soa_sync_check(
    access: ZoneAccess = Depends(zone_access()),
) -> dict[str, Any]:
    return await zone_check_service.soa_sync_check(access.zone)


@router.get("/{zone_id}/email-check")
async def email_security_check(
    access: ZoneAccess = Depends(zone_access()),
) -> dict[str, Any]:
    return zone_check_service.email_security_check(access.zone)

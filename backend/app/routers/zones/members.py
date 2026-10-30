"""Members of the account a zone belongs to, and the caller's role."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger
from app.routers.zones.access import ZoneAccess, zone_access
from app.schemas.admin import ZoneMemberAdd, ZoneMemberResponse, ZoneMemberUpdate
from app.services import admin_service
from app.services.audit_service import AuditLogger

router = APIRouter()


@router.get("/{zone_id}/role")
async def get_zone_role(access: ZoneAccess = Depends(zone_access())) -> dict[str, Any]:
    return {"role": access.role}


@router.get("/{zone_id}/members", response_model=list[ZoneMemberResponse])
async def list_zone_members(
    db: AsyncSession = Depends(get_db),
    access: ZoneAccess = Depends(zone_access("admin")),
) -> list[Any]:
    account = access.zone.get("account") or ""
    if not account:
        return []
    return await admin_service.list_account_members(db, account)


@router.post("/{zone_id}/members", response_model=ZoneMemberResponse, status_code=201)
async def add_zone_member(
    zone_id: str,
    payload: ZoneMemberAdd,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "add_member")),
) -> dict[str, Any]:
    account = access.zone.get("account") or ""
    if not account:
        await audit.failure(
            "add_member",
            "zone",
            zone_id,
            {"detail": "This zone is not associated with any account"},
        )
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    target_user = await admin_service.get_user_by_id(db, payload.user_id)
    if not target_user:
        await audit.failure(
            "add_member",
            "zone",
            zone_id,
            {"detail": "User not found", "user_id": payload.user_id},
        )
        raise HTTPException(status_code=404, detail="User not found")
    await admin_service.upsert_account_member(
        db, account, payload.user_id, payload.role
    )
    await audit.success(
        "add_member",
        "zone",
        zone_id,
        {"member": target_user.username, "role": payload.role.value},
    )
    return {
        "user_id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "role": payload.role.value,
    }


@router.patch("/{zone_id}/members/{user_id}", response_model=ZoneMemberResponse)
async def update_zone_member(
    zone_id: str,
    user_id: int,
    payload: ZoneMemberUpdate,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "update_member")),
) -> dict[str, Any]:
    account = access.zone.get("account") or ""
    if not account:
        await audit.failure(
            "update_member",
            "zone",
            zone_id,
            {"detail": "This zone is not associated with any account"},
        )
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    target_user = await admin_service.get_user_by_id(db, user_id)
    if not target_user:
        await audit.failure(
            "update_member",
            "zone",
            zone_id,
            {"detail": "User not found", "user_id": user_id},
        )
        raise HTTPException(status_code=404, detail="User not found")
    await admin_service.upsert_account_member(db, account, user_id, payload.role)
    await audit.success(
        "update_member",
        "zone",
        zone_id,
        {"member": target_user.username, "role": payload.role.value},
    )
    return {
        "user_id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "role": payload.role.value,
    }


@router.delete("/{zone_id}/members/{user_id}", status_code=204)
async def remove_zone_member(
    zone_id: str,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
    access: ZoneAccess = Depends(zone_access("admin", "remove_member")),
) -> None:
    account = access.zone.get("account") or ""
    if not account:
        await audit.failure(
            "remove_member",
            "zone",
            zone_id,
            {"detail": "This zone is not associated with any account"},
        )
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    removed = await admin_service.remove_account_member(db, account, user_id)
    if not removed:
        await audit.failure(
            "remove_member",
            "zone",
            zone_id,
            {"detail": "Member not found", "user_id": user_id},
        )
        raise HTTPException(status_code=404, detail="Member not found")
    await audit.success("remove_member", "zone", zone_id, {"user_id": user_id})

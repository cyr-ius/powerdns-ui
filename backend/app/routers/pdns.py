import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.dependencies import get_current_user
from app.models.record_type import RecordType
from app.models.user import User
from app.models.zone_record_type import ZoneRecordType
from app.schemas.admin import (
    UserBasicResponse,
    ZoneMemberAdd,
    ZoneMemberResponse,
    ZoneMemberUpdate,
    ZoneRecordTypesResponse,
    ZoneRecordTypesUpdate,
)
from app.schemas.pdns import (
    CryptoKey,
    CryptoKeyCreate,
    CryptoKeyUpdate,
    Metadata,
    PatchRRsets,
    Zone,
    ZoneCreate,
    ZoneDetail,
    ZoneUpdate,
)
from app.services import admin_service, audit_service
from app.services.pdns_service import pdns_request, pdns_request_text

router = APIRouter(prefix="/api/zones")

_SERVER = "/servers/localhost"

_ROLE_LEVELS: dict[str, int] = {"viewer": 0, "manager": 1, "admin": 2}


def _zone_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Zone not found")


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Resource not found")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


def _require_min_role(role: str, minimum: str) -> None:
    if _ROLE_LEVELS.get(role, -1) < _ROLE_LEVELS[minimum]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient rights for this operation",
        )


async def _check_zone_access(
    zone_id: str, user: User, db: AsyncSession
) -> tuple[dict, str]:
    """Fetch zone and verify the user has access. Returns (zone_dict, effective_role)."""
    try:
        zone: dict = await pdns_request("GET", f"{_SERVER}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    if user.is_admin:
        return zone, "admin"
    account = zone.get("account") or ""
    ua = await admin_service.get_user_role_for_account(db, user.id, account)  # type: ignore[arg-type]
    if ua is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this zone",
        )
    role = ua.role.value if hasattr(ua.role, "value") else str(ua.role)
    return zone, role


# ── Users (basic, for zone member management) ─────────────────────────────────


@router.get("/users", response_model=list[UserBasicResponse])
async def list_users_basic(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    return await admin_service.list_users_basic(db)


# ── Zones ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[Zone])
async def list_zones(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    zones: list = await pdns_request("GET", f"{_SERVER}/zones")
    if current_user.is_admin:
        return zones
    user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
    return [z for z in zones if (z.get("account") or "") in user_accounts]


@router.post("", response_model=ZoneDetail, status_code=201)
async def create_zone(
    payload: ZoneCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if not payload.account or payload.account not in user_accounts:
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
        if (
            ua is None
            or _ROLE_LEVELS.get(
                ua.role.value if hasattr(ua.role, "value") else str(ua.role), -1
            )
            < _ROLE_LEVELS["admin"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators of an account can create zones",
            )
    data = payload.model_dump(exclude_none=True)
    if not data["name"].endswith("."):
        data["name"] += "."
    zone = await pdns_request("POST", f"{_SERVER}/zones", json=data)
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="create",
        resource_type="zone",
        resource_id=data["name"],
        ip_address=request.client.host if request.client else None,
    )
    return zone


# ─── Zone members ──────────────────────────────────────────────────────────────


@router.get("/{zone_id}/role")
async def get_zone_role(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    return {"role": role}


@router.get("/{zone_id}/members", response_model=list[ZoneMemberResponse])
async def list_zone_members(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        return []
    return await admin_service.list_account_members(db, account)


@router.post("/{zone_id}/members", response_model=ZoneMemberResponse, status_code=201)
async def add_zone_member(
    zone_id: str,
    payload: ZoneMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    target_user = await admin_service.get_user_by_id(db, payload.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    await admin_service.upsert_account_member(
        db, account, payload.user_id, payload.role
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    target_user = await admin_service.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    await admin_service.upsert_account_member(db, account, user_id, payload.role)
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    removed = await admin_service.remove_account_member(db, account, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")


# ─── Sub-resource routes (must come BEFORE the /{zone_id} catch-all) ──────────


@router.patch("/{zone_id}/rrsets", status_code=204)
async def patch_rrsets(
    zone_id: str,
    payload: PatchRRsets,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "manager")
    try:
        await pdns_request(
            "PATCH", f"{_SERVER}/zones/{zone_id}", json=payload.model_dump()
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="update_records",
        resource_type="zone",
        resource_id=zone_id,
        ip_address=request.client.host if request.client else None,
    )


# ── Metadata ──────────────────────────────────────────────────────────────────


@router.get("/{zone_id}/metadata", response_model=list[Metadata])
async def list_metadata(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request("GET", f"{_SERVER}/zones/{zone_id}/metadata")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.post("/{zone_id}/metadata", response_model=Metadata, status_code=201)
async def create_metadata(
    zone_id: str,
    payload: Metadata,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request(
            "POST", f"{_SERVER}/zones/{zone_id}/metadata", json=payload.model_dump()
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.get("/{zone_id}/metadata/{kind}", response_model=Metadata)
async def get_metadata(
    zone_id: str,
    kind: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request("GET", f"{_SERVER}/zones/{zone_id}/metadata/{kind}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{zone_id}/metadata/{kind}", response_model=Metadata)
async def replace_metadata(
    zone_id: str,
    kind: str,
    payload: Metadata,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request(
            "PUT",
            f"{_SERVER}/zones/{zone_id}/metadata/{kind}",
            json=payload.model_dump(),
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{zone_id}/metadata/{kind}", status_code=204)
async def delete_metadata(
    zone_id: str,
    kind: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        await pdns_request("DELETE", f"{_SERVER}/zones/{zone_id}/metadata/{kind}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


# ── CryptoKeys ────────────────────────────────────────────────────────────────


@router.get("/{zone_id}/cryptokeys", response_model=list[CryptoKey])
async def list_cryptokeys(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request("GET", f"{_SERVER}/zones/{zone_id}/cryptokeys")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.post("/{zone_id}/cryptokeys", response_model=CryptoKey, status_code=201)
async def create_cryptokey(
    zone_id: str,
    payload: CryptoKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request(
            "POST",
            f"{_SERVER}/zones/{zone_id}/cryptokeys",
            json=payload.model_dump(exclude_none=True),
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.get("/{zone_id}/cryptokeys/{key_id}", response_model=CryptoKey)
async def get_cryptokey(
    zone_id: str,
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request(
            "GET", f"{_SERVER}/zones/{zone_id}/cryptokeys/{key_id}"
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{zone_id}/cryptokeys/{key_id}", status_code=204)
async def update_cryptokey(
    zone_id: str,
    key_id: int,
    payload: CryptoKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        await pdns_request(
            "PUT",
            f"{_SERVER}/zones/{zone_id}/cryptokeys/{key_id}",
            json=payload.model_dump(),
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{zone_id}/cryptokeys/{key_id}", status_code=204)
async def delete_cryptokey(
    zone_id: str,
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        await pdns_request("DELETE", f"{_SERVER}/zones/{zone_id}/cryptokeys/{key_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


# ── Zone operations ───────────────────────────────────────────────────────────


@router.put("/{zone_id}/notify", status_code=200)
async def notify_slaves(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request("PUT", f"{_SERVER}/zones/{zone_id}/notify")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{zone_id}/axfr-retrieve", status_code=200)
async def axfr_retrieve(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request("PUT", f"{_SERVER}/zones/{zone_id}/axfr-retrieve")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{zone_id}/rectify", status_code=200)
async def rectify_zone(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        return await pdns_request("PUT", f"{_SERVER}/zones/{zone_id}/rectify")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.get("/{zone_id}/export")
async def export_zone(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "viewer")
    try:
        content = await pdns_request_text("GET", f"{_SERVER}/zones/{zone_id}/export")
        filename = zone_id.rstrip(".") + ".zone"
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


# ── Zone CRUD (catch-all — must stay LAST) ────────────────────────────────────


@router.get("/{zone_id}", response_model=ZoneDetail)
async def get_zone(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    zone, _ = await _check_zone_access(zone_id, current_user, db)
    return zone


@router.put("/{zone_id}", status_code=204)
async def update_zone(
    zone_id: str,
    payload: ZoneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    # Prevent non-global-admins from changing the account field
    if not current_user.is_admin and payload.account != zone.get("account"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a global administrator can modify the account associated with a zone",
        )
    try:
        await pdns_request(
            "PUT",
            f"{_SERVER}/zones/{zone_id}",
            json=payload.model_dump(exclude_none=True),
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        await pdns_request("DELETE", f"{_SERVER}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="delete",
        resource_type="zone",
        resource_id=zone_id,
        ip_address=request.client.host if request.client else None,
    )


# ── Zone Record Types ─────────────────────────────────────────────────────────


@router.get("/{zone_id}/record-types", response_model=ZoneRecordTypesResponse)
async def get_zone_record_types(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ZoneRecordTypesResponse:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "viewer")
    zone_types = await db.exec(  # type: ignore[call-overload]
        select(ZoneRecordType).where(ZoneRecordType.zone_id == zone_id)
    )
    rows = zone_types.all()
    if rows:
        return ZoneRecordTypesResponse(
            types=sorted(r.record_type_name for r in rows),
            is_custom=True,
        )
    global_types = await db.exec(  # type: ignore[call-overload]
        select(RecordType).where(RecordType.enabled == True).order_by(RecordType.name)  # noqa: E712
    )
    return ZoneRecordTypesResponse(
        types=[rt.name for rt in global_types.all()],
        is_custom=False,
    )


@router.put("/{zone_id}/record-types", response_model=ZoneRecordTypesResponse)
async def set_zone_record_types(
    zone_id: str,
    payload: ZoneRecordTypesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ZoneRecordTypesResponse:
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    existing = await db.exec(  # type: ignore[call-overload]
        select(ZoneRecordType).where(ZoneRecordType.zone_id == zone_id)
    )
    for row in existing.all():
        await db.delete(row)
    if not payload.types:
        await db.commit()
        global_types = await db.exec(  # type: ignore[call-overload]
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

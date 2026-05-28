import asyncio
import re

import dns.asyncquery
import dns.asyncresolver
import dns.exception
import dns.message
import dns.name as dns_name_mod
import dns.rdatatype
import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
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
    ip = request.client.host if request.client else None
    if not current_user.is_admin:
        user_accounts = await admin_service.get_user_account_names(db, current_user.id)  # type: ignore[arg-type]
        if not payload.account or payload.account not in user_accounts:
            await audit_service.log_action(
                db,
                username=current_user.username,
                user_id=current_user.id,
                action="create",
                resource_type="zone",
                resource_id=payload.name,
                ip_address=ip,
                status="failure",
                details={"detail": "You must specify an account to which you belong"},
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
        if (
            ua is None
            or _ROLE_LEVELS.get(
                ua.role.value if hasattr(ua.role, "value") else str(ua.role), -1
            )
            < _ROLE_LEVELS["admin"]
        ):
            await audit_service.log_action(
                db,
                username=current_user.username,
                user_id=current_user.id,
                action="create",
                resource_type="zone",
                resource_id=payload.name,
                ip_address=ip,
                status="failure",
                details={
                    "detail": "Only administrators of an account can create zones"
                },
            )
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
        ip_address=ip,
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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ip = request.client.host if request.client else None
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="add_member",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": "This zone is not associated with any account"},
        )
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    target_user = await admin_service.get_user_by_id(db, payload.user_id)
    if not target_user:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="add_member",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": "User not found", "user_id": payload.user_id},
        )
        raise HTTPException(status_code=404, detail="User not found")
    await admin_service.upsert_account_member(
        db, account, payload.user_id, payload.role
    )
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="add_member",
        resource_type="zone",
        resource_id=zone_id,
        details={"member": target_user.username, "role": payload.role.value},
        ip_address=ip,
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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ip = request.client.host if request.client else None
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="update_member",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": "This zone is not associated with any account"},
        )
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    target_user = await admin_service.get_user_by_id(db, user_id)
    if not target_user:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="update_member",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": "User not found", "user_id": user_id},
        )
        raise HTTPException(status_code=404, detail="User not found")
    await admin_service.upsert_account_member(db, account, user_id, payload.role)
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="update_member",
        resource_type="zone",
        resource_id=zone_id,
        details={"member": target_user.username, "role": payload.role.value},
        ip_address=ip,
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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    account = zone.get("account") or ""
    if not account:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="remove_member",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": "This zone is not associated with any account"},
        )
        raise HTTPException(
            status_code=400, detail="This zone is not associated with any account"
        )
    removed = await admin_service.remove_account_member(db, account, user_id)
    if not removed:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="remove_member",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": "Member not found", "user_id": user_id},
        )
        raise HTTPException(status_code=404, detail="Member not found")
    await audit_service.log_action(
        db,
        username=current_user.username,
        user_id=current_user.id,
        action="remove_member",
        resource_type="zone",
        resource_id=zone_id,
        details={"user_id": user_id},
        ip_address=ip,
    )


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


@router.post("/{zone_id}/import", status_code=204)
async def import_zone(
    zone_id: str,
    file: UploadFile,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    _, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    try:
        content = (await file.read()).decode("utf-8")
        imported_rrsets = _parse_zone_file(zone_id, content)
    except Exception as exc:
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="import",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": f"Invalid zone file: {exc}"},
        )
        raise HTTPException(
            status_code=422, detail=f"Invalid zone file: {exc}"
        ) from exc
    try:
        current_zone = await pdns_request("GET", f"{_SERVER}/zones/{zone_id}")
        current_rrsets = current_zone.get("rrsets", [])
        # SOA and NS are managed by PowerDNS — never touch them during import.
        safe_rrsets = [r for r in imported_rrsets if r["type"] not in ("SOA", "NS")]
        imported_keys = {(r["name"], r["type"]) for r in safe_rrsets}
        patch: list[dict] = [{"changetype": "REPLACE", **r} for r in safe_rrsets]
        for rrset in current_rrsets:
            if rrset["type"] in ("SOA", "NS"):
                continue
            if (rrset["name"], rrset["type"]) not in imported_keys:
                patch.append(
                    {
                        "changetype": "DELETE",
                        "name": rrset["name"],
                        "type": rrset["type"],
                    }
                )
        await pdns_request(
            "PATCH", f"{_SERVER}/zones/{zone_id}", json={"rrsets": patch}
        )
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="import",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="import",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc


def _parse_zone_file(zone_name: str, content: str) -> list[dict]:
    import dns.name
    import dns.rdatatype
    import dns.zone

    origin = dns.name.from_text(zone_name)
    zone = dns.zone.from_text(content, origin=origin, check_origin=False)
    rrsets = []
    for rel_name, node in zone.nodes.items():
        fqdn = str(rel_name.derelativize(origin))
        for rdataset in node.rdatasets:
            rrsets.append(
                {
                    "name": fqdn,
                    "type": dns.rdatatype.to_text(rdataset.rdtype),
                    "ttl": rdataset.ttl,
                    "records": [
                        {"content": r.to_text(), "disabled": False} for r in rdataset
                    ],
                }
            )
    return rrsets


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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    zone, role = await _check_zone_access(zone_id, current_user, db)
    _require_min_role(role, "admin")
    # Prevent non-global-admins from changing the account field
    if not current_user.is_admin and payload.account != zone.get("account"):
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="update",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={
                "detail": "Only a global administrator can modify the account associated with a zone"
            },
        )
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
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="update",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_user.username,
            user_id=current_user.id,
            action="update",
            resource_type="zone",
            resource_id=zone_id,
            ip_address=ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc


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


# ── SOA sync check ────────────────────────────────────────────────────────────


async def _query_ns_serial(ns: str, zone: str) -> dict:
    try:
        ns_hostname = ns.rstrip(".")
        answers = await dns.asyncresolver.resolve(ns_hostname, "A", lifetime=5)
        ns_ip = str(answers[0].address)
        qname = dns_name_mod.from_text(zone)
        request = dns.message.make_query(qname, dns.rdatatype.SOA)
        response = await dns.asyncquery.udp(request, ns_ip, timeout=3)
        for rrset in response.answer:
            if rrset.rdtype == dns.rdatatype.SOA:
                return {"ip": ns_ip, "serial": rrset[0].serial, "error": None}
        return {"ip": ns_ip, "serial": None, "error": "No SOA in response"}
    except dns.exception.Timeout:
        return {"ip": None, "serial": None, "error": "Timeout"}
    except dns.resolver.NXDOMAIN:
        return {"ip": None, "serial": None, "error": "NS hostname not found"}
    except Exception as exc:
        return {"ip": None, "serial": None, "error": str(exc)}


@router.get("/{zone_id}/soa-check", dependencies=[Depends(get_current_user)])
async def soa_sync_check(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    zone, _ = await _check_zone_access(zone_id, current_user, db)
    zone_name: str = zone.get("name", "")

    ns_names: list[str] = []
    authoritative_serial: int | None = None
    for rrset in zone.get("rrsets", []):
        if rrset["type"] == "SOA" and rrset["name"] == zone_name:
            try:
                authoritative_serial = int(rrset["records"][0]["content"].split()[2])
            except IndexError, ValueError, KeyError:
                pass
        if rrset["type"] == "NS" and rrset["name"] == zone_name:
            for rec in rrset["records"]:
                if not rec.get("disabled", False):
                    ns_names.append(rec["content"])

    raw = await asyncio.gather(*[_query_ns_serial(ns, zone_name) for ns in ns_names])

    nameservers = []
    for ns, result in zip(ns_names, raw):
        serial: int | None = result.get("serial")
        if serial is None:
            ns_status = "error"
        elif serial == authoritative_serial:
            ns_status = "synced"
        elif serial < (authoritative_serial or 0):
            ns_status = "outdated"
        else:
            ns_status = "ahead"
        nameservers.append(
            {
                "ns": ns,
                "ip": result.get("ip"),
                "serial": serial,
                "status": ns_status,
                "error": result.get("error"),
            }
        )

    return {
        "zone": zone_name,
        "authoritative_serial": authoritative_serial,
        "nameservers": nameservers,
    }


# ── Email security check (SPF / DMARC / DKIM) ────────────────────────────────


def _clean_txt(content: str) -> str:
    """Remove surrounding quotes and unescape semicolons from PDNS TXT content."""
    s = content.strip()
    # Strip wrapping quotes if present
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.replace("\\;", ";")


def _check_spf(apex_txt: list[str]) -> dict:
    spf = [r for r in apex_txt if r.startswith("v=spf1")]
    if not spf:
        return {
            "status": "missing",
            "record": None,
            "details": "No SPF record found at zone apex.",
        }
    if len(spf) > 1:
        return {
            "status": "error",
            "record": spf[0],
            "details": f"{len(spf)} SPF records found — only one is allowed (RFC 7208).",
        }
    record = spf[0]
    if "-all" in record:
        return {
            "status": "ok",
            "record": record,
            "details": "Hard fail (-all): only listed senders are authorised.",
        }
    if "~all" in record:
        return {
            "status": "warning",
            "record": record,
            "details": "Soft fail (~all): unauthorised senders are accepted but tagged. Consider -all.",
        }
    if "?all" in record:
        return {
            "status": "warning",
            "record": record,
            "details": "Neutral (?all): no enforcement. Consider ~all or -all.",
        }
    if "+all" in record:
        return {
            "status": "error",
            "record": record,
            "details": "Permissive (+all): any server may send. This is insecure.",
        }
    return {
        "status": "warning",
        "record": record,
        "details": "No 'all' mechanism found. Specify ~all or -all.",
    }


def _check_dmarc(dmarc_txt: list[str]) -> dict:
    dmarc = [r for r in dmarc_txt if r.startswith("v=DMARC1")]
    if not dmarc:
        return {
            "status": "missing",
            "record": None,
            "policy": None,
            "details": "No DMARC record found at _dmarc.<zone>.",
        }
    record = dmarc[0]
    p_match = re.search(r"\bp=(\w+)", record)
    policy = p_match.group(1).lower() if p_match else None
    has_rua = bool(re.search(r"\brua=", record))
    has_ruf = bool(re.search(r"\bruf=", record))

    if policy == "reject":
        status = "ok"
        detail = "Strict policy (reject): non-compliant messages are rejected."
    elif policy == "quarantine":
        status = "ok"
        detail = "Moderate policy (quarantine): non-compliant messages go to spam."
    elif policy == "none":
        status = "warning"
        detail = (
            "Monitoring only (p=none): no enforcement. Upgrade to quarantine or reject."
        )
    else:
        return {
            "status": "error",
            "record": record,
            "policy": None,
            "details": "Missing or unrecognised p= tag.",
        }

    extras = []
    if not has_rua:
        extras.append(
            "No rua= reporting address — you will not receive aggregate reports."
        )
        if status == "ok":
            status = "warning"
    if has_ruf:
        extras.append("ruf= forensic reporting configured.")
    if extras:
        detail += " " + " ".join(extras)

    return {"status": status, "record": record, "policy": policy, "details": detail}


def _check_dkim(rrsets: list[dict], zone_name: str) -> list[dict]:
    results: list[dict] = []
    suffix = f"._domainkey.{zone_name}"
    for rrset in rrsets:
        if rrset.get("type") != "TXT":
            continue
        name: str = rrset.get("name", "")
        if not name.endswith(suffix):
            continue
        selector = name[: -len(suffix)]
        for rec in rrset.get("records", []):
            content = _clean_txt(rec.get("content", ""))
            if "v=DKIM1" not in content:
                results.append(
                    {
                        "selector": selector,
                        "status": "invalid",
                        "record": content,
                        "details": "Not a valid DKIM record (missing v=DKIM1).",
                    }
                )
                continue
            p_match = re.search(r"\bp=([^;\s]*)", content)
            p_value = p_match.group(1).strip() if p_match else ""
            if not p_value:
                results.append(
                    {
                        "selector": selector,
                        "status": "revoked",
                        "record": content,
                        "details": "Public key is empty — key has been revoked (p=).",
                    }
                )
            else:
                results.append(
                    {
                        "selector": selector,
                        "status": "ok",
                        "record": content,
                        "details": "DKIM key active and valid.",
                    }
                )
    return results


@router.get("/{zone_id}/email-check", dependencies=[Depends(get_current_user)])
async def email_security_check(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    zone, _ = await _check_zone_access(zone_id, current_user, db)
    zone_name: str = zone.get("name", "")
    rrsets: list[dict] = zone.get("rrsets", [])

    apex_txt: list[str] = []
    dmarc_txt: list[str] = []
    dmarc_name = f"_dmarc.{zone_name}"

    for rrset in rrsets:
        if rrset.get("type") != "TXT":
            continue
        name = rrset.get("name", "")
        for rec in rrset.get("records", []):
            cleaned = _clean_txt(rec.get("content", ""))
            if name == zone_name:
                apex_txt.append(cleaned)
            elif name == dmarc_name:
                dmarc_txt.append(cleaned)

    return {
        "zone": zone_name,
        "spf": _check_spf(apex_txt),
        "dmarc": _check_dmarc(dmarc_txt),
        "dkim": _check_dkim(rrsets, zone_name),
    }

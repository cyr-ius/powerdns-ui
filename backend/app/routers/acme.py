"""PowerDNS API compatibility layer for certbot-dns-pdns plugin.

Exposes the minimal PowerDNS HTTP API subset that certbot-dns-pdns (via
dns-lexicon) needs to perform DNS-01 ACME challenges:

  GET   /api/v1/servers/{server_id}/zones
  GET   /api/v1/servers/{server_id}/zones/{zone_id}
  PATCH /api/v1/servers/{server_id}/zones/{zone_id}
  PUT   /api/v1/servers/{server_id}/zones/{zone_id}/notify

Secured with per-user ACME API keys managed via /api/acme-keys.
Each key carries an explicit allow-list of zones.

certbot credentials file:
  dns_pdns_endpoint  = https://dns.example.com
  dns_pdns_api_key   = ak_<your key>
  dns_pdns_server_id = localhost
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_client_ip
from app.models.acme_key import AcmeApiKey
from app.services import acme_service, admin_service
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request, pdns_request_root

router = APIRouter(prefix="/api/v1", tags=["acme-pdns-compat"])
router_api = APIRouter(prefix="/api", tags=["acme-pdns-compat"])

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)
_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("ACME PDNS compatibility router initialized")


async def _get_acme_key(
    raw_key: str = Security(_API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
) -> AcmeApiKey:
    key = await acme_service.verify_key(db, raw_key)
    if key is None or key.key_type != "acme":
        raise HTTPException(status_code=401, detail="Invalid ACME API key")
    return key


async def _check_zone_allowed(
    key: AcmeApiKey,
    zone_id: str,
    audit: AuditLogger,
    action: str,
) -> None:
    allowed = acme_service._decode_zones(key)
    normalised = zone_id.rstrip(".") + "."
    if normalised not in [z.rstrip(".") + "." for z in allowed]:
        detail = f"Zone '{zone_id}' is not in this key's allowed zones"
        await audit.failure(action, "acme_zone", zone_id, {"detail": detail})
        raise HTTPException(status_code=403, detail=detail)


def _normalize_acme_body(body: dict) -> dict:
    """Normalize a Traefik/LEGO patch payload for PowerDNS 4.x/5.x compatibility.

    LEGO may send names without a trailing dot, a spurious `kind` field copied
    from the zone object, and `name`/`type`/`ttl` fields inside each record
    (PowerDNS 3.x compat). PowerDNS requires FQDNs and does not accept those
    extra fields at the record level.
    """
    rrsets = []
    for rrset in body.get("rrsets", []):
        name = rrset.get("name", "")
        if name and not name.endswith("."):
            name += "."
        changetype = rrset.get("changetype", "REPLACE").upper()
        clean: dict = {
            "name": name,
            "type": rrset.get("type", ""),
            "changetype": changetype,
        }
        if changetype != "DELETE":
            clean["ttl"] = rrset.get("ttl", 120)
            clean["records"] = [
                {"content": r.get("content", ""), "disabled": r.get("disabled", False)}
                for r in rrset.get("records", [])
            ]
        rrsets.append(clean)
    return {"rrsets": rrsets}


async def _resolve_username(db: AsyncSession, key: AcmeApiKey) -> str:
    if key.user_id is None:
        return "acme-key"
    user = await admin_service.get_user_by_id(db, key.user_id)
    return user.username if user else f"user:{key.user_id}"


@router_api.get("")
async def get_api_versions(
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    try:
        data = await pdns_request_root("/api")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    return JSONResponse(content=data)


@router.get("/servers/{server_id}/zones")
async def list_zones(
    server_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    username = await _resolve_username(db, key)
    audit = AuditLogger(db, username, key.user_id, get_client_ip(request))
    allowed = acme_service._decode_zones(key)
    try:
        zones: list[dict] = await pdns_request("GET", f"/servers/{server_id}/zones")
    except httpx.HTTPStatusError as exc:
        await audit.failure(
            "list", "acme_zone", details={"acme_key": key.name, "detail": str(exc)}
        )
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    normalised_allowed = {z.rstrip(".") + "." for z in allowed}
    filtered = [
        z for z in zones if z.get("name", "").rstrip(".") + "." in normalised_allowed
    ]
    await audit.success("list", "acme_zone", details={"acme_key": key.name})
    return JSONResponse(content=filtered)


@router.put("/servers/{server_id}/zones/{zone_id}/notify", status_code=200)
async def notify_zone(
    server_id: str,
    zone_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    username = await _resolve_username(db, key)
    audit = AuditLogger(db, username, key.user_id, get_client_ip(request))
    await _check_zone_allowed(key, zone_id, audit, "notify")
    try:
        data = await pdns_request("PUT", f"/servers/{server_id}/zones/{zone_id}/notify")
    except httpx.HTTPStatusError as exc:
        await audit.failure(
            "notify", "acme_zone", zone_id, {"acme_key": key.name, "detail": str(exc)}
        )
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    await audit.success("notify", "acme_zone", zone_id, {"acme_key": key.name})
    return JSONResponse(content=data)


@router.get("/servers/{server_id}/zones/{zone_id:path}")
async def get_zone(
    server_id: str,
    zone_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    username = await _resolve_username(db, key)
    audit = AuditLogger(db, username, key.user_id, get_client_ip(request))
    await _check_zone_allowed(key, zone_id, audit, "read")
    try:
        data = await pdns_request("GET", f"/servers/{server_id}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        await audit.failure(
            "read", "acme_zone", zone_id, {"acme_key": key.name, "detail": str(exc)}
        )
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    await audit.success("read", "acme_zone", zone_id, {"acme_key": key.name})
    return JSONResponse(content=data)


@router.patch("/servers/{server_id}/zones/{zone_id:path}", status_code=204)
async def patch_zone(
    server_id: str,
    zone_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    key: AcmeApiKey = Depends(_get_acme_key),
) -> None:
    username = await _resolve_username(db, key)
    audit = AuditLogger(db, username, key.user_id, get_client_ip(request))
    await _check_zone_allowed(key, zone_id, audit, "update")
    body = await request.json()
    for rrset in body.get("rrsets", []):
        if rrset.get("type", "").upper() != "TXT":
            await audit.failure(
                "update",
                "acme_zone",
                zone_id,
                {
                    "acme_key": key.name,
                    "detail": "Only TXT record modifications are allowed via ACME endpoint",
                },
            )
            raise HTTPException(
                status_code=403,
                detail="Only TXT record modifications are allowed via ACME endpoint",
            )
        if not rrset.get("name", "").startswith("_acme-challenge."):
            await audit.failure(
                "update",
                "acme_zone",
                zone_id,
                {
                    "acme_key": key.name,
                    "detail": "Only _acme-challenge records can be modified via ACME endpoint",
                },
            )
            raise HTTPException(
                status_code=403,
                detail="Only _acme-challenge records can be modified via ACME endpoint",
            )
    clean_body = _normalize_acme_body(body)
    try:
        _LOGGER.debug(
            "Patching zone '%s' on server '%s' with body: %s",
            zone_id,
            server_id,
            clean_body,
        )
        await pdns_request(
            "PATCH", f"/servers/{server_id}/zones/{zone_id}", json=clean_body
        )
    except httpx.HTTPStatusError as exc:
        await audit.failure(
            "update", "acme_zone", zone_id, {"acme_key": key.name, "detail": str(exc)}
        )
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    records = [r.get("name") for r in body.get("rrsets", [])]
    await audit.success(
        "update", "acme_zone", zone_id, {"acme_key": key.name, "records": records}
    )

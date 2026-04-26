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

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.acme_key import AcmeApiKey
from app.services import acme_service
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api/v1", tags=["acme-pdns-compat"])

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


async def _get_acme_key(
    raw_key: str = Security(_API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
) -> AcmeApiKey:
    key = await acme_service.verify_key(db, raw_key)
    if key is None or key.key_type != "acme":
        raise HTTPException(status_code=401, detail="Invalid ACME API key")
    return key


def _check_zone_allowed(key: AcmeApiKey, zone_id: str) -> None:
    allowed = acme_service._decode_zones(key)
    # Normalise trailing dot for comparison
    normalised = zone_id.rstrip(".") + "."
    if normalised not in [z.rstrip(".") + "." for z in allowed]:
        raise HTTPException(
            status_code=403,
            detail=f"Zone '{zone_id}' is not in this key's allowed zones",
        )


@router.get("/servers/{server_id}/zones")
async def list_zones(
    server_id: str,
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    allowed = acme_service._decode_zones(key)
    try:
        zones: list[dict] = await pdns_request("GET", f"/servers/{server_id}/zones")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc
    normalised_allowed = {z.rstrip(".") + "." for z in allowed}
    filtered = [
        z for z in zones if z.get("name", "").rstrip(".") + "." in normalised_allowed
    ]
    return JSONResponse(content=filtered)


@router.put("/servers/{server_id}/zones/{zone_id}/notify", status_code=200)
async def notify_zone(
    server_id: str,
    zone_id: str,
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    _check_zone_allowed(key, zone_id)
    try:
        data = await pdns_request("PUT", f"/servers/{server_id}/zones/{zone_id}/notify")
        return JSONResponse(content=data)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc


@router.get("/servers/{server_id}/zones/{zone_id:path}")
async def get_zone(
    server_id: str,
    zone_id: str,
    key: AcmeApiKey = Depends(_get_acme_key),
) -> JSONResponse:
    _check_zone_allowed(key, zone_id)
    try:
        data = await pdns_request("GET", f"/servers/{server_id}/zones/{zone_id}")
        return JSONResponse(content=data)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc


@router.patch("/servers/{server_id}/zones/{zone_id:path}", status_code=204)
async def patch_zone(
    server_id: str,
    zone_id: str,
    request: Request,
    key: AcmeApiKey = Depends(_get_acme_key),
) -> None:
    _check_zone_allowed(key, zone_id)
    body = await request.json()
    for rrset in body.get("rrsets", []):
        if rrset.get("type", "").upper() != "TXT":
            raise HTTPException(
                status_code=403,
                detail="Only TXT record modifications are allowed via ACME endpoint",
            )
        if not rrset.get("name", "").startswith("_acme-challenge."):
            raise HTTPException(
                status_code=403,
                detail="Only _acme-challenge records can be modified via ACME endpoint",
            )
    try:
        await pdns_request("PATCH", f"/servers/{server_id}/zones/{zone_id}", json=body)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        ) from exc

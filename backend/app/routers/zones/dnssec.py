"""DNSSEC crypto keys of a zone, reserved to the zone administrators."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends

from app.routers.zones.access import SERVER, pdns_error_handler, zone_access
from app.schemas.pdns import CryptoKey, CryptoKeyCreate, CryptoKeyUpdate
from app.services.pdns_service import pdns_request

router = APIRouter(dependencies=[Depends(zone_access("admin"))])


@router.get("/{zone_id}/cryptokeys", response_model=list[CryptoKey])
async def list_cryptokeys(zone_id: str) -> list[Any]:
    try:
        return await pdns_request("GET", f"{SERVER}/zones/{zone_id}/cryptokeys")  # type: ignore[no-any-return]
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.post("/{zone_id}/cryptokeys", response_model=CryptoKey, status_code=201)
async def create_cryptokey(zone_id: str, payload: CryptoKeyCreate) -> dict[str, Any]:
    try:
        return await pdns_request(  # type: ignore[no-any-return]
            "POST",
            f"{SERVER}/zones/{zone_id}/cryptokeys",
            json=payload.model_dump(exclude_none=True),
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.get("/{zone_id}/cryptokeys/{key_id}", response_model=CryptoKey)
async def get_cryptokey(zone_id: str, key_id: int) -> dict[str, Any]:
    try:
        return await pdns_request(  # type: ignore[no-any-return]
            "GET", f"{SERVER}/zones/{zone_id}/cryptokeys/{key_id}"
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.put("/{zone_id}/cryptokeys/{key_id}", status_code=204)
async def update_cryptokey(zone_id: str, key_id: int, payload: CryptoKeyUpdate) -> None:
    try:
        await pdns_request(
            "PUT",
            f"{SERVER}/zones/{zone_id}/cryptokeys/{key_id}",
            json=payload.model_dump(),
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.delete("/{zone_id}/cryptokeys/{key_id}", status_code=204)
async def delete_cryptokey(zone_id: str, key_id: int) -> None:
    try:
        await pdns_request("DELETE", f"{SERVER}/zones/{zone_id}/cryptokeys/{key_id}")
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc

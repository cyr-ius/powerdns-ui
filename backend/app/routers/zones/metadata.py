"""Zone metadata, reserved to the zone administrators."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends

from app.routers.zones.access import SERVER, pdns_error_handler, zone_access
from app.schemas.pdns import Metadata
from app.services.pdns_service import pdns_request

router = APIRouter(dependencies=[Depends(zone_access("admin"))])


@router.get("/{zone_id}/metadata", response_model=list[Metadata])
async def list_metadata(zone_id: str) -> list[Any]:
    try:
        return await pdns_request("GET", f"{SERVER}/zones/{zone_id}/metadata")  # type: ignore[no-any-return]
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.post("/{zone_id}/metadata", response_model=Metadata, status_code=201)
async def create_metadata(zone_id: str, payload: Metadata) -> dict[str, Any]:
    try:
        return await pdns_request(  # type: ignore[no-any-return]
            "POST", f"{SERVER}/zones/{zone_id}/metadata", json=payload.model_dump()
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.get("/{zone_id}/metadata/{kind}", response_model=Metadata)
async def get_metadata(zone_id: str, kind: str) -> dict[str, Any]:
    try:
        return await pdns_request("GET", f"{SERVER}/zones/{zone_id}/metadata/{kind}")  # type: ignore[no-any-return]
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.put("/{zone_id}/metadata/{kind}", response_model=Metadata)
async def replace_metadata(
    zone_id: str, kind: str, payload: Metadata
) -> dict[str, Any]:
    try:
        return await pdns_request(  # type: ignore[no-any-return]
            "PUT",
            f"{SERVER}/zones/{zone_id}/metadata/{kind}",
            json=payload.model_dump(),
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.delete("/{zone_id}/metadata/{kind}", status_code=204)
async def delete_metadata(zone_id: str, kind: str) -> None:
    try:
        await pdns_request("DELETE", f"{SERVER}/zones/{zone_id}/metadata/{kind}")
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc

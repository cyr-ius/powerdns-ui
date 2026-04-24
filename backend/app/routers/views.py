import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_admin
from app.schemas.pdns import ViewZoneAdd
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api/views", dependencies=[Depends(get_current_admin)])

_SERVER = "/servers/localhost"


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="View not found")
    if exc.response.status_code == 409:
        return HTTPException(status_code=409, detail="This zone is already in the view")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


@router.get("", response_model=list[str])
async def list_views() -> list:
    try:
        result = await pdns_request("GET", f"{_SERVER}/views")
        return result.get("views", [])
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.get("/{view}", response_model=list[str])
async def get_view_zones(view: str) -> list:
    try:
        result = await pdns_request("GET", f"{_SERVER}/views/{view}")
        return result.get("zones", [])
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.post("/{view}", status_code=204)
async def add_zone_to_view(view: str, payload: ViewZoneAdd) -> None:
    zone = payload.name if payload.name.endswith(".") else payload.name + "."
    # PDNS expects "{zone}.{view}" e.g. "example.org..trusted"
    pdns_name = f"{zone}.{view}"
    try:
        await pdns_request(
            "POST",
            f"{_SERVER}/views/{view}",
            json={"name": pdns_name},
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{view}/{zone_id}", status_code=204)
async def remove_zone_from_view(view: str, zone_id: str) -> None:
    try:
        await pdns_request("DELETE", f"{_SERVER}/views/{view}/{zone_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_admin
from app.schemas.pdns import Network, NetworkAssign
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api/networks", dependencies=[Depends(get_current_admin)])

_SERVER = "/servers/localhost"


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Network not found")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


@router.get("", response_model=list[Network])
async def list_networks() -> list:
    try:
        result = await pdns_request("GET", f"{_SERVER}/networks")
        return result.get("networks", result) if isinstance(result, dict) else result
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{ip}/{prefixlen}", status_code=204)
async def assign_network_view(ip: str, prefixlen: int, payload: NetworkAssign) -> None:
    try:
        await pdns_request(
            "PUT",
            f"{_SERVER}/networks/{ip}/{prefixlen}",
            json=payload.model_dump(),
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{ip}/{prefixlen}", status_code=204)
async def delete_network(ip: str, prefixlen: int) -> None:
    try:
        await pdns_request("DELETE", f"{_SERVER}/networks/{ip}/{prefixlen}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc

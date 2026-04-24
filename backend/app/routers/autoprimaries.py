import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_admin
from app.schemas.pdns import Autoprimary, AutoprimaryCreate
from app.services.pdns_service import pdns_request

router = APIRouter(
    prefix="/api/autoprimaries", dependencies=[Depends(get_current_admin)]
)

_SERVER = "/servers/localhost"


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Autoprimary not found")
    if exc.response.status_code == 409:
        return HTTPException(status_code=409, detail="This autoprimary already exists")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


@router.get("", response_model=list[Autoprimary])
async def list_autoprimaries() -> list:
    try:
        return await pdns_request("GET", f"{_SERVER}/autoprimaries")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.post("", status_code=201)
async def create_autoprimary(payload: AutoprimaryCreate) -> dict:
    try:
        await pdns_request(
            "POST",
            f"{_SERVER}/autoprimaries",
            json=payload.model_dump(exclude_none=True),
        )
        return {}
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{ip}/{nameserver}", status_code=204)
async def delete_autoprimary(ip: str, nameserver: str) -> None:
    try:
        await pdns_request("DELETE", f"{_SERVER}/autoprimaries/{ip}/{nameserver}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc

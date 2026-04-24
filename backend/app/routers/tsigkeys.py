import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_admin
from app.schemas.pdns import TsigKey, TsigKeyCreate, TsigKeyUpdate
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api/tsigkeys", dependencies=[Depends(get_current_admin)])

_SERVER = "/servers/localhost"


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="TSIG key not found")
    if exc.response.status_code == 409:
        return HTTPException(
            status_code=409, detail="A key with this name already exists"
        )
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


@router.get("", response_model=list[TsigKey])
async def list_tsigkeys() -> list:
    try:
        return await pdns_request("GET", f"{_SERVER}/tsigkeys")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.post("", response_model=TsigKey, status_code=201)
async def create_tsigkey(payload: TsigKeyCreate) -> dict:
    try:
        return await pdns_request(
            "POST", f"{_SERVER}/tsigkeys", json=payload.model_dump(exclude_none=True)
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.get("/{tsigkey_id}", response_model=TsigKey)
async def get_tsigkey(tsigkey_id: str) -> dict:
    try:
        return await pdns_request("GET", f"{_SERVER}/tsigkeys/{tsigkey_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{tsigkey_id}", response_model=TsigKey)
async def update_tsigkey(tsigkey_id: str, payload: TsigKeyUpdate) -> dict:
    try:
        return await pdns_request(
            "PUT",
            f"{_SERVER}/tsigkeys/{tsigkey_id}",
            json=payload.model_dump(exclude_none=True),
        )
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.delete("/{tsigkey_id}", status_code=204)
async def delete_tsigkey(tsigkey_id: str) -> None:
    try:
        await pdns_request("DELETE", f"{_SERVER}/tsigkeys/{tsigkey_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.schemas.pdns import TsigKey, TsigKeyCreate, TsigKeyUpdate
from app.services import audit_service
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
async def create_tsigkey(
    payload: TsigKeyCreate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ip = request.client.host if request.client else None
    try:
        result = await pdns_request(
            "POST", f"{_SERVER}/tsigkeys", json=payload.model_dump(exclude_none=True)
        )
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="create",
            resource_type="tsig_key",
            resource_id=payload.name,
            ip_address=ip,
        )
        return result
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="create",
            resource_type="tsig_key",
            resource_id=payload.name,
            ip_address=ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc


@router.get("/{tsigkey_id}", response_model=TsigKey)
async def get_tsigkey(tsigkey_id: str) -> dict:
    try:
        return await pdns_request("GET", f"{_SERVER}/tsigkeys/{tsigkey_id}")
    except httpx.HTTPStatusError as exc:
        raise _pdns_error_handler(exc) from exc


@router.put("/{tsigkey_id}", response_model=TsigKey)
async def update_tsigkey(
    tsigkey_id: str,
    payload: TsigKeyUpdate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ip = request.client.host if request.client else None
    try:
        result = await pdns_request(
            "PUT",
            f"{_SERVER}/tsigkeys/{tsigkey_id}",
            json=payload.model_dump(exclude_none=True),
        )
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="update",
            resource_type="tsig_key",
            resource_id=tsigkey_id,
            ip_address=ip,
        )
        return result
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="update",
            resource_type="tsig_key",
            resource_id=tsigkey_id,
            ip_address=ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc


@router.delete("/{tsigkey_id}", status_code=204)
async def delete_tsigkey(
    tsigkey_id: str,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    try:
        await pdns_request("DELETE", f"{_SERVER}/tsigkeys/{tsigkey_id}")
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="delete",
            resource_type="tsig_key",
            resource_id=tsigkey_id,
            ip_address=ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="delete",
            resource_type="tsig_key",
            resource_id=tsigkey_id,
            ip_address=ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc

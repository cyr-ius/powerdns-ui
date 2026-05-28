import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.schemas.pdns import Autoprimary, AutoprimaryCreate
from app.services import audit_service
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
async def create_autoprimary(
    payload: AutoprimaryCreate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ip = request.client.host if request.client else None
    try:
        await pdns_request(
            "POST",
            f"{_SERVER}/autoprimaries",
            json=payload.model_dump(exclude_none=True),
        )
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="create",
            resource_type="autoprimary",
            resource_id=f"{payload.ip}/{payload.nameserver}",
            ip_address=ip,
        )
        return {}
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="create",
            resource_type="autoprimary",
            resource_id=f"{payload.ip}/{payload.nameserver}",
            ip_address=ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc


@router.delete("/{ip}/{nameserver}", status_code=204)
async def delete_autoprimary(
    ip: str,
    nameserver: str,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    client_ip = request.client.host if request.client else None
    try:
        await pdns_request("DELETE", f"{_SERVER}/autoprimaries/{ip}/{nameserver}")
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="delete",
            resource_type="autoprimary",
            resource_id=f"{ip}/{nameserver}",
            ip_address=client_ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="delete",
            resource_type="autoprimary",
            resource_id=f"{ip}/{nameserver}",
            ip_address=client_ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.schemas.pdns import ViewZoneAdd
from app.services import audit_service
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
async def add_zone_to_view(
    view: str,
    payload: ViewZoneAdd,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    zone = payload.name if payload.name.endswith(".") else payload.name + "."
    pdns_name = f"{zone}.{view}"
    try:
        await pdns_request(
            "POST",
            f"{_SERVER}/views/{view}",
            json={"name": pdns_name},
        )
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="add_zone",
            resource_type="view",
            resource_id=view,
            details={"zone": zone},
            ip_address=ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="add_zone",
            resource_type="view",
            resource_id=view,
            ip_address=ip,
            status="failure",
            details={"zone": zone, "detail": http_exc.detail},
        )
        raise http_exc from exc


@router.delete("/{view}/{zone_id}", status_code=204)
async def remove_zone_from_view(
    view: str,
    zone_id: str,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    ip = request.client.host if request.client else None
    try:
        await pdns_request("DELETE", f"{_SERVER}/views/{view}/{zone_id}")
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="remove_zone",
            resource_type="view",
            resource_id=view,
            details={"zone": zone_id},
            ip_address=ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="remove_zone",
            resource_type="view",
            resource_id=view,
            ip_address=ip,
            status="failure",
            details={"zone": zone_id, "detail": http_exc.detail},
        )
        raise http_exc from exc

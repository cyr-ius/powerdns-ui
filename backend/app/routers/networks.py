import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.schemas.pdns import Network, NetworkAssign
from app.services import audit_service
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
async def assign_network_view(
    ip: str,
    prefixlen: int,
    payload: NetworkAssign,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    client_ip = request.client.host if request.client else None
    try:
        await pdns_request(
            "PUT",
            f"{_SERVER}/networks/{ip}/{prefixlen}",
            json=payload.model_dump(),
        )
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="assign",
            resource_type="network",
            resource_id=f"{ip}/{prefixlen}",
            details={"view": payload.model_dump().get("view")},
            ip_address=client_ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="assign",
            resource_type="network",
            resource_id=f"{ip}/{prefixlen}",
            ip_address=client_ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc


@router.delete("/{ip}/{prefixlen}", status_code=204)
async def delete_network(
    ip: str,
    prefixlen: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    client_ip = request.client.host if request.client else None
    try:
        await pdns_request("DELETE", f"{_SERVER}/networks/{ip}/{prefixlen}")
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="delete",
            resource_type="network",
            resource_id=f"{ip}/{prefixlen}",
            ip_address=client_ip,
        )
    except httpx.HTTPStatusError as exc:
        http_exc = _pdns_error_handler(exc)
        await audit_service.log_action(
            db,
            username=current_admin.username,
            user_id=current_admin.id,
            action="delete",
            resource_type="network",
            resource_id=f"{ip}/{prefixlen}",
            ip_address=client_ip,
            status="failure",
            details={"detail": http_exc.detail},
        )
        raise http_exc from exc

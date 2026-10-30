"""Zone access control shared by the zone routers."""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_user
from app.models.user import User
from app.services import admin_service
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request

SERVER = "/servers/localhost"

ROLE_LEVELS: dict[str, int] = {"viewer": 0, "manager": 1, "admin": 2}

# PowerDNS zone ids keep [A-Za-z0-9.-] and escape any other character as =XX
# (e.g. "/" as "=2F"). "." and ".." would be read as dot segments of the API URL.
_ZONE_ID_RE = re.compile(r"[A-Za-z0-9._=-]{1,255}")


def check_zone_id(zone_id: str) -> None:
    """Reject a zone id that is not a PowerDNS zone id."""
    if zone_id in (".", "..") or not _ZONE_ID_RE.fullmatch(zone_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid zone id",
        )


def pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Resource not found")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


@dataclass
class ZoneAccess:
    """The zone fetched from PowerDNS and the caller's effective role on it."""

    zone: dict[str, Any]
    role: str


async def _check_zone_access(
    zone_id: str,
    user: User,
    db: AsyncSession,
    audit: AuditLogger | None,
    action: str,
) -> ZoneAccess:
    check_zone_id(zone_id)
    try:
        zone: dict[str, Any] = await pdns_request("GET", f"{SERVER}/zones/{zone_id}")
    except httpx.HTTPStatusError as exc:
        http_exc = pdns_error_handler(exc)
        if audit:
            await audit.failure(action, "zone", zone_id, {"detail": http_exc.detail})
        raise http_exc from exc
    if user.is_admin:
        return ZoneAccess(zone, "admin")
    account = zone.get("account") or ""
    ua = await admin_service.get_user_role_for_account(db, user.id, account)  # type: ignore[arg-type]
    if ua is None:
        if audit:
            await audit.failure(
                action, "zone", zone_id, {"detail": "Access denied to this zone"}
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this zone",
        )
    return ZoneAccess(zone, str(ua.role))


def zone_access(
    minimum: str | None = None, action: str | None = None
) -> Callable[..., Awaitable[ZoneAccess]]:
    """Build a dependency that checks the caller's role on the ``zone_id`` zone.

    ``minimum`` is the lowest role allowed (none: any member of the zone's
    account). With ``action``, a refusal is written to the audit log under that
    action.
    """

    async def dependency(
        zone_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        audit: AuditLogger = Depends(get_audit_logger),
    ) -> ZoneAccess:
        logger = audit if action else None
        access = await _check_zone_access(
            zone_id, current_user, db, logger, action or "access"
        )
        if minimum and ROLE_LEVELS.get(access.role, -1) < ROLE_LEVELS[minimum]:
            if logger:
                await logger.failure(
                    action or "access",
                    "zone",
                    zone_id,
                    {"detail": "Insufficient rights for this operation"},
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient rights for this operation",
            )
        return access

    return dependency

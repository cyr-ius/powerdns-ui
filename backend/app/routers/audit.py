import json
from datetime import datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_admin
from app.models.smtp_settings import SmtpSettings
from app.schemas.audit import (
    AuditLogResponse,
    PdnsLogEntry,
    SmtpSettingsResponse,
    SmtpSettingsUpdate,
    SmtpTestResult,
    SyslogSettingsResponse,
    SyslogSettingsUpdate,
)
from app.services import audit_service
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/api/admin/audit", dependencies=[Depends(get_current_admin)])

_SERVER = "/servers/localhost"


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list:
    return await audit_service.list_audit_logs(
        db,
        skip=skip,
        limit=limit,
        username=username,
        action=action,
        resource_type=resource_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/count")
async def count_audit_logs(
    username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await audit_service.count_audit_logs(
        db,
        username=username,
        action=action,
        resource_type=resource_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return {"count": count}


@router.get("/pdns-logs", response_model=list[PdnsLogEntry])
async def get_pdns_logs() -> list:
    try:
        stats = await pdns_request(
            "GET", f"{_SERVER}/statistics", params={"includerings": "true"}
        )
    except httpx.HTTPStatusError:
        return []

    for item in stats:
        if (
            item.get("name") == "logmessages"
            and item.get("type") == "RingStatisticItem"
        ):
            return [
                {"name": e.get("name", ""), "value": e.get("value", "")}
                for e in item.get("value", [])
            ]
    return []


@router.get("/syslog", response_model=SyslogSettingsResponse)
async def get_syslog_settings(
    db: AsyncSession = Depends(get_db),
) -> SyslogSettingsResponse:
    cfg = await audit_service.get_syslog_settings(db)
    if cfg:
        return SyslogSettingsResponse(
            enabled=cfg.enabled,
            host=cfg.host,
            port=cfg.port,
            protocol=cfg.protocol,
            facility=cfg.facility,
            app_name=cfg.app_name,
        )
    return SyslogSettingsResponse(
        enabled=False,
        host="localhost",
        port=514,
        protocol="udp",
        facility="local0",
        app_name="pdns-ui",
    )


@router.put("/syslog", response_model=SyslogSettingsResponse)
async def update_syslog_settings(
    payload: SyslogSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> SyslogSettingsResponse:
    cfg = await audit_service.upsert_syslog_settings(db, payload.model_dump())
    return SyslogSettingsResponse(
        enabled=cfg.enabled,
        host=cfg.host,
        port=cfg.port,
        protocol=cfg.protocol,
        facility=cfg.facility,
        app_name=cfg.app_name,
    )


def _parse_filter_list(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError, ValueError:
        return []


def _smtp_response(cfg: SmtpSettings) -> SmtpSettingsResponse:
    return SmtpSettingsResponse(
        enabled=cfg.enabled,
        host=cfg.host,
        port=cfg.port,
        username=cfg.username,
        password=cfg.password,
        from_email=cfg.from_email,
        recipient_email=cfg.recipient_email,
        use_tls=cfg.use_tls,
        use_starttls=cfg.use_starttls,
        alert_actions=_parse_filter_list(cfg.alert_actions),
        alert_resources=_parse_filter_list(cfg.alert_resources),
        alert_statuses=_parse_filter_list(cfg.alert_statuses),
        env_locked=audit_service.smtp_env_locked_fields(),
    )


@router.get("/smtp", response_model=SmtpSettingsResponse)
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db),
) -> SmtpSettingsResponse:
    cfg = await audit_service.get_smtp_settings(db)
    return _smtp_response(cfg or SmtpSettings(id=1))


@router.put("/smtp", response_model=SmtpSettingsResponse)
async def update_smtp_settings(
    payload: SmtpSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> SmtpSettingsResponse:
    cfg = await audit_service.upsert_smtp_settings(db, payload.model_dump())
    await audit.success("update", "smtp_settings")
    return _smtp_response(cfg)


@router.post("/smtp/test", response_model=SmtpTestResult)
async def test_smtp_settings(
    payload: SmtpSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> SmtpTestResult:
    """Send a probe e-mail using the submitted settings.

    The form is tested as displayed — the settings need not be saved first —
    except for fields pinned by the environment, which always win.
    """
    cfg = audit_service.build_smtp_config(payload.model_dump())
    try:
        await run_in_threadpool(audit_service.send_test_email, cfg)
    except Exception as exc:
        await audit.failure("test", "smtp_settings", details={"detail": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SMTP test failed: {exc}",
        ) from exc

    await audit.success("test", "smtp_settings", cfg.recipient_email)
    return SmtpTestResult(sent=True, recipient=cfg.recipient_email)

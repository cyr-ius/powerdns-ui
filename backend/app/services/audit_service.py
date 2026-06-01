import json
import logging
import logging.handlers
import smtplib
import socket
from datetime import datetime
from email.mime.text import MIMEText

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.audit_log import AuditLog
from app.models.smtp_settings import SmtpSettings
from app.models.syslog_settings import SyslogSettings

logger = logging.getLogger(__name__)

_FACILITIES = {
    "kern": 0,
    "user": 1,
    "mail": 2,
    "daemon": 3,
    "auth": 4,
    "syslog": 5,
    "lpr": 6,
    "news": 7,
    "uucp": 8,
    "cron": 9,
    "local0": 16,
    "local1": 17,
    "local2": 18,
    "local3": 19,
    "local4": 20,
    "local5": 21,
    "local6": 22,
    "local7": 23,
}


async def log_action(
    db: AsyncSession,
    username: str,
    action: str,
    resource_type: str,
    user_id: int | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    status: str = "success",
) -> None:
    entry = AuditLog(
        username=username,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip_address=ip_address,
        status=status,
    )
    db.add(entry)
    await db.commit()

    syslog_cfg = await get_syslog_settings(db)
    if syslog_cfg and syslog_cfg.enabled:
        _send_to_syslog(syslog_cfg, entry)

    smtp_cfg = await get_smtp_settings(db)
    if smtp_cfg and smtp_cfg.enabled and _matches_alert_filters(smtp_cfg, entry):
        _send_audit_email(smtp_cfg, entry)


class AuditLogger:
    """Contexte d'audit pré-rempli avec les infos de l'utilisateur et l'IP."""

    def __init__(
        self,
        db: AsyncSession,
        username: str,
        user_id: int | None = None,
        ip: str | None = None,
    ) -> None:
        self.db = db
        self.username = username
        self.user_id = user_id
        self.ip = ip

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
        status: str = "success",
    ) -> None:
        await log_action(
            self.db,
            username=self.username,
            user_id=self.user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=self.ip,
            status=status,
        )

    async def success(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        await self.log(action, resource_type, resource_id, details, "success")

    async def failure(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        await self.log(action, resource_type, resource_id, details, "failure")


def _send_to_syslog(cfg: SyslogSettings, entry: AuditLog) -> None:
    facility = _FACILITIES.get(cfg.facility, 16)
    socktype = socket.SOCK_DGRAM if cfg.protocol == "udp" else socket.SOCK_STREAM
    try:
        handler = logging.handlers.SysLogHandler(
            address=(cfg.host, cfg.port),
            facility=facility,
            socktype=socktype,
        )
        syslog_logger = logging.getLogger(cfg.app_name)
        syslog_logger.addHandler(handler)
        syslog_logger.setLevel(logging.INFO)
        msg = (
            f"user={entry.username} action={entry.action} "
            f"resource={entry.resource_type}"
        )
        if entry.resource_id:
            msg += f":{entry.resource_id}"
        if entry.ip_address:
            msg += f" ip={entry.ip_address}"
        msg += f" status={entry.status}"
        if entry.details:
            msg += f" details={entry.details}"
        syslog_logger.info(msg)
        handler.close()
        syslog_logger.removeHandler(handler)
    except Exception as exc:
        logger.warning("Impossible d'envoyer vers syslog : %s", exc)


def _parse_filter_list(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError, ValueError:
        return []


def _matches_alert_filters(cfg: SmtpSettings, entry: AuditLog) -> bool:
    actions = _parse_filter_list(cfg.alert_actions)
    resources = _parse_filter_list(cfg.alert_resources)
    statuses = _parse_filter_list(cfg.alert_statuses)
    if actions and entry.action not in actions:
        return False
    if resources and entry.resource_type not in resources:
        return False
    if statuses and entry.status not in statuses:
        return False
    return True


async def get_smtp_settings(db: AsyncSession) -> SmtpSettings | None:
    result = await db.exec(select(SmtpSettings).where(SmtpSettings.id == 1))  # type: ignore[call-overload]
    return result.first()


async def upsert_smtp_settings(db: AsyncSession, data: dict) -> SmtpSettings:
    for key in ("alert_actions", "alert_resources", "alert_statuses"):
        if key in data and isinstance(data[key], list):
            data[key] = json.dumps(data[key])
    existing = await get_smtp_settings(db)
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.add(existing)
    else:
        existing = SmtpSettings(id=1, **data)
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing


def _send_audit_email(cfg: SmtpSettings, entry: AuditLog) -> None:
    if not cfg.recipient_email or not cfg.host:
        return
    subject = f"[pdns-ui] Audit: {entry.action} on {entry.resource_type}"
    body_lines = [
        f"User      : {entry.username}",
        f"Action    : {entry.action}",
        f"Resource  : {entry.resource_type}",
    ]
    if entry.resource_id:
        body_lines.append(f"Resource ID: {entry.resource_id}")
    if entry.ip_address:
        body_lines.append(f"IP        : {entry.ip_address}")
    body_lines.append(f"Status    : {entry.status}")
    if entry.details:
        body_lines.append(f"Details   : {entry.details}")
    body_lines.append(f"Date      : {entry.created_at}")
    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = subject
    msg["From"] = cfg.from_email or "pdns-ui@localhost"
    msg["To"] = cfg.recipient_email
    try:
        if cfg.use_tls:
            with smtplib.SMTP_SSL(cfg.host, cfg.port) as smtp:
                if cfg.username:
                    smtp.login(cfg.username, cfg.password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg.host, cfg.port) as smtp:
                if cfg.use_starttls:
                    smtp.starttls()
                if cfg.username:
                    smtp.login(cfg.username, cfg.password)
                smtp.send_message(msg)
    except Exception as exc:
        logger.warning("Impossible d'envoyer l'email d'audit : %s", exc)


async def list_audit_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AuditLog]:
    q = select(AuditLog)
    if username:
        q = q.where(AuditLog.username.contains(username))  # type: ignore[union-attr]
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if status:
        q = q.where(AuditLog.status == status)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    q = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)  # type: ignore[union-attr]
    result = await db.exec(q)  # type: ignore[call-overload]
    return list(result.all())


async def count_audit_logs(
    db: AsyncSession,
    username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    from sqlalchemy import func
    from sqlmodel import select as sel

    q = sel(func.count()).select_from(AuditLog)
    if username:
        q = q.where(AuditLog.username.contains(username))  # type: ignore[union-attr]
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if status:
        q = q.where(AuditLog.status == status)
    if date_from:
        q = q.where(AuditLog.created_at >= date_from)
    if date_to:
        q = q.where(AuditLog.created_at <= date_to)
    result = await db.exec(q)  # type: ignore[call-overload]
    return result.one()


async def get_syslog_settings(db: AsyncSession) -> SyslogSettings | None:
    result = await db.exec(select(SyslogSettings).where(SyslogSettings.id == 1))  # type: ignore[call-overload]
    return result.first()


async def upsert_syslog_settings(db: AsyncSession, data: dict) -> SyslogSettings:
    existing = await get_syslog_settings(db)
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.add(existing)
    else:
        existing = SyslogSettings(id=1, **data)
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing

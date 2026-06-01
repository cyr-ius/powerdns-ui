from datetime import datetime

from pydantic import BaseModel, model_validator


class AuditLogResponse(BaseModel):
    id: int
    username: str
    user_id: int | None
    action: str
    resource_type: str
    resource_id: str | None
    details: str | None
    ip_address: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SyslogSettingsResponse(BaseModel):
    enabled: bool
    host: str
    port: int
    protocol: str
    facility: str
    app_name: str


class SyslogSettingsUpdate(BaseModel):
    enabled: bool
    host: str
    port: int
    protocol: str
    facility: str
    app_name: str


class PdnsLogEntry(BaseModel):
    name: str
    value: str


class SmtpSettingsResponse(BaseModel):
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    from_email: str
    recipient_email: str
    use_tls: bool
    use_starttls: bool
    alert_actions: list[str] = []
    alert_resources: list[str] = []
    alert_statuses: list[str] = []


class SmtpSettingsUpdate(BaseModel):
    enabled: bool
    host: str
    port: int
    username: str
    password: str
    from_email: str
    recipient_email: str
    use_tls: bool
    use_starttls: bool
    alert_actions: list[str] = []
    alert_resources: list[str] = []
    alert_statuses: list[str] = []

    @model_validator(mode="after")
    def recipient_required_when_enabled(self) -> SmtpSettingsUpdate:
        if self.enabled and not self.recipient_email.strip():
            raise ValueError(
                "recipient_email is required when SMTP notifications are enabled"
            )
        return self

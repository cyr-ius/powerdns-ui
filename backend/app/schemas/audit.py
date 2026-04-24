from datetime import datetime

from pydantic import BaseModel


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

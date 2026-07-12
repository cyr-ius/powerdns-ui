from datetime import datetime

from pydantic import BaseModel


class AcmeApiKeyZoneCreate(BaseModel):
    name: str
    key: str | None = None
    comment: str | None = None


class AcmeApiKeyUpdate(BaseModel):
    comment: str | None = None


class AcmeApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    zones: list[str]
    zone_name: str | None
    comment: str | None
    created_at: datetime


class AcmeApiKeyCreated(AcmeApiKeyResponse):
    key: str


class AcmeApiKeyAdminResponse(AcmeApiKeyResponse):
    username: str | None = None
    user_id: int | None = None

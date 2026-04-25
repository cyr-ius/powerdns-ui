from datetime import datetime

from pydantic import BaseModel


class AcmeApiKeyCreate(BaseModel):
    name: str
    key: str | None = None


class AcmeApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    zones: list[str]
    created_at: datetime


class AcmeApiKeyCreated(AcmeApiKeyResponse):
    key: str


class AcmeApiKeyAdminResponse(AcmeApiKeyResponse):
    username: str
    user_id: int


class AcmeApiKeyZonesUpdate(BaseModel):
    zones: list[str]

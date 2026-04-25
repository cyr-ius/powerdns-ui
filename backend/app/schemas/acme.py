from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AcmeApiKeyCreate(BaseModel):
    name: str
    key: str | None = None
    key_type: Literal["acme", "api"] = "acme"


class AcmeApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    zones: list[str]
    key_type: str
    created_at: datetime


class AcmeApiKeyCreated(AcmeApiKeyResponse):
    key: str


class AcmeApiKeyAdminResponse(AcmeApiKeyResponse):
    username: str
    user_id: int


class AcmeApiKeyZonesUpdate(BaseModel):
    zones: list[str]

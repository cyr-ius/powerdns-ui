from datetime import datetime

from pydantic import BaseModel


class TokenCreate(BaseModel):
    name: str
    token: str | None = None
    comment: str | None = None


class TokenUpdate(BaseModel):
    comment: str | None = None


class TokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str
    comment: str | None
    created_at: datetime


class TokenCreated(TokenResponse):
    token: str


class TokenAdminResponse(TokenResponse):
    username: str | None = None
    user_id: int | None = None

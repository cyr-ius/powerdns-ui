from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel


class TokenDurationDays(IntEnum):
    """Durations offered when creating a token (days). Absent => unlimited."""

    SEVEN = 7
    THIRTY = 30
    NINETY = 90
    ONE_EIGHTY = 180
    THREE_SIXTY_FIVE = 365


class TokenCreate(BaseModel):
    name: str
    token: str | None = None
    comment: str | None = None
    duration_days: TokenDurationDays | None = None


class TokenUpdate(BaseModel):
    comment: str | None = None


class TokenResponse(BaseModel):
    id: int
    name: str
    token_prefix: str
    comment: str | None
    created_at: datetime
    expires_at: datetime | None
    is_expired: bool


class TokenCreated(TokenResponse):
    token: str


class TokenAdminResponse(TokenResponse):
    username: str | None = None
    user_id: int | None = None

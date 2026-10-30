from datetime import UTC, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __table_args__ = (
        Index("ix_user_oidc_identity", "oidc_issuer", "oidc_subject", unique=True),
    )

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str | None = Field(default=None)
    hashed_password: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    is_oidc: bool = Field(default=False)
    is_admin: bool = Field(default=False)
    # Bumped on logout, password change or deactivation: every session JWT
    # carries the version it was issued with, so older ones stop being accepted.
    token_version: int = Field(default=0)
    # Stable OIDC identity (issuer, subject); preferred_username can change.
    oidc_issuer: str | None = Field(default=None, max_length=255)
    oidc_subject: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

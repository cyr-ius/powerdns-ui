from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class ZoneRole(StrEnum):
    admin = "admin"
    manager = "manager"
    viewer = "viewer"


class Account(SQLModel, table=True):
    __tablename__ = "account"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserAccount(SQLModel, table=True):
    __tablename__ = "useraccount"  # pyright: ignore[reportAssignmentType]

    user_id: int = Field(foreign_key="user.id", primary_key=True)
    account_id: int = Field(foreign_key="account.id", primary_key=True)
    role: ZoneRole = Field(default=ZoneRole.admin)

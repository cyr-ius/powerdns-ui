from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "auditlog"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    user_id: int | None = Field(default=None, index=True)
    action: str = Field(index=True)
    resource_type: str = Field(index=True)
    resource_id: str | None = Field(default=None)
    details: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    status: str = Field(default="success")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

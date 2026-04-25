from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class AcmeApiKey(SQLModel, table=True):
    __tablename__ = "acmeapikey"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(max_length=100)
    key_prefix: str = Field(max_length=12)
    key_hash: str = Field(unique=True, index=True)
    zones: str = Field(default="[]")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

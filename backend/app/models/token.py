from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class PersonalAccessToken(SQLModel, table=True):
    __tablename__ = "personalaccesstoken"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(max_length=100)
    token_prefix: str = Field(max_length=12)
    token_hash: str = Field(unique=True, index=True)
    comment: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

from sqlmodel import Field, SQLModel


class RecordType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=20)
    enabled: bool = Field(default=True)
    applicable_to: str = Field(default="both")  # "direct", "reverse", "both"

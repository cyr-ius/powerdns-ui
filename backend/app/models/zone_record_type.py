from sqlmodel import Field, SQLModel


class ZoneRecordType(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    zone_id: str = Field(index=True, max_length=255)
    record_type_name: str = Field(max_length=20)

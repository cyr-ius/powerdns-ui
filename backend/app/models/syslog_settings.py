from sqlmodel import Field, SQLModel


class SyslogSettings(SQLModel, table=True):
    __tablename__ = "syslogsettings"

    id: int | None = Field(default=None, primary_key=True)
    enabled: bool = Field(default=False)
    host: str = Field(default="localhost")
    port: int = Field(default=514)
    protocol: str = Field(default="udp")
    facility: str = Field(default="local0")
    app_name: str = Field(default="pdns-ui")

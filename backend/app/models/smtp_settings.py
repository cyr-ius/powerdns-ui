from sqlmodel import Field, SQLModel


class SmtpSettings(SQLModel, table=True):
    __tablename__ = "smtpsettings"

    id: int | None = Field(default=None, primary_key=True)
    enabled: bool = Field(default=False)
    host: str = Field(default="localhost")
    port: int = Field(default=587)
    username: str = Field(default="")
    password: str = Field(default="")
    from_email: str = Field(default="")
    recipient_email: str = Field(default="")
    use_tls: bool = Field(default=False)
    use_starttls: bool = Field(default=True)
    alert_actions: str = Field(default="")
    alert_resources: str = Field(default="")
    alert_statuses: str = Field(default="")

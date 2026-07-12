from sqlmodel import Field, SQLModel


class OidcSettings(SQLModel, table=True):
    __tablename__ = "oidcsettings"

    id: int = Field(default=1, primary_key=True)
    enabled: bool = Field(default=False)
    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    discovery_url: str = Field(default="")
    redirect_uri: str = Field(default="")
    scopes: str = Field(default="openid email profile")
    local_login_disabled: bool = Field(default=False)
    post_logout_redirect_uri: str = Field(default="")

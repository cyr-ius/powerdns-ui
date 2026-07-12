from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    is_oidc: bool
    is_admin: bool
    is_account_admin: bool = False


class OidcLoginResponse(BaseModel):
    authorization_url: str


class LogoutResponse(BaseModel):
    # Set when the provider supports RP-initiated logout: the browser must be
    # sent there to terminate the SSO session as well.
    logout_url: str | None = None


class OidcConfig(BaseModel):
    enabled: bool
    client_id: str | None = None
    local_login_disabled: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

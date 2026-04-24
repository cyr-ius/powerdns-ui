from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    is_oidc: bool
    is_admin: bool


class OidcLoginResponse(BaseModel):
    authorization_url: str


class OidcConfig(BaseModel):
    enabled: bool
    client_id: str | None = None
    local_login_disabled: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

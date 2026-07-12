from pydantic import BaseModel, field_validator

from app.models.account import ZoneRole


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    is_oidc: bool
    is_admin: bool
    accounts: list[str]
    account_roles: dict[str, str] = {}


class UserBasicResponse(BaseModel):
    id: int
    username: str


class ZoneMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str | None
    role: str


class ZoneMemberAdd(BaseModel):
    user_id: int
    role: ZoneRole


class ZoneMemberUpdate(BaseModel):
    role: ZoneRole


class UserCreateRequest(BaseModel):
    username: str
    password: str
    email: str | None = None
    is_admin: bool = False


class UserUpdateRequest(BaseModel):
    email: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class AccountResponse(BaseModel):
    id: int
    name: str
    description: str | None
    user_count: int


class AccountCreate(BaseModel):
    name: str
    description: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class UserAccountAssign(BaseModel):
    user_ids: list[int]


class OidcSettingsResponse(BaseModel):
    enabled: bool
    client_id: str
    client_secret: str
    discovery_url: str
    redirect_uri: str
    scopes: str
    local_login_disabled: bool = False
    post_logout_redirect_uri: str = ""
    # Fields pinned by environment variables: read-only in the settings screen.
    env_locked: list[str] = []


class OidcSettingsUpdate(BaseModel):
    enabled: bool
    client_id: str = ""
    client_secret: str = ""
    discovery_url: str = ""
    redirect_uri: str = ""
    scopes: str = "openid email profile"
    local_login_disabled: bool = False
    post_logout_redirect_uri: str = ""


# ── Record Types ──────────────────────────────────────────────────────────────


class RecordTypeResponse(BaseModel):
    id: int
    name: str
    enabled: bool
    applicable_to: str


class RecordTypeCreate(BaseModel):
    name: str
    enabled: bool = True
    applicable_to: str = "both"

    @field_validator("applicable_to")
    @classmethod
    def validate_applicable_to(cls, v: str) -> str:
        if v not in ("direct", "reverse", "both"):
            raise ValueError("applicable_to must be 'direct', 'reverse', or 'both'")
        return v


class RecordTypeUpdate(BaseModel):
    enabled: bool | None = None
    applicable_to: str | None = None

    @field_validator("applicable_to")
    @classmethod
    def validate_applicable_to(cls, v: str | None) -> str | None:
        if v is not None and v not in ("direct", "reverse", "both"):
            raise ValueError("applicable_to must be 'direct', 'reverse', or 'both'")
        return v


# ── Zone Record Types ─────────────────────────────────────────────────────────


class ZoneRecordTypesResponse(BaseModel):
    types: list[str]
    is_custom: bool


class ZoneRecordTypesUpdate(BaseModel):
    types: list[str]

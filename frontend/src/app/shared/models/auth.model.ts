export interface User {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  is_oidc: boolean;
  is_admin: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OidcConfig {
  enabled: boolean;
  client_id: string | null;
  local_login_disabled: boolean;
}

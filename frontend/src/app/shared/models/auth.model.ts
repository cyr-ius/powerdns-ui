export interface User {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  is_oidc: boolean;
  is_admin: boolean;
  is_account_admin: boolean;
}

export interface OidcConfig {
  enabled: boolean;
  client_id: string | null;
  local_login_disabled: boolean;
}

export interface LogoutResponse {
  /** Provider end_session URL when RP-initiated logout applies. */
  logout_url: string | null;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  is_oidc: boolean;
  is_admin: boolean;
  accounts: string[];
  account_roles: Record<string, string>;
}

export interface Account {
  id: number;
  name: string;
  description: string | null;
  user_count: number;
}

export interface AccountCreate {
  name: string;
  description?: string | null;
}

export interface OidcSettings {
  enabled: boolean;
  client_id: string;
  client_secret: string;
  discovery_url: string;
  redirect_uri: string;
  scopes: string;
  local_login_disabled: boolean;
}

export interface RecordType {
  id: number;
  name: string;
  enabled: boolean;
  applicable_to: "direct" | "reverse" | "both";
}

export interface RecordTypeCreate {
  name: string;
  enabled: boolean;
  applicable_to: "direct" | "reverse" | "both";
}

export interface ZoneRecordTypes {
  types: string[];
  is_custom: boolean;
}

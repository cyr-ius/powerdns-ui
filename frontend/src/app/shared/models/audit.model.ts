export interface AuditLog {
  id: number;
  username: string;
  user_id: number | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: string | null;
  ip_address: string | null;
  status: string;
  created_at: string;
}

export interface SyslogSettings {
  enabled: boolean;
  host: string;
  port: number;
  protocol: "udp" | "tcp";
  facility: string;
  app_name: string;
}

export interface PdnsLogEntry {
  name: string;
  value: string;
}

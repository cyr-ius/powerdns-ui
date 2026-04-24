export type ZoneRole = "admin" | "manager" | "viewer";

export interface ZoneMember {
  user_id: number;
  username: string;
  email: string | null;
  role: ZoneRole;
}

export interface UserBasic {
  id: number;
  username: string;
}

export interface DnsRecord {
  content: string;
  disabled: boolean;
}

export interface RRset {
  name: string;
  type: string;
  ttl: number;
  records: DnsRecord[];
  comments: unknown[];
}

export interface Zone {
  id: string;
  name: string;
  kind: string;
  serial: number | null;
  dnssec: boolean;
  account: string | null;
  catalog: string | null;
  masters: string[];
}

export interface ZoneDetail extends Zone {
  rrsets: RRset[];
}

export interface ZoneCreate {
  name: string;
  kind: string;
  nameservers: string[];
  masters: string[];
  account?: string;
  catalog?: string;
}

export interface ZoneUpdate {
  name: string;
  kind: string;
  account?: string | null;
  catalog?: string | null;
  masters?: string[];
}

export interface RRsetChange {
  changetype: "REPLACE" | "DELETE";
  name: string;
  type: string;
  ttl?: number;
  records?: DnsRecord[];
}

export interface PatchRRsets {
  rrsets: RRsetChange[];
}

// ── Metadata ──────────────────────────────────────────────────────────────────

export interface Metadata {
  kind: string;
  metadata: string[];
}

// ── CryptoKeys ────────────────────────────────────────────────────────────────

export interface CryptoKey {
  id: number;
  keytype: string;
  active: boolean;
  published: boolean;
  dnskey: string | null;
  ds: string[] | null;
  cds: string[] | null;
  algorithm: string | null;
  bits: number | null;
}

export interface CryptoKeyCreate {
  keytype: string;
  active: boolean;
  published?: boolean;
  algorithm?: string;
  bits?: number;
}

export interface CryptoKeyUpdate {
  active?: boolean;
  published?: boolean;
}

// ── TSIG Keys ─────────────────────────────────────────────────────────────────

export interface TsigKey {
  id: string;
  name: string;
  algorithm: string;
  key: string | null;
  type: string | null;
}

export interface TsigKeyCreate {
  name: string;
  algorithm: string;
  key?: string;
}

// ── Search ────────────────────────────────────────────────────────────────────

export interface SearchResult {
  name: string;
  object_type: "zone" | "record" | "comment";
  zone_id?: string;
  zone?: string;
  type?: string;
  content?: string;
  disabled?: boolean;
  ttl?: number;
}

// ── Statistics ────────────────────────────────────────────────────────────────

export interface SimpleStatisticItem {
  name?: string;
  value?: string;
}

export interface StatisticItem {
  name?: string;
  type?: string;
  value?: string | SimpleStatisticItem[];
  size?: number;
}

// ── Cache ─────────────────────────────────────────────────────────────────────

export interface CacheFlushResult {
  count?: number;
  result?: string;
}

// ── Server ────────────────────────────────────────────────────────────────────

export interface ConfigSetting {
  name: string;
  type?: string;
  value?: string;
}

export interface ServerInfo {
  type?: string;
  id?: string;
  daemon_type?: string;
  version?: string;
  url?: string;
}

// ── Autoprimaries ─────────────────────────────────────────────────────────────

export interface Autoprimary {
  ip: string;
  nameserver: string;
  account?: string | null;
}

// ── Networks ──────────────────────────────────────────────────────────────────

export interface Network {
  network: string;
  view: string;
}

// ── Views ─────────────────────────────────────────────────────────────────────

export interface ViewDetail {
  name: string;
  zones: string[];
}

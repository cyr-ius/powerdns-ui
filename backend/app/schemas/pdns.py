from pydantic import BaseModel


class Record(BaseModel):
    content: str
    disabled: bool = False


class Comment(BaseModel):
    content: str
    account: str = ""
    modified_at: int | None = None


class RRset(BaseModel):
    name: str
    type: str
    ttl: int = 3600
    records: list[Record] = []
    comments: list[Comment] = []


class Zone(BaseModel):
    model_config = {"extra": "allow"}

    id: str
    name: str
    kind: str
    serial: int | None = None
    dnssec: bool = False
    account: str | None = None
    catalog: str | None = None
    masters: list[str] = []


class ZoneDetail(Zone):
    rrsets: list[RRset] = []


class ZoneCreate(BaseModel):
    name: str
    kind: str = "Native"
    nameservers: list[str] = []
    masters: list[str] = []
    account: str | None = None
    catalog: str | None = None


class ZoneUpdate(BaseModel):
    name: str
    kind: str
    account: str | None = None
    catalog: str | None = None
    masters: list[str] = []


class RRsetChange(BaseModel):
    changetype: str
    name: str
    type: str
    ttl: int | None = None
    records: list[Record] | None = None


class PatchRRsets(BaseModel):
    rrsets: list[RRsetChange]


# ── Metadata ──────────────────────────────────────────────────────────────────


class Metadata(BaseModel):
    kind: str
    metadata: list[str] = []


# ── CryptoKeys (DNSSEC) ───────────────────────────────────────────────────────


class CryptoKey(BaseModel):
    model_config = {"extra": "allow"}

    id: int | None = None
    keytype: str | None = None
    active: bool = True
    published: bool = True
    dnskey: str | None = None
    ds: list[str] | None = None
    cds: list[str] | None = None
    algorithm: str | None = None
    bits: int | None = None


class CryptoKeyCreate(BaseModel):
    keytype: str = "ksk"
    active: bool = True
    algorithm: str | None = None
    bits: int | None = None
    content: str | None = None


class CryptoKeyUpdate(BaseModel):
    active: bool | None = None
    published: bool | None = None


# ── TSIG Keys ─────────────────────────────────────────────────────────────────


class TsigKey(BaseModel):
    model_config = {"extra": "allow"}

    id: str | None = None
    name: str
    algorithm: str
    key: str | None = None
    type: str | None = None


class TsigKeyCreate(BaseModel):
    name: str
    algorithm: str
    key: str | None = None


class TsigKeyUpdate(BaseModel):
    name: str | None = None
    algorithm: str | None = None
    key: str | None = None


# ── Search ────────────────────────────────────────────────────────────────────


class SearchResult(BaseModel):
    model_config = {"extra": "allow"}

    name: str
    object_type: str  # "zone" | "record" | "comment"
    zone_id: str | None = None
    zone: str | None = None
    type: str | None = None
    content: str | None = None
    disabled: bool | None = None
    ttl: int | None = None


# ── Statistics ────────────────────────────────────────────────────────────────


class SimpleStatisticItem(BaseModel):
    name: str | None = None
    value: str | None = None


class StatisticItem(BaseModel):
    model_config = {"extra": "allow"}

    name: str | None = None
    type: str | None = None
    value: str | list[SimpleStatisticItem] | None = None
    size: int | None = None


# ── Cache ─────────────────────────────────────────────────────────────────────


class CacheFlushResult(BaseModel):
    count: int | None = None
    result: str | None = None


# ── Server ────────────────────────────────────────────────────────────────────


class ConfigSetting(BaseModel):
    name: str
    type: str | None = None
    value: str | None = None


class ServerInfo(BaseModel):
    model_config = {"extra": "allow"}

    type: str | None = None
    id: str | None = None
    daemon_type: str | None = None
    version: str | None = None
    url: str | None = None


# ── Autoprimaries ─────────────────────────────────────────────────────────────


class Autoprimary(BaseModel):
    ip: str
    nameserver: str
    account: str | None = None


class AutoprimaryCreate(BaseModel):
    ip: str
    nameserver: str
    account: str | None = None


# ── Networks ──────────────────────────────────────────────────────────────────


class Network(BaseModel):
    network: str
    view: str


class NetworkAssign(BaseModel):
    view: str


# ── Views ─────────────────────────────────────────────────────────────────────


class ViewZoneAdd(BaseModel):
    name: str

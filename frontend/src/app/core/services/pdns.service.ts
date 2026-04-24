import { HttpClient, HttpParams } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";
import { ZoneRecordTypes } from "../../shared/models/admin.model";
import {
  Autoprimary,
  CacheFlushResult,
  ConfigSetting,
  CryptoKey,
  CryptoKeyCreate,
  CryptoKeyUpdate,
  Metadata,
  Network,
  PatchRRsets,
  SearchResult,
  ServerInfo,
  StatisticItem,
  TsigKey,
  TsigKeyCreate,
  UserBasic,
  Zone,
  ZoneCreate,
  ZoneDetail,
  ZoneMember,
  ZoneRole,
  ZoneUpdate,
} from "../../shared/models/pdns.model";

@Injectable({ providedIn: "root" })
export class PdnsService {
  private readonly http = inject(HttpClient);

  // ── Zones ────────────────────────────────────────────────────────────────

  getZones(): Promise<Zone[]> {
    return firstValueFrom(this.http.get<Zone[]>("/api/zones"));
  }

  getZone(id: string): Promise<ZoneDetail> {
    return firstValueFrom(this.http.get<ZoneDetail>(`/api/zones/${id}`));
  }

  createZone(payload: ZoneCreate): Promise<ZoneDetail> {
    return firstValueFrom(this.http.post<ZoneDetail>("/api/zones", payload));
  }

  updateZone(id: string, payload: ZoneUpdate): Promise<void> {
    return firstValueFrom(this.http.put<void>(`/api/zones/${id}`, payload));
  }

  deleteZone(id: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/zones/${id}`));
  }

  patchRRsets(zoneId: string, patch: PatchRRsets): Promise<unknown> {
    return firstValueFrom(this.http.patch(`/api/zones/${zoneId}/rrsets`, patch));
  }

  notifySlaves(zoneId: string): Promise<{ result: string }> {
    return firstValueFrom(this.http.put<{ result: string }>(`/api/zones/${zoneId}/notify`, null));
  }

  axfrRetrieve(zoneId: string): Promise<{ result: string }> {
    return firstValueFrom(this.http.put<{ result: string }>(`/api/zones/${zoneId}/axfr-retrieve`, null));
  }

  exportZone(zoneId: string): Promise<string> {
    return firstValueFrom(this.http.get(`/api/zones/${zoneId}/export`, { responseType: "text" }));
  }

  // ── Metadata ─────────────────────────────────────────────────────────────

  getMetadata(zoneId: string): Promise<Metadata[]> {
    return firstValueFrom(this.http.get<Metadata[]>(`/api/zones/${zoneId}/metadata`));
  }

  setMetadata(zoneId: string, kind: string, values: string[]): Promise<Metadata> {
    return firstValueFrom(
      this.http.put<Metadata>(`/api/zones/${zoneId}/metadata/${kind}`, {
        kind,
        metadata: values,
      }),
    );
  }

  deleteMetadata(zoneId: string, kind: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/zones/${zoneId}/metadata/${kind}`));
  }

  // ── CryptoKeys ────────────────────────────────────────────────────────────

  getCryptoKeys(zoneId: string): Promise<CryptoKey[]> {
    return firstValueFrom(this.http.get<CryptoKey[]>(`/api/zones/${zoneId}/cryptokeys`));
  }

  createCryptoKey(zoneId: string, payload: CryptoKeyCreate): Promise<CryptoKey> {
    return firstValueFrom(this.http.post<CryptoKey>(`/api/zones/${zoneId}/cryptokeys`, payload));
  }

  updateCryptoKey(zoneId: string, keyId: number, payload: CryptoKeyUpdate): Promise<unknown> {
    return firstValueFrom(this.http.put(`/api/zones/${zoneId}/cryptokeys/${keyId}`, payload));
  }

  deleteCryptoKey(zoneId: string, keyId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/zones/${zoneId}/cryptokeys/${keyId}`));
  }

  rectifyZone(zoneId: string): Promise<unknown> {
    return firstValueFrom(this.http.put(`/api/zones/${zoneId}/rectify`, null));
  }

  // ── TSIG Keys ─────────────────────────────────────────────────────────────

  getTsigKeys(): Promise<TsigKey[]> {
    return firstValueFrom(this.http.get<TsigKey[]>("/api/tsigkeys"));
  }

  getTsigKey(id: string): Promise<TsigKey> {
    return firstValueFrom(this.http.get<TsigKey>(`/api/tsigkeys/${id}`));
  }

  createTsigKey(payload: TsigKeyCreate): Promise<TsigKey> {
    return firstValueFrom(this.http.post<TsigKey>("/api/tsigkeys", payload));
  }

  deleteTsigKey(id: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/tsigkeys/${id}`));
  }

  // ── Zone Members ─────────────────────────────────────────────────────────

  getZoneRole(zoneId: string): Promise<{ role: ZoneRole }> {
    return firstValueFrom(this.http.get<{ role: ZoneRole }>(`/api/zones/${zoneId}/role`));
  }

  getZoneMembers(zoneId: string): Promise<ZoneMember[]> {
    return firstValueFrom(this.http.get<ZoneMember[]>(`/api/zones/${zoneId}/members`));
  }

  addZoneMember(zoneId: string, userId: number, role: ZoneRole): Promise<ZoneMember> {
    return firstValueFrom(this.http.post<ZoneMember>(`/api/zones/${zoneId}/members`, { user_id: userId, role }));
  }

  updateZoneMember(zoneId: string, userId: number, role: ZoneRole): Promise<ZoneMember> {
    return firstValueFrom(this.http.patch<ZoneMember>(`/api/zones/${zoneId}/members/${userId}`, { role }));
  }

  removeZoneMember(zoneId: string, userId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/zones/${zoneId}/members/${userId}`));
  }

  getUsers(): Promise<UserBasic[]> {
    return firstValueFrom(this.http.get<UserBasic[]>("/api/zones/users"));
  }

  // ── Accounts ─────────────────────────────────────────────────────────────

  getAccounts(): Promise<string[]> {
    return firstValueFrom(this.http.get<string[]>("/api/accounts"));
  }

  // ── Server ────────────────────────────────────────────────────────────────

  getServerInfo(): Promise<ServerInfo> {
    return firstValueFrom(this.http.get<ServerInfo>("/api/server"));
  }

  getConfig(): Promise<ConfigSetting[]> {
    return firstValueFrom(this.http.get<ConfigSetting[]>("/api/config"));
  }

  // ── Search ────────────────────────────────────────────────────────────────

  search(q: string, max = 100, objectType = "all"): Promise<SearchResult[]> {
    const params = new HttpParams().set("q", q).set("max", max).set("object_type", objectType);
    return firstValueFrom(this.http.get<SearchResult[]>("/api/search", { params }));
  }

  // ── Statistics ────────────────────────────────────────────────────────────

  getStatistics(includerings = false): Promise<StatisticItem[]> {
    const params = new HttpParams().set("includerings", String(includerings));
    return firstValueFrom(this.http.get<StatisticItem[]>("/api/statistics", { params }));
  }

  // ── Cache ─────────────────────────────────────────────────────────────────

  flushCache(domain: string): Promise<CacheFlushResult> {
    const params = new HttpParams().set("domain", domain);
    return firstValueFrom(this.http.put<CacheFlushResult>("/api/cache/flush", null, { params }));
  }

  // ── Catalogues ────────────────────────────────────────────────────────────

  getCatalogues(): Promise<Zone[]> {
    return firstValueFrom(this.http.get<Zone[]>("/api/catalogues"));
  }

  createCatalogue(payload: ZoneCreate): Promise<ZoneDetail> {
    return firstValueFrom(this.http.post<ZoneDetail>("/api/catalogues", payload));
  }

  deleteCatalogue(zoneId: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/catalogues/${zoneId}`));
  }

  getCatalogueMembers(zoneId: string): Promise<Zone[]> {
    return firstValueFrom(this.http.get<Zone[]>(`/api/catalogues/${zoneId}/members`));
  }

  addCatalogueMember(catalogueId: string, memberZoneId: string): Promise<unknown> {
    return firstValueFrom(this.http.post(`/api/catalogues/${catalogueId}/members/${memberZoneId}`, null));
  }

  removeCatalogueMember(catalogueId: string, memberZoneId: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/catalogues/${catalogueId}/members/${memberZoneId}`));
  }

  // ── Autoprimaries ─────────────────────────────────────────────────────────

  getAutoprimaries(): Promise<Autoprimary[]> {
    return firstValueFrom(this.http.get<Autoprimary[]>("/api/autoprimaries"));
  }

  createAutoprimary(payload: Autoprimary): Promise<unknown> {
    return firstValueFrom(this.http.post("/api/autoprimaries", payload));
  }

  deleteAutoprimary(ip: string, nameserver: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/autoprimaries/${ip}/${nameserver}`));
  }

  // ── Networks ──────────────────────────────────────────────────────────────

  getNetworks(): Promise<Network[]> {
    return firstValueFrom(this.http.get<Network[]>("/api/networks"));
  }

  assignNetworkView(ip: string, prefixlen: number, view: string): Promise<unknown> {
    return firstValueFrom(this.http.put(`/api/networks/${ip}/${prefixlen}`, { view }));
  }

  deleteNetwork(ip: string, prefixlen: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/networks/${ip}/${prefixlen}`));
  }

  // ── Views ─────────────────────────────────────────────────────────────────

  getViews(): Promise<string[]> {
    return firstValueFrom(this.http.get<string[]>("/api/views"));
  }

  getViewZones(view: string): Promise<string[]> {
    return firstValueFrom(this.http.get<string[]>(`/api/views/${view}`));
  }

  addZoneToView(view: string, name: string): Promise<unknown> {
    return firstValueFrom(this.http.post(`/api/views/${view}`, { name }));
  }

  removeZoneFromView(view: string, zoneId: string): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/views/${view}/${zoneId}`));
  }

  // ── Zone Record Types ─────────────────────────────────────────────────────

  getZoneRecordTypes(zoneId: string): Promise<ZoneRecordTypes> {
    return firstValueFrom(this.http.get<ZoneRecordTypes>(`/api/zones/${zoneId}/record-types`));
  }

  setZoneRecordTypes(zoneId: string, types: string[]): Promise<ZoneRecordTypes> {
    return firstValueFrom(this.http.put<ZoneRecordTypes>(`/api/zones/${zoneId}/record-types`, { types }));
  }
}

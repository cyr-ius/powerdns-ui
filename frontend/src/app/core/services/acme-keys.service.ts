import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";

export interface AcmeApiKey {
  id: number;
  name: string;
  key_prefix: string;
  zones: string[];
  zone_name: string | null;
  comment: string | null;
  created_at: string;
  last_used_at: string | null;
  username?: string;
  user_id?: number;
}

export interface AcmeApiKeyCreated extends AcmeApiKey {
  key: string;
}

@Injectable({ providedIn: "root" })
export class AcmeKeysService {
  private readonly http = inject(HttpClient);

  /** Lists all ACME keys, across all users/zones (admin only). */
  listAllKeys(): Promise<AcmeApiKey[]> {
    return firstValueFrom(this.http.get<AcmeApiKey[]>("/api/acme-keys/all"));
  }

  /** Deletes an ACME key, regardless of owner (admin only). */
  deleteKey(keyId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/acme-keys/${keyId}`));
  }

  /** Reassigns the owner of an ACME key to another user (admin only). */
  reassignOwner(keyId: number, userId: number): Promise<AcmeApiKey> {
    return firstValueFrom(this.http.patch<AcmeApiKey>(`/api/acme-keys/${keyId}/owner`, { user_id: userId }));
  }

  // ── Zone-centric methods for ACME keys ──────────────────────────────

  /** Lists the ACME keys of a zone (zone admin required). */
  listZoneAcmeKeys(zoneId: string): Promise<AcmeApiKey[]> {
    return firstValueFrom(this.http.get<AcmeApiKey[]>(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys`));
  }

  /** Creates an ACME key for a zone (zone admin required). */
  createZoneAcmeKey(zoneId: string, name: string, key?: string, comment?: string): Promise<AcmeApiKeyCreated> {
    return firstValueFrom(
      this.http.post<AcmeApiKeyCreated>(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys`, {
        name,
        key: key || undefined,
        comment: comment || undefined,
      }),
    );
  }

  /** Updates the name and/or comment of a zone ACME key. */
  updateZoneAcmeKey(zoneId: string, keyId: number, name: string, comment: string | null): Promise<AcmeApiKey> {
    return firstValueFrom(
      this.http.patch<AcmeApiKey>(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys/${keyId}`, {
        name,
        comment,
      }),
    );
  }

  /** Deletes a zone ACME key. */
  deleteZoneAcmeKey(zoneId: string, keyId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys/${keyId}`));
  }
}

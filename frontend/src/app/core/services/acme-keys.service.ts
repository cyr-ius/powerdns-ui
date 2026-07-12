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
  username?: string;
  user_id?: number;
}

export interface AcmeApiKeyCreated extends AcmeApiKey {
  key: string;
}

@Injectable({ providedIn: "root" })
export class AcmeKeysService {
  private readonly http = inject(HttpClient);

  /** Liste toutes les clés ACME, tous utilisateurs/zones confondus (admin uniquement). */
  listAllKeys(): Promise<AcmeApiKey[]> {
    return firstValueFrom(this.http.get<AcmeApiKey[]>("/api/acme-keys/all"));
  }

  /** Supprime une clé ACME, quel qu'en soit le propriétaire (admin uniquement). */
  deleteKey(keyId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/acme-keys/${keyId}`));
  }

  // ── Méthodes zone-centric pour les clés ACME ──────────────────────────────

  /** Liste les clés ACME d'une zone (admin de zone requis). */
  listZoneAcmeKeys(zoneId: string): Promise<AcmeApiKey[]> {
    return firstValueFrom(this.http.get<AcmeApiKey[]>(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys`));
  }

  /** Crée une clé ACME pour une zone (admin de zone requis). */
  createZoneAcmeKey(zoneId: string, name: string, key?: string, comment?: string): Promise<AcmeApiKeyCreated> {
    return firstValueFrom(
      this.http.post<AcmeApiKeyCreated>(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys`, {
        name,
        key: key || undefined,
        comment: comment || undefined,
      }),
    );
  }

  /** Met à jour le commentaire d'une clé ACME de zone. */
  updateZoneAcmeKey(zoneId: string, keyId: number, comment: string | null): Promise<AcmeApiKey> {
    return firstValueFrom(
      this.http.patch<AcmeApiKey>(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys/${keyId}`, { comment }),
    );
  }

  /** Supprime une clé ACME de zone. */
  deleteZoneAcmeKey(zoneId: string, keyId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/zones/${encodeURIComponent(zoneId)}/acme-keys/${keyId}`));
  }
}

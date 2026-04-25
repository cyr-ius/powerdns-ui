import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";

export interface AcmeApiKey {
  id: number;
  name: string;
  key_prefix: string;
  zones: string[];
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

  listKeys(): Promise<AcmeApiKey[]> {
    return firstValueFrom(this.http.get<AcmeApiKey[]>("/api/acme-keys"));
  }

  listAllKeys(): Promise<AcmeApiKey[]> {
    return firstValueFrom(this.http.get<AcmeApiKey[]>("/api/acme-keys/all"));
  }

  createKey(name: string, key?: string): Promise<AcmeApiKeyCreated> {
    return firstValueFrom(this.http.post<AcmeApiKeyCreated>("/api/acme-keys", { name, key: key || undefined }));
  }

  updateZones(keyId: number, zones: string[]): Promise<AcmeApiKey> {
    return firstValueFrom(this.http.put<AcmeApiKey>(`/api/acme-keys/${keyId}/zones`, { zones }));
  }

  deleteKey(keyId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/acme-keys/${keyId}`));
  }
}

import { HttpClient } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { firstValueFrom } from "rxjs";
import { ConfigSetting } from "../../shared/models/pdns.model";

@Injectable({ providedIn: "root" })
export class ServerService {
  private readonly http = inject(HttpClient);

  readonly backendType = signal<string | null>(null);

  // Views and Networks are only supported by the LMDB backend
  // launch can be "lmdb", "lmdb:primary", etc.
  readonly supportsViewsAndNetworks = computed(() => {
    const launch = this.backendType();
    if (!launch) return false;
    return launch.split(",").some((v) => v.trim().toLowerCase().startsWith("lmdb"));
  });

  async init(): Promise<void> {
    try {
      const config = await firstValueFrom(this.http.get<ConfigSetting[]>("/api/config"));
      const launchSetting = config.find((s) => s.name === "launch");
      this.backendType.set(launchSetting?.value ?? null);
    } catch {
      // Non-admin or unreachable — leave null (features hidden)
    }
  }
}

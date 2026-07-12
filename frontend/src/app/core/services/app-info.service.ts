import { HttpClient } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { firstValueFrom } from "rxjs";

export interface AppInfo {
  version: string;
  github: string;
  github_repository: string;
  issues_url: string;
  swagger_enabled: boolean;
  docs_url: string | null;
  health_url: string;
  api_keys_enabled: boolean;
}

export interface GithubRelease {
  tag_name: string;
  html_url: string;
  name: string;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
}

@Injectable({ providedIn: "root" })
export class AppInfoService {
  private readonly http = inject(HttpClient);

  readonly appInfo = signal<AppInfo | null>(null);
  readonly latestRelease = signal<GithubRelease | null>(null);
  readonly releaseCheckDone = signal(false);

  readonly health = signal<HealthStatus | null>(null);
  readonly healthChecking = signal(false);
  readonly healthy = computed(() => this.health()?.status === "healthy");

  // Personal access tokens are hidden entirely when the backend disables them.
  readonly apiKeysEnabled = computed(() => this.appInfo()?.api_keys_enabled ?? false);
  readonly swaggerEnabled = computed(() => this.appInfo()?.swagger_enabled ?? false);

  readonly updateAvailable = computed(() => {
    const info = this.appInfo();
    const latest = this.latestRelease();
    if (!info || !latest) return false;
    return latest.tag_name.replace(/^v/, "") !== info.version;
  });

  private inFlight: Promise<void> | null = null;

  /** Fetch the metadata once; a failed attempt is retried by the next caller. */
  async load(): Promise<void> {
    if (this.appInfo()) return;
    this.inFlight ??= this.fetch().finally(() => (this.inFlight = null));
    await this.inFlight;
  }

  private async fetch(): Promise<void> {
    try {
      const info = await firstValueFrom(this.http.get<AppInfo>("/api/info"));
      this.appInfo.set(info);
      try {
        const release = await firstValueFrom(
          this.http.get<GithubRelease>(`https://api.github.com/repos/${info.github_repository}/releases/latest`, {
            headers: { Accept: "application/vnd.github+json" },
          }),
        );
        this.latestRelease.set(release);
      } catch {
        // GitHub rate limit or no release
      }
    } catch {
      // backend unavailable — appInfo stays null so a later view retries
    } finally {
      this.releaseCheckDone.set(true);
    }
  }

  /** Probe the health endpoint; a failure leaves the status null, reported as down. */
  async checkHealth(): Promise<void> {
    this.healthChecking.set(true);
    try {
      this.health.set(await firstValueFrom(this.http.get<HealthStatus>("/api/health")));
    } catch {
      this.health.set(null);
    } finally {
      this.healthChecking.set(false);
    }
  }
}

import { HttpClient } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { firstValueFrom } from "rxjs";

interface AppInfo {
  version: string;
  github: string;
  github_repository: string;
  docs_url: string;
}

interface GithubRelease {
  tag_name: string;
  html_url: string;
  name: string;
}

@Injectable({ providedIn: "root" })
export class AppInfoService {
  private readonly http = inject(HttpClient);

  readonly appInfo = signal<AppInfo | null>(null);
  readonly latestRelease = signal<GithubRelease | null>(null);
  readonly releaseCheckDone = signal(false);

  readonly updateAvailable = computed(() => {
    const info = this.appInfo();
    const latest = this.latestRelease();
    if (!info || !latest) return false;
    return latest.tag_name.replace(/^v/, "") !== info.version;
  });

  private loaded = false;

  async load(): Promise<void> {
    if (this.loaded) return;
    this.loaded = true;
    try {
      const info = await firstValueFrom(this.http.get<AppInfo>("/api/info"));
      this.appInfo.set(info);
      try {
        const release = await firstValueFrom(
          this.http.get<GithubRelease>(
            `https://api.github.com/repos/${info.github_repository}/releases/latest`,
            { headers: { Accept: "application/vnd.github+json" } },
          ),
        );
        this.latestRelease.set(release);
      } catch {
        // GitHub rate limit or no release
      }
    } catch {
      // backend unavailable
    } finally {
      this.releaseCheckDone.set(true);
    }
  }
}

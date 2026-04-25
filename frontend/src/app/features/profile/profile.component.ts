import { DatePipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { RouterLink } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { AuthService } from "../../core/services/auth.service";
import { AcmeApiKey, AcmeKeysService } from "../../core/services/acme-keys.service";
import { PdnsService } from "../../core/services/pdns.service";
import { Theme, ThemeService } from "../../core/services/theme.service";
import { TranslateModule, TranslateService } from "@ngx-translate/core";
import { Zone } from "../../shared/models/pdns.model";

type Tab = "info" | "appearance" | "password" | "apikeys";

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

@Component({
  selector: "app-profile",
  imports: [DatePipe, RouterLink, FormField, TranslateModule],
  templateUrl: "./profile.component.html",
  styleUrl: "./profile.component.css",
})
export class ProfileComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly themeService = inject(ThemeService);
  private readonly http = inject(HttpClient);
  private readonly translate = inject(TranslateService);
  private readonly acmeKeysSvc = inject(AcmeKeysService);
  private readonly pdns = inject(PdnsService);

  // ── Tabs ──────────────────────────────────────────────────────────────────
  readonly activeTab = signal<Tab>("info");

  // ── Language ──────────────────────────────────────────────────────────────
  readonly currentLang = signal(localStorage.getItem("lang") ?? "en");

  setLanguage(lang: string): void {
    this.translate.use(lang);
    this.currentLang.set(lang);
    localStorage.setItem("lang", lang);
  }

  // ── Themes ────────────────────────────────────────────────────────────────
  readonly themes: { value: Theme; label: string; icon: string }[] = [
    { value: "light", label: "Light", icon: "bi-sun" },
    { value: "dark", label: "Dark", icon: "bi-moon" },
    { value: "auto", label: "Auto (system)", icon: "bi-circle-half" },
  ];

  setTheme(theme: Theme): void {
    this.themeService.setTheme(theme);
  }

  // ── Password ──────────────────────────────────────────────────────────────
  readonly isChangingPassword = signal(false);
  readonly passwordSuccess = signal(false);
  readonly passwordError = signal<string | null>(null);

  readonly passwordModel = signal({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  readonly passwordForm = form(this.passwordModel, (s) => {
    required(s.current_password, { message: "Current password required" });
    required(s.new_password, { message: "New password required" });
    required(s.confirm_password, { message: "Confirmation required" });
  });

  onChangePassword(): void {
    submit(this.passwordForm, async () => {
      const { current_password, new_password, confirm_password } = this.passwordModel();
      if (new_password !== confirm_password) {
        this.passwordError.set("Passwords do not match");
        return;
      }
      this.isChangingPassword.set(true);
      this.passwordError.set(null);
      this.passwordSuccess.set(false);
      try {
        await firstValueFrom(
          this.http.put("/api/auth/change-password", { current_password, new_password }),
        );
        this.passwordSuccess.set(true);
        this.passwordModel.set({ current_password: "", new_password: "", confirm_password: "" });
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.passwordError.set(detail ?? "Error occurred while changing password");
      } finally {
        this.isChangingPassword.set(false);
      }
    });
  }

  // ── About ─────────────────────────────────────────────────────────────────
  readonly appInfo = signal<AppInfo | null>(null);
  readonly latestRelease = signal<GithubRelease | null>(null);
  readonly releaseCheckDone = signal(false);

  get updateAvailable(): boolean {
    const info = this.appInfo();
    const latest = this.latestRelease();
    if (!info || !latest) return false;
    return latest.tag_name.replace(/^v/, "") !== info.version;
  }

  private async _loadAppInfo(): Promise<void> {
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
        // no release or GitHub quota exceeded
      }
    } catch {
      // backend unavailable
    } finally {
      this.releaseCheckDone.set(true);
    }
  }

  // ── API Keys ──────────────────────────────────────────────────────────────
  readonly keys = signal<AcmeApiKey[]>([]);
  readonly isLoadingKeys = signal(false);
  readonly keysError = signal<string | null>(null);

  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);

  readonly createdKey = signal<string | null>(null);
  readonly createdKeyType = signal<"acme" | "api">("api");
  readonly copied = signal(false);

  readonly editingKey = signal<AcmeApiKey | null>(null);
  readonly availableZones = signal<Zone[]>([]);
  readonly selectedZones = signal<Set<string>>(new Set());
  readonly isSavingZones = signal(false);
  readonly zonesError = signal<string | null>(null);

  readonly createModel = signal({ name: "", secret: "", keyType: "api" as "acme" | "api" });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "APIKEYS.NAME_REQUIRED" });
  });

  async loadApiKeys(): Promise<void> {
    this.isLoadingKeys.set(true);
    this.keysError.set(null);
    try {
      this.keys.set(await this.acmeKeysSvc.listKeys());
    } catch {
      this.keysError.set("APIKEYS.LOAD_ERROR");
    } finally {
      this.isLoadingKeys.set(false);
    }
  }

  openCreateModal(): void {
    const defaultType = this.auth.isAcmeCreator() ? "acme" : "api";
    this.createModel.set({ name: "", secret: "", keyType: defaultType });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  closeCreatedKeyModal(): void {
    this.createdKey.set(null);
    this.copied.set(false);
  }

  setKeyType(type: "acme" | "api"): void {
    this.createModel.update((m) => ({ ...m, keyType: type }));
  }

  onCreate(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, secret, keyType } = this.createModel();
        const created = await this.acmeKeysSvc.createKey(name, keyType, secret.trim() || undefined);
        this.showCreateModal.set(false);
        this.keys.update((list) => [...list, created]);
        this.createdKey.set(created.key);
        this.createdKeyType.set(created.key_type);
      } catch {
        this.createError.set("APIKEYS.CREATE_ERROR");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async copyKey(): Promise<void> {
    const key = this.createdKey();
    if (!key) return;
    await navigator.clipboard.writeText(key);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  async openZoneModal(key: AcmeApiKey): Promise<void> {
    this.editingKey.set(key);
    this.selectedZones.set(new Set(key.zones));
    this.zonesError.set(null);
    try {
      this.availableZones.set(await this.pdns.getZones());
    } catch {
      this.zonesError.set("APIKEYS.ZONES_LOAD_ERROR");
    }
  }

  closeZoneModal(): void {
    this.editingKey.set(null);
  }

  toggleZone(zoneName: string): void {
    this.selectedZones.update((set) => {
      const next = new Set(set);
      next.has(zoneName) ? next.delete(zoneName) : next.add(zoneName);
      return next;
    });
  }

  async saveZones(): Promise<void> {
    const key = this.editingKey();
    if (!key) return;
    this.isSavingZones.set(true);
    this.zonesError.set(null);
    try {
      const updated = await this.acmeKeysSvc.updateZones(key.id, [...this.selectedZones()]);
      this.keys.update((list) => list.map((k) => (k.id === updated.id ? updated : k)));
      this.editingKey.set(null);
    } catch {
      this.zonesError.set("APIKEYS.ZONES_SAVE_ERROR");
    } finally {
      this.isSavingZones.set(false);
    }
  }

  async deleteKey(key: AcmeApiKey): Promise<void> {
    if (!confirm(`Supprimer la clé "${key.name}" ?`)) return;
    try {
      await this.acmeKeysSvc.deleteKey(key.id);
      this.keys.update((list) => list.filter((k) => k.id !== key.id));
    } catch {
      this.keysError.set("APIKEYS.DELETE_ERROR");
    }
  }

  trackById(_: number, key: AcmeApiKey): number {
    return key.id;
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  ngOnInit(): void {
    void this._loadAppInfo();
    void this.loadApiKeys();
  }
}

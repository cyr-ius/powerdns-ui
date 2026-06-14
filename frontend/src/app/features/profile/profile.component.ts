import { DatePipe } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { RouterLink } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { AppInfoService } from "../../core/services/app-info.service";
import { AuthService } from "../../core/services/auth.service";
import { AcmeApiKey, AcmeKeysService } from "../../core/services/acme-keys.service";
import { Theme, ThemeService } from "../../core/services/theme.service";
import { TranslatePipe, TranslateService } from "@ngx-translate/core";

type Tab = "info" | "appearance" | "password" | "apikeys";

@Component({
  selector: "app-profile",
  imports: [DatePipe, RouterLink, FormField, TranslatePipe],
  templateUrl: "./profile.component.html",
  styleUrl: "./profile.component.css",
})
export class ProfileComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly themeService = inject(ThemeService);
  readonly appInfoSvc = inject(AppInfoService);
  private readonly http = inject(HttpClient);
  private readonly translate = inject(TranslateService);
  private readonly acmeKeysSvc = inject(AcmeKeysService);

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

  // ── API Keys (REST) ───────────────────────────────────────────────────────
  readonly keys = signal<AcmeApiKey[]>([]);
  readonly isLoadingKeys = signal(false);
  readonly keysError = signal<string | null>(null);

  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);

  readonly createdKey = signal<string | null>(null);
  readonly copied = signal(false);

  readonly createModel = signal({ name: "", secret: "", comment: "" });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "APIKEYS.NAME_REQUIRED" });
  });

  // ── Edit modal ────────────────────────────────────────────────────────────
  readonly editingKeyData = signal<AcmeApiKey | null>(null);
  readonly isEditing = signal(false);
  readonly editError = signal<string | null>(null);
  readonly editModel = signal({ comment: "" });
  readonly editForm = form(this.editModel, () => {});

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
    this.createModel.set({ name: "", secret: "", comment: "" });
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

  onCreate(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, secret, comment } = this.createModel();
        const created = await this.acmeKeysSvc.createKey(name, "api", secret.trim() || undefined, comment.trim() || undefined);
        this.showCreateModal.set(false);
        this.keys.update((list) => [...list, created]);
        this.createdKey.set(created.key);
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

  openEditModal(key: AcmeApiKey): void {
    this.editingKeyData.set(key);
    this.editModel.set({ comment: key.comment ?? "" });
    this.editError.set(null);
  }

  closeEditModal(): void {
    this.editingKeyData.set(null);
  }

  onEditKey(): void {
    submit(this.editForm, async () => {
      const key = this.editingKeyData();
      if (!key) return;
      this.isEditing.set(true);
      this.editError.set(null);
      try {
        const { comment } = this.editModel();
        const updated = await this.acmeKeysSvc.updateKey(key.id, comment.trim() || null);
        this.keys.update((list) => list.map((k) => (k.id === updated.id ? updated : k)));
        this.editingKeyData.set(null);
      } catch {
        this.editError.set("APIKEYS.EDIT_ERROR");
      } finally {
        this.isEditing.set(false);
      }
    });
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
    void this.appInfoSvc.load();
    void this.loadApiKeys();
  }
}

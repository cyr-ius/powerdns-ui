import { HttpClient } from "@angular/common/http";
import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { RouterLink } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { AuthService } from "../../core/services/auth.service";
import { Theme, ThemeService } from "../../core/services/theme.service";
import { TranslateModule, TranslateService } from "@ngx-translate/core";

interface AppInfo {
  version: string;
  github: string;
  docs_url: string;
}

interface GithubRelease {
  tag_name: string;
  html_url: string;
  name: string;
}

@Component({
  selector: "app-profile",
  imports: [RouterLink, FormField, TranslateModule],
  templateUrl: "./profile.component.html",
  styleUrl: "./profile.component.css",
})
export class ProfileComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly themeService = inject(ThemeService);
  private readonly http = inject(HttpClient);
  private readonly translate = inject(TranslateService);

  readonly currentLang = signal(localStorage.getItem('lang') ?? 'en');

  setLanguage(lang: string): void {
    this.translate.use(lang);
    this.currentLang.set(lang);
    localStorage.setItem('lang', lang);
  }

  readonly isChangingPassword = signal(false);
  readonly passwordSuccess = signal(false);
  readonly passwordError = signal<string | null>(null);

  readonly appInfo = signal<AppInfo | null>(null);
  readonly latestRelease = signal<GithubRelease | null>(null);
  readonly releaseCheckDone = signal(false);

  get updateAvailable(): boolean {
    const info = this.appInfo();
    const latest = this.latestRelease();
    if (!info || !latest) return false;
    return latest.tag_name.replace(/^v/, "") !== info.version;
  }

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

  ngOnInit(): void {
    void this._loadAppInfo();
  }

  private async _loadAppInfo(): Promise<void> {
    try {
      const info = await firstValueFrom(this.http.get<AppInfo>("/api/info"));
      this.appInfo.set(info);
      try {
        const release = await firstValueFrom(
          this.http.get<GithubRelease>("https://api.github.com/repos/cyr-ius/powerdns-ui/releases/latest"),
        );
        this.latestRelease.set(release);
      } catch {
        // Pas de release ou quota GitHub dépassé
      }
    } catch {
      // Backend indisponible
    } finally {
      this.releaseCheckDone.set(true);
    }
  }

  readonly themes: { value: Theme; label: string; icon: string }[] = [
    { value: "light", label: "Light", icon: "bi-sun" },
    { value: "dark", label: "Dark", icon: "bi-moon" },
    { value: "auto", label: "Auto (system)", icon: "bi-circle-half" },
  ];

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
          this.http.put("/api/auth/change-password", {
            current_password,
            new_password,
          }),
        );
        this.passwordSuccess.set(true);
        this.passwordModel.set({
          current_password: "",
          new_password: "",
          confirm_password: "",
        });
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.passwordError.set(detail ?? "Error occurred while changing password");
      } finally {
        this.isChangingPassword.set(false);
      }
    });
  }

  setTheme(theme: Theme): void {
    this.themeService.setTheme(theme);
  }
}

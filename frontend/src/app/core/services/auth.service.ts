import { HttpClient } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { OidcConfig, User } from "../../shared/models/auth.model";

@Injectable({ providedIn: "root" })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  // The session JWT lives in an HttpOnly cookie set by the backend and is never
  // accessible to JavaScript. Auth state is derived from the loaded user.
  private readonly _user = signal<User | null>(null);
  private readonly _oidcConfig = signal<OidcConfig | null>(null);

  readonly isAuthenticated = computed(() => !!this._user());
  readonly currentUser = computed(() => this._user());
  readonly isAdmin = computed(() => this._user()?.is_admin ?? false);
  readonly isAcmeCreator = computed(() => (this._user()?.is_admin || this._user()?.is_account_admin) ?? false);
  readonly oidcConfig = computed(() => this._oidcConfig());
  readonly sessionExpired = signal(false);

  /** Restore the session on startup from the HttpOnly cookie, if present. */
  async bootstrap(): Promise<void> {
    try {
      this._user.set(await firstValueFrom(this.http.get<User>("/api/auth/me")));
    } catch {
      this._user.set(null);
    }
  }

  async login(username: string, password: string): Promise<void> {
    // The backend sets the auth cookie on this response; we only fetch the user.
    await firstValueFrom(this.http.post<void>("/api/auth/login", { username, password }));
    await this.fetchCurrentUser();
  }

  async fetchCurrentUser(): Promise<void> {
    this._user.set(await firstValueFrom(this.http.get<User>("/api/auth/me")));
  }

  async loadOidcConfig(): Promise<void> {
    const config = await firstValueFrom(this.http.get<OidcConfig>("/api/auth/config"));
    this._oidcConfig.set(config);
  }

  async loginWithOidc(): Promise<void> {
    const resp = await firstValueFrom(this.http.get<{ authorization_url: string }>("/api/auth/oidc/login"));
    window.location.href = resp.authorization_url;
  }

  markSessionExpired(): void {
    this._user.set(null);
    this.sessionExpired.set(true);
  }

  async logout(): Promise<void> {
    this.sessionExpired.set(false);
    try {
      await firstValueFrom(this.http.post("/api/auth/logout", {}));
    } catch {
      // Ignore network errors: clearing local state is enough to log out.
    }
    this._user.set(null);
    await this.router.navigate(["/login"]);
  }
}

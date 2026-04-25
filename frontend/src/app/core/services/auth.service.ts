import { HttpClient } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { firstValueFrom } from "rxjs";
import { OidcConfig, TokenResponse, User } from "../../shared/models/auth.model";

@Injectable({ providedIn: "root" })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly TOKEN_KEY = "pdns_token";

  private readonly _token = signal<string | null>(localStorage.getItem(this.TOKEN_KEY));
  private readonly _user = signal<User | null>(null);
  private readonly _oidcConfig = signal<OidcConfig | null>(null);

  readonly isAuthenticated = computed(() => !!this._token());
  readonly currentUser = computed(() => this._user());
  readonly isAdmin = computed(() => this._user()?.is_admin ?? false);
  readonly isAcmeCreator = computed(() => (this._user()?.is_admin || this._user()?.is_account_admin) ?? false);
  readonly oidcConfig = computed(() => this._oidcConfig());
  readonly sessionExpired = signal(false);

  getToken(): string | null {
    return this._token();
  }

  async login(username: string, password: string): Promise<void> {
    const resp = await firstValueFrom(this.http.post<TokenResponse>("/api/auth/login", { username, password }));
    this._storeToken(resp.access_token);
    await this.fetchCurrentUser();
  }

  async loginWithToken(token: string): Promise<void> {
    this._storeToken(token);
    await this.fetchCurrentUser();
  }

  async fetchCurrentUser(): Promise<void> {
    try {
      const user = await firstValueFrom(this.http.get<User>("/api/auth/me"));
      this._user.set(user);
    } catch {
      this.logout();
    }
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
    localStorage.removeItem(this.TOKEN_KEY);
    this._token.set(null);
    this._user.set(null);
    this.sessionExpired.set(true);
  }

  logout(): void {
    this.sessionExpired.set(false);
    localStorage.removeItem(this.TOKEN_KEY);
    this._token.set(null);
    this._user.set(null);
    this.router.navigate(["/login"]);
  }

  private _storeToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
    this._token.set(token);
  }
}

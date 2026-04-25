import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { ActivatedRoute, Router } from "@angular/router";
import { AuthService } from "../../../core/services/auth.service";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  selector: "app-login",
  imports: [FormField, TranslateModule],
  templateUrl: "./login.component.html",
  styleUrl: "./login.component.css",
})
export class LoginComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly oidcEnabled = signal(false);
  readonly localLoginDisabled = signal(false);

  readonly loginModel = signal({ username: "", password: "" });
  readonly loginForm = form(this.loginModel, (s) => {
    required(s.username, { message: "The username is required" });
    required(s.password, { message: "The password is required" });
  });

  async ngOnInit(): Promise<void> {
    if (this.auth.isAuthenticated()) {
      await this.router.navigate(["/zones"]);
      return;
    }
    const token = this.route.snapshot.queryParamMap.get("token");
    if (token) {
      await this.auth.loginWithToken(token);
      await this.router.navigate(["/zones"]);
      return;
    }
    const oidcError = this.route.snapshot.queryParamMap.get("error");
    if (oidcError) {
      this.error.set("The SSO login failed. Please try again.");
    }
    await this.auth.loadOidcConfig();
    this.oidcEnabled.set(this.auth.oidcConfig()?.enabled ?? false);
    this.localLoginDisabled.set(this.auth.oidcConfig()?.local_login_disabled ?? false);
  }

  onSubmit(): void {
    submit(this.loginForm, async () => {
      this.isLoading.set(true);
      this.error.set(null);
      try {
        const { username, password } = this.loginModel();
        await this.auth.login(username, password);
        await this.router.navigate(["/zones"]);
      } catch {
        this.error.set("Incorrect credentials. Please try again.");
      } finally {
        this.isLoading.set(false);
      }
    });
  }

  async onOidcLogin(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      await this.auth.loginWithOidc();
    } catch {
      this.error.set("Impossible to contact the SSO provider.");
      this.isLoading.set(false);
    }
  }
}

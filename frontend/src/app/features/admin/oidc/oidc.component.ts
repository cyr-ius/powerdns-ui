import { Component, inject, OnInit, signal } from "@angular/core";
import { disabled, form, FormField, required, submit } from "@angular/forms/signals";
import { AdminService } from "../../../core/services/admin.service";
import { OidcSettings } from "../../../shared/models/admin.model";

@Component({
  selector: "app-admin-oidc",
  imports: [FormField],
  templateUrl: "./oidc.component.html",
})
export class AdminOidcComponent implements OnInit {
  private readonly adminService = inject(AdminService);

  readonly isLoading = signal(true);
  readonly success = signal(false);
  readonly error = signal<string | null>(null);

  private readonly defaultCfg: OidcSettings = {
    enabled: false,
    client_id: "",
    client_secret: "",
    discovery_url: "",
    redirect_uri: "",
    scopes: "openid email profile",
    local_login_disabled: false,
  };

  readonly oidcConfig = signal(this.defaultCfg);
  readonly oidcForm = form(this.oidcConfig, (p) => {
    required(p.client_id, { message: "The client_id is required" });
    required(p.client_secret, { message: "The client_secret is required" });
    required(p.discovery_url, { message: "The discovery URL is required" });
    required(p.redirect_uri, { message: "The redirect URI is required" });
    disabled(p.local_login_disabled, ({ valueOf }) => valueOf(p.enabled) !== true);
  });

  async ngOnInit(): Promise<void> {
    try {
      this.oidcConfig.set(await this.adminService.getOidcSettings());
    } catch {
      this.error.set("Impossible to load OIDC configuration.");
    } finally {
      this.isLoading.set(false);
    }
  }

  async onSave(): Promise<void> {
    submit(this.oidcForm, async () => {
      this.success.set(false);
      this.error.set(null);
      try {
        await this.adminService.updateOidcSettings(this.oidcConfig());
        this.success.set(true);
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.error.set(detail ?? "Error occurred while saving");
      }
    });
  }
}

import { Component, OnInit, computed, inject, signal } from "@angular/core";
import { disabled, form, FormField, required, submit } from "@angular/forms/signals";
import { AuditService } from "../../../core/services/audit.service";
import { SmtpSettings } from "../../../shared/models/audit.model";
import { TranslatePipe } from "@ngx-translate/core";

@Component({
  selector: "app-admin-mail",
  imports: [FormField, TranslatePipe],
  templateUrl: "./mail.component.html",
})
export class AdminMailComponent implements OnInit {
  private readonly auditService = inject(AuditService);

  readonly isLoading = signal(true);
  readonly success = signal(false);
  readonly error = signal<string | null>(null);
  readonly showPassword = signal(false);

  readonly isTesting = signal(false);
  /** Recipient of the last successful probe, null when none was sent. */
  readonly testSuccess = signal<string | null>(null);
  readonly testError = signal<string | null>(null);

  /** Fields pinned by environment variables; the backend ignores changes to them. */
  readonly envLocked = computed(() => this.smtpModel().env_locked ?? []);

  readonly smtpModel = signal<SmtpSettings>({
    enabled: false,
    host: "localhost",
    port: 587,
    username: "",
    password: "",
    from_email: "",
    recipient_email: "",
    use_tls: false,
    use_starttls: true,
    alert_actions: [],
    alert_resources: [],
    alert_statuses: [],
  });

  readonly smtpForm = form(this.smtpModel, (p) => {
    required(p.host, { message: "MAIL.HOST_REQUIRED" });
    required(p.port, { message: "MAIL.PORT_REQUIRED" });
    required(p.recipient_email, { message: "MAIL.RECIPIENT_EMAIL_REQUIRED" });
    disabled(p.host, ({ valueOf }) => valueOf(p.enabled) !== true);
    disabled(p.port, ({ valueOf }) => valueOf(p.enabled) !== true);
    disabled(p.recipient_email, ({ valueOf }) => valueOf(p.enabled) !== true);
  });

  async ngOnInit(): Promise<void> {
    try {
      this.smtpModel.set(await this.auditService.getSmtpSettings());
    } catch {
      this.error.set("MAIL.LOAD_ERROR");
    } finally {
      this.isLoading.set(false);
    }
  }

  async onSave(): Promise<void> {
    submit(this.smtpForm, async () => {
      this.success.set(false);
      this.error.set(null);
      try {
        const updated = await this.auditService.updateSmtpSettings(this.smtpModel());
        this.smtpModel.set(updated);
        this.success.set(true);
      } catch {
        this.error.set("MAIL.SAVE_ERROR");
      }
    });
  }

  /** Probe the relay with the form as displayed, without saving it first. */
  async onTest(): Promise<void> {
    this.isTesting.set(true);
    this.testSuccess.set(null);
    this.testError.set(null);
    try {
      const result = await this.auditService.testSmtpSettings(this.smtpModel());
      this.testSuccess.set(result.recipient);
    } catch (err) {
      const detail = (err as { error?: { detail?: string } }).error?.detail;
      this.testError.set(detail ?? "MAIL.TEST_ERROR");
    } finally {
      this.isTesting.set(false);
    }
  }

  onTlsChange(): void {
    this.smtpModel.update((v) => {
      if (v.use_tls) {
        return {
          ...v,
          use_starttls: false,
          port: v.port === 587 ? 465 : v.port,
        };
      }
      return { ...v, port: v.port === 465 ? 587 : v.port };
    });
  }

  onStarttlsChange(): void {
    this.smtpModel.update((v) => {
      if (v.use_starttls) {
        return { ...v, use_tls: false, port: v.port === 465 ? 587 : v.port };
      }
      return v;
    });
  }
}

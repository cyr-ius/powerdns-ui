import { Component, OnInit, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { AuditService } from "../../../core/services/audit.service";
import { SmtpSettings } from "../../../shared/models/audit.model";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  selector: "app-admin-mail",
  imports: [FormsModule, TranslateModule],
  templateUrl: "./mail.component.html",
})
export class AdminMailComponent implements OnInit {
  private readonly auditService = inject(AuditService);

  readonly isLoading = signal(true);
  readonly isSaving = signal(false);
  readonly success = signal(false);
  readonly error = signal<string | null>(null);

  smtp: SmtpSettings = {
    enabled: false,
    host: "localhost",
    port: 587,
    username: "",
    password: "",
    from_email: "",
    recipient_email: "",
    use_tls: false,
    use_starttls: true,
  };

  showPassword = false;

  async ngOnInit(): Promise<void> {
    try {
      this.smtp = await this.auditService.getSmtpSettings();
    } catch {
      this.error.set("MAIL.LOAD_ERROR");
    } finally {
      this.isLoading.set(false);
    }
  }

  async onSave(): Promise<void> {
    this.isSaving.set(true);
    this.success.set(false);
    this.error.set(null);
    try {
      this.smtp = await this.auditService.updateSmtpSettings(this.smtp);
      this.success.set(true);
    } catch {
      this.error.set("MAIL.SAVE_ERROR");
    } finally {
      this.isSaving.set(false);
    }
  }

  onTlsChange(): void {
    if (this.smtp.use_tls) {
      this.smtp.use_starttls = false;
      if (this.smtp.port === 587) this.smtp.port = 465;
    } else {
      if (this.smtp.port === 465) this.smtp.port = 587;
    }
  }

  onStarttlsChange(): void {
    if (this.smtp.use_starttls) {
      this.smtp.use_tls = false;
      if (this.smtp.port === 465) this.smtp.port = 587;
    }
  }
}

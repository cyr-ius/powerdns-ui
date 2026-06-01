import { Component, OnInit, inject, signal } from "@angular/core";
import { disabled, form, FormField, required, submit } from "@angular/forms/signals";
import { AuditService } from "../../../core/services/audit.service";
import { AuditLog, PdnsLogEntry, SmtpSettings, SyslogSettings } from "../../../shared/models/audit.model";
import { TranslateModule } from "@ngx-translate/core";

type Tab = "audit" | "pdns";

const ACTION_LABELS: Record<string, string> = {
  login: "Connection",
  change_password: "Change password",
  reset_password: "Reset password",
  create: "Creation",
  update: "Modification",
  delete: "Deletion",
  update_records: "Update records",
  update_oidc_settings: "Modif. OIDC",
};

const RESOURCE_LABELS: Record<string, string> = {
  auth: "Authentication",
  user: "User",
  account: "Account",
  zone: "Zone",
  oidc_settings: "OIDC",
};

@Component({
  selector: "app-admin-audit",
  imports: [FormField, TranslateModule],
  templateUrl: "./audit.component.html",
  styleUrl: "./audit.component.css",
})
export class AdminAuditComponent implements OnInit {
  private readonly auditService = inject(AuditService);

  readonly activeTab = signal<Tab>("audit");

  // Audit logs tab
  readonly logs = signal<AuditLog[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly totalCount = signal(0);

  // Filters
  readonly filterUsername = signal("");
  readonly filterAction = signal("");
  readonly filterResource = signal("");
  readonly filterStatus = signal("");
  readonly filterDateFrom = signal("");
  readonly filterDateTo = signal("");
  readonly page = signal(0);
  readonly pageSize = 50;

  // PDNS logs tab
  readonly pdnsLogs = signal<PdnsLogEntry[]>([]);
  readonly pdnsLoading = signal(false);
  readonly pdnsError = signal<string | null>(null);

  // Syslog settings modal
  readonly showSyslogModal = signal(false);
  readonly syslogError = signal<string | null>(null);
  readonly syslogSettings = signal<SyslogSettings>({
    enabled: false,
    host: "localhost",
    port: 514,
    protocol: "udp",
    facility: "local0",
    app_name: "pdns-ui",
  });

  readonly syslogModel = signal<SyslogSettings>({ ...this.syslogSettings() });
  readonly syslogForm = form(this.syslogModel, (p) => {
    required(p.host, { message: "AUDIT.SYSLOG_HOST_REQUIRED" });
    required(p.port, { message: "AUDIT.SYSLOG_PORT_REQUIRED" });
    disabled(p.host, ({ valueOf }) => valueOf(p.enabled) !== true);
    disabled(p.port, ({ valueOf }) => valueOf(p.enabled) !== true);
    disabled(p.protocol, ({ valueOf }) => valueOf(p.enabled) !== true);
    disabled(p.facility, ({ valueOf }) => valueOf(p.enabled) !== true);
    disabled(p.app_name, ({ valueOf }) => valueOf(p.enabled) !== true);
  });

  readonly facilities = [
    "kern",
    "user",
    "mail",
    "daemon",
    "auth",
    "syslog",
    "local0",
    "local1",
    "local2",
    "local3",
    "local4",
    "local5",
    "local6",
    "local7",
  ];

  // Email audit modal
  readonly showEmailModal = signal(false);
  readonly emailError = signal<string | null>(null);
  readonly smtpSettings = signal<SmtpSettings>({
    enabled: false,
    host: "localhost",
    port: 587,
    username: "",
    password: "",
    from_email: "",
    recipient_email: "",
    use_tls: false,
    use_starttls: true,
  });

  readonly emailModel = signal<SmtpSettings>({ ...this.smtpSettings() });
  readonly emailForm = form(this.emailModel, (p) => {
    required(p.recipient_email, { message: "AUDIT.EMAIL_RECIPIENT_REQUIRED" });
    disabled(p.recipient_email, ({ valueOf }) => valueOf(p.enabled) !== true);
  });

  readonly actionLabel = (a: string) => ACTION_LABELS[a] ?? a;
  readonly resourceLabel = (r: string) => RESOURCE_LABELS[r] ?? r;

  readonly statusClass = (s: string) =>
    s === "success" ? "bg-success-subtle text-success-emphasis" : "bg-danger-subtle text-danger-emphasis";

  async ngOnInit(): Promise<void> {
    await Promise.all([this.loadLogs(), this.loadSyslogSettings(), this.loadSmtpSettings()]);
  }

  async switchTab(tab: Tab): Promise<void> {
    this.activeTab.set(tab);
    if (tab === "pdns" && this.pdnsLogs().length === 0) {
      await this.loadPdnsLogs();
    }
  }

  async loadLogs(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const filters = this.buildFilters();
      const [logs, countRes] = await Promise.all([
        this.auditService.listAuditLogs({ ...filters, skip: this.page() * this.pageSize, limit: this.pageSize }),
        this.auditService.countAuditLogs(filters),
      ]);
      this.logs.set(logs);
      this.totalCount.set(countRes.count);
    } catch {
      this.error.set("Unable to load audit log.");
    } finally {
      this.isLoading.set(false);
    }
  }

  private buildFilters() {
    return {
      username: this.filterUsername() || undefined,
      action: this.filterAction() || undefined,
      resource_type: this.filterResource() || undefined,
      status: this.filterStatus() || undefined,
      date_from: this.filterDateFrom() || undefined,
      date_to: this.filterDateTo() || undefined,
    };
  }

  async applyFilters(): Promise<void> {
    this.page.set(0);
    await this.loadLogs();
  }

  async resetFilters(): Promise<void> {
    this.filterUsername.set("");
    this.filterAction.set("");
    this.filterResource.set("");
    this.filterStatus.set("");
    this.filterDateFrom.set("");
    this.filterDateTo.set("");
    this.page.set(0);
    await this.loadLogs();
  }

  get totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize);
  }

  async prevPage(): Promise<void> {
    if (this.page() > 0) {
      this.page.update((p) => p - 1);
      await this.loadLogs();
    }
  }

  async nextPage(): Promise<void> {
    if (this.page() < this.totalPages - 1) {
      this.page.update((p) => p + 1);
      await this.loadLogs();
    }
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleString("fr-FR");
  }

  async loadPdnsLogs(): Promise<void> {
    this.pdnsLoading.set(true);
    this.pdnsError.set(null);
    try {
      this.pdnsLogs.set(await this.auditService.getPdnsLogs());
    } catch {
      this.pdnsError.set("Unable to load PDNS logs.");
    } finally {
      this.pdnsLoading.set(false);
    }
  }

  // ── Syslog modal ────────────────────────────────────────────────────────────

  async loadSyslogSettings(): Promise<void> {
    try {
      const cfg = await this.auditService.getSyslogSettings();
      this.syslogSettings.set(cfg);
    } catch {
      // non-blocking
    }
  }

  openSyslogModal(): void {
    this.syslogModel.set({ ...this.syslogSettings() });
    this.syslogError.set(null);
    this.showSyslogModal.set(true);
  }

  async saveSyslog(): Promise<void> {
    submit(this.syslogForm, async () => {
      this.syslogError.set(null);
      try {
        const saved = await this.auditService.updateSyslogSettings(this.syslogModel());
        this.syslogSettings.set(saved);
        this.showSyslogModal.set(false);
      } catch {
        this.syslogError.set("Error occurred while saving.");
      }
    });
  }

  // ── Email modal ──────────────────────────────────────────────────────────────

  async loadSmtpSettings(): Promise<void> {
    try {
      const cfg = await this.auditService.getSmtpSettings();
      this.smtpSettings.set(cfg);
    } catch {
      // non-blocking
    }
  }

  openEmailModal(): void {
    this.emailModel.set({ ...this.smtpSettings() });
    this.emailError.set(null);
    this.showEmailModal.set(true);
  }

  async saveEmail(): Promise<void> {
    submit(this.emailForm, async () => {
      this.emailError.set(null);
      try {
        const saved = await this.auditService.updateSmtpSettings(this.emailModel());
        this.smtpSettings.set(saved);
        this.showEmailModal.set(false);
      } catch {
        this.emailError.set("Error occurred while saving.");
      }
    });
  }
}

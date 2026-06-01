import { Component, OnInit, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
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
  imports: [FormsModule, TranslateModule],
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

  filterUsername = "";
  filterAction = "";
  filterResource = "";
  filterStatus = "";
  filterDateFrom = "";
  filterDateTo = "";
  page = 0;
  readonly pageSize = 50;

  // PDNS logs tab
  readonly pdnsLogs = signal<PdnsLogEntry[]>([]);
  readonly pdnsLoading = signal(false);
  readonly pdnsError = signal<string | null>(null);

  // Syslog settings modal
  readonly showSyslogModal = signal(false);
  readonly isSavingSyslog = signal(false);
  readonly syslogError = signal<string | null>(null);
  readonly syslogSettings = signal<SyslogSettings>({
    enabled: false,
    host: "localhost",
    port: 514,
    protocol: "udp",
    facility: "local0",
    app_name: "pdns-ui",
  });
  syslogDraft: SyslogSettings = { ...this.syslogSettings() };

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
  readonly isSavingEmail = signal(false);
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
  emailDraft: SmtpSettings = { ...this.smtpSettings() };

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
        this.auditService.listAuditLogs({ ...filters, skip: this.page * this.pageSize, limit: this.pageSize }),
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
      username: this.filterUsername || undefined,
      action: this.filterAction || undefined,
      resource_type: this.filterResource || undefined,
      status: this.filterStatus || undefined,
      date_from: this.filterDateFrom || undefined,
      date_to: this.filterDateTo || undefined,
    };
  }

  async applyFilters(): Promise<void> {
    this.page = 0;
    await this.loadLogs();
  }

  async resetFilters(): Promise<void> {
    this.filterUsername = "";
    this.filterAction = "";
    this.filterResource = "";
    this.filterStatus = "";
    this.filterDateFrom = "";
    this.filterDateTo = "";
    this.page = 0;
    await this.loadLogs();
  }

  get totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize);
  }

  async prevPage(): Promise<void> {
    if (this.page > 0) {
      this.page--;
      await this.loadLogs();
    }
  }

  async nextPage(): Promise<void> {
    if (this.page < this.totalPages - 1) {
      this.page++;
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
    this.syslogDraft = { ...this.syslogSettings() };
    this.syslogError.set(null);
    this.showSyslogModal.set(true);
  }

  async saveSyslog(): Promise<void> {
    this.isSavingSyslog.set(true);
    this.syslogError.set(null);
    try {
      const saved = await this.auditService.updateSyslogSettings(this.syslogDraft);
      this.syslogSettings.set(saved);
      this.showSyslogModal.set(false);
    } catch {
      this.syslogError.set("Error occurred while saving.");
    } finally {
      this.isSavingSyslog.set(false);
    }
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
    this.emailDraft = { ...this.smtpSettings() };
    this.emailError.set(null);
    this.showEmailModal.set(true);
  }

  async saveEmail(): Promise<void> {
    this.isSavingEmail.set(true);
    this.emailError.set(null);
    try {
      const saved = await this.auditService.updateSmtpSettings(this.emailDraft);
      this.smtpSettings.set(saved);
      this.showEmailModal.set(false);
    } catch {
      this.emailError.set("Error occurred while saving.");
    } finally {
      this.isSavingEmail.set(false);
    }
  }
}

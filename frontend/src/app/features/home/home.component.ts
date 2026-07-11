import { DatePipe } from "@angular/common";
import { Component, OnInit, computed, inject, signal } from "@angular/core";
import { RouterLink } from "@angular/router";
import { TranslatePipe } from "@ngx-translate/core";
import { AppInfoService } from "../../core/services/app-info.service";
import { AuditService } from "../../core/services/audit.service";
import { AuthService } from "../../core/services/auth.service";
import { PdnsService } from "../../core/services/pdns.service";
import { AuditLog } from "../../shared/models/audit.model";
import { ServerInfo, Zone } from "../../shared/models/pdns.model";

@Component({
  selector: "app-home",
  imports: [RouterLink, DatePipe, TranslatePipe],
  templateUrl: "./home.component.html",
})
export class HomeComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly appInfoSvc = inject(AppInfoService);
  private readonly pdns = inject(PdnsService);
  private readonly audit = inject(AuditService);

  readonly isLoading = signal(true);
  readonly zones = signal<Zone[]>([]);
  readonly serverInfo = signal<ServerInfo | null>(null);
  readonly recentLogs = signal<AuditLog[]>([]);

  readonly zoneCount = computed(() => this.zones().length);
  readonly dnssecCount = computed(() => this.zones().filter((z) => z.dnssec).length);
  readonly primaryCount = computed(() => this.zones().filter((z) => z.kind === "Master" || z.kind === "Native").length);
  readonly secondaryCount = computed(() => this.zones().filter((z) => z.kind === "Slave").length);

  async ngOnInit(): Promise<void> {
    await this.appInfoSvc.load();
    void this.appInfoSvc.checkHealth();

    // The dashboard degrades gracefully: a panel the user has no access to (or
    // that PowerDNS cannot answer) simply stays empty.
    const [zones, server, logs] = await Promise.all([
      this.pdns.getZones().catch(() => [] as Zone[]),
      this.pdns.getServerInfo().catch(() => null),
      this.auth.isAdmin()
        ? this.audit.listAuditLogs({ limit: 8 }).catch(() => [] as AuditLog[])
        : Promise.resolve([] as AuditLog[]),
    ]);

    this.zones.set(zones);
    this.serverInfo.set(server);
    this.recentLogs.set(logs);
    this.isLoading.set(false);
  }
}

import { DatePipe } from "@angular/common";
import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { CacheFlushResult, ServerInfo, SimpleStatisticItem, StatisticItem, Zone } from "../../shared/models/pdns.model";
import { TranslateModule } from "@ngx-translate/core";

const KEY_STATS = [
  "uptime",
  "queries",
  "udp-queries",
  "tcp-queries",
  "latency",
  "cache-hits",
  "cache-misses",
  "packetcache-hit",
  "packetcache-miss",
  "backend-queries",
  "servfail-packets",
  "corrupt-packets",
  "signatures",
];

@Component({
  selector: "app-statistics",
  imports: [FormField, DatePipe, TranslateModule],
  templateUrl: "./statistics.component.html",
  styleUrl: "./statistics.component.css",
})
export class StatisticsComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly serverInfo = signal<ServerInfo | null>(null);
  readonly statistics = signal<StatisticItem[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly lastRefresh = signal<Date | null>(null);

  readonly filterModel = signal({ filter: "" });
  readonly filterForm = form(this.filterModel);

  readonly zones = signal<Zone[]>([]);
  readonly zonesLoading = signal(false);

  readonly flushModel = signal({ zone: "" });
  readonly flushForm = form(this.flushModel, (s) => {
    required(s.zone, { message: "La zone est requise" });
  });

  readonly isFlushing = signal(false);
  readonly flushResult = signal<CacheFlushResult | null>(null);
  readonly flushError = signal<string | null>(null);

  readonly zonesByAccount = computed(() => {
    const groups = new Map<string, Zone[]>();
    for (const z of this.zones()) {
      const key = z.account ?? "";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(z);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([account, zones]) => ({ account, zones }));
  });

  readonly keyStats = computed(() => {
    const stats = this.statistics();
    return KEY_STATS.map((name) => ({
      name,
      item: stats.find((s) => s.name === name),
    })).filter((s) => s.item !== undefined);
  });

  readonly filteredStats = computed(() => {
    const q = this.filterModel().filter.toLowerCase();
    return this.statistics().filter(
      (s) => s.type === "StatisticItem" && (!q || (s.name ?? "").toLowerCase().includes(q)),
    );
  });

  readonly cacheHitRate = computed(() => {
    const hits = this._statValue("cache-hits");
    const misses = this._statValue("cache-misses");
    if (hits === null || misses === null || hits + misses === 0) return null;
    return ((hits / (hits + misses)) * 100).toFixed(1);
  });

  async ngOnInit(): Promise<void> {
    await Promise.all([this.loadStats(), this.loadServerInfo(), this.loadZones()]);
  }

  async loadZones(): Promise<void> {
    this.zonesLoading.set(true);
    try {
      this.zones.set(await this.pdns.getZones());
    } catch {
      // non-blocking
    } finally {
      this.zonesLoading.set(false);
    }
  }

  async loadServerInfo(): Promise<void> {
    try {
      this.serverInfo.set(await this.pdns.getServerInfo());
    } catch {
      // non-blocking
    }
  }

  async loadStats(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.statistics.set(await this.pdns.getStatistics(false));
      this.lastRefresh.set(new Date());
    } catch {
      this.error.set("Impossible de charger les statistiques du serveur.");
    } finally {
      this.isLoading.set(false);
    }
  }

  onFlushCache(): void {
    submit(this.flushForm, async () => {
      const zone = this.flushModel().zone;
      this.isFlushing.set(true);
      this.flushResult.set(null);
      this.flushError.set(null);
      try {
        const res = await this.pdns.flushCache(zone);
        this.flushResult.set(res);
        this.flushModel.set({ zone: "" });
      } catch {
        this.flushError.set(`Impossible de vider le cache pour "${zone}".`);
      } finally {
        this.isFlushing.set(false);
      }
    });
  }

  statValue(name: string): string {
    const s = this.statistics().find((st) => st.name === name);
    if (!s || typeof s.value !== "string") return "—";
    return s.value;
  }

  statLabel(name: string): string {
    const labels: Record<string, string> = {
      uptime: "Uptime (s)",
      queries: "Total queries",
      "udp-queries": "UDP requests",
      "tcp-queries": "TCP requests",
      latency: "Latency (µs)",
      "cache-hits": "Cache hits",
      "cache-misses": "Cache misses",
      "packetcache-hit": "Packet cache hits",
      "packetcache-miss": "Packet cache misses",
      "backend-queries": "Backend requests",
      "servfail-packets": "SERVFAIL",
      "corrupt-packets": "Corrupt packets",
      signatures: "DNSSEC signatures",
    };
    return labels[name] ?? name;
  }

  statIcon(name: string): string {
    if (name === "uptime") return "bi-clock-history";
    if (name.includes("queries") || name.includes("query")) return "bi-activity";
    if (name.includes("cache")) return "bi-lightning-charge";
    if (name.includes("latency")) return "bi-stopwatch";
    if (name.includes("fail") || name.includes("corrupt")) return "bi-exclamation-triangle";
    if (name.includes("signature")) return "bi-shield-check";
    return "bi-bar-chart";
  }

  statColorClass(name: string): string {
    if (name.includes("fail") || name.includes("corrupt")) return "text-danger";
    if (name.includes("miss")) return "text-warning";
    if (name.includes("hit")) return "text-success";
    if (name === "uptime") return "text-info";
    return "text-primary";
  }

  isRingOrMap(stat: StatisticItem): boolean {
    return stat.type === "RingStatisticItem" || stat.type === "MapStatisticItem";
  }

  asItems(value: unknown): SimpleStatisticItem[] {
    return Array.isArray(value) ? (value as SimpleStatisticItem[]) : [];
  }

  trackByStat(_: number, s: StatisticItem): string {
    return s.name ?? "";
  }

  private _statValue(name: string): number | null {
    const s = this.statistics().find((st) => st.name === name);
    if (!s || typeof s.value !== "string") return null;
    const n = Number(s.value);
    return isNaN(n) ? null : n;
  }
}

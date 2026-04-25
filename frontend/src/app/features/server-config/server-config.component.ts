import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { ConfigSetting } from "../../shared/models/pdns.model";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  selector: "app-server-config",
  imports: [FormField, TranslateModule],
  templateUrl: "./server-config.component.html",
  styleUrl: "./server-config.component.css",
})
export class ServerConfigComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly settings = signal<ConfigSetting[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  readonly filterModel = signal({ filter: "" });
  readonly filterForm = form(this.filterModel);

  readonly filtered = computed(() => {
    const q = this.filterModel().filter.toLowerCase();
    return q
      ? this.settings().filter((s) => s.name.toLowerCase().includes(q) || (s.value ?? "").toLowerCase().includes(q))
      : this.settings();
  });

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.settings.set(await this.pdns.getConfig());
    } catch {
      this.error.set("Impossible de charger la configuration du serveur.");
    } finally {
      this.isLoading.set(false);
    }
  }

  trackByName(_: number, s: ConfigSetting): string {
    return s.name;
  }
}

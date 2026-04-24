import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { RouterLink } from "@angular/router";
import { PdnsService } from "../../../core/services/pdns.service";
import { Zone } from "../../../shared/models/pdns.model";
import { cidrToReverseZoneName } from "../../../shared/utils/dns-reverse.utils";

@Component({
  selector: "app-zone-list",
  imports: [RouterLink, FormField],
  templateUrl: "./zone-list.component.html",
  styleUrl: "./zone-list.component.css",
})
export class ZoneListComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly zones = signal<Zone[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly showCreateModal = signal(false);
  readonly createError = signal<string | null>(null);
  readonly isCreating = signal(false);

  readonly searchModel = signal({ search: "" });
  readonly searchForm = form(this.searchModel);

  readonly filteredZones = computed(() => {
    const q = this.searchModel().search.toLowerCase();
    return this.zones().filter((z) => z.name.toLowerCase().includes(q));
  });

  readonly accounts = signal<string[]>([]);

  readonly createMode = signal<"standard" | "reverse">("standard");
  readonly reverseCidr = signal("");
  readonly reverseZoneName = computed(() => cidrToReverseZoneName(this.reverseCidr()));

  readonly createModel = signal({
    name: "",
    kind: "Native",
    nameservers: "",
    account: "",
  });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "The zone name is required" });
    required(s.nameservers, {
      message: "At least one nameserver is required (defines the SOA mname)",
    });
  });

  async ngOnInit(): Promise<void> {
    await Promise.all([this.loadZones(), this.loadAccounts()]);
  }

  async loadAccounts(): Promise<void> {
    try {
      this.accounts.set(await this.pdns.getAccounts());
    } catch {
      // non-blocking
    }
  }

  async loadZones(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const data = await this.pdns.getZones();
      this.zones.set(data);
    } catch {
      this.error.set("Unable to load DNS zones.");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreateModal(): void {
    this.createModel.set({
      name: "",
      kind: "Native",
      nameservers: "",
      account: "",
    });
    this.createError.set(null);
    this.createMode.set("standard");
    this.reverseCidr.set("");
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  onCreate(): void {
    if (this.createMode() === "reverse") {
      const genName = this.reverseZoneName();
      if (!genName) {
        this.createError.set("Invalid CIDR network. Examples: 192.168.1.0/24 or 2001:db8::/32");
        return;
      }
      this.createModel.update((m) => ({ ...m, name: genName }));
    }

    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, kind, nameservers, account } = this.createModel();
        const nsList = nameservers
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        await this.pdns.createZone({
          name,
          kind,
          nameservers: nsList,
          masters: [],
          account: account || undefined,
        });
        this.showCreateModal.set(false);
        await this.loadZones();
      } catch {
        this.createError.set("Error occurred while creating the zone.");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async deleteZone(zone: Zone): Promise<void> {
    if (!confirm(`Delete the zone "${zone.name}" ? This action is irreversible.`)) return;
    try {
      await this.pdns.deleteZone(zone.id);
      this.zones.update((list) => list.filter((z) => z.id !== zone.id));
    } catch {
      this.error.set(`Error occurred while deleting the zone "${zone.name}".`);
    }
  }

  trackById(_: number, zone: Zone): string {
    return zone.id;
  }
}

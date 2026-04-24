import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { Zone } from "../../shared/models/pdns.model";

@Component({
  selector: "app-catalogues",
  imports: [FormField],
  templateUrl: "./catalogues.component.html",
  styleUrl: "./catalogues.component.css",
})
export class CataloguesComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly catalogues = signal<Zone[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  readonly selectedCatalogue = signal<Zone | null>(null);
  readonly members = signal<Zone[]>([]);
  readonly availableZones = signal<Zone[]>([]);
  readonly isLoadingMembers = signal(false);
  readonly membersError = signal<string | null>(null);

  readonly showCreateModal = signal(false);
  readonly createError = signal<string | null>(null);
  readonly isCreating = signal(false);

  readonly createModel = signal({ name: "", nameservers: "", account: "" });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "The catalogue name is required" });
  });

  readonly accounts = signal<string[]>([]);

  readonly nonMembers = computed(() => {
    const memberIds = new Set(this.members().map((z) => z.id));
    return this.availableZones().filter((z) => !memberIds.has(z.id) && z.kind !== "Producer");
  });

  async ngOnInit(): Promise<void> {
    await Promise.all([this.loadCatalogues(), this.loadAccounts()]);
  }

  async loadCatalogues(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.catalogues.set(await this.pdns.getCatalogues());
    } catch {
      this.error.set("Impossible to load catalogues.");
    } finally {
      this.isLoading.set(false);
    }
  }

  async loadAccounts(): Promise<void> {
    try {
      this.accounts.set(await this.pdns.getAccounts());
    } catch {
      // non-blocking
    }
  }

  async selectCatalogue(cat: Zone): Promise<void> {
    this.selectedCatalogue.set(cat);
    this.isLoadingMembers.set(true);
    this.membersError.set(null);
    try {
      const [members, zones] = await Promise.all([this.pdns.getCatalogueMembers(cat.id), this.pdns.getZones()]);
      this.members.set(members);
      this.availableZones.set(zones);
    } catch {
      this.membersError.set("Impossible to load members.");
    } finally {
      this.isLoadingMembers.set(false);
    }
  }

  async addMember(zone: Zone): Promise<void> {
    const cat = this.selectedCatalogue();
    if (!cat) return;
    try {
      await this.pdns.addCatalogueMember(cat.id, zone.id);
      this.members.update((list) => [...list, zone]);
    } catch {
      this.membersError.set(`Impossible to add "${zone.name}" to the catalogue.`);
    }
  }

  async removeMember(zone: Zone): Promise<void> {
    const cat = this.selectedCatalogue();
    if (!cat) return;
    if (!confirm(`Remove "${zone.name}" from the catalogue "${cat.name}" ?`)) return;
    try {
      await this.pdns.removeCatalogueMember(cat.id, zone.id);
      this.members.update((list) => list.filter((z) => z.id !== zone.id));
    } catch {
      this.membersError.set(`Impossible to remove "${zone.name}" from the catalogue.`);
    }
  }

  openCreateModal(): void {
    this.createModel.set({ name: "", nameservers: "", account: "" });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  onCreate(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, nameservers, account } = this.createModel();
        const nsList = nameservers
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        await this.pdns.createCatalogue({
          name,
          kind: "Producer",
          nameservers: nsList,
          masters: [],
          account: account || undefined,
        });
        this.showCreateModal.set(false);
        await this.loadCatalogues();
      } catch {
        this.createError.set("Error occurred while creating the catalogue.");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async deleteCatalogue(cat: Zone): Promise<void> {
    if (!confirm(`Delete the catalogue "${cat.name}" ? This action is irreversible.`)) return;
    try {
      await this.pdns.deleteCatalogue(cat.id);
      this.catalogues.update((list) => list.filter((c) => c.id !== cat.id));
      if (this.selectedCatalogue()?.id === cat.id) {
        this.selectedCatalogue.set(null);
        this.members.set([]);
      }
    } catch {
      this.error.set(`Impossible to delete the catalogue "${cat.name}".`);
    }
  }

  trackById(_: number, zone: Zone): string {
    return zone.id;
  }
}

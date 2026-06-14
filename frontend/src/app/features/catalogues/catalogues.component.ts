import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { Zone } from "../../shared/models/pdns.model";
import { TranslatePipe } from "@ngx-translate/core";

type CatalogTab = "producer" | "consumer";

@Component({
  selector: "app-catalogues",
  imports: [FormField, TranslatePipe],
  templateUrl: "./catalogues.component.html",
  styleUrl: "./catalogues.component.css",
})
export class CataloguesComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly activeTab = signal<CatalogTab>("producer");

  // ── Producer ──────────────────────────────────────────────────────────────
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
    return this.availableZones().filter((z) => !memberIds.has(z.id) && z.kind !== "Producer" && z.kind !== "Consumer");
  });

  // ── Consumer ──────────────────────────────────────────────────────────────
  readonly consumers = signal<Zone[]>([]);
  readonly isLoadingConsumers = signal(false);
  readonly consumerError = signal<string | null>(null);

  readonly selectedConsumer = signal<Zone | null>(null);
  readonly consumerMembers = signal<Zone[]>([]);
  readonly isLoadingConsumerMembers = signal(false);
  readonly consumerMembersError = signal<string | null>(null);

  readonly showCreateConsumerModal = signal(false);
  readonly createConsumerError = signal<string | null>(null);
  readonly isCreatingConsumer = signal(false);

  readonly createConsumerModel = signal({ name: "", masters: "", account: "" });
  readonly createConsumerForm = form(this.createConsumerModel, (s) => {
    required(s.name, { message: "The consumer name is required" });
    required(s.masters, { message: "At least one master server is required" });
  });

  async ngOnInit(): Promise<void> {
    await Promise.all([this.loadCatalogues(), this.loadConsumers(), this.loadAccounts()]);
  }

  // ── Producer methods ──────────────────────────────────────────────────────

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

  // ── Consumer methods ──────────────────────────────────────────────────────

  async loadConsumers(): Promise<void> {
    this.isLoadingConsumers.set(true);
    this.consumerError.set(null);
    try {
      this.consumers.set(await this.pdns.getConsumers());
    } catch {
      this.consumerError.set("Impossible to load consumer catalog zones.");
    } finally {
      this.isLoadingConsumers.set(false);
    }
  }

  async selectConsumer(consumer: Zone): Promise<void> {
    this.selectedConsumer.set(consumer);
    this.isLoadingConsumerMembers.set(true);
    this.consumerMembersError.set(null);
    try {
      this.consumerMembers.set(await this.pdns.getConsumerMembers(consumer.id));
    } catch {
      this.consumerMembersError.set("Impossible to load consumer members.");
    } finally {
      this.isLoadingConsumerMembers.set(false);
    }
  }

  openCreateConsumerModal(): void {
    this.createConsumerModel.set({ name: "", masters: "", account: "" });
    this.createConsumerError.set(null);
    this.showCreateConsumerModal.set(true);
  }

  closeCreateConsumerModal(): void {
    this.showCreateConsumerModal.set(false);
  }

  onCreateConsumer(): void {
    submit(this.createConsumerForm, async () => {
      this.isCreatingConsumer.set(true);
      this.createConsumerError.set(null);
      try {
        const { name, masters, account } = this.createConsumerModel();
        const mastersList = masters
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        await this.pdns.createConsumer({
          name,
          kind: "Consumer",
          nameservers: [],
          masters: mastersList,
          account: account || undefined,
        });
        this.showCreateConsumerModal.set(false);
        await this.loadConsumers();
      } catch {
        this.createConsumerError.set("Error occurred while creating the consumer catalog zone.");
      } finally {
        this.isCreatingConsumer.set(false);
      }
    });
  }

  async deleteConsumer(consumer: Zone): Promise<void> {
    if (!confirm(`Delete the consumer "${consumer.name}" ? This action is irreversible.`)) return;
    try {
      await this.pdns.deleteConsumer(consumer.id);
      this.consumers.update((list) => list.filter((c) => c.id !== consumer.id));
      if (this.selectedConsumer()?.id === consumer.id) {
        this.selectedConsumer.set(null);
        this.consumerMembers.set([]);
      }
    } catch {
      this.consumerError.set(`Impossible to delete the consumer "${consumer.name}".`);
    }
  }

  trackById(_: number, zone: Zone): string {
    return zone.id;
  }
}

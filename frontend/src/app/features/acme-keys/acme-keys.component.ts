import { DatePipe } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { TranslateModule } from "@ngx-translate/core";
import { AuthService } from "../../core/services/auth.service";
import { AcmeApiKey, AcmeKeysService } from "../../core/services/acme-keys.service";
import { PdnsService } from "../../core/services/pdns.service";
import { Zone } from "../../shared/models/pdns.model";

@Component({
  selector: "app-acme-keys",
  imports: [DatePipe, FormField, TranslateModule],
  templateUrl: "./acme-keys.component.html",
  styleUrl: "./acme-keys.component.css",
})
export class AcmeKeysComponent implements OnInit {
  private readonly acmeKeys = inject(AcmeKeysService);
  private readonly pdns = inject(PdnsService);
  readonly auth = inject(AuthService);

  readonly keys = signal<AcmeApiKey[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  // Create modal
  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);

  // Created key display modal
  readonly createdKey = signal<string | null>(null);
  readonly copied = signal(false);

  // Zone assignment modal
  readonly editingKey = signal<AcmeApiKey | null>(null);
  readonly availableZones = signal<Zone[]>([]);
  readonly selectedZones = signal<Set<string>>(new Set());
  readonly isSavingZones = signal(false);
  readonly zonesError = signal<string | null>(null);

  readonly createModel = signal({ name: "", secret: "" });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "ACMEKEYS.NAME_REQUIRED" });
  });

  async ngOnInit(): Promise<void> {
    await this.loadKeys();
  }

  async loadKeys(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const loader = this.auth.isAdmin() ? this.acmeKeys.listAllKeys() : this.acmeKeys.listKeys();
      this.keys.set(await loader);
    } catch {
      this.error.set("ACMEKEYS.LOAD_ERROR");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreateModal(): void {
    this.createModel.set({ name: "", secret: "" });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  closeCreatedKeyModal(): void {
    this.createdKey.set(null);
    this.copied.set(false);
  }

  onCreate(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, secret } = this.createModel();
        const created = await this.acmeKeys.createKey(name, secret.trim() || undefined);
        this.showCreateModal.set(false);
        this.keys.update((list) => [...list, created]);
        this.createdKey.set(created.key);
      } catch {
        this.createError.set("ACMEKEYS.CREATE_ERROR");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async copyKey(): Promise<void> {
    const key = this.createdKey();
    if (!key) return;
    await navigator.clipboard.writeText(key);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  async openZoneModal(key: AcmeApiKey): Promise<void> {
    this.editingKey.set(key);
    this.selectedZones.set(new Set(key.zones));
    this.zonesError.set(null);
    try {
      this.availableZones.set(await this.pdns.getZones());
    } catch {
      this.zonesError.set("ACMEKEYS.ZONES_LOAD_ERROR");
    }
  }

  closeZoneModal(): void {
    this.editingKey.set(null);
  }

  toggleZone(zoneName: string): void {
    this.selectedZones.update((set) => {
      const next = new Set(set);
      next.has(zoneName) ? next.delete(zoneName) : next.add(zoneName);
      return next;
    });
  }

  async saveZones(): Promise<void> {
    const key = this.editingKey();
    if (!key) return;
    this.isSavingZones.set(true);
    this.zonesError.set(null);
    try {
      const updated = await this.acmeKeys.updateZones(key.id, [...this.selectedZones()]);
      this.keys.update((list) => list.map((k) => (k.id === updated.id ? updated : k)));
      this.editingKey.set(null);
    } catch {
      this.zonesError.set("ACMEKEYS.ZONES_SAVE_ERROR");
    } finally {
      this.isSavingZones.set(false);
    }
  }

  async deleteKey(key: AcmeApiKey): Promise<void> {
    if (!confirm(`Supprimer la clé ACME "${key.name}" ?`)) return;
    try {
      await this.acmeKeys.deleteKey(key.id);
      this.keys.update((list) => list.filter((k) => k.id !== key.id));
    } catch {
      this.error.set("ACMEKEYS.DELETE_ERROR");
    }
  }

  trackById(_: number, key: AcmeApiKey): number {
    return key.id;
  }
}

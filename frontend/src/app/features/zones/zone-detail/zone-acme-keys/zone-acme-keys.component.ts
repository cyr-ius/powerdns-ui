import { DatePipe } from "@angular/common";
import { Component, inject, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { TranslatePipe } from "@ngx-translate/core";
import { AcmeApiKey, AcmeApiKeyCreated, AcmeKeysService } from "../../../../core/services/acme-keys.service";
import { ZoneDetailStore } from "../zone-detail.store";

/** ACME keys tab: API keys allowed to answer ACME challenges in the zone. */
@Component({
  selector: "app-zone-acme-keys",
  imports: [FormField, TranslatePipe, DatePipe],
  templateUrl: "./zone-acme-keys.component.html",
  styleUrl: "./zone-acme-keys.component.css",
  host: { class: "d-block" },
})
export class ZoneAcmeKeysComponent {
  private readonly acmeKeysSvc = inject(AcmeKeysService);
  private readonly store = inject(ZoneDetailStore);

  readonly zoneAcmeKeys = this.store.zoneAcmeKeys;
  readonly isLoadingAcmeKeys = this.store.isLoadingAcmeKeys;
  readonly acmeKeysError = this.store.acmeKeysError;

  // ── Creation ──────────────────────────────────────────────────────────────
  readonly showAcmeCreateModal = signal(false);
  readonly isCreatingAcmeKey = signal(false);
  readonly acmeCreateError = signal<string | null>(null);
  readonly createdAcmeKey = signal<AcmeApiKeyCreated | null>(null);
  readonly showAcmeSecretModal = signal(false);
  readonly acmeCopied = signal(false);

  readonly acmeCreateModel = signal({ name: "", secret: "", comment: "" });
  readonly acmeCreateForm = form(this.acmeCreateModel, (s) => {
    required(s.name);
  });

  // ── Editing ───────────────────────────────────────────────────────────────
  readonly editingAcmeKey = signal<AcmeApiKey | null>(null);
  readonly isEditingAcmeKey = signal(false);
  readonly acmeEditError = signal<string | null>(null);
  readonly acmeEditModel = signal({ name: "", comment: "" });
  readonly acmeEditForm = form(this.acmeEditModel, (s) => {
    required(s.name);
  });

  openAcmeCreateModal(): void {
    this.acmeCreateModel.set({ name: "", secret: "", comment: "" });
    this.acmeCreateError.set(null);
    this.showAcmeCreateModal.set(true);
  }

  closeAcmeCreateModal(): void {
    this.showAcmeCreateModal.set(false);
  }

  onCreateAcmeKey(): void {
    submit(this.acmeCreateForm, async () => {
      this.isCreatingAcmeKey.set(true);
      this.acmeCreateError.set(null);
      try {
        const { name, secret, comment } = this.acmeCreateModel();
        const created = await this.acmeKeysSvc.createZoneAcmeKey(
          this.store.zoneId,
          name,
          secret.trim() || undefined,
          comment.trim() || undefined,
        );
        this.createdAcmeKey.set(created);
        this.showAcmeCreateModal.set(false);
        this.showAcmeSecretModal.set(true);
        this.acmeCopied.set(false);
        this.zoneAcmeKeys.update((keys) => [...keys, created]);
      } catch {
        this.acmeCreateError.set("ZONE_DETAIL.ACME_KEY_CREATE_ERROR");
      } finally {
        this.isCreatingAcmeKey.set(false);
      }
    });
  }

  copyAcmeKey(): void {
    const key = this.createdAcmeKey()?.key;
    if (!key) return;
    void navigator.clipboard.writeText(key).then(() => {
      this.acmeCopied.set(true);
      setTimeout(() => this.acmeCopied.set(false), 2000);
    });
  }

  closeAcmeSecretModal(): void {
    this.showAcmeSecretModal.set(false);
    this.createdAcmeKey.set(null);
  }

  async deleteAcmeKey(key: AcmeApiKey): Promise<void> {
    if (!confirm(`Supprimer la clé ACME « ${key.name} » ?`)) return;
    try {
      await this.acmeKeysSvc.deleteZoneAcmeKey(this.store.zoneId, key.id);
      this.zoneAcmeKeys.update((keys) => keys.filter((k) => k.id !== key.id));
    } catch {
      this.acmeKeysError.set("ZONE_DETAIL.ACME_KEY_DELETE_ERROR");
    }
  }

  openAcmeEditModal(key: AcmeApiKey): void {
    this.editingAcmeKey.set(key);
    this.acmeEditModel.set({ name: key.name, comment: key.comment ?? "" });
    this.acmeEditError.set(null);
  }

  closeAcmeEditModal(): void {
    this.editingAcmeKey.set(null);
  }

  onEditAcmeKey(): void {
    submit(this.acmeEditForm, async () => {
      const key = this.editingAcmeKey();
      if (!key) return;
      this.isEditingAcmeKey.set(true);
      this.acmeEditError.set(null);
      try {
        const { name, comment } = this.acmeEditModel();
        const updated = await this.acmeKeysSvc.updateZoneAcmeKey(this.store.zoneId, key.id, name, comment.trim() || null);
        this.zoneAcmeKeys.update((keys) => keys.map((k) => (k.id === updated.id ? updated : k)));
        this.editingAcmeKey.set(null);
      } catch {
        this.acmeEditError.set("ZONE_DETAIL.ACME_KEY_EDIT_ERROR");
      } finally {
        this.isEditingAcmeKey.set(false);
      }
    });
  }
}

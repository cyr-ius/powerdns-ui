import { Component, inject, signal } from "@angular/core";
import { form, FormField, submit } from "@angular/forms/signals";
import { TranslatePipe } from "@ngx-translate/core";
import { PdnsService } from "../../../../core/services/pdns.service";
import { CryptoKey, CryptoKeyCreate } from "../../../../shared/models/pdns.model";
import { ZoneDetailStore } from "../zone-detail.store";

const CRYPTO_ALGORITHMS = ["ECDSAP256SHA256", "ECDSAP384SHA384", "ED25519", "ED448", "RSASHA256", "RSASHA512"];

/** DNSSEC tab: crypto keys of the zone and rectification. */
@Component({
  selector: "app-zone-dnssec",
  imports: [FormField, TranslatePipe],
  templateUrl: "./zone-dnssec.component.html",
  styleUrl: "./zone-dnssec.component.css",
  host: { class: "d-block" },
})
export class ZoneDnssecComponent {
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  readonly zone = this.store.zone;
  readonly cryptoKeys = this.store.cryptoKeys;
  readonly isLoadingKeys = this.store.isLoadingKeys;
  readonly keyError = this.store.keyError;
  readonly showKeyModal = signal(false);
  readonly isSubmittingKey = signal(false);
  readonly isRectifying = signal(false);
  readonly expandedKeyId = signal<number | null>(null);
  readonly copiedText = signal<string | null>(null);
  readonly cryptoAlgorithms = CRYPTO_ALGORITHMS;

  // bits: 0 = use the algorithm's default
  readonly keyModel = signal({
    keytype: "ksk",
    algorithm: "ECDSAP256SHA256",
    bits: 0,
  });
  readonly keyForm = form(this.keyModel);

  openKeyModal(): void {
    this.keyModel.set({
      keytype: "ksk",
      algorithm: "ECDSAP256SHA256",
      bits: 0,
    });
    this.showKeyModal.set(true);
  }

  closeKeyModal(): void {
    this.showKeyModal.set(false);
  }

  onCreateKey(): void {
    submit(this.keyForm, async () => {
      this.isSubmittingKey.set(true);
      this.keyError.set(null);
      try {
        const { keytype, algorithm, bits } = this.keyModel();
        const payload: CryptoKeyCreate = {
          keytype,
          active: true,
          algorithm: algorithm || undefined,
          bits: bits > 0 ? bits : undefined,
        };
        await this.pdns.createCryptoKey(this.store.zoneId, payload);
        this.showKeyModal.set(false);
        await this.store.loadCryptoKeys();
        await this.store.loadZone();
      } catch {
        this.keyError.set("Error occurred while creating the key.");
      } finally {
        this.isSubmittingKey.set(false);
      }
    });
  }

  async rectifyZone(): Promise<void> {
    this.isRectifying.set(true);
    this.keyError.set(null);
    try {
      await this.pdns.rectifyZone(this.store.zoneId);
      this.store.actionMessage.set({
        type: "success",
        text: "Zone rectified successfully.",
      });
    } catch {
      this.store.actionMessage.set({
        type: "error",
        text: "Error occurred while rectifying the zone.",
      });
    } finally {
      this.isRectifying.set(false);
    }
  }

  toggleExpandKey(keyId: number): void {
    this.expandedKeyId.set(this.expandedKeyId() === keyId ? null : keyId);
  }

  copyText(text: string): void {
    void navigator.clipboard.writeText(text).then(() => {
      this.copiedText.set(text);
      setTimeout(() => this.copiedText.set(null), 2000);
    });
  }

  async toggleKey(key: CryptoKey): Promise<void> {
    try {
      await this.pdns.updateCryptoKey(this.store.zoneId, key.id, {
        active: !key.active,
      });
      await this.store.loadCryptoKeys();
    } catch {
      this.keyError.set("Unable to modify the key state.");
    }
  }

  async togglePublished(key: CryptoKey): Promise<void> {
    try {
      await this.pdns.updateCryptoKey(this.store.zoneId, key.id, {
        published: !key.published,
      });
      await this.store.loadCryptoKeys();
    } catch {
      this.keyError.set("Unable to modify the publication state of the key.");
    }
  }

  async deleteKey(key: CryptoKey): Promise<void> {
    if (!confirm(`Supprimer la clé DNSSEC #${key.id} (${key.keytype}) ?`)) return;
    try {
      await this.pdns.deleteCryptoKey(this.store.zoneId, key.id);
      await this.store.loadCryptoKeys();
      await this.store.loadZone();
    } catch {
      this.keyError.set("Unable to delete the key.");
    }
  }

  trackByKey(_: number, key: CryptoKey): number {
    return key.id;
  }
}

import { inject, Injectable, signal } from "@angular/core";
import { PdnsService } from "../../../core/services/pdns.service";
import { ZoneDetailStore } from "./zone-detail.store";

/**
 * Edition of list and single-value metadata, shared by the Transfer and
 * DNS Update tabs. Provided by each tab, so each one has its own status.
 */
@Injectable()
export class ZoneMetadataEntries {
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  readonly isSubmitting = signal(false);
  readonly error = signal<string | null>(null);
  readonly success = signal<string | null>(null);

  values(kind: string): string[] {
    return this.store.metadata().find((m) => m.kind === kind)?.metadata ?? [];
  }

  async add(kind: string, value: string): Promise<void> {
    const v = value.trim();
    if (!v) return;
    this.isSubmitting.set(true);
    this.error.set(null);
    try {
      const current = this.values(kind);
      if (!current.includes(v)) {
        await this.pdns.setMetadata(this.store.zoneId, kind, [...current, v]);
      }
      await this.store.loadMetadata();
      this.flashSuccess();
    } catch {
      this.error.set(`Error occurred while updating ${kind}.`);
    } finally {
      this.isSubmitting.set(false);
    }
  }

  async remove(kind: string, value: string): Promise<void> {
    this.isSubmitting.set(true);
    this.error.set(null);
    try {
      const updated = this.values(kind).filter((v) => v !== value);
      if (updated.length === 0) {
        await this.pdns.deleteMetadata(this.store.zoneId, kind);
      } else {
        await this.pdns.setMetadata(this.store.zoneId, kind, updated);
      }
      await this.store.loadMetadata();
    } catch {
      this.error.set(`Error occurred while removing from ${kind}.`);
    } finally {
      this.isSubmitting.set(false);
    }
  }

  async saveSingle(kind: string, value: string): Promise<void> {
    this.isSubmitting.set(true);
    this.error.set(null);
    try {
      if (!value.trim()) {
        await this.pdns.deleteMetadata(this.store.zoneId, kind);
      } else {
        await this.pdns.setMetadata(this.store.zoneId, kind, [value.trim()]);
      }
      await this.store.loadMetadata();
      this.flashSuccess();
    } catch {
      this.error.set(`Error occurred while updating ${kind}.`);
    } finally {
      this.isSubmitting.set(false);
    }
  }

  private flashSuccess(): void {
    this.success.set("Successfully updated.");
    setTimeout(() => this.success.set(null), 3000);
  }
}

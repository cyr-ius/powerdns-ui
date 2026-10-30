import { Component, inject, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { TranslatePipe } from "@ngx-translate/core";
import { PdnsService } from "../../../../core/services/pdns.service";
import { Metadata } from "../../../../shared/models/pdns.model";
import { ZoneDetailStore } from "../zone-detail.store";

const METADATA_KINDS = [
  "ALLOW-AXFR-FROM",
  "ALLOW-DNSUPDATE-FROM",
  "ALSO-NOTIFY",
  "API-RECTIFY",
  "AXFR-MASTER-TSIG",
  "AXFR-SOURCE",
  "FORWARD-DNSUPDATE",
  "IXFR",
  "NOTIFY-DNSUPDATE",
  "NSEC3NARROW",
  "NSEC3PARAM",
  "PRESIGNED",
  "PUBLISH-CDS",
  "PUBLISH-CDNSKEY",
  "SOA-EDIT",
  "SOA-EDIT-API",
  "SOA-EDIT-DNSUPDATE",
  "TSIG-ALLOW-AXFR",
  "TSIG-ALLOW-DNSUPDATE",
];

/** Metadata tab: raw view and edition of the zone metadata. */
@Component({
  selector: "app-zone-metadata",
  imports: [FormField, TranslatePipe],
  templateUrl: "./zone-metadata.component.html",
  styleUrl: "./zone-metadata.component.css",
  host: { class: "d-block" },
})
export class ZoneMetadataComponent {
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  readonly metadata = this.store.metadata;
  readonly isLoadingMeta = this.store.isLoadingMeta;
  readonly metaError = this.store.metaError;
  readonly showMetaModal = signal(false);
  readonly isSubmittingMeta = signal(false);
  readonly metaKindOptions = METADATA_KINDS;

  readonly metaModel = signal({ kind: "", value: "" });
  readonly metaForm = form(this.metaModel, (s) => {
    required(s.kind);
    required(s.value);
  });

  openMetaModal(): void {
    this.metaModel.set({ kind: "", value: "" });
    this.showMetaModal.set(true);
  }

  closeMetaModal(): void {
    this.showMetaModal.set(false);
  }

  onSaveMeta(): void {
    submit(this.metaForm, async () => {
      this.isSubmittingMeta.set(true);
      try {
        const { kind, value } = this.metaModel();
        await this.pdns.setMetadata(this.store.zoneId, kind, [value]);
        this.showMetaModal.set(false);
        await this.store.loadMetadata();
      } catch {
        this.metaError.set("Error occurred while saving the metadata.");
      } finally {
        this.isSubmittingMeta.set(false);
      }
    });
  }

  async deleteMeta(kind: string): Promise<void> {
    if (!confirm(`Supprimer la métadonnée "${kind}" ?`)) return;
    try {
      await this.pdns.deleteMetadata(this.store.zoneId, kind);
      await this.store.loadMetadata();
    } catch {
      this.metaError.set(`Unable to delete the metadata "${kind}".`);
    }
  }

  trackByMeta(_: number, meta: Metadata): string {
    return meta.kind;
  }
}

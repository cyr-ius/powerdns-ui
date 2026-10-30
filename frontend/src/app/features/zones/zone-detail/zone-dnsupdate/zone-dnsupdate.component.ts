import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { RouterLink } from "@angular/router";
import { TranslatePipe } from "@ngx-translate/core";
import { TsigKey } from "../../../../shared/models/pdns.model";
import { ZoneDetailStore } from "../zone-detail.store";
import { ZoneMetadataEntries } from "../zone-metadata-entries";

/** DNS Update tab: RFC 2136 access to the zone (addresses and TSIG keys). */
@Component({
  selector: "app-zone-dnsupdate",
  imports: [RouterLink, TranslatePipe],
  templateUrl: "./zone-dnsupdate.component.html",
  providers: [ZoneMetadataEntries],
  host: { class: "d-block" },
})
export class ZoneDnsupdateComponent {
  private readonly store = inject(ZoneDetailStore);
  private readonly entries = inject(ZoneMetadataEntries);

  readonly tsigKeys = this.store.tsigKeys;
  readonly isLoadingMeta = this.store.isLoadingMeta;
  readonly dnsupdateEnabled = this.store.dnsupdateEnabled;
  readonly tsigAllowDnsupdate = this.store.tsigAllowDnsupdate;
  readonly allowDnsupdateFrom = this.store.allowDnsupdateFrom;
  readonly isSubmittingTransfer = this.entries.isSubmitting;
  readonly transferError = this.entries.error;
  readonly transferSuccess = this.entries.success;

  readonly newTsigAllowDnsupdate = signal("");
  readonly newAllowDnsupdateFrom = signal("");

  readonly availableTsigForDnsupdate = computed(() =>
    this.tsigKeys().filter((k) => !this.tsigAllowDnsupdate().includes(k.id)),
  );

  // Editable copy, reset whenever the metadata is reloaded.
  readonly editForwardDnsupdate = linkedSignal(() => this.entries.values("FORWARD-DNSUPDATE")[0] ?? "");

  async addTsigAllowDnsupdateEntry(): Promise<void> {
    await this.entries.add("TSIG-ALLOW-DNSUPDATE", this.newTsigAllowDnsupdate());
    this.newTsigAllowDnsupdate.set("");
  }

  async addAllowDnsupdateFromEntry(): Promise<void> {
    await this.entries.add("ALLOW-DNSUPDATE-FROM", this.newAllowDnsupdateFrom());
    this.newAllowDnsupdateFrom.set("");
  }

  removeMetadataEntry(kind: string, value: string): Promise<void> {
    return this.entries.remove(kind, value);
  }

  saveSingleMetadata(kind: string, value: string): Promise<void> {
    return this.entries.saveSingle(kind, value);
  }

  getTsigKeyById(id: string): TsigKey | undefined {
    return this.tsigKeys().find((k) => k.id === id);
  }
}

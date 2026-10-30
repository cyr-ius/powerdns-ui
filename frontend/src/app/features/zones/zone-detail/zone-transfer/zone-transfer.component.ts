import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { RouterLink } from "@angular/router";
import { TranslatePipe } from "@ngx-translate/core";
import { TsigKey } from "../../../../shared/models/pdns.model";
import { ZoneDetailStore } from "../zone-detail.store";
import { ZoneMetadataEntries } from "../zone-metadata-entries";

/** Transfer tab: AXFR access, notifications and TSIG keys of the zone. */
@Component({
  selector: "app-zone-transfer",
  imports: [RouterLink, TranslatePipe],
  templateUrl: "./zone-transfer.component.html",
  providers: [ZoneMetadataEntries],
  host: { class: "d-block" },
})
export class ZoneTransferComponent {
  private readonly store = inject(ZoneDetailStore);
  private readonly entries = inject(ZoneMetadataEntries);

  readonly zone = this.store.zone;
  readonly tsigKeys = this.store.tsigKeys;
  readonly isLoadingMeta = this.store.isLoadingMeta;
  readonly isSubmittingTransfer = this.entries.isSubmitting;
  readonly transferError = this.entries.error;
  readonly transferSuccess = this.entries.success;

  readonly newAllowAxfrFrom = signal("");
  readonly newAlsoNotify = signal("");
  readonly newTsigAllowAxfr = signal("");

  readonly allowAxfrFrom = computed(() => this.entries.values("ALLOW-AXFR-FROM"));
  readonly alsoNotify = computed(() => this.entries.values("ALSO-NOTIFY"));
  readonly tsigAllowAxfr = computed(() => this.entries.values("TSIG-ALLOW-AXFR"));
  readonly axfrMasterTsig = computed(() => this.entries.values("AXFR-MASTER-TSIG")[0] ?? "");
  readonly axfrSource = computed(() => this.entries.values("AXFR-SOURCE")[0] ?? "");
  readonly availableTsigForAxfr = computed(() => this.tsigKeys().filter((k) => !this.tsigAllowAxfr().includes(k.id)));

  // Editable copies, reset whenever the metadata is reloaded.
  readonly editAxfrMasterTsig = linkedSignal(() => this.axfrMasterTsig());
  readonly editAxfrSource = linkedSignal(() => this.axfrSource());

  async addAllowAxfrFromEntry(): Promise<void> {
    await this.entries.add("ALLOW-AXFR-FROM", this.newAllowAxfrFrom());
    this.newAllowAxfrFrom.set("");
  }

  async addAlsoNotifyEntry(): Promise<void> {
    await this.entries.add("ALSO-NOTIFY", this.newAlsoNotify());
    this.newAlsoNotify.set("");
  }

  async addTsigAllowAxfrEntry(): Promise<void> {
    await this.entries.add("TSIG-ALLOW-AXFR", this.newTsigAllowAxfr());
    this.newTsigAllowAxfr.set("");
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

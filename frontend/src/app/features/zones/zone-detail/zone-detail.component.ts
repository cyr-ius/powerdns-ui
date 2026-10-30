import { Component, ElementRef, inject, OnInit, signal, viewChild } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { TranslatePipe } from "@ngx-translate/core";
import { PdnsService } from "../../../core/services/pdns.service";
import { ZoneAcmeKeysComponent } from "./zone-acme-keys/zone-acme-keys.component";
import { ZoneChecksComponent } from "./zone-checks/zone-checks.component";
import { ZoneDetailStore } from "./zone-detail.store";
import { ZoneDnssecComponent } from "./zone-dnssec/zone-dnssec.component";
import { ZoneDnsupdateComponent } from "./zone-dnsupdate/zone-dnsupdate.component";
import { ZoneMembersComponent } from "./zone-members/zone-members.component";
import { ZoneMetadataComponent } from "./zone-metadata/zone-metadata.component";
import { ZoneRecordsComponent } from "./zone-records/zone-records.component";
import { ZoneSettingsComponent } from "./zone-settings/zone-settings.component";
import { ZoneTransferComponent } from "./zone-transfer/zone-transfer.component";

export type Tab = "records" | "metadata" | "dnssec" | "settings" | "transfer" | "dnsupdate" | "members" | "acmekeys";

/** Zone page: header, zone actions and the tabs, which share a ZoneDetailStore. */
@Component({
  selector: "app-zone-detail",
  imports: [
    RouterLink,
    TranslatePipe,
    ZoneChecksComponent,
    ZoneRecordsComponent,
    ZoneMetadataComponent,
    ZoneDnssecComponent,
    ZoneTransferComponent,
    ZoneDnsupdateComponent,
    ZoneSettingsComponent,
    ZoneMembersComponent,
    ZoneAcmeKeysComponent,
  ],
  templateUrl: "./zone-detail.component.html",
  providers: [ZoneDetailStore],
})
export class ZoneDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  protected get zoneId(): string {
    return this.store.zoneId;
  }

  readonly zone = this.store.zone;
  readonly isLoading = this.store.isLoading;
  readonly error = this.store.error;
  readonly actionMessage = this.store.actionMessage;
  readonly currentRole = this.store.currentRole;
  readonly isZoneAdmin = this.store.isZoneAdmin;
  readonly isReverseZone = this.store.isReverseZone;
  readonly tsigAllowDnsupdate = this.store.tsigAllowDnsupdate;
  readonly allowDnsupdateFrom = this.store.allowDnsupdateFrom;
  readonly members = this.store.members;
  readonly zoneAcmeKeys = this.store.zoneAcmeKeys;
  readonly isCheckingSoa = this.store.isCheckingSoa;
  readonly isCheckingEmail = this.store.isCheckingEmail;
  readonly activeTab = signal<Tab>("records");

  // ── Zone actions ─────────────────────────────────────────────────────────
  readonly isNotifying = signal(false);
  readonly isRetrieving = signal(false);
  readonly isExporting = signal(false);
  readonly isImporting = signal(false);
  readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>("fileInput");

  async ngOnInit(): Promise<void> {
    this.store.zoneId = this.route.snapshot.paramMap.get("id") ?? "";
    await Promise.all([
      this.store.loadZone(),
      this.store.loadAllZones(),
      this.store.loadZoneRole(),
      this.store.loadServerConfig(),
    ]);
    void this.store.loadMetadata();
    void this.store.loadZoneRecordTypes();
    if (this.isZoneAdmin()) {
      void this.store.loadMembers();
      void this.store.loadZoneAcmeKeys();
    }
  }

  loadZone(): Promise<void> {
    return this.store.loadZone();
  }

  checkSoaSync(): Promise<void> {
    return this.store.checkSoaSync();
  }

  checkEmailSecurity(): Promise<void> {
    return this.store.checkEmailSecurity();
  }

  setTab(tab: Tab): void {
    const store = this.store;
    this.activeTab.set(tab);
    if ((tab === "metadata" || tab === "transfer" || tab === "settings" || tab === "dnsupdate") && !store.metadataLoaded)
      void store.loadMetadata();
    if (tab === "dnssec" && store.cryptoKeys().length === 0) void store.loadCryptoKeys();
    if ((tab === "transfer" || tab === "dnsupdate") && store.tsigKeys().length === 0) void store.loadTsigKeys();
    if (tab === "members" && !store.membersLoaded) void store.loadMembers();
    if (tab === "acmekeys" && !store.acmeKeysLoaded) void store.loadZoneAcmeKeys();
  }

  // ── Zone actions ─────────────────────────────────────────────────────────

  async notifySlaves(): Promise<void> {
    this.isNotifying.set(true);
    this.actionMessage.set(null);
    try {
      const res = await this.pdns.notifySlaves(this.zoneId);
      this.actionMessage.set({
        type: "success",
        text: res.result ?? "Notification sent.",
      });
    } catch {
      this.actionMessage.set({
        type: "error",
        text: "Error occurred while sending the notification.",
      });
    } finally {
      this.isNotifying.set(false);
    }
  }

  async axfrRetrieve(): Promise<void> {
    this.isRetrieving.set(true);
    this.actionMessage.set(null);
    try {
      const res = await this.pdns.axfrRetrieve(this.zoneId);
      this.actionMessage.set({
        type: "success",
        text: res.result ?? "AXFR retrieval triggered.",
      });
    } catch {
      this.actionMessage.set({
        type: "error",
        text: "Error occurred while triggering AXFR retrieval.",
      });
    } finally {
      this.isRetrieving.set(false);
    }
  }

  async exportZone(): Promise<void> {
    this.isExporting.set(true);
    this.actionMessage.set(null);
    try {
      const content = await this.pdns.exportZone(this.zoneId);
      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = (this.zone()?.name ?? this.zoneId).replace(/\.$/, "") + ".zone";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      this.actionMessage.set({
        type: "error",
        text: "Error occurred while exporting the zone.",
      });
    } finally {
      this.isExporting.set(false);
    }
  }

  triggerImport(): void {
    this.fileInput().nativeElement.click();
  }

  async onFileSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    input.value = "";
    this.isImporting.set(true);
    this.actionMessage.set(null);
    try {
      await this.pdns.importZone(this.zoneId, file);
      this.actionMessage.set({ type: "success", text: "Zone imported successfully." });
      await this.store.loadZone();
    } catch {
      this.actionMessage.set({ type: "error", text: "Error occurred while importing the zone." });
    } finally {
      this.isImporting.set(false);
    }
  }
}

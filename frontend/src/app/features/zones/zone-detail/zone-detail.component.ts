import { Component, computed, ElementRef, inject, OnInit, signal, viewChild } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { AdminService } from "../../../core/services/admin.service";
import { AuthService } from "../../../core/services/auth.service";
import { AcmeApiKey, AcmeKeysService } from "../../../core/services/acme-keys.service";
import { PdnsService } from "../../../core/services/pdns.service";
import type { RecordType, ZoneRecordTypes } from "../../../shared/models/admin.model";
import {
  CryptoKey,
  CryptoKeyCreate,
  Metadata,
  RRset,
  TsigKey,
  UserBasic,
  Zone,
  ZoneDetail,
  ZoneMember,
  ZoneRole,
} from "../../../shared/models/pdns.model";
import { buildPtrName, findBestReverseZone } from "../../../shared/utils/dns-reverse.utils";
import { TranslateModule } from "@ngx-translate/core";

const ALL_DNS_TYPES = ["A", "AAAA", "CAA", "CNAME", "DNAME", "LOC", "MX", "NS", "PTR", "SOA", "SPF", "SRV", "TXT"];
const CRYPTO_ALGORITHMS = ["ECDSAP256SHA256", "ECDSAP384SHA384", "ED25519", "ED448", "RSASHA256", "RSASHA512"];
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

export type Tab = "records" | "metadata" | "dnssec" | "settings" | "transfer" | "dnsupdate" | "members" | "apikeys";

@Component({
  selector: "app-zone-detail",
  imports: [RouterLink, FormField, TranslateModule],
  templateUrl: "./zone-detail.component.html",
  styleUrl: "./zone-detail.component.css",
})
export class ZoneDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly pdns = inject(PdnsService);
  private readonly adminService = inject(AdminService);
  readonly auth = inject(AuthService);
  private readonly acmeKeysSvc = inject(AcmeKeysService);

  protected zoneId = "";

  // ── Role / permissions ────────────────────────────────────────────────────
  readonly currentRole = signal<ZoneRole | null>(null);
  readonly canWrite = computed(
    () => this.auth.isAdmin() || this.currentRole() === "manager" || this.currentRole() === "admin",
  );
  readonly isZoneAdmin = computed(() => this.auth.isAdmin() || this.currentRole() === "admin");

  // ── Members ───────────────────────────────────────────────────────────────
  readonly members = signal<ZoneMember[]>([]);
  readonly allUsers = signal<UserBasic[]>([]);
  readonly isLoadingMembers = signal(false);
  readonly membersError = signal<string | null>(null);
  readonly membersSuccess = signal<string | null>(null);
  readonly newMemberUserId = signal<number | null>(null);
  readonly newMemberRole = signal<ZoneRole>("viewer");
  readonly isSavingMember = signal(false);
  private membersLoaded = false;

  readonly zone = signal<ZoneDetail | null>(null);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly activeTab = signal<Tab>("records");

  // ── Records ──────────────────────────────────────────────────────────────
  readonly showRecordModal = signal(false);
  readonly isSubmittingRecord = signal(false);
  readonly recordError = signal<string | null>(null);
  readonly zoneRecordTypes = signal<string[]>([]);
  readonly dnsTypes = computed(() => (this.zoneRecordTypes().length > 0 ? this.zoneRecordTypes() : ALL_DNS_TYPES));
  private readonly recordNameInput = viewChild<ElementRef<HTMLInputElement>>("recordNameInput");

  readonly sortColumn = signal<"name" | "type" | "ttl">("name");
  readonly sortDirection = signal<"asc" | "desc">("asc");

  readonly recordsPageSize = 20;
  readonly recordsPage = signal(1);
  readonly recordsTotalPages = computed(() =>
    Math.max(1, Math.ceil((this.zone()?.rrsets.length ?? 0) / this.recordsPageSize)),
  );
  readonly sortedRRsets = computed(() => {
    const rrsets = [...(this.zone()?.rrsets ?? [])];
    const col = this.sortColumn();
    const dir = this.sortDirection() === "asc" ? 1 : -1;
    rrsets.sort((a, b) => String(a[col] ?? "").localeCompare(String(b[col] ?? "")) * dir);
    return rrsets;
  });
  readonly pagedRRsets = computed(() => {
    const rrsets = this.sortedRRsets();
    const start = (this.recordsPage() - 1) * this.recordsPageSize;
    return rrsets.slice(start, start + this.recordsPageSize);
  });

  // ── Edit RRset ────────────────────────────────────────────────────────────
  readonly showEditModal = signal(false);
  readonly editingRRset = signal<RRset | null>(null);
  readonly editTtl = signal(3600);
  readonly editRecords = signal<{ content: string; disabled: boolean }[]>([]);
  readonly editError = signal<string | null>(null);
  readonly isSubmittingEdit = signal(false);

  readonly recordModel = signal({
    name: "",
    type: "A",
    ttl: 3600,
    content: "",
  });
  readonly recordForm = form(this.recordModel, (s) => {
    required(s.name);
    required(s.content);
  });

  // ── Metadata ─────────────────────────────────────────────────────────────
  readonly metadata = signal<Metadata[]>([]);
  readonly isLoadingMeta = signal(false);
  readonly metaError = signal<string | null>(null);
  readonly showMetaModal = signal(false);
  readonly isSubmittingMeta = signal(false);
  readonly metaKindOptions = METADATA_KINDS;

  readonly metaModel = signal({ kind: "", value: "" });
  readonly metaForm = form(this.metaModel, (s) => {
    required(s.kind);
    required(s.value);
  });

  // ── DNSSEC / CryptoKeys ──────────────────────────────────────────────────
  readonly cryptoKeys = signal<CryptoKey[]>([]);
  readonly isLoadingKeys = signal(false);
  readonly keyError = signal<string | null>(null);
  readonly showKeyModal = signal(false);
  readonly isSubmittingKey = signal(false);
  readonly isRectifying = signal(false);
  readonly expandedKeyId = signal<number | null>(null);
  readonly copiedText = signal<string | null>(null);
  readonly cryptoAlgorithms = CRYPTO_ALGORITHMS;

  // bits: 0 = utiliser le défaut de l'algorithme
  readonly keyModel = signal({
    keytype: "ksk",
    algorithm: "ECDSAP256SHA256",
    bits: 0,
  });
  readonly keyForm = form(this.keyModel);

  // ── Transfer ──────────────────────────────────────────────────────────────
  readonly tsigKeys = signal<TsigKey[]>([]);
  readonly isSubmittingTransfer = signal(false);
  readonly transferError = signal<string | null>(null);
  readonly transferSuccess = signal<string | null>(null);
  private metadataLoaded = false;

  readonly newAllowAxfrFrom = signal("");
  readonly newAlsoNotify = signal("");
  readonly newTsigAllowAxfr = signal("");
  readonly newTsigAllowDnsupdate = signal("");
  readonly newAllowDnsupdateFrom = signal("");
  readonly editAxfrMasterTsig = signal("");
  readonly editAxfrSource = signal("");
  readonly editForwardDnsupdate = signal("");

  readonly allowAxfrFrom = computed(() => this.metadata().find((m) => m.kind === "ALLOW-AXFR-FROM")?.metadata ?? []);
  readonly alsoNotify = computed(() => this.metadata().find((m) => m.kind === "ALSO-NOTIFY")?.metadata ?? []);
  readonly tsigAllowAxfr = computed(() => this.metadata().find((m) => m.kind === "TSIG-ALLOW-AXFR")?.metadata ?? []);
  readonly tsigAllowDnsupdate = computed(
    () => this.metadata().find((m) => m.kind === "TSIG-ALLOW-DNSUPDATE")?.metadata ?? [],
  );
  readonly allowDnsupdateFrom = computed(
    () => this.metadata().find((m) => m.kind === "ALLOW-DNSUPDATE-FROM")?.metadata ?? [],
  );
  readonly axfrMasterTsig = computed(
    () => this.metadata().find((m) => m.kind === "AXFR-MASTER-TSIG")?.metadata?.[0] ?? "",
  );
  readonly axfrSource = computed(() => this.metadata().find((m) => m.kind === "AXFR-SOURCE")?.metadata?.[0] ?? "");
  readonly forwardDnsupdate = computed(
    () => this.metadata().find((m) => m.kind === "FORWARD-DNSUPDATE")?.metadata?.[0] ?? "",
  );
  readonly availableTsigForAxfr = computed(() => this.tsigKeys().filter((k) => !this.tsigAllowAxfr().includes(k.id)));
  readonly availableTsigForDnsupdate = computed(() =>
    this.tsigKeys().filter((k) => !this.tsigAllowDnsupdate().includes(k.id)),
  );

  // ── Zone actions ─────────────────────────────────────────────────────────
  readonly actionMessage = signal<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  readonly isNotifying = signal(false);
  readonly isRetrieving = signal(false);
  readonly isExporting = signal(false);
  readonly isImporting = signal(false);
  readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>("fileInput");

  // ── Settings ─────────────────────────────────────────────────────────────
  readonly isSavingSettings = signal(false);
  readonly settingsError = signal<string | null>(null);
  readonly settingsSuccess = signal(false);
  readonly settingsModel = signal({ kind: "Native", masters: "" });
  readonly settingsForm = form(this.settingsModel, (s) => {
    required(s.kind);
  });

  // ── Zone Record Types ─────────────────────────────────────────────────────
  readonly globalRecordTypes = signal<RecordType[]>([]);
  readonly zoneRecordTypesMeta = signal<ZoneRecordTypes | null>(null);
  readonly pendingZoneTypes = signal<Set<string>>(new Set());
  readonly isSavingZoneTypes = signal(false);
  readonly zoneTypesSuccess = signal(false);
  readonly zoneTypesError = signal<string | null>(null);

  readonly isReverseZone = computed(() => {
    const name = (this.zone()?.name ?? "").toLowerCase();
    return (
      name.endsWith(".in-addr.arpa.") || name === "in-addr.arpa." || name.endsWith(".ip6.arpa.") || name === "ip6.arpa."
    );
  });

  readonly availableGlobalTypes = computed(() =>
    this.globalRecordTypes().filter((rt) => {
      if (this.isReverseZone()) return rt.applicable_to === "reverse" || rt.applicable_to === "both";
      return rt.applicable_to === "direct" || rt.applicable_to === "both";
    }),
  );

  // ── API Keys ──────────────────────────────────────────────────────────────
  readonly zoneApiKeys = signal<AcmeApiKey[]>([]);
  readonly isLoadingApiKeys = signal(false);
  private apiKeysLoaded = false;

  // ── Reverse DNS ──────────────────────────────────────────────────────────
  readonly allZones = signal<Zone[]>([]);
  readonly isTogglingAutoReverse = signal(false);

  readonly autoReverseEnabled = computed(() =>
    this.metadata().some((m) => m.kind === "X-AUTO-REVERSE" && m.metadata[0] === "1"),
  );

  readonly reverseZoneForCurrentRecord = computed(() => {
    const { type, content } = this.recordModel();
    if (type !== "A" && type !== "AAAA") return null;
    if (!content.trim()) return null;
    return findBestReverseZone(content, this.allZones());
  });

  async ngOnInit(): Promise<void> {
    this.zoneId = this.route.snapshot.paramMap.get("id") ?? "";
    await Promise.all([this.loadZone(), this.loadAllZones(), this.loadZoneRole()]);
    void this.loadMetadata();
    void this.loadZoneRecordTypes();
    if (this.isZoneAdmin()) {
      void this.loadMembers();
      void this.loadZoneApiKeys();
    }
  }

  async loadZoneRole(): Promise<void> {
    try {
      const { role } = await this.pdns.getZoneRole(this.zoneId);
      this.currentRole.set(role);
    } catch {
      // non-blocking — falls back to null (no write access)
    }
  }

  async loadAllZones(): Promise<void> {
    try {
      this.allZones.set(await this.pdns.getZones());
    } catch {
      // non-blocking
    }
  }

  setTab(tab: Tab): void {
    this.activeTab.set(tab);
    if ((tab === "metadata" || tab === "transfer" || tab === "settings" || tab === "dnsupdate") && !this.metadataLoaded)
      void this.loadMetadata();
    if ((tab === "transfer" || tab === "dnsupdate") && this.metadataLoaded) this.initTransferForm();
    if (tab === "dnssec" && this.cryptoKeys().length === 0) void this.loadCryptoKeys();
    if ((tab === "transfer" || tab === "dnsupdate") && this.tsigKeys().length === 0) void this.loadTsigKeys();
    if (tab === "members" && !this.membersLoaded) void this.loadMembers();
    if (tab === "apikeys" && !this.apiKeysLoaded) void this.loadZoneApiKeys();
  }

  async loadZoneApiKeys(): Promise<void> {
    this.isLoadingApiKeys.set(true);
    try {
      const all = this.auth.isAdmin()
        ? await this.acmeKeysSvc.listAllKeys()
        : await this.acmeKeysSvc.listKeys();
      const zoneName = (this.zone()?.name ?? "").replace(/\.$/, "");
      this.zoneApiKeys.set(
        all.filter(
          (k) =>
            k.key_type === "api" ||
            k.zones.some((z) => z.replace(/\.$/, "") === zoneName),
        ),
      );
      this.apiKeysLoaded = true;
    } catch {
      // non-blocking
    } finally {
      this.isLoadingApiKeys.set(false);
    }
  }

  async loadZone(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const data = await this.pdns.getZone(this.zoneId);
      this.zone.set(data);
      this.recordsPage.set(1);
      this.settingsModel.set({
        kind: data.kind,
        masters: data.masters?.join(", ") ?? "",
      });
    } catch {
      this.error.set("Unable to load the area.");
    } finally {
      this.isLoading.set(false);
    }
  }

  // ── Records ──────────────────────────────────────────────────────────────

  openRecordModal(): void {
    this.recordModel.set({
      name: this.zone()?.name ?? "",
      type: "A",
      ttl: 3600,
      content: "",
    });
    this.recordError.set(null);
    this.showRecordModal.set(true);
    setTimeout(() => {
      const el = this.recordNameInput()?.nativeElement;
      if (el) {
        el.focus();
        el.setSelectionRange(0, 0);
      }
    });
  }

  closeRecordModal(): void {
    this.showRecordModal.set(false);
  }

  onAddRecord(): void {
    submit(this.recordForm, async () => {
      this.isSubmittingRecord.set(true);
      this.recordError.set(null);
      try {
        const { name, type, ttl, content } = this.recordModel();
        const normalizedName = name.endsWith(".") ? name : `${name}.`;
        const existingRRset = this.zone()?.rrsets.find((r) => r.name === normalizedName && r.type === type);
        const existingRecords = existingRRset?.records ?? [];
        await this.pdns.patchRRsets(this.zoneId, {
          rrsets: [
            {
              changetype: "REPLACE",
              name: normalizedName,
              type,
              ttl,
              records: [...existingRecords, { content, disabled: false }],
            },
          ],
        });

        if (this.autoReverseEnabled() && (type === "A" || type === "AAAA")) {
          await this.tryCreatePtrRecord(content, normalizedName, ttl);
        }

        this.showRecordModal.set(false);
        await this.loadZone();
      } catch {
        this.recordError.set("Error occurred while adding the record.");
      } finally {
        this.isSubmittingRecord.set(false);
      }
    });
  }

  private async tryCreatePtrRecord(ip: string, hostname: string, ttl: number): Promise<void> {
    const reverseZone = findBestReverseZone(ip, this.allZones());
    if (!reverseZone) return;
    const ptrName = buildPtrName(ip);
    try {
      await this.pdns.patchRRsets(reverseZone.id, {
        rrsets: [
          {
            changetype: "REPLACE",
            name: ptrName,
            type: "PTR",
            ttl,
            records: [{ content: hostname, disabled: false }],
          },
        ],
      });
    } catch {
      this.actionMessage.set({
        type: "error",
        text: `PTR not created in ${reverseZone.name} — check permissions for this zone.`,
      });
    }
  }

  async deleteRRset(rrset: RRset): Promise<void> {
    if (!confirm(`Supprimer l'enregistrement "${rrset.name}" (${rrset.type}) ?`)) return;
    try {
      await this.pdns.patchRRsets(this.zoneId, {
        rrsets: [{ changetype: "DELETE", name: rrset.name, type: rrset.type }],
      });
      await this.loadZone();
    } catch {
      this.error.set("Unable to delete the record.");
    }
  }

  openEditModal(rrset: RRset): void {
    this.editingRRset.set(rrset);
    this.editTtl.set(rrset.ttl);
    this.editRecords.set(rrset.records.map((r) => ({ ...r })));
    this.editError.set(null);
    this.showEditModal.set(true);
  }

  closeEditModal(): void {
    this.showEditModal.set(false);
  }

  updateEditRecord(index: number, content: string): void {
    this.editRecords.update((records) => records.map((r, i) => (i === index ? { ...r, content } : r)));
  }

  toggleEditRecordDisabled(index: number): void {
    this.editRecords.update((records) => records.map((r, i) => (i === index ? { ...r, disabled: !r.disabled } : r)));
  }

  removeEditRecord(index: number): void {
    this.editRecords.update((records) => records.filter((_, i) => i !== index));
  }

  addEditRecord(): void {
    this.editRecords.update((records) => [...records, { content: "", disabled: false }]);
  }

  async onSaveEdit(): Promise<void> {
    const rrset = this.editingRRset();
    if (!rrset) return;
    if (this.editRecords().length === 0) {
      this.editError.set("At least one record is required.");
      return;
    }
    this.isSubmittingEdit.set(true);
    this.editError.set(null);
    try {
      await this.pdns.patchRRsets(this.zoneId, {
        rrsets: [
          {
            changetype: "REPLACE",
            name: rrset.name,
            type: rrset.type,
            ttl: this.editTtl(),
            records: this.editRecords(),
          },
        ],
      });
      this.showEditModal.set(false);
      await this.loadZone();
    } catch {
      this.editError.set("Error occurred while modifying the record.");
    } finally {
      this.isSubmittingEdit.set(false);
    }
  }

  sortBy(col: "name" | "type" | "ttl"): void {
    if (this.sortColumn() === col) {
      this.sortDirection.set(this.sortDirection() === "asc" ? "desc" : "asc");
    } else {
      this.sortColumn.set(col);
      this.sortDirection.set("asc");
    }
    this.recordsPage.set(1);
  }

  async toggleRecordDisabled(rrset: RRset, recIndex: number): Promise<void> {
    const records = rrset.records.map((r, i) => (i === recIndex ? { ...r, disabled: !r.disabled } : r));
    try {
      await this.pdns.patchRRsets(this.zoneId, {
        rrsets: [
          {
            changetype: "REPLACE",
            name: rrset.name,
            type: rrset.type,
            ttl: rrset.ttl,
            records,
          },
        ],
      });
      await this.loadZone();
    } catch {
      this.error.set("Unable to modify the record's status.");
    }
  }

  // ── Metadata ─────────────────────────────────────────────────────────────

  async loadMetadata(): Promise<void> {
    this.isLoadingMeta.set(true);
    this.metaError.set(null);
    try {
      this.metadata.set(await this.pdns.getMetadata(this.zoneId));
      this.metadataLoaded = true;
      if (this.activeTab() === "transfer" || this.activeTab() === "dnsupdate") this.initTransferForm();
    } catch {
      this.metaError.set("Unable to load metadata.");
    } finally {
      this.isLoadingMeta.set(false);
    }
  }

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
        await this.pdns.setMetadata(this.zoneId, kind, [value]);
        this.showMetaModal.set(false);
        await this.loadMetadata();
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
      await this.pdns.deleteMetadata(this.zoneId, kind);
      await this.loadMetadata();
    } catch {
      this.metaError.set(`Unable to delete the metadata "${kind}".`);
    }
  }

  // ── Transfer ──────────────────────────────────────────────────────────────

  private initTransferForm(): void {
    this.editAxfrMasterTsig.set(this.axfrMasterTsig());
    this.editAxfrSource.set(this.axfrSource());
    this.editForwardDnsupdate.set(this.forwardDnsupdate());
  }

  async loadTsigKeys(): Promise<void> {
    try {
      this.tsigKeys.set(await this.pdns.getTsigKeys());
    } catch {
      // non-blocking
    }
  }

  private async addMetadataEntry(kind: string, value: string): Promise<void> {
    const v = value.trim();
    if (!v) return;
    this.isSubmittingTransfer.set(true);
    this.transferError.set(null);
    try {
      const current = this.metadata().find((m) => m.kind === kind)?.metadata ?? [];
      if (!current.includes(v)) {
        await this.pdns.setMetadata(this.zoneId, kind, [...current, v]);
      }
      await this.loadMetadata();
      this.flashTransferSuccess();
    } catch {
      this.transferError.set(`Error occurred while updating ${kind}.`);
    } finally {
      this.isSubmittingTransfer.set(false);
    }
  }

  async removeMetadataEntry(kind: string, value: string): Promise<void> {
    this.isSubmittingTransfer.set(true);
    this.transferError.set(null);
    try {
      const current = this.metadata().find((m) => m.kind === kind)?.metadata ?? [];
      const updated = current.filter((v) => v !== value);
      if (updated.length === 0) {
        await this.pdns.deleteMetadata(this.zoneId, kind);
      } else {
        await this.pdns.setMetadata(this.zoneId, kind, updated);
      }
      await this.loadMetadata();
    } catch {
      this.transferError.set(`Error occurred while removing from ${kind}.`);
    } finally {
      this.isSubmittingTransfer.set(false);
    }
  }

  async saveSingleMetadata(kind: string, value: string): Promise<void> {
    this.isSubmittingTransfer.set(true);
    this.transferError.set(null);
    try {
      if (!value.trim()) {
        await this.pdns.deleteMetadata(this.zoneId, kind);
      } else {
        await this.pdns.setMetadata(this.zoneId, kind, [value.trim()]);
      }
      await this.loadMetadata();
      this.flashTransferSuccess();
    } catch {
      this.transferError.set(`Error occurred while updating ${kind}.`);
    } finally {
      this.isSubmittingTransfer.set(false);
    }
  }

  async addAllowAxfrFromEntry(): Promise<void> {
    await this.addMetadataEntry("ALLOW-AXFR-FROM", this.newAllowAxfrFrom());
    this.newAllowAxfrFrom.set("");
  }

  async addAlsoNotifyEntry(): Promise<void> {
    await this.addMetadataEntry("ALSO-NOTIFY", this.newAlsoNotify());
    this.newAlsoNotify.set("");
  }

  async addTsigAllowAxfrEntry(): Promise<void> {
    await this.addMetadataEntry("TSIG-ALLOW-AXFR", this.newTsigAllowAxfr());
    this.newTsigAllowAxfr.set("");
  }

  async addTsigAllowDnsupdateEntry(): Promise<void> {
    await this.addMetadataEntry("TSIG-ALLOW-DNSUPDATE", this.newTsigAllowDnsupdate());
    this.newTsigAllowDnsupdate.set("");
  }

  async addAllowDnsupdateFromEntry(): Promise<void> {
    await this.addMetadataEntry("ALLOW-DNSUPDATE-FROM", this.newAllowDnsupdateFrom());
    this.newAllowDnsupdateFrom.set("");
  }

  getTsigKeyById(id: string): TsigKey | undefined {
    return this.tsigKeys().find((k) => k.id === id);
  }

  private flashTransferSuccess(): void {
    this.transferSuccess.set("Successfully updated.");
    setTimeout(() => this.transferSuccess.set(null), 3000);
  }

  // ── DNSSEC / CryptoKeys ──────────────────────────────────────────────────

  async loadCryptoKeys(): Promise<void> {
    this.isLoadingKeys.set(true);
    this.keyError.set(null);
    try {
      this.cryptoKeys.set(await this.pdns.getCryptoKeys(this.zoneId));
    } catch {
      this.keyError.set("Unable to load cryptographic keys.");
    } finally {
      this.isLoadingKeys.set(false);
    }
  }

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
        await this.pdns.createCryptoKey(this.zoneId, payload);
        this.showKeyModal.set(false);
        await this.loadCryptoKeys();
        await this.loadZone();
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
      await this.pdns.rectifyZone(this.zoneId);
      this.actionMessage.set({
        type: "success",
        text: "Zone rectified successfully.",
      });
    } catch {
      this.actionMessage.set({
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
      await this.pdns.updateCryptoKey(this.zoneId, key.id, {
        active: !key.active,
      });
      await this.loadCryptoKeys();
    } catch {
      this.keyError.set("Unable to modify the key state.");
    }
  }

  async togglePublished(key: CryptoKey): Promise<void> {
    try {
      await this.pdns.updateCryptoKey(this.zoneId, key.id, {
        published: !key.published,
      });
      await this.loadCryptoKeys();
    } catch {
      this.keyError.set("Unable to modify the publication state of the key.");
    }
  }

  async deleteKey(key: CryptoKey): Promise<void> {
    if (!confirm(`Supprimer la clé DNSSEC #${key.id} (${key.keytype}) ?`)) return;
    try {
      await this.pdns.deleteCryptoKey(this.zoneId, key.id);
      await this.loadCryptoKeys();
      await this.loadZone();
    } catch {
      this.keyError.set("Unable to delete the key.");
    }
  }

  // ── Settings ─────────────────────────────────────────────────────────────

  async loadZoneRecordTypes(): Promise<void> {
    try {
      const [meta, globalTypes] = await Promise.all([
        this.pdns.getZoneRecordTypes(this.zoneId),
        this.adminService.listRecordTypes(),
      ]);
      this.zoneRecordTypesMeta.set(meta);
      this.globalRecordTypes.set(globalTypes);
      this.pendingZoneTypes.set(new Set(meta.types));
      this.zoneRecordTypes.set(meta.types);
    } catch {
      // non-blocking
    }
  }

  toggleZoneType(name: string): void {
    this.pendingZoneTypes.update((s) => {
      const next = new Set(s);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async saveZoneRecordTypes(): Promise<void> {
    this.isSavingZoneTypes.set(true);
    this.zoneTypesError.set(null);
    this.zoneTypesSuccess.set(false);
    try {
      const result = await this.pdns.setZoneRecordTypes(this.zoneId, Array.from(this.pendingZoneTypes()));
      this.zoneRecordTypesMeta.set(result);
      this.zoneRecordTypes.set(result.types);
      this.pendingZoneTypes.set(new Set(result.types));
      this.zoneTypesSuccess.set(true);
      setTimeout(() => this.zoneTypesSuccess.set(false), 3000);
    } catch {
      this.zoneTypesError.set("Error occurred while saving the types.");
    } finally {
      this.isSavingZoneTypes.set(false);
    }
  }

  async resetZoneRecordTypes(): Promise<void> {
    this.isSavingZoneTypes.set(true);
    this.zoneTypesError.set(null);
    this.zoneTypesSuccess.set(false);
    try {
      const result = await this.pdns.setZoneRecordTypes(this.zoneId, []);
      this.zoneRecordTypesMeta.set(result);
      this.pendingZoneTypes.set(new Set(result.types));
      this.zoneRecordTypes.set(result.types);
      this.zoneTypesSuccess.set(true);
      setTimeout(() => this.zoneTypesSuccess.set(false), 3000);
    } catch {
      this.zoneTypesError.set("Error occurred while resetting the types.");
    } finally {
      this.isSavingZoneTypes.set(false);
    }
  }

  onSaveSettings(): void {
    submit(this.settingsForm, async () => {
      const zone = this.zone();
      if (!zone) return;
      this.isSavingSettings.set(true);
      this.settingsError.set(null);
      this.settingsSuccess.set(false);
      try {
        const { kind, masters } = this.settingsModel();
        const mastersList = masters
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        await this.pdns.updateZone(this.zoneId, {
          name: zone.name,
          kind,
          masters: mastersList,
        });
        this.settingsSuccess.set(true);
        await this.loadZone();
      } catch {
        this.settingsError.set("Error occurred while saving the settings.");
      } finally {
        this.isSavingSettings.set(false);
      }
    });
  }

  async toggleAutoReverse(): Promise<void> {
    this.isTogglingAutoReverse.set(true);
    this.settingsError.set(null);
    try {
      if (this.autoReverseEnabled()) {
        await this.pdns.deleteMetadata(this.zoneId, "X-AUTO-REVERSE");
      } else {
        await this.pdns.setMetadata(this.zoneId, "X-AUTO-REVERSE", ["1"]);
      }
      await this.loadMetadata();
    } catch {
      this.settingsError.set("Error occurred while updating the automatic PTR parameter.");
    } finally {
      this.isTogglingAutoReverse.set(false);
    }
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
      await this.loadZone();
    } catch {
      this.actionMessage.set({ type: "error", text: "Error occurred while importing the zone." });
    } finally {
      this.isImporting.set(false);
    }
  }

  // ── Members ──────────────────────────────────────────────────────────────

  async loadMembers(): Promise<void> {
    this.isLoadingMembers.set(true);
    this.membersError.set(null);
    try {
      const [members, users] = await Promise.all([this.pdns.getZoneMembers(this.zoneId), this.pdns.getUsers()]);
      this.members.set(members);
      this.allUsers.set(users);
      this.membersLoaded = true;
    } catch {
      this.membersError.set("Error occurred while loading the members.");
    } finally {
      this.isLoadingMembers.set(false);
    }
  }

  availableUsersToAdd(): UserBasic[] {
    const memberIds = new Set(this.members().map((m) => m.user_id));
    return this.allUsers().filter((u) => !memberIds.has(u.id));
  }

  async addMember(): Promise<void> {
    const userId = this.newMemberUserId();
    if (!userId) return;
    this.isSavingMember.set(true);
    this.membersError.set(null);
    try {
      const member = await this.pdns.addZoneMember(this.zoneId, userId, this.newMemberRole());
      this.members.update((list) => [...list, member]);
      this.newMemberUserId.set(null);
      this.newMemberRole.set("viewer");
      this.flashMembersSuccess("Member added.");
    } catch {
      this.membersError.set("Error occurred while adding the member.");
    } finally {
      this.isSavingMember.set(false);
    }
  }

  async updateMemberRole(member: ZoneMember, role: ZoneRole): Promise<void> {
    try {
      const updated = await this.pdns.updateZoneMember(this.zoneId, member.user_id, role);
      this.members.update((list) => list.map((m) => (m.user_id === member.user_id ? updated : m)));
      this.flashMembersSuccess("Role updated.");
    } catch {
      this.membersError.set("Error occurred while updating the role.");
    }
  }

  async removeMember(member: ZoneMember): Promise<void> {
    if (!confirm(`Remove ${member.username} from this zone ?`)) return;
    try {
      await this.pdns.removeZoneMember(this.zoneId, member.user_id);
      this.members.update((list) => list.filter((m) => m.user_id !== member.user_id));
      this.flashMembersSuccess("Member removed.");
    } catch {
      this.membersError.set("Error occurred while removing the member.");
    }
  }

  private flashMembersSuccess(msg: string): void {
    this.membersSuccess.set(msg);
    setTimeout(() => this.membersSuccess.set(null), 3000);
  }

  // ── Pagination ────────────────────────────────────────────────────────────

  goToPage(page: number): void {
    const p = Math.max(1, Math.min(page, this.recordsTotalPages()));
    this.recordsPage.set(p);
  }

  pageRange(): number[] {
    const total = this.recordsTotalPages();
    const current = this.recordsPage();
    const delta = 2;
    const range: number[] = [];
    for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
      range.push(i);
    }
    return range;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  trackByRRset(_: number, rrset: RRset): string {
    return `${rrset.name}-${rrset.type}`;
  }

  trackByMeta(_: number, meta: Metadata): string {
    return meta.kind;
  }

  trackByKey(_: number, key: CryptoKey): number {
    return key.id;
  }
}

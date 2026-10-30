import { Component, computed, ElementRef, inject, linkedSignal, signal, viewChild } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { TranslatePipe } from "@ngx-translate/core";
import { PdnsService } from "../../../../core/services/pdns.service";
import { RRset } from "../../../../shared/models/pdns.model";
import { buildPtrName, findBestReverseZone } from "../../../../shared/utils/dns-reverse.utils";
import { ZoneDetailStore } from "../zone-detail.store";

const ALL_DNS_TYPES = ["A", "AAAA", "CAA", "CNAME", "DNAME", "LOC", "MX", "NS", "PTR", "SOA", "SPF", "SRV", "TXT"];

/** Records tab: list, add, edit and delete the RRsets of the zone. */
@Component({
  selector: "app-zone-records",
  imports: [FormField, TranslatePipe],
  templateUrl: "./zone-records.component.html",
  styleUrl: "./zone-records.component.css",
  host: { class: "d-block" },
})
export class ZoneRecordsComponent {
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  readonly zone = this.store.zone;
  readonly error = this.store.error;
  readonly canWrite = this.store.canWrite;
  readonly autoReverseEnabled = this.store.autoReverseEnabled;
  readonly dnsTypes = computed(() =>
    this.store.zoneRecordTypes().length > 0 ? this.store.zoneRecordTypes() : ALL_DNS_TYPES,
  );

  // ── Add record ────────────────────────────────────────────────────────────
  readonly showRecordModal = signal(false);
  readonly isSubmittingRecord = signal(false);
  readonly recordError = signal<string | null>(null);
  private readonly recordNameInput = viewChild<ElementRef<HTMLInputElement>>("recordNameInput");

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

  readonly reverseZoneForCurrentRecord = computed(() => {
    const { type, content } = this.recordModel();
    if (type !== "A" && type !== "AAAA") return null;
    if (!content.trim()) return null;
    return findBestReverseZone(content, this.store.allZones());
  });

  // ── Sorting and pagination ────────────────────────────────────────────────
  readonly sortColumn = signal<"name" | "type" | "ttl">("name");
  readonly sortDirection = signal<"asc" | "desc">("asc");

  readonly recordsPageSize = 20;
  // Back to the first page whenever the zone is reloaded.
  readonly recordsPage = linkedSignal({ source: this.zone, computation: () => 1 });
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
        await this.pdns.patchRRsets(this.store.zoneId, {
          rrsets: [
            {
              changetype: "EXTEND",
              name: normalizedName,
              type,
              ttl,
              records: [{ content, disabled: false }],
            },
          ],
        });

        if (this.autoReverseEnabled() && (type === "A" || type === "AAAA")) {
          await this.tryCreatePtrRecord(content, normalizedName, ttl);
        }

        this.showRecordModal.set(false);
        await this.store.loadZone();
      } catch {
        this.recordError.set("Error occurred while adding the record.");
      } finally {
        this.isSubmittingRecord.set(false);
      }
    });
  }

  private async tryCreatePtrRecord(ip: string, hostname: string, ttl: number): Promise<void> {
    const reverseZone = findBestReverseZone(ip, this.store.allZones());
    if (!reverseZone) return;
    const ptrName = buildPtrName(ip);
    try {
      await this.pdns.patchRRsets(reverseZone.id, {
        rrsets: [
          {
            changetype: "EXTEND",
            name: ptrName,
            type: "PTR",
            ttl,
            records: [{ content: hostname, disabled: false }],
          },
        ],
      });
    } catch {
      this.store.actionMessage.set({
        type: "error",
        text: `PTR not created in ${reverseZone.name} — check permissions for this zone.`,
      });
    }
  }

  async pruneRecordValue(rrset: RRset, record: { content: string; disabled: boolean }): Promise<void> {
    if (!confirm(`Supprimer la valeur "${record.content}" de "${rrset.name}" (${rrset.type}) ?`)) return;
    try {
      await this.pdns.patchRRsets(this.store.zoneId, {
        rrsets: [
          {
            changetype: "PRUNE",
            name: rrset.name,
            type: rrset.type,
            ttl: rrset.ttl,
            records: [record],
          },
        ],
      });
      await this.store.loadZone();
    } catch {
      this.error.set("Unable to delete this value.");
    }
  }

  async deleteRRset(rrset: RRset): Promise<void> {
    if (!confirm(`Supprimer l'enregistrement "${rrset.name}" (${rrset.type}) ?`)) return;
    try {
      await this.pdns.patchRRsets(this.store.zoneId, {
        rrsets: [{ changetype: "DELETE", name: rrset.name, type: rrset.type }],
      });
      await this.store.loadZone();
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
      await this.pdns.patchRRsets(this.store.zoneId, {
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
      await this.store.loadZone();
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
      await this.pdns.patchRRsets(this.store.zoneId, {
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
      await this.store.loadZone();
    } catch {
      this.error.set("Unable to modify the record's status.");
    }
  }

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

  trackByRRset(_: number, rrset: RRset): string {
    return `${rrset.name}-${rrset.type}`;
  }
}

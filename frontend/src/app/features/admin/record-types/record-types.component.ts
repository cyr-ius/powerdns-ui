import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { AdminService } from "../../../core/services/admin.service";
import { RecordType } from "../../../shared/models/admin.model";

@Component({
  selector: "app-admin-record-types",
  imports: [FormField],
  templateUrl: "./record-types.component.html",
})
export class AdminRecordTypesComponent implements OnInit {
  private readonly adminService = inject(AdminService);

  readonly recordTypes = signal<RecordType[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);
  readonly createModel = signal({ name: "", applicable_to: "both" as "direct" | "reverse" | "both", enabled: true });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "Nom requis" });
  });

  readonly deleteTarget = signal<RecordType | null>(null);
  readonly isDeleting = signal(false);

  readonly applicableOptions = [
    { value: "direct", label: "Direct zone only" },
    { value: "reverse", label: "Reverse zone only" },
    { value: "both", label: "Both" },
  ];

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.recordTypes.set(await this.adminService.listRecordTypes());
    } catch {
      this.error.set("Impossible to load record types.");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreate(): void {
    this.createModel.set({ name: "", applicable_to: "both", enabled: true });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  onCreateSubmit(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, applicable_to, enabled } = this.createModel();
        await this.adminService.createRecordType({ name, applicable_to, enabled });
        this.showCreateModal.set(false);
        await this.load();
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.createError.set(detail ?? "Error occurred while creating the record type");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async toggleEnabled(rt: RecordType): Promise<void> {
    try {
      await this.adminService.updateRecordType(rt.id, { enabled: !rt.enabled });
      await this.load();
    } catch {
      this.error.set("Error occurred while updating.");
    }
  }

  async updateApplicableTo(rt: RecordType, value: string): Promise<void> {
    try {
      await this.adminService.updateRecordType(rt.id, { applicable_to: value });
      await this.load();
    } catch {
      this.error.set("Error occurred while updating.");
    }
  }

  confirmDelete(rt: RecordType): void {
    this.deleteTarget.set(rt);
  }

  async doDelete(): Promise<void> {
    const rt = this.deleteTarget();
    if (!rt) return;
    this.isDeleting.set(true);
    try {
      await this.adminService.deleteRecordType(rt.id);
      this.deleteTarget.set(null);
      await this.load();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: string } })?.error?.detail;
      this.error.set(detail ?? "Error occurred while deleting the record type");
      this.deleteTarget.set(null);
    } finally {
      this.isDeleting.set(false);
    }
  }

  applicableLabel(value: string): string {
    return this.applicableOptions.find((o) => o.value === value)?.label ?? value;
  }
}

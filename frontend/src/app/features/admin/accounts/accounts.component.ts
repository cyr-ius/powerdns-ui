import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { AdminService } from "../../../core/services/admin.service";
import { PdnsService } from "../../../core/services/pdns.service";
import { Account, AdminUser } from "../../../shared/models/admin.model";
import { Zone } from "../../../shared/models/pdns.model";
import { TranslatePipe } from "@ngx-translate/core";

@Component({
  selector: "app-admin-accounts",
  imports: [FormField, TranslatePipe],
  templateUrl: "./accounts.component.html",
  styleUrl: "./accounts.component.css",
})
export class AdminAccountsComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly pdns = inject(PdnsService);

  readonly accounts = signal<Account[]>([]);
  readonly allUsers = signal<AdminUser[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  // Create modal
  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);
  readonly createModel = signal({ name: "", description: "" });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "Nom requis" });
  });

  // Assign users modal
  readonly showAssignModal = signal(false);
  readonly assignTarget = signal<Account | null>(null);
  readonly selectedUserIds = signal<Set<number>>(new Set());
  readonly isSavingAssign = signal(false);

  // Assign zones modal
  readonly showZonesModal = signal(false);
  readonly zonesTarget = signal<Account | null>(null);
  readonly allZones = signal<Zone[]>([]);
  readonly originalZoneNames = signal<Set<string>>(new Set());
  readonly selectedZoneNames = signal<Set<string>>(new Set());
  readonly isLoadingZones = signal(false);
  readonly isSavingZones = signal(false);
  readonly zonesError = signal<string | null>(null);

  // Delete confirm
  readonly deleteTarget = signal<Account | null>(null);
  readonly isDeleting = signal(false);

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const [accounts, users] = await Promise.all([this.adminService.listAccounts(), this.adminService.listUsers()]);
      this.accounts.set(accounts);
      this.allUsers.set(users);
    } catch {
      this.error.set("Unable to load data.");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreate(): void {
    this.createModel.set({ name: "", description: "" });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  onCreateSubmit(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { name, description } = this.createModel();
        await this.adminService.createAccount({ name, description: description || null });
        this.showCreateModal.set(false);
        await this.load();
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.createError.set(detail ?? "Error occurred while creating the account");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  openAssign(account: Account): void {
    this.assignTarget.set(account);
    const accountName = account.name;
    const current = new Set(
      this.allUsers()
        .filter((u) => u.accounts.includes(accountName))
        .map((u) => u.id),
    );
    this.selectedUserIds.set(current);
    this.showAssignModal.set(true);
  }

  toggleUser(userId: number): void {
    this.selectedUserIds.update((set) => {
      const next = new Set(set);
      next.has(userId) ? next.delete(userId) : next.add(userId);
      return next;
    });
  }

  isSelected(userId: number): boolean {
    return this.selectedUserIds().has(userId);
  }

  async saveAssign(): Promise<void> {
    const account = this.assignTarget();
    if (!account) return;
    this.isSavingAssign.set(true);
    try {
      await this.adminService.setAccountUsers(account.id, Array.from(this.selectedUserIds()));
      this.showAssignModal.set(false);
      await this.load();
    } catch {
      this.error.set("Error occurred while assigning users to the account.");
      this.showAssignModal.set(false);
    } finally {
      this.isSavingAssign.set(false);
    }
  }

  async openZones(account: Account): Promise<void> {
    this.zonesTarget.set(account);
    this.zonesError.set(null);
    this.isLoadingZones.set(true);
    this.showZonesModal.set(true);
    try {
      const zones = await this.pdns.getZones();
      this.allZones.set(zones);
      const current = new Set(
        zones.filter((z) => z.account === account.name).map((z) => z.name),
      );
      this.originalZoneNames.set(current);
      this.selectedZoneNames.set(new Set(current));
    } catch {
      this.zonesError.set("Unable to load zones.");
    } finally {
      this.isLoadingZones.set(false);
    }
  }

  toggleZone(zoneName: string): void {
    this.selectedZoneNames.update((set) => {
      const next = new Set(set);
      next.has(zoneName) ? next.delete(zoneName) : next.add(zoneName);
      return next;
    });
  }

  async saveZones(): Promise<void> {
    const account = this.zonesTarget();
    if (!account) return;
    this.isSavingZones.set(true);
    this.zonesError.set(null);
    try {
      const original = this.originalZoneNames();
      const selected = this.selectedZoneNames();
      const toAdd = [...selected].filter((n) => !original.has(n));
      const toRemove = [...original].filter((n) => !selected.has(n));
      const zoneMap = new Map(this.allZones().map((z) => [z.name, z]));
      await Promise.all([
        ...toAdd.map((name) => {
          const z = zoneMap.get(name)!;
          return this.pdns.updateZone(name, { name: z.name, kind: z.kind, account: account.name });
        }),
        ...toRemove.map((name) => {
          const z = zoneMap.get(name)!;
          // Detach with an empty string, not null: the backend drops null
          // fields (exclude_none), so null would never reach PowerDNS.
          return this.pdns.updateZone(name, { name: z.name, kind: z.kind, account: "" });
        }),
      ]);
      this.showZonesModal.set(false);
      await this.load();
    } catch {
      this.zonesError.set("Error occurred while saving zones.");
    } finally {
      this.isSavingZones.set(false);
    }
  }

  confirmDelete(account: Account): void {
    this.deleteTarget.set(account);
  }

  async doDelete(): Promise<void> {
    const account = this.deleteTarget();
    if (!account) return;
    this.isDeleting.set(true);
    try {
      await this.adminService.deleteAccount(account.id);
      this.deleteTarget.set(null);
      await this.load();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: string } })?.error?.detail;
      this.error.set(detail ?? "Error occurred while deleting the account");
      this.deleteTarget.set(null);
    } finally {
      this.isDeleting.set(false);
    }
  }
}

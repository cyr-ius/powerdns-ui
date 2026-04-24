import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { AdminService } from "../../../core/services/admin.service";
import { Account, AdminUser } from "../../../shared/models/admin.model";

@Component({
  selector: "app-admin-accounts",
  imports: [FormField],
  templateUrl: "./accounts.component.html",
  styleUrl: "./accounts.component.css",
})
export class AdminAccountsComponent implements OnInit {
  private readonly adminService = inject(AdminService);

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
    // Preselect users already in this account
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
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
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

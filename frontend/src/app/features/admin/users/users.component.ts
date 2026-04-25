import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { AdminService } from "../../../core/services/admin.service";
import { AdminUser } from "../../../shared/models/admin.model";
import { TranslateModule } from "@ngx-translate/core";

@Component({
  selector: "app-admin-users",
  imports: [FormField, TranslateModule],
  templateUrl: "./users.component.html",
  styleUrl: "./users.component.css",
})
export class AdminUsersComponent implements OnInit {
  private readonly adminService = inject(AdminService);

  readonly users = signal<AdminUser[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  // Create user modal
  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);
  readonly createModel = signal({ username: "", password: "", email: "", is_admin: false });
  readonly createForm = form(this.createModel, (s) => {
    required(s.username, { message: "The username is required" });
    required(s.password, { message: "The password is required" });
  });

  // Reset password modal
  readonly showResetModal = signal(false);
  readonly resetTarget = signal<AdminUser | null>(null);
  readonly isResetting = signal(false);
  readonly resetError = signal<string | null>(null);
  readonly resetModel = signal({ password: "", confirm: "" });
  readonly resetForm = form(this.resetModel, (s) => {
    required(s.password, { message: "The new password is required" });
    required(s.confirm, { message: "The confirmation is required" });
  });

  // Delete confirm
  readonly deleteTarget = signal<AdminUser | null>(null);
  readonly isDeleting = signal(false);

  readonly authBadge = (u: AdminUser) => (u.is_oidc ? "SSO" : "Local");
  readonly authBadgeClass = (u: AdminUser) => (u.is_oidc ? "bg-info" : "bg-secondary");

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.users.set(await this.adminService.listUsers());
    } catch {
      this.error.set("Impossible to load users.");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreate(): void {
    this.createModel.set({ username: "", password: "", email: "", is_admin: false });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  onCreateSubmit(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { username, password, email, is_admin } = this.createModel();
        await this.adminService.createUser({ username, password, email: email || null, is_admin });
        this.showCreateModal.set(false);
        await this.load();
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.createError.set(detail ?? "Error occurred while creating the user");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async toggleActive(user: AdminUser): Promise<void> {
    try {
      const updated = await this.adminService.updateUser(user.id, { is_active: !user.is_active });
      this.users.update((list) => list.map((u) => (u.id === updated.id ? updated : u)));
    } catch {
      this.error.set("Impossible to modify the status.");
    }
  }

  async toggleAdmin(user: AdminUser): Promise<void> {
    try {
      const updated = await this.adminService.updateUser(user.id, { is_admin: !user.is_admin });
      this.users.update((list) => list.map((u) => (u.id === updated.id ? updated : u)));
    } catch {
      this.error.set("Impossible to modify the role.");
    }
  }

  openReset(user: AdminUser): void {
    this.resetTarget.set(user);
    this.resetModel.set({ password: "", confirm: "" });
    this.resetError.set(null);
    this.showResetModal.set(true);
  }

  onResetSubmit(): void {
    submit(this.resetForm, async () => {
      const { password, confirm } = this.resetModel();
      if (password !== confirm) {
        this.resetError.set("The passwords do not match");
        return;
      }
      this.isResetting.set(true);
      this.resetError.set(null);
      try {
        await this.adminService.resetPassword(this.resetTarget()!.id, password);
        this.showResetModal.set(false);
      } catch (err: unknown) {
        const detail = (err as { error?: { detail?: string } })?.error?.detail;
        this.resetError.set(detail ?? "Error occurred while resetting the password");
      } finally {
        this.isResetting.set(false);
      }
    });
  }

  confirmDelete(user: AdminUser): void {
    this.deleteTarget.set(user);
  }

  async doDelete(): Promise<void> {
    const user = this.deleteTarget();
    if (!user) return;
    this.isDeleting.set(true);
    try {
      await this.adminService.deleteUser(user.id);
      this.deleteTarget.set(null);
      await this.load();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: string } })?.error?.detail;
      this.error.set(detail ?? "Error occurred while deleting the user");
      this.deleteTarget.set(null);
    } finally {
      this.isDeleting.set(false);
    }
  }
}

import { DatePipe } from "@angular/common";
import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { TranslatePipe } from "@ngx-translate/core";
import { AdminService } from "../../core/services/admin.service";
import { AcmeApiKey, AcmeKeysService } from "../../core/services/acme-keys.service";
import { AdminUser } from "../../shared/models/admin.model";

@Component({
  selector: "app-acme-keys",
  imports: [DatePipe, TranslatePipe, FormsModule],
  templateUrl: "./acme-keys.component.html",
  styleUrl: "./acme-keys.component.css",
})
export class AcmeKeysComponent implements OnInit {
  private readonly acmeKeys = inject(AcmeKeysService);
  private readonly adminService = inject(AdminService);

  readonly keys = signal<AcmeApiKey[]>([]);
  readonly allUsers = signal<AdminUser[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly hasOrphans = computed(() => this.keys().some((k) => !k.username));

  // Reassign owner modal
  readonly reassignTarget = signal<AcmeApiKey | null>(null);
  readonly reassignUserId = signal<number | null>(null);
  readonly isReassigning = signal(false);
  readonly reassignError = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    await this.loadKeys();
  }

  async loadKeys(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const [keys, users] = await Promise.all([this.acmeKeys.listAllKeys(), this.adminService.listUsers()]);
      this.keys.set(keys);
      this.allUsers.set(users);
    } catch {
      this.error.set("APIKEYS.LOAD_ERROR");
    } finally {
      this.isLoading.set(false);
    }
  }

  async deleteKey(key: AcmeApiKey): Promise<void> {
    if (!confirm(`Supprimer la clé "${key.name}" (${key.username}) ?`)) return;
    try {
      await this.acmeKeys.deleteKey(key.id);
      this.keys.update((list) => list.filter((k) => k.id !== key.id));
    } catch {
      this.error.set("APIKEYS.DELETE_ERROR");
    }
  }

  openReassign(key: AcmeApiKey): void {
    this.reassignTarget.set(key);
    this.reassignUserId.set(key.user_id ?? null);
    this.reassignError.set(null);
  }

  closeReassign(): void {
    this.reassignTarget.set(null);
  }

  async saveReassign(): Promise<void> {
    const key = this.reassignTarget();
    const userId = this.reassignUserId();
    if (!key || userId === null) return;
    this.isReassigning.set(true);
    this.reassignError.set(null);
    try {
      const updated = await this.acmeKeys.reassignOwner(key.id, userId);
      this.keys.update((list) => list.map((k) => (k.id === key.id ? updated : k)));
      this.reassignTarget.set(null);
    } catch {
      this.reassignError.set("APIKEYS.REASSIGN_ERROR");
    } finally {
      this.isReassigning.set(false);
    }
  }

  trackById(_: number, key: AcmeApiKey): number {
    return key.id;
  }
}

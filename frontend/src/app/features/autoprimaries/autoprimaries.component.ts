import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { Autoprimary } from "../../shared/models/pdns.model";
import { TranslatePipe } from "@ngx-translate/core";

@Component({
  selector: "app-autoprimaries",
  imports: [FormField, TranslatePipe],
  templateUrl: "./autoprimaries.component.html",
})
export class AutoprimariesComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly autoprimaries = signal<Autoprimary[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);

  readonly createModel = signal({ ip: "", nameserver: "", account: "" });
  readonly createForm = form(this.createModel, (s) => {
    required(s.ip, { message: "The IP address is required" });
    required(s.nameserver, { message: "The nameserver name is required" });
  });

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.autoprimaries.set(await this.pdns.getAutoprimaries());
    } catch {
      this.error.set("Impossible to load autoprimaries.");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreateModal(): void {
    this.createModel.set({ ip: "", nameserver: "", account: "" });
    this.createError.set(null);
    this.showCreateModal.set(true);
  }

  closeCreateModal(): void {
    this.showCreateModal.set(false);
  }

  onCreate(): void {
    submit(this.createForm, async () => {
      this.isCreating.set(true);
      this.createError.set(null);
      try {
        const { ip, nameserver, account } = this.createModel();
        await this.pdns.createAutoprimary({ ip, nameserver, account: account || null });
        this.showCreateModal.set(false);
        await this.load();
      } catch (err: unknown) {
        const httpErr = err as { error?: { detail?: string } };
        this.createError.set(httpErr?.error?.detail ?? "Error occurred while creating the autoprimaire.");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async delete(ap: Autoprimary): Promise<void> {
    if (!confirm(`Delete the autoprimaire "${ap.ip} / ${ap.nameserver}" ?`)) return;
    try {
      await this.pdns.deleteAutoprimary(ap.ip, ap.nameserver);
      this.autoprimaries.update((list) => list.filter((a) => !(a.ip === ap.ip && a.nameserver === ap.nameserver)));
    } catch {
      this.error.set(`Impossible to delete the autoprimaire "${ap.ip}".`);
    }
  }

  trackByKey(_: number, ap: Autoprimary): string {
    return `${ap.ip}:${ap.nameserver}`;
  }
}

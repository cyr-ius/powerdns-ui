import { Component, inject, OnInit, signal } from "@angular/core";
import { form, FormField, pattern, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { TsigKey } from "../../shared/models/pdns.model";
import { TranslatePipe } from "@ngx-translate/core";

const TSIG_ALGORITHMS = ["hmac-sha256", "hmac-sha512", "hmac-sha384", "hmac-sha224", "hmac-sha1", "hmac-md5"];

@Component({
  selector: "app-tsigkeys",
  imports: [FormField, TranslatePipe],
  templateUrl: "./tsigkeys.component.html",
  styleUrl: "./tsigkeys.component.css",
})
export class TsigKeysComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly keys = signal<TsigKey[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly showCreateModal = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);
  readonly revealedKey = signal<string | null>(null);
  readonly revealedId = signal<string | null>(null);
  readonly isRevealing = signal(false);

  readonly algorithms = TSIG_ALGORITHMS;

  readonly createModel = signal({
    name: "",
    algorithm: "hmac-sha256",
    secret: "",
  });
  readonly createForm = form(this.createModel, (s) => {
    required(s.name, { message: "TSIGKEYS.NAME_REQUIRED" });
    pattern(s.name, /^[a-zA-Z0-9._-]+$/, { message: "TSIGKEYS.NAME_PATTERN" });
  });

  async ngOnInit(): Promise<void> {
    await this.loadKeys();
  }

  async loadKeys(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.keys.set(await this.pdns.getTsigKeys());
    } catch {
      this.error.set("Impossible de charger les clés TSIG.");
    } finally {
      this.isLoading.set(false);
    }
  }

  openCreateModal(): void {
    this.createModel.set({ name: "", algorithm: "hmac-sha256", secret: "" });
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
        const { name, algorithm, secret } = this.createModel();
        await this.pdns.createTsigKey({
          name,
          algorithm,
          key: secret.trim() || undefined,
        });
        this.showCreateModal.set(false);
        await this.loadKeys();
      } catch (err: unknown) {
        const httpErr = err as { error?: { detail?: string } };
        this.createError.set(httpErr?.error?.detail ?? "Erreur lors de la création de la clé TSIG.");
      } finally {
        this.isCreating.set(false);
      }
    });
  }

  async revealKey(key: TsigKey): Promise<void> {
    if (this.revealedId() === key.id) {
      this.revealedId.set(null);
      this.revealedKey.set(null);
      return;
    }
    this.isRevealing.set(true);
    try {
      const detail = await this.pdns.getTsigKey(key.id);
      this.revealedId.set(key.id);
      this.revealedKey.set(detail.key ?? "(vide)");
    } catch {
      this.error.set("Impossible de récupérer le secret de la clé.");
    } finally {
      this.isRevealing.set(false);
    }
  }

  async deleteKey(key: TsigKey): Promise<void> {
    if (!confirm(`Supprimer la clé TSIG "${key.name}" ? Cette action est irréversible.`)) return;
    try {
      await this.pdns.deleteTsigKey(key.id);
      if (this.revealedId() === key.id) {
        this.revealedId.set(null);
        this.revealedKey.set(null);
      }
      this.keys.update((list) => list.filter((k) => k.id !== key.id));
    } catch {
      this.error.set(`Impossible de supprimer la clé "${key.name}".`);
    }
  }

  trackById(_: number, key: TsigKey): string {
    return key.id;
  }
}

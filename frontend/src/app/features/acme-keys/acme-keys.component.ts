import { DatePipe } from "@angular/common";
import { Component, inject, OnInit, signal } from "@angular/core";
import { TranslatePipe } from "@ngx-translate/core";
import { AcmeApiKey, AcmeKeysService } from "../../core/services/acme-keys.service";

@Component({
  selector: "app-acme-keys",
  imports: [DatePipe, TranslatePipe],
  templateUrl: "./acme-keys.component.html",
  styleUrl: "./acme-keys.component.css",
})
export class AcmeKeysComponent implements OnInit {
  private readonly acmeKeys = inject(AcmeKeysService);

  readonly keys = signal<AcmeApiKey[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    await this.loadKeys();
  }

  async loadKeys(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.keys.set(await this.acmeKeys.listAllKeys());
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

  trackById(_: number, key: AcmeApiKey): number {
    return key.id;
  }
}

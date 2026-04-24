import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { Network } from "../../shared/models/pdns.model";

@Component({
  selector: "app-networks",
  imports: [FormField],
  templateUrl: "./networks.component.html",
})
export class NetworksComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly networks = signal<Network[]>([]);
  readonly views = signal<string[]>([]);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  readonly showAddModal = signal(false);
  readonly isSubmitting = signal(false);
  readonly addError = signal<string | null>(null);

  readonly editingNetwork = signal<Network | null>(null);
  readonly editView = signal("");

  readonly addModel = signal({ network: "", view: "" });
  readonly addForm = form(this.addModel, (s) => {
    required(s.network, {
      message: "The CIDR network is required (e.g., 192.0.2.0/24)",
    });
    required(s.view, { message: "The view is required" });
  });

  readonly availableViews = computed(() => this.views());

  async ngOnInit(): Promise<void> {
    await Promise.all([this.loadNetworks(), this.loadViews()]);
  }

  async loadNetworks(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.networks.set(await this.pdns.getNetworks());
    } catch {
      this.error.set("Impossible to load networks.");
    } finally {
      this.isLoading.set(false);
    }
  }

  async loadViews(): Promise<void> {
    try {
      this.views.set(await this.pdns.getViews());
    } catch {
      // Views not critical for network display
    }
  }

  openAddModal(): void {
    this.addModel.set({ network: "", view: this.views()[0] ?? "" });
    this.addError.set(null);
    this.showAddModal.set(true);
  }

  closeAddModal(): void {
    this.showAddModal.set(false);
  }

  onAdd(): void {
    submit(this.addForm, async () => {
      this.isSubmitting.set(true);
      this.addError.set(null);
      try {
        const { network, view } = this.addModel();
        const [ip, prefixlenStr] = network.split("/");
        const prefixlen = parseInt(prefixlenStr, 10);
        if (!ip || isNaN(prefixlen)) {
          this.addError.set("Invalid CIDR format. Example: 192.0.2.0/24");
          return;
        }
        await this.pdns.assignNetworkView(ip, prefixlen, view);
        this.showAddModal.set(false);
        await this.loadNetworks();
      } catch (err: unknown) {
        const httpErr = err as { error?: { detail?: string } };
        this.addError.set(httpErr?.error?.detail ?? "Error occurred while adding the network.");
      } finally {
        this.isSubmitting.set(false);
      }
    });
  }

  startEdit(net: Network): void {
    this.editingNetwork.set(net);
    this.editView.set(net.view);
  }

  cancelEdit(): void {
    this.editingNetwork.set(null);
  }

  async saveEdit(net: Network): Promise<void> {
    const newView = this.editView();
    if (!newView) return;
    const [ip, prefixlenStr] = net.network.split("/");
    const prefixlen = parseInt(prefixlenStr, 10);
    try {
      await this.pdns.assignNetworkView(ip, prefixlen, newView);
      this.networks.update((list) => list.map((n) => (n.network === net.network ? { ...n, view: newView } : n)));
      this.editingNetwork.set(null);
    } catch {
      this.error.set(`Impossible to modify the view for "${net.network}".`);
    }
  }

  async deleteNetwork(net: Network): Promise<void> {
    if (!confirm(`Delete the network association "${net.network}" → view "${net.view}" ?`)) return;
    const [ip, prefixlenStr] = net.network.split("/");
    const prefixlen = parseInt(prefixlenStr, 10);
    try {
      await this.pdns.deleteNetwork(ip, prefixlen);
      this.networks.update((list) => list.filter((n) => n.network !== net.network));
    } catch {
      this.error.set(`Impossible to delete the network "${net.network}".`);
    }
  }

  trackByNetwork(_: number, net: Network): string {
    return net.network;
  }
}

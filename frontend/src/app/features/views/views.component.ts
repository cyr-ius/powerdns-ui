import { Component, computed, inject, OnInit, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { PdnsService } from "../../core/services/pdns.service";
import { ViewDetail } from "../../shared/models/pdns.model";
import { TranslatePipe } from "@ngx-translate/core";

@Component({
  selector: "app-views",
  imports: [FormField, TranslatePipe],
  templateUrl: "./views.component.html",
})
export class ViewsComponent implements OnInit {
  private readonly pdns = inject(PdnsService);

  readonly views = signal<ViewDetail[]>([]);
  readonly selectedView = signal<ViewDetail | null>(null);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);

  readonly showAddViewModal = signal(false);
  readonly showAddZoneModal = signal(false);
  readonly isSubmitting = signal(false);
  readonly modalError = signal<string | null>(null);

  readonly newViewModel = signal({ viewName: "", zoneName: "" });
  readonly newViewForm = form(this.newViewModel, (s) => {
    required(s.viewName, { message: "Le nom de la vue est requis" });
    required(s.zoneName, { message: "Le nom de la zone est requis" });
  });

  readonly addZoneModel = signal({ zoneName: "" });
  readonly addZoneForm = form(this.addZoneModel, (s) => {
    required(s.zoneName, { message: "Le nom de la zone est requis" });
  });

  readonly selectedZones = computed(() => this.selectedView()?.zones ?? []);

  async ngOnInit(): Promise<void> {
    await this.loadViews();
  }

  async loadViews(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      const viewNames = await this.pdns.getViews();
      const details = await Promise.all(
        viewNames.map(async (name) => {
          const zones = await this.pdns.getViewZones(name);
          return { name, zones } as ViewDetail;
        }),
      );
      this.views.set(details);
      const current = this.selectedView();
      if (current) {
        const refreshed = details.find((v) => v.name === current.name) ?? null;
        this.selectedView.set(refreshed);
      }
    } catch {
      this.error.set("Impossible de charger les vues.");
    } finally {
      this.isLoading.set(false);
    }
  }

  selectView(view: ViewDetail): void {
    this.selectedView.set(view);
  }

  openAddViewModal(): void {
    this.newViewModel.set({ viewName: "", zoneName: "" });
    this.modalError.set(null);
    this.showAddViewModal.set(true);
  }

  closeAddViewModal(): void {
    this.showAddViewModal.set(false);
  }

  onCreateView(): void {
    submit(this.newViewForm, async () => {
      this.isSubmitting.set(true);
      this.modalError.set(null);
      try {
        const { viewName, zoneName } = this.newViewModel();
        const name = zoneName.endsWith(".") ? zoneName : `${zoneName}.`;
        await this.pdns.addZoneToView(viewName, name);
        this.showAddViewModal.set(false);
        await this.loadViews();
      } catch (err: unknown) {
        const httpErr = err as { error?: { detail?: string } };
        this.modalError.set(httpErr?.error?.detail ?? "Erreur lors de la création de la vue.");
      } finally {
        this.isSubmitting.set(false);
      }
    });
  }

  openAddZoneModal(): void {
    this.addZoneModel.set({ zoneName: "" });
    this.modalError.set(null);
    this.showAddZoneModal.set(true);
  }

  closeAddZoneModal(): void {
    this.showAddZoneModal.set(false);
  }

  onAddZone(): void {
    submit(this.addZoneForm, async () => {
      this.isSubmitting.set(true);
      this.modalError.set(null);
      try {
        const view = this.selectedView();
        if (!view) return;
        const zoneName = this.addZoneModel().zoneName;
        const name = zoneName.endsWith(".") ? zoneName : `${zoneName}.`;
        await this.pdns.addZoneToView(view.name, name);
        this.showAddZoneModal.set(false);
        await this.loadViews();
      } catch (err: unknown) {
        const httpErr = err as { error?: { detail?: string } };
        this.modalError.set(httpErr?.error?.detail ?? "Erreur lors de l'ajout de la zone.");
      } finally {
        this.isSubmitting.set(false);
      }
    });
  }

  async removeZone(zone: string): Promise<void> {
    const view = this.selectedView();
    if (!view) return;
    if (!confirm(`Retirer la zone "${zone}" de la vue "${view.name}" ?`)) return;
    try {
      await this.pdns.removeZoneFromView(view.name, zone);
      await this.loadViews();
    } catch {
      this.error.set(`Impossible de retirer la zone "${zone}" de la vue.`);
    }
  }

  async deleteView(view: ViewDetail): Promise<void> {
    if (!confirm(`Supprimer la vue "${view.name}" et toutes ses associations de zones ?`)) return;
    try {
      await Promise.all(view.zones.map((z) => this.pdns.removeZoneFromView(view.name, z)));
      if (this.selectedView()?.name === view.name) this.selectedView.set(null);
      await this.loadViews();
    } catch {
      this.error.set(`Impossible de supprimer la vue "${view.name}".`);
    }
  }

  // PDNS stores zone entries as "{zone}.{view}" (e.g. "example.org..trusted")
  // Strip ".<viewName>" suffix for display; keep full name for API calls
  displayZoneName(fullName: string, viewName: string): string {
    const suffix = `.${viewName}`;
    return fullName.endsWith(suffix) ? fullName.slice(0, -suffix.length) : fullName;
  }

  trackByName(_: number, name: string): string {
    return name;
  }

  trackByViewName(_: number, view: ViewDetail): string {
    return view.name;
  }
}

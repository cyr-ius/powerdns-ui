import { Component, computed, inject, linkedSignal, signal } from "@angular/core";
import { form, FormField, required, submit } from "@angular/forms/signals";
import { TranslatePipe } from "@ngx-translate/core";
import { PdnsService } from "../../../../core/services/pdns.service";
import { ZoneDetailStore } from "../zone-detail.store";

/** Settings tab: zone kind and masters, allowed record types, PTR and Lua options. */
@Component({
  selector: "app-zone-settings",
  imports: [FormField, TranslatePipe],
  templateUrl: "./zone-settings.component.html",
  host: { class: "d-block" },
})
export class ZoneSettingsComponent {
  private readonly pdns = inject(PdnsService);
  private readonly store = inject(ZoneDetailStore);

  readonly isZoneAdmin = this.store.isZoneAdmin;
  readonly isLoadingMeta = this.store.isLoadingMeta;
  readonly autoReverseEnabled = this.store.autoReverseEnabled;
  readonly luaRecordsEnabled = this.store.luaRecordsEnabled;
  readonly zoneRecordTypesMeta = this.store.zoneRecordTypesMeta;

  // ── Zone settings ─────────────────────────────────────────────────────────
  readonly isSavingSettings = signal(false);
  readonly settingsError = signal<string | null>(null);
  readonly settingsSuccess = signal(false);
  // Reset to the zone values whenever the zone is reloaded.
  readonly settingsModel = linkedSignal(() => {
    const zone = this.store.zone();
    return { kind: zone?.kind ?? "Native", masters: zone?.masters?.join(", ") ?? "" };
  });
  readonly settingsForm = form(this.settingsModel, (s) => {
    required(s.kind);
  });

  // ── Zone record types ─────────────────────────────────────────────────────
  readonly pendingZoneTypes = linkedSignal(() => new Set(this.store.zoneRecordTypesMeta()?.types ?? []));
  readonly isSavingZoneTypes = signal(false);
  readonly zoneTypesSuccess = signal(false);
  readonly zoneTypesError = signal<string | null>(null);

  readonly availableGlobalTypes = computed(() =>
    this.store.globalRecordTypes().filter((rt) => {
      if (this.store.isReverseZone()) return rt.applicable_to === "reverse" || rt.applicable_to === "both";
      return rt.applicable_to === "direct" || rt.applicable_to === "both";
    }),
  );

  // ── Reverse DNS and Lua records ───────────────────────────────────────────
  readonly isTogglingAutoReverse = signal(false);
  readonly isTogglingLuaRecords = signal(false);

  toggleZoneType(name: string): void {
    this.pendingZoneTypes.update((s) => {
      const next = new Set(s);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async saveZoneRecordTypes(): Promise<void> {
    this.isSavingZoneTypes.set(true);
    this.zoneTypesError.set(null);
    this.zoneTypesSuccess.set(false);
    try {
      const result = await this.pdns.setZoneRecordTypes(this.store.zoneId, Array.from(this.pendingZoneTypes()));
      this.store.setZoneRecordTypes(result);
      this.zoneTypesSuccess.set(true);
      setTimeout(() => this.zoneTypesSuccess.set(false), 3000);
    } catch {
      this.zoneTypesError.set("Error occurred while saving the types.");
    } finally {
      this.isSavingZoneTypes.set(false);
    }
  }

  async resetZoneRecordTypes(): Promise<void> {
    this.isSavingZoneTypes.set(true);
    this.zoneTypesError.set(null);
    this.zoneTypesSuccess.set(false);
    try {
      const result = await this.pdns.setZoneRecordTypes(this.store.zoneId, []);
      this.store.setZoneRecordTypes(result);
      this.zoneTypesSuccess.set(true);
      setTimeout(() => this.zoneTypesSuccess.set(false), 3000);
    } catch {
      this.zoneTypesError.set("Error occurred while resetting the types.");
    } finally {
      this.isSavingZoneTypes.set(false);
    }
  }

  onSaveSettings(): void {
    submit(this.settingsForm, async () => {
      const zone = this.store.zone();
      if (!zone) return;
      this.isSavingSettings.set(true);
      this.settingsError.set(null);
      this.settingsSuccess.set(false);
      try {
        const { kind, masters } = this.settingsModel();
        const mastersList = masters
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        await this.pdns.updateZone(this.store.zoneId, {
          name: zone.name,
          kind,
          masters: mastersList,
        });
        this.settingsSuccess.set(true);
        await this.store.loadZone();
      } catch {
        this.settingsError.set("Error occurred while saving the settings.");
      } finally {
        this.isSavingSettings.set(false);
      }
    });
  }

  async toggleAutoReverse(): Promise<void> {
    this.isTogglingAutoReverse.set(true);
    this.settingsError.set(null);
    try {
      if (this.autoReverseEnabled()) {
        await this.pdns.deleteMetadata(this.store.zoneId, "X-AUTO-REVERSE");
      } else {
        await this.pdns.setMetadata(this.store.zoneId, "X-AUTO-REVERSE", ["1"]);
      }
      await this.store.loadMetadata();
    } catch {
      this.settingsError.set("Error occurred while updating the automatic PTR parameter.");
    } finally {
      this.isTogglingAutoReverse.set(false);
    }
  }

  async toggleLuaRecords(): Promise<void> {
    this.isTogglingLuaRecords.set(true);
    this.settingsError.set(null);
    try {
      const currentTypes = new Set(this.zoneRecordTypesMeta()?.types ?? []);
      if (this.luaRecordsEnabled()) {
        await this.pdns.deleteMetadata(this.store.zoneId, "X-LUA-RECORDS");
        currentTypes.delete("LUA");
      } else {
        await this.pdns.setMetadata(this.store.zoneId, "X-LUA-RECORDS", ["1"]);
        currentTypes.add("LUA");
      }
      this.store.setZoneRecordTypes(await this.pdns.setZoneRecordTypes(this.store.zoneId, Array.from(currentTypes)));
      await this.store.loadMetadata();
    } catch {
      this.settingsError.set("Error occurred while updating the Lua Records setting.");
    } finally {
      this.isTogglingLuaRecords.set(false);
    }
  }
}

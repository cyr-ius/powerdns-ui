import { computed, inject, Injectable, signal } from "@angular/core";
import { AdminService } from "../../../core/services/admin.service";
import { AuthService } from "../../../core/services/auth.service";
import { AcmeApiKey, AcmeKeysService } from "../../../core/services/acme-keys.service";
import { EmailCheckResult, PdnsService, SoaCheckResult } from "../../../core/services/pdns.service";
import type { RecordType, ZoneRecordTypes } from "../../../shared/models/admin.model";
import {
  CryptoKey,
  Metadata,
  TsigKey,
  UserBasic,
  Zone,
  ZoneDetail,
  ZoneMember,
  ZoneRole,
} from "../../../shared/models/pdns.model";

export type ActionMessage = { type: "success" | "error"; text: string };

/**
 * State of one zone detail page, shared by its tabs.
 *
 * Provided by ZoneDetailComponent: each page gets its own instance. Holds the
 * data read by several tabs or by the tab badges; the state of a single tab
 * (modals, forms, sorting) stays in the tab component.
 */
@Injectable()
export class ZoneDetailStore {
  private readonly pdns = inject(PdnsService);
  private readonly adminService = inject(AdminService);
  private readonly acmeKeysSvc = inject(AcmeKeysService);
  readonly auth = inject(AuthService);

  zoneId = "";

  // ── Zone ──────────────────────────────────────────────────────────────────
  readonly zone = signal<ZoneDetail | null>(null);
  readonly isLoading = signal(false);
  readonly error = signal<string | null>(null);
  readonly actionMessage = signal<ActionMessage | null>(null);

  readonly isReverseZone = computed(() => {
    const name = (this.zone()?.name ?? "").toLowerCase();
    return (
      name.endsWith(".in-addr.arpa.") || name === "in-addr.arpa." || name.endsWith(".ip6.arpa.") || name === "ip6.arpa."
    );
  });

  // ── Role / permissions ────────────────────────────────────────────────────
  readonly currentRole = signal<ZoneRole | null>(null);
  readonly canWrite = computed(
    () => this.auth.isAdmin() || this.currentRole() === "manager" || this.currentRole() === "admin",
  );
  readonly isZoneAdmin = computed(() => this.auth.isAdmin() || this.currentRole() === "admin");

  // ── Metadata ──────────────────────────────────────────────────────────────
  readonly metadata = signal<Metadata[]>([]);
  readonly isLoadingMeta = signal(false);
  readonly metaError = signal<string | null>(null);
  metadataLoaded = false;

  readonly tsigAllowDnsupdate = computed(
    () => this.metadata().find((m) => m.kind === "TSIG-ALLOW-DNSUPDATE")?.metadata ?? [],
  );
  readonly allowDnsupdateFrom = computed(
    () => this.metadata().find((m) => m.kind === "ALLOW-DNSUPDATE-FROM")?.metadata ?? [],
  );
  readonly autoReverseEnabled = computed(() =>
    this.metadata().some((m) => m.kind === "X-AUTO-REVERSE" && m.metadata[0] === "1"),
  );
  readonly luaRecordsEnabled = computed(() =>
    this.metadata().some((m) => m.kind === "X-LUA-RECORDS" && m.metadata[0] === "1"),
  );

  // ── Record types ──────────────────────────────────────────────────────────
  readonly zoneRecordTypes = signal<string[]>([]);
  readonly zoneRecordTypesMeta = signal<ZoneRecordTypes | null>(null);
  readonly globalRecordTypes = signal<RecordType[]>([]);

  // ── Other zones (reverse DNS) ─────────────────────────────────────────────
  readonly allZones = signal<Zone[]>([]);

  // ── DNSSEC ────────────────────────────────────────────────────────────────
  readonly cryptoKeys = signal<CryptoKey[]>([]);
  readonly isLoadingKeys = signal(false);
  readonly keyError = signal<string | null>(null);

  // ── TSIG keys ─────────────────────────────────────────────────────────────
  readonly tsigKeys = signal<TsigKey[]>([]);

  // ── Members ───────────────────────────────────────────────────────────────
  readonly members = signal<ZoneMember[]>([]);
  readonly allUsers = signal<UserBasic[]>([]);
  readonly isLoadingMembers = signal(false);
  readonly membersError = signal<string | null>(null);
  membersLoaded = false;

  // ── ACME keys ─────────────────────────────────────────────────────────────
  readonly zoneAcmeKeys = signal<AcmeApiKey[]>([]);
  readonly isLoadingAcmeKeys = signal(false);
  readonly acmeKeysError = signal<string | null>(null);
  acmeKeysLoaded = false;

  // ── Server config ─────────────────────────────────────────────────────────
  readonly dnsupdateEnabled = signal<boolean>(true);

  // ── SOA sync and e-mail security checks ───────────────────────────────────
  readonly soaCheck = signal<SoaCheckResult | null>(null);
  readonly isCheckingSoa = signal(false);
  readonly soaCheckError = signal<string | null>(null);
  readonly showSoaPanel = signal(false);

  readonly emailCheck = signal<EmailCheckResult | null>(null);
  readonly isCheckingEmail = signal(false);
  readonly emailCheckError = signal<string | null>(null);
  readonly showEmailPanel = signal(false);

  async loadZone(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);
    try {
      this.zone.set(await this.pdns.getZone(this.zoneId));
    } catch {
      this.error.set("Unable to load the area.");
    } finally {
      this.isLoading.set(false);
    }
  }

  async loadZoneRole(): Promise<void> {
    try {
      const { role } = await this.pdns.getZoneRole(this.zoneId);
      this.currentRole.set(role);
    } catch {
      // non-blocking — falls back to null (no write access)
    }
  }

  async loadServerConfig(): Promise<void> {
    try {
      const config = await this.pdns.getConfig();
      const setting = config.find((s) => s.name === "dnsupdate");
      this.dnsupdateEnabled.set(setting?.value === "yes");
    } catch {
      // non-blocking — assume enabled on error
    }
  }

  async loadAllZones(): Promise<void> {
    try {
      this.allZones.set(await this.pdns.getZones());
    } catch {
      // non-blocking
    }
  }

  async loadMetadata(): Promise<void> {
    this.isLoadingMeta.set(true);
    this.metaError.set(null);
    try {
      this.metadata.set(await this.pdns.getMetadata(this.zoneId));
      this.metadataLoaded = true;
    } catch {
      this.metaError.set("Unable to load metadata.");
    } finally {
      this.isLoadingMeta.set(false);
    }
  }

  async loadZoneRecordTypes(): Promise<void> {
    try {
      const [meta, globalTypes] = await Promise.all([
        this.pdns.getZoneRecordTypes(this.zoneId),
        this.adminService.listRecordTypes(),
      ]);
      this.globalRecordTypes.set(globalTypes);
      this.setZoneRecordTypes(meta);
    } catch {
      // non-blocking
    }
  }

  setZoneRecordTypes(meta: ZoneRecordTypes): void {
    this.zoneRecordTypesMeta.set(meta);
    this.zoneRecordTypes.set(meta.types);
  }

  async loadCryptoKeys(): Promise<void> {
    this.isLoadingKeys.set(true);
    this.keyError.set(null);
    try {
      this.cryptoKeys.set(await this.pdns.getCryptoKeys(this.zoneId));
    } catch {
      this.keyError.set("Unable to load cryptographic keys.");
    } finally {
      this.isLoadingKeys.set(false);
    }
  }

  async loadTsigKeys(): Promise<void> {
    try {
      this.tsigKeys.set(await this.pdns.getTsigKeys());
    } catch {
      // non-blocking
    }
  }

  async loadMembers(): Promise<void> {
    this.isLoadingMembers.set(true);
    this.membersError.set(null);
    try {
      const [members, users] = await Promise.all([this.pdns.getZoneMembers(this.zoneId), this.pdns.getUsers()]);
      this.members.set(members);
      this.allUsers.set(users);
      this.membersLoaded = true;
    } catch {
      this.membersError.set("Error occurred while loading the members.");
    } finally {
      this.isLoadingMembers.set(false);
    }
  }

  async loadZoneAcmeKeys(): Promise<void> {
    this.isLoadingAcmeKeys.set(true);
    this.acmeKeysError.set(null);
    try {
      this.zoneAcmeKeys.set(await this.acmeKeysSvc.listZoneAcmeKeys(this.zoneId));
      this.acmeKeysLoaded = true;
    } catch {
      this.acmeKeysError.set("ZONE_DETAIL.ACME_KEYS_LOAD_ERROR");
    } finally {
      this.isLoadingAcmeKeys.set(false);
    }
  }

  async checkSoaSync(): Promise<void> {
    this.isCheckingSoa.set(true);
    this.soaCheckError.set(null);
    this.showSoaPanel.set(true);
    try {
      this.soaCheck.set(await this.pdns.checkSoaSync(this.zoneId));
    } catch {
      this.soaCheckError.set("ZONE_DETAIL.SOA_CHECK_ERROR");
    } finally {
      this.isCheckingSoa.set(false);
    }
  }

  async checkEmailSecurity(): Promise<void> {
    this.isCheckingEmail.set(true);
    this.emailCheckError.set(null);
    this.showEmailPanel.set(true);
    try {
      this.emailCheck.set(await this.pdns.checkEmailSecurity(this.zoneId));
    } catch {
      this.emailCheckError.set("ZONE_DETAIL.EMAIL_CHECK_ERROR");
    } finally {
      this.isCheckingEmail.set(false);
    }
  }
}

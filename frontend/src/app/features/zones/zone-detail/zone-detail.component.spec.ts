import { signal } from "@angular/core";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, provideRouter } from "@angular/router";
import { provideTranslateService } from "@ngx-translate/core";
import { AcmeKeysService } from "../../../core/services/acme-keys.service";
import { AdminService } from "../../../core/services/admin.service";
import { AuthService } from "../../../core/services/auth.service";
import { PdnsService } from "../../../core/services/pdns.service";
import { ZoneDetailComponent } from "./zone-detail.component";

const ZONE = {
  id: "example.org.",
  name: "example.org.",
  kind: "Native",
  account: "acme",
  dnssec: false,
  serial: 2026103001,
  masters: [],
  rrsets: [{ name: "www.example.org.", type: "A", ttl: 3600, records: [{ content: "192.0.2.1", disabled: false }] }],
};

const METADATA = [
  { kind: "ALLOW-AXFR-FROM", metadata: ["198.51.100.0/24"] },
  { kind: "ALLOW-DNSUPDATE-FROM", metadata: ["203.0.113.5"] },
];

function setup() {
  const pdns = {
    getZone: async () => ZONE,
    getZones: async () => [ZONE],
    getZoneRole: async () => ({ role: "admin" }),
    getConfig: async () => [{ name: "dnsupdate", value: "yes" }],
    getMetadata: async () => METADATA,
    getZoneRecordTypes: async () => ({ types: [], is_custom: false }),
    getCryptoKeys: async () => [],
    getTsigKeys: async () => [],
    getZoneMembers: async () => [{ user_id: 2, username: "alice", email: null, role: "manager" }],
    getUsers: async () => [],
  };
  TestBed.configureTestingModule({
    imports: [ZoneDetailComponent],
    providers: [
      provideRouter([]),
      provideTranslateService(),
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map([["id", ZONE.id]]) } } },
      { provide: PdnsService, useValue: pdns },
      { provide: AdminService, useValue: { listRecordTypes: async () => [] } },
      { provide: AcmeKeysService, useValue: { listZoneAcmeKeys: async () => [{ id: 1, name: "certbot" }] } },
      { provide: AuthService, useValue: { isAdmin: signal(true) } },
    ],
  });
  return TestBed.createComponent(ZoneDetailComponent);
}

// ngOnInit starts the secondary loads without awaiting them: let them settle.
async function settle(fixture: ReturnType<typeof setup>): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve));
  await fixture.whenStable();
}

describe("ZoneDetailComponent", () => {
  it("renders each tab from the shared zone state", async () => {
    const fixture = setup();
    await settle(fixture);
    const page = fixture.nativeElement as HTMLElement;
    const tabs = Array.from(page.querySelectorAll<HTMLButtonElement>(".nav-tabs .nav-link"));

    // Badges come from data loaded before any tab is opened.
    expect(tabs.map((t) => t.textContent?.trim())).toEqual([
      expect.stringContaining("1"),
      expect.any(String),
      expect.any(String),
      expect.any(String),
      expect.stringContaining("ZONE_DETAIL.KEY_ACTIVE"),
      expect.any(String),
      expect.stringContaining("1"),
      expect.stringContaining("1"),
    ]);
    expect(page.querySelector("app-zone-records")?.textContent).toContain("www.example.org.");

    const expected: [string, string][] = [
      ["app-zone-metadata", "ALLOW-AXFR-FROM"],
      ["app-zone-dnssec", ""],
      ["app-zone-transfer", "198.51.100.0/24"],
      ["app-zone-dnsupdate", "203.0.113.5"],
      ["app-zone-settings", ""],
      ["app-zone-members", "alice"],
      ["app-zone-acme-keys", "certbot"],
    ];
    for (const [index, [selector, text]] of expected.entries()) {
      tabs[index + 1].click();
      await settle(fixture);
      const tab = page.querySelector(selector);
      expect(tab, selector).not.toBeNull();
      expect(tab?.textContent).toContain(text);
      expect(page.querySelector("app-zone-records")).toBeNull();
    }
  });
});

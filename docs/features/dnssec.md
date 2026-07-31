# DNSSEC

DNSSEC is managed per [zone](zones.md) from the zone's **DNSSEC** tab.

## What you can do

- Enable/disable DNSSEC signing for the zone.
- Manage cryptographic keys (KSK/ZSK): create with a chosen key type, algorithm and bit length, or let PowerDNS pick sensible defaults.
- **Activate/deactivate** a key — controls whether it is currently used to sign the zone.
- **Publish/unpublish** a key — controls whether its `DNSKEY` record is present in the zone, independently of whether it's actively signing.
- View the resulting `DNSKEY`, `DS` and `CDS` records to hand off to the parent zone or domain registrar.

## Key lifecycle

| State         | Meaning                                                            |
| ------------- | ------------------------------------------------------------------ |
| `active`      | The key is used to sign the zone's records                         |
| `inactive`    | The key exists but is not currently signing                        |
| `published`   | The key's `DNSKEY` record is served in the zone                    |
| `unpublished` | The key's `DNSKEY` record is withheld (e.g. during a key rollover) |

This maps directly to the PowerDNS `cryptokeys` API, which lets `active` and `published` be toggled independently — a prerequisite for safe key rollovers (pre-publish a new key before activating it, keep an old key published for a TTL after deactivation, etc.).

## Registrar handoff

Once DNSSEC is enabled and keys are published, copy the `DS` (or `CDS`, if your registrar supports CDS/CDNSKEY automated scanning) record(s) shown on the DNSSEC tab into your domain registrar's DS record field to complete the chain of trust from the parent zone.

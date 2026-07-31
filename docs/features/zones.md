# DNS Zones & Records

PowerDNS UI exposes the full zone lifecycle on top of the PowerDNS Authoritative API.

## Zone kinds

A zone can be created as one of the three PowerDNS kinds:

- **Native** — standalone zone, no replication managed by PowerDNS itself (typical for a single authoritative server, or replication handled outside PowerDNS, e.g. at the database level).
- **Master** — primary zone; changes are served to configured secondaries via notifications and AXFR/IXFR.
- **Slave** — secondary zone; content is pulled from one or more `masters` via AXFR and kept in sync automatically.

Each zone belongs to an **account** and can optionally be assigned to a [catalog](catalog-zones.md) at creation time — both scope who can manage the zone and how it is grouped for AXFR distribution.

## Creating a zone

From **Zones → New Zone**, provide:

- Name (FQDN)
- Kind (`Native` / `Master` / `Slave`)
- Nameservers (creates the initial `NS` records)
- Masters (IP addresses, only for `Slave` zones)
- Account (owner account, scopes visibility/permissions)
- Catalog (optional, assigns the zone as a Producer catalog member)
- SOA-EDIT-API behaviour

## Records

Each zone's record set (RRset) is grouped by name + type, and supports:

- Adding, editing and deleting records within an RRset (multiple records per name/type, e.g. round-robin `A` records)
- Per-record `content` and `disabled` flag — disabling a record keeps it in the zone without serving it
- Per-RRset `TTL`
- **Comments** on RRsets, tracked with author account and modification time — useful for change tracking independent of the [audit log](../administration/audit-log.md)

Available record types can be restricted per zone from the zone's **Settings** tab (see [Lua Records](lua-records.md) for how the `LUA` type is added).

## Going further

- [DNSSEC](dnssec.md) — signing keys, KSK/ZSK, DS/CDS records
- [Reverse DNS](reverse-dns.md) — PTR zone creation from an IPv4/IPv6 network
- [Catalog Zones](catalog-zones.md) — Producer/Consumer membership
- [Lua Records](lua-records.md) — dynamic responses

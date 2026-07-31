# Catalog Zones

[Catalog zones](https://doc.powerdns.com/authoritative/catalog.html) ([RFC 9432](https://www.rfc-editor.org/rfc/rfc9432)) let a PowerDNS server automatically distribute zone provisioning to secondary servers, without manually configuring each zone on every secondary.

## Producer

A **Producer** catalog zone is a primary zone that lists member zones. When a zone is added to a Producer, secondary Consumer servers discover and provision it automatically on their next zone transfer.

- Create a Producer from the **Catalogs → Producer** tab.
- Assign an existing zone to a Producer either at [zone creation time](zones.md#creating-a-zone) or from the Catalogs page.
- Add / remove member zones manually from the Producer's member list.

## Consumer

A **Consumer** catalog zone is a secondary zone that pulls its configuration from a Producer via AXFR. Member zones are created automatically by PowerDNS after each zone transfer — they **cannot** be managed manually on the Consumer side.

- Create a Consumer from the **Catalogs → Consumer** tab.
- Provide the name of the catalog (must match the Producer's zone name exactly) and the IP address(es) of the Producer server.
- The received member zones are displayed in **read-only** mode, reflecting what PowerDNS has actually provisioned from the last transfer.

## Typical setup

```text
Producer (primary, e.g. "catalog.example.com.")
  └── member zones: example.com., example.net., ...
        │  AXFR
        ▼
Consumer (secondary)
  └── receives + auto-provisions the same member zones
```

This is the recommended replacement for the classic `also-notify` / manually-mirrored `slave-config` approach when running many zones across several secondaries: add or remove a zone once on the Producer, and every Consumer picks it up automatically.

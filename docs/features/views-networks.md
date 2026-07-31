# DNS Views & Networks

DNS Views implement **split-horizon DNS**: the same query can return different answers depending on which network the client is on (e.g. internal clients get private IPs, external clients get public IPs). This is an **LMDB-backend-only** PowerDNS feature.

!!! note "Availability"
    The **Views** and **Networks** menus only appear in PowerDNS UI if the detected PowerDNS backend is `lmdb`. See [PowerDNS Configuration](../configuration/powerdns.md#dns-views-and-networks-lmdb-backend-only) to enable it server-side.

## Views

A view is a named group of zone variants. From **Views**, an administrator can:

- List existing views (as reported by the PowerDNS `/views` API).
- Associate a zone with a view — the same zone name can have distinct content per view.
- Remove a zone from a view.

## Networks

A network (a CIDR block) is assigned to a view, so PowerDNS knows which view to serve to clients whose source address falls in that block. From **Networks**, an administrator can:

- List configured network → view assignments.
- Assign a network (CIDR) to a view.
- Remove a network assignment.

## Access

Both Views and Networks management are restricted to administrators.

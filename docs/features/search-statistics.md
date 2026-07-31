# Search & Statistics

## Search

The global **Search** page queries the PowerDNS `/search-data` endpoint across:

- Zone names
- Record names and content
- Comments

Results are scoped to the zones the current user's account(s) can access — see [Roles & Permissions](../administration/roles-permissions.md) — except for Super Admins, who search across every zone.

## Statistics

The **Statistics** page surfaces the PowerDNS server's real-time metrics (queries per second, cache hit ratios, packet counters, latency, etc.) as reported by the `/statistics` endpoint, without needing to query the PowerDNS API or a separate monitoring stack directly.

## Server Configuration

The **Server Configuration** page shows the active PowerDNS configuration as reported by the server itself (`/config`), useful to confirm which settings (backend, DNSSEC defaults, API flags, …) are actually in effect versus what's in `pdns.conf` on disk.

## Cache Flush

Administrators can trigger a cache flush for a given domain from the server tools, invalidating cached records so subsequent queries reflect recent zone changes immediately rather than waiting for TTL expiry.

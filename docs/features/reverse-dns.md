# Reverse DNS

PowerDNS UI can create reverse (`in-addr.arpa.` for IPv4, `ip6.arpa.` for IPv6) [zones](zones.md) directly from a network, instead of requiring the zone name and boundary to be computed by hand.

## What it does

- Given an IPv4 or IPv6 network (e.g. `192.0.2.0/24` or `2001:db8::/64`), PowerDNS UI computes the correct reverse zone name(s) and creates the zone(s) — including splitting across multiple reverse zones when the prefix doesn't align on an octet (IPv4) or nibble (IPv6) boundary.
- `PTR` records can then be generated automatically for hosts in the network, avoiding manual octet/nibble reversal errors that are a common source of misconfigured reverse DNS.

## Why it matters

Correct reverse DNS (PTR) is required by many mail servers as part of anti-spam checks (matching HELO/EHLO or the sending IP to a resolvable hostname), and is generally good practice for any publicly routable host. Computing reverse zone boundaries by hand — especially for IPv6 or for IPv4 networks not on a /24 boundary — is tedious and error-prone; PowerDNS UI automates it.

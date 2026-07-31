# TSIG Keys

[TSIG](https://doc.powerdns.com/authoritative/tsig.html) (Transaction SIGnature) keys authenticate DNS operations between servers — most commonly zone transfers (AXFR/IXFR) and DNS Update (RFC 2136) requests — using a shared secret rather than relying on IP allow-listing alone.

## Management

From **TSIG Keys** (administrators only), you can:

- List existing keys.
- Create a key with a name and algorithm (e.g. `hmac-sha256`), optionally supplying your own secret or letting PowerDNS generate one.
- Update a key's name, algorithm or secret.
- Delete a key.

## Typical uses

- Securing zone transfers to a secondary server: configure the same TSIG key on both PowerDNS instances, then reference it on the secondary's AXFR request and on the primary's `allow-axfr-ips`/TSIG zone metadata.
- Authenticating [autoprimary](autoprimaries.md) notifications.
- Authenticating DNS Update (dynamic DNS) clients, such as the ACME DNS-01 flow described in [ACME Keys & Personal Access Tokens](acme-pat.md).

!!! danger "Handle secrets carefully"
    A TSIG secret grants whoever holds it the ability to perform the operations it authorizes (e.g. transfer or update a zone). Treat it like any other credential — rotate it via **Update**, and delete unused keys.

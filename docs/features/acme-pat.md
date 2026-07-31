# ACME Keys & Personal Access Tokens

PowerDNS UI exposes two distinct API credential mechanisms, scoped and authenticated differently. Don't confuse them.

## Personal Access Tokens (PAT)

Users create personal access tokens from their profile (`/api/tokens`). A token authenticates REST calls as an **HTTP Bearer** credential, with the same permissions as the user who created it:

```bash
curl -H "Authorization: Bearer <token>" https://<host>/api/zones
```

This scheme is declared in the OpenAPI document, so the Swagger UI (`/api/docs`) can authorize its requests with a token — see [API Reference](../api.md).

Setting [`API_KEYS_ENABLED=false`](../configuration/environment-variables.md) refuses tokens on every endpoint and hides token management from the interface entirely — useful if your organization mandates OIDC-only access with no long-lived credentials.

## ACME Keys

ACME keys exist for the [`certbot-dns-pdns`](https://github.com/pan-net-security/certbot-dns-pdns)-style DNS-01 challenge flow used by Let's Encrypt and `cert-manager`. They are a **separate mechanism** from PATs:

- **Scoped to one or more specific zones**, not to the calling user's full permission set — a key created for `example.com.` cannot touch other zones.
- Created from the owning zone's page (or reassigned/administered globally from **Administration → ACME Keys**).
- Authenticate via the **`X-API-Key`** header — this header is not used anywhere else in the PowerDNS UI API.

```bash
curl -H "X-API-Key: <acme-key>" https://<host>/api/acme/...
```

Each key has a name, an optional comment, tracks its creation time and last-used time, and can be reassigned to a different owning user by an administrator (e.g. when a service account changes hands) without needing to reissue the key itself.

## Which one to use

| Use case                                                             | Credential            |
| -------------------------------------------------------------------- | --------------------- |
| Automating zone/record management as yourself, or via the Swagger UI | Personal Access Token |
| `cert-manager` / `certbot` DNS-01 solver, scoped to one zone         | ACME Key              |

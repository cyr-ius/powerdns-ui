# PowerDNS UI

**PowerDNS UI** is a modern web management interface for the [PowerDNS Authoritative Server](https://www.powerdns.com/auth.html). It wraps the PowerDNS REST API with an Angular frontend, a FastAPI backend, and its own user/role/audit layer, so teams can manage zones, records, DNSSEC, catalog zones and more without touching the raw API or a CLI.

[![License](https://img.shields.io/badge/License-MIT-blue)](license.md)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Angular](https://img.shields.io/badge/Angular-22-green)

[Get started :material-arrow-right:](getting-started.md){ .md-button .md-button--primary }
[View on GitHub :material-github:](https://github.com/cyr-ius/pdns-ui){ .md-button }

## Why PowerDNS UI

PowerDNS ships with a powerful REST API but no first-party web UI. PowerDNS UI fills that gap with:

- A **single container** deployment — the Angular app is served statically by FastAPI.
- Its **own accounts, roles and permissions**, layered on top of the PowerDNS API key so end users never need direct access to PowerDNS itself.
- A full **audit trail** of every action, with optional syslog export.
- Support for advanced PowerDNS features: DNSSEC, Catalog Zones, Lua Records, DNS Views/Networks (LMDB), TSIG keys, Autoprimaries.

## Features

| Area                        | Highlights                                                                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| **DNS Zones**               | Create, edit, delete (Native / Master / Slave), record management, catalog assignment at creation |
| **DNSSEC**                  | Cryptographic key management per zone                                                             |
| **Reverse DNS**             | IPv4/IPv6 PTR zone creation with automatic PTR record generation                                  |
| **Lua Records**             | Per-zone activation of dynamic Lua records (admin/zone-admin only)                                |
| **Catalog Zones**           | Producer zones (manual member management) and Consumer zones (automatic AXFR sync)                |
| **ACME Keys**               | Per-zone and per-user API keys for DNS-01 ACME challenges (Let's Encrypt / cert-manager)          |
| **TSIG Keys**               | Creation and management of signing keys                                                           |
| **Autoprimaries**           | Automatic primary server configuration                                                            |
| **DNS Views** _(LMDB only)_ | Split-horizon, zone ↔ view association                                                            |
| **Networks** _(LMDB only)_  | Network assignment to views                                                                       |
| **Search**                  | Global search across zones, records, and comments                                                 |
| **Statistics**              | Real-time PowerDNS server metrics                                                                 |
| **Server Configuration**    | Active configuration visualization                                                                |
| **Audit Log**               | History of all user actions + PDNS logs, export to syslog                                         |
| **User Management**         | Admin / manager / viewer roles per account                                                        |
| **OIDC SSO**                | Delegated authentication (Keycloak, Authentik, etc.)                                              |
| **Theme**                   | Light / dark / automatic                                                                          |

See the [Features](features/zones.md) section for a detailed walkthrough of each area, or jump straight to [Getting Started](getting-started.md) to deploy your first instance.

## Architecture

```text
┌─────────────────────────────────────┐
│          Browser (Angular 22)       │
└───────────────┬─────────────────────┘
                │ HTTP
┌───────────────▼─────────────────────┐
│        FastAPI  (Python 3.12+)      │
│        SQLite  (SQLModel)           │
└───────────────┬─────────────────────┘
                │ REST API
┌───────────────▼─────────────────────┐
│   PowerDNS Authoritative Server     │
└─────────────────────────────────────┘
```

The Angular frontend is built and served statically by FastAPI — a single container is sufficient for a full deployment. PowerDNS UI never talks to the PowerDNS database directly: every operation goes through the official PowerDNS Authoritative REST API, and is additionally authorized, logged and attributed to a PowerDNS UI user/account.

## Where to go next

- [Getting Started](getting-started.md) — Docker Compose in under five minutes.
- [Configuration](configuration/powerdns.md) — PowerDNS prerequisites and environment variables.
- [Features](features/zones.md) — in-depth guide to zones, DNSSEC, catalog zones, Lua records, TSIG, autoprimaries, views/networks.
- [Administration](administration/roles-permissions.md) — roles, user management, audit log.
- [API Reference](api.md) — the built-in Swagger UI and authentication schemes.
- [Development](development.md) — running the backend and frontend locally.

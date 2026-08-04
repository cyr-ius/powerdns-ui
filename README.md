# 🌐 PowerDNS UI

![License](https://img.shields.io/github/license/cyr-ius/powerdns-ui?label=License&color=blue) ![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python) ![Angular](https://img.shields.io/badge/Angular-22-blue?logo=angular) [![ci::status]][ci::github] [![docker::pulls]][docker::hub] [![documentation::badge]][documentation::web]

[ci::status]: https://img.shields.io/github/actions/workflow/status/cyr-ius/powerdns-ui/docker-publish.yml?logo=github
[ci::github]: https://github.com/cyr-ius/powerdns-ui/actions
[docker::pulls]: https://img.shields.io/docker/pulls/cyrius44/powerdns-ui.svg?logo=docker
[docker::hub]: https://hub.docker.com/r/cyrius44/powerdns-ui
[documentation::badge]: https://img.shields.io/badge/Documentation-Wiki-green?logo=helpdesk
[documentation::web]: https://cyr-ius.github.io/powerdns-ui/

**PowerDNS UI** is a modern web management interface for the [PowerDNS Authoritative Server](https://www.powerdns.com/auth.html). It wraps the PowerDNS REST API with an Angular frontend and a FastAPI backend, adding its own accounts, roles and audit layer so teams can manage zones, records, DNSSEC and more without touching the raw API.

<img width="1151" height="680" alt="PowerDNS UI zone view" src="https://github.com/user-attachments/assets/542b271b-f806-4be9-9ebf-58d04e4d0676" />

---

## Features

- 🗂️ **DNS Zones** — create, edit, delete (Native / Master / Slave), record management with catalog assignment at creation
- 🔑 **DNSSEC** — cryptographic key management per zone
- 🔁 **Reverse DNS** — IPv4/IPv6 PTR zone creation with automatic PTR record generation
- 🧩 **Catalog Zones** — Producer (manual members) and Consumer (automatic AXFR sync) zones
- 🧮 **Lua Records** — per-zone activation of dynamic Lua records (admin/zone-admin only)
- 🔐 **ACME & TSIG Keys** — DNS-01 challenge keys and signing key management
- 🛰️ **Autoprimaries** & **DNS Views / Networks** _(LMDB only)_
- 🔍 **Search & Statistics** — global search plus real-time PowerDNS server metrics
- 📋 **Audit Log** — history of every user action + PDNS logs, syslog export
- 👥 **User Management** — admin / manager / viewer roles per account, OIDC SSO
- 🎨 **Theme** — light / dark / automatic

Single container (Angular served statically by FastAPI), SQLite by default — see the [Architecture](https://cyr-ius.github.io/powerdns-ui/#architecture) section for details.

---

## Quick Start

```yaml
# docker-compose.yaml
services:
  pdns:
    image: powerdns/pdns-auth-51:5.1.3
    restart: unless-stopped
    volumes:
      - powerdns_data:/var/lib/powerdns
    ports:
      - 53:53
      - 53:53/udp
    command:
      - "--api=yes"
      - "--api-key=${PDNS_AUTH_API_KEY:-change-this-api-key-in-production}"
      - "--webserver=yes"
      - "--webserver-address=0.0.0.0"
      - "--webserver-port=8081"
      - "--webserver-allow-from=0.0.0.0/0"

  pdns-ui:
    image: ghcr.io/cyr-ius/pdns-ui:latest
    restart: unless-stopped
    depends_on: [pdns]
    environment:
      - PDNS_AUTH_API_URL=http://pdns:8081
      - PDNS_AUTH_API_KEY=change-this-api-key-in-production
    volumes:
      - powerdns-ui_data:/var/lib/powerdns-ui
    ports:
      - 8080:8080

volumes:
  powerdns_data:
  powerdns-ui_data:
```

```bash
docker compose up -d
```

Open **http://localhost:8080** and log in as `admin` with the one-time password printed in the container logs on first start, then change it immediately.

> **Note:** mounting a persistent volume on `/var/lib/powerdns-ui` is required — the generated admin password and JWT secret key are stored there.

For the full installation guide (PowerDNS API setup, MariaDB backend, reverse proxy) see **[Getting Started](https://cyr-ius.github.io/powerdns-ui/getting-started/)**.

---

## Documentation

Full documentation — configuration reference, every feature explained, the REST API, and how to contribute — is published at **[cyr-ius.github.io/powerdns-ui](https://cyr-ius.github.io/powerdns-ui/)**.

| Looking for...                          | Go to                                                                                               |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Every environment variable              | [Environment Variables](https://cyr-ius.github.io/powerdns-ui/configuration/environment-variables/) |
| PowerDNS API setup & DNS Views/Networks | [PowerDNS Configuration](https://cyr-ius.github.io/powerdns-ui/configuration/powerdns/)             |
| OIDC SSO & e-mail alerting              | [OIDC & Mail Connectors](https://cyr-ius.github.io/powerdns-ui/configuration/oidc-mail/)            |
| Rate limiting behind a reverse proxy    | [Rate Limiting & Reverse Proxy](https://cyr-ius.github.io/powerdns-ui/configuration/rate-limiting/) |
| MariaDB (gmysql) backend schema init    | [MariaDB Backend](https://cyr-ius.github.io/powerdns-ui/configuration/mariadb/)                     |
| Roles, permissions & user management    | [Administration](https://cyr-ius.github.io/powerdns-ui/administration/roles-permissions/)           |
| REST API endpoints                      | [API Reference](https://cyr-ius.github.io/powerdns-ui/api/)                                         |
| Running the frontend/backend locally    | [Development](https://cyr-ius.github.io/powerdns-ui/development/)                                   |

---

## License

MIT — see [LICENSE](LICENSE) for details.

## About

Author: [@cyr-ius](https://github.com/cyr-ius) — Sponsor: [GitHub Sponsors](https://github.com/sponsors/cyr-ius)
</content>

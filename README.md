# PowerDNS UI

Web management interface for [PowerDNS Authoritative Server](https://www.powerdns.com/auth.html).

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Angular](https://img.shields.io/badge/angular-21-red)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Docker Compose](#docker-compose)
  - [Build from Source](#build-from-source)
- [PowerDNS Configuration](#powerdns-configuration)
- [Environment Variables](#environment-variables)
- [MariaDB Backend (gmysql)](#mariadb-backend-gmysql)
  - [When to run it](#when-to-run-it)
  - [Usage](#usage)
  - [Custom SQL schema](#--schema----custom-sql-file)
  - [Recommended startup order](#recommended-startup-order)
- [Catalog Zones](#catalog-zones)
  - [Producer](#producer)
  - [Consumer](#consumer)
- [Lua Records](#lua-records)
- [OIDC Authentication](#oidc-authentication)
- [Roles and Permissions](#roles-and-permissions)
- [Audit Log](#audit-log)
- [API](#api)
- [Development](#development)
  - [Prerequisites](#prerequisites)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Screenshots](#screenshots)
- [Demos](#demos)
- [License](#license)

---

## Features

- **DNS Zones** — create, edit, delete (Native / Master / Slave), record management with catalog assignment at creation
- **DNSSEC** — cryptographic key management per zone
- **Reverse DNS** — IPv4/IPv6 PTR zone creation with automatic PTR record generation
- **Lua Records** — per-zone activation of dynamic Lua records (admin/zone-admin only), automatically adds the `LUA` record type
- **Catalog Zones** — Producer zones (manual member management) and Consumer zones (automatic sync via AXFR from a Producer)
- **ACME Keys** — per-zone and per-user API keys for DNS-01 ACME challenges (Let's Encrypt / cert-manager integration)
- **TSIG Keys** — creation and management of signing keys
- **Autoprimaries** — automatic primary server configuration
- **DNS Views** _(LMDB only)_ — split-horizon, zone ↔ view association
- **Networks** _(LMDB only)_ — network assignment to views
- **Search** — global search across zones, records, and comments
- **Statistics** — real-time PowerDNS server metrics
- **Server Configuration** — active configuration visualization
- **Audit Log** — history of all user actions + PDNS logs, export to syslog
- **User Management** — admin / manager / viewer roles per account
- **OIDC SSO** — delegated authentication (Keycloak, Authentik, etc.)
- **Theme** — light / dark / automatic

## Architecture

```
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

The Angular frontend is served statically by FastAPI — a single container is sufficient.

## Quick Start

### Docker Compose

```yaml
# docker-compose.yaml
services:
  pdns:
    image: powerdns/pdns-auth-50
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
      - "--loglevel=6"
      - "--loglevel-show=yes"

  pdns-ui:
    image: ghcr.io/cyr-ius/pdns-ui:latest
    restart: unless-stopped
    depends_on: [pdns]
    environment:
      # Leave ADMIN_PASSWORD/SECRET_KEY unset to auto-generate secure values:
      # a one-time admin password is printed in the logs on first start, and a
      # random SECRET_KEY is generated and persisted under DATA_DIR.
      - PDNS_AUTH_API_URL=http://pdns:8081
      - PDNS_AUTH_API_KEY=change-this-api-key-in-production
      # Set to false to disable the Swagger UI and OpenAPI schema in production.
      - SWAGGER_ENABLED=true
    volumes:
      - powerdns-ui_data:/var/lib/powerdns-ui
    ports:
      - 8080:8080/tcp
    depends_on:
      - pdns

volumes:
  powerdns_data:
  powerdns-ui_data:

```

```bash
docker compose up -d
```

Access: http://localhost:8080 — default credentials: `admin` / `changeme`

### Build from Source

```bash
# Build with version
docker build --build-arg VERSION=1.2.0 -t powerdns-ui .

# Without version (default: 1.0.0)
docker build -t powerdns-ui .
```

## PowerDNS Configuration

Enable the REST API in `pdns.conf`:

```ini
webserver=yes
webserver-address=0.0.0.0
webserver-port=8081
webserver-allow-from=127.0.0.1,172.16.0.0/12,192.168.0.0/16
```

For **DNS Views** and **Networks** (LMDB backend only):

```ini
launch=lmdb
lmdb-filename=/var/lib/powerdns/pdns.lmdb
views=yes
```

> The _Views_ and _Networks_ menus only appear in the interface if the detected backend is `lmdb`.

## Environment Variables

| Variable                      | Default                             | Description                                                    |
| ----------------------------- | ----------------------------------- | -------------------------------------------------------------- |
| `ADMIN_USERNAME`              | `admin`                             | Super-administrator account name created at startup            |
| `ADMIN_PASSWORD`              | `changeme`                          | Initial admin password                                         |
| `SECRET_KEY`                  | _(change this)_                     | JWT signing key — **must be changed in production**            |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480`                               | Token validity duration (minutes)                              |
| `PDNS_AUTH_API_URL`           | `http://pdns:8081`                  | PowerDNS REST API URL                                          |
| `PDNS_AUTH_API_KEY`           | `change-this-api-key-in-production` | PowerDNS API key (`api-key` in pdns.conf)                      |
| `DATABASE_URL`                | `sqlite+aiosqlite:///…/database.db` | Database URL                                                   |
| `DATA_DIR`                    | `/var/lib/powerdns-ui`              | Data directory (SQLite)                                        |
| `LOG_LEVEL`                   | `INFO`                              | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                |
| `SWAGGER_ENABLED`             | `true`                              | Expose the Swagger UI (`/api/docs`) and OpenAPI schema         |
| `APP_VERSION`                 | `1.0.0`                             | Application version (injected via `--build-arg VERSION=x.y.z`) |

## MariaDB Backend (gmysql)

When PowerDNS is configured with the `gmysql` backend, the database schema must be present before the server starts. The UI container bundles the official PDNS schema and exposes a one-shot script to apply it.

### When to run it

- **First deployment** — before starting `pdns` for the first time.
- **After recreating the database volume** — the schema is lost along with the data.

> The script is idempotent: if the `domains` table already exists it exits immediately without touching anything.

### Usage

```
python init_pdns_schema.py --host HOST [options]

required:
  --host HOST          MariaDB host

optional:
  --port PORT          MariaDB port           (default: 3306)
  --user USER          MariaDB user           (default: powerdns)
  --password PASSWORD  MariaDB password       (default: pdns)
  --database DATABASE  MariaDB database       (default: powerdns)
  --schema FILE_OR_URL SQL schema to apply (see below)
```

**Via `docker compose run`** (one-shot, before or after `up`):

```bash
docker compose run --rm pdns-ui \
  python /app/backend/scripts/init_pdns_schema.py \
  --host pdns-db --password pdns
```

**Local development:**

```bash
python backend/scripts/init_pdns_schema.py \
  --host localhost --user powerdns --password pdns --database powerdns
```

### `--schema` — custom SQL file

When `--schema` is omitted the script uses the file bundled in the image (`/var/lib/powerdns/schema.sql`), then falls back to `docker/pdns_schema.sql` in the repository.

You can override it with:

| Value passed                            | Behaviour                                                                                                     |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Local path (`/tmp/my.sql`)              | Reads the file directly                                                                                       |
| Full URL (`https://…/schema.mysql.sql`) | Downloads and applies                                                                                         |
| Filename only (`schema.mysql.sql`)      | Downloads from the [PowerDNS GitHub repo](https://github.com/PowerDNS/pdns/tree/master/modules/gmysqlbackend) |

```bash
# Use a specific file from the PowerDNS GitHub repo (branch: master)
docker exec pdns-ui \
  python /app/backend/scripts/init_pdns_schema.py \
  --host pdns-db --password pdns \
  --schema schema.mysql.sql
```

### Example output

```
INFO: Connecting to MariaDB powerdns@pdns-db:3306/powerdns ...
INFO: Using bundled schema: /var/lib/powerdns/schema.sql
INFO: PDNS schema successfully created in 'powerdns'.
```

### Recommended startup order

```
pdns-db  →  init_pdns_schema  →  pdns  →  pdns-ui
```

---

## Catalog Zones

Catalog zones (RFC 9432) allow a PowerDNS server to automatically distribute zone configurations to secondary servers.

### Producer

A **Producer** catalog zone is a primary zone that lists member zones. When a zone is added to a Producer, secondary Consumer servers discover and provision it automatically.

- Create a Producer from the **Catalogs → Producer** tab
- Assign an existing zone to a Producer at creation time or from the Catalogs page
- Add / remove member zones manually from the Producer's member list

### Consumer

A **Consumer** catalog zone is a secondary zone that pulls its configuration from a Producer via AXFR. Member zones are created automatically by PowerDNS after each zone transfer — they cannot be managed manually.

- Create a Consumer from the **Catalogs → Consumer** tab
- Provide the name of the catalog (must match the Producer's zone name) and the IP address(es) of the Producer server
- The received member zones are displayed in read-only mode

---

## Lua Records

[Lua Records](https://doc.powerdns.com/authoritative/lua-records/index.html) allow dynamic DNS responses generated by Lua scripts embedded directly in zone records.

Activation is per-zone and restricted to **Super Admins** and **Zone Admins**:

1. Open a zone → **Settings** tab
2. Enable the **Lua Records** toggle
3. The `LUA` record type is automatically added to the zone's available types

> Lua Records must also be enabled at the PowerDNS server level (`enable-lua-records=yes` in `pdns.conf`).

---

## OIDC Authentication

SSO configuration (Keycloak, Authentik, …) is done entirely from the web interface: **Administration → OIDC**. No environment variables are required — settings are stored in the database.

Configurable fields: enable/disable, Client ID, Client Secret, Discovery URL, Redirect URI, scopes, disable local login.

## Roles and Permissions

| Role              | Zones       | Records      | Members            | Zone Settings (Lua Records, Record Types) |
| ----------------- | ----------- | ------------ | ------------------ | ----------------------------------------- |
| **Super Admin**   | All         | Read / Write | Full management    | ✅ All zones                              |
| **Account Admin** | Own account | Read / Write | Account management | —                                         |
| **Manager**       | Own account | Read / Write | —                  | —                                         |
| **Viewer**        | Own account | Read only    | —                  | —                                         |
| **Zone Admin**    | Own zone    | Read / Write | Zone management    | ✅ Own zone                               |

Users are grouped by **accounts**. Each account is associated with zones and users with their role.

> **Zone Admin** is a per-zone role assignable from the zone's _Members_ tab. It grants full control over that zone's settings, including enabling Lua Records and customizing available record types.

## Audit Log

All actions are tracked: logins, zone/record modifications, user management, configuration changes.

**Syslog Export**: configurable from the _Audit Log_ page (_Syslog: active/inactive_ button) — host, port, UDP/TCP protocol, facility.

## API

Interactive documentation is available on the running instance:

- Swagger UI: http://localhost:8080/api/docs

## Development

### Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Node.js 22+

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run start   # proxy to localhost:8080
```

## Screenshots

<img width="1151" height="680" alt="image" src="https://github.com/user-attachments/assets/542b271b-f806-4be9-9ebf-58d04e4d0676" />
<img width="1151" height="680" alt="image" src="https://github.com/user-attachments/assets/4a17d385-c4cc-4772-923f-4a7a696cbc81" />
<img width="1151" height="680" alt="image" src="https://github.com/user-attachments/assets/e3718deb-2b8b-47ea-9515-dcaeab94e6ed" />
<img width="1151" height="680" alt="image" src="https://github.com/user-attachments/assets/36df2912-52e6-4890-8d6b-e2322583b774" />

## Demos

<img width="640" height="480" alt="Capture vidéo du 2026-04-27 12-31-15(1)" src="https://github.com/user-attachments/assets/4a5eb088-0441-42ab-a926-8d22ec835112" />

## License

MIT — see [LICENSE](LICENSE)

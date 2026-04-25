# PowerDNS UI

Web management interface for [PowerDNS Authoritative Server](https://www.powerdns.com/auth.html).

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Angular](https://img.shields.io/badge/angular-21-red)

## Features

- **DNS Zones** — create, edit, delete (Native / Master / Slave), record management
- **DNSSEC** — cryptographic key management per zone
- **Reverse DNS** — IPv4/IPv6 PTR zone creation with automatic PTR record generation
- **Catalogs** — PDNS catalog zone management
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
│          Browser (Angular 21)       │
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
    environment:
      - PDNS_AUTH_API_KEY=change-this-api-key-in-production
    volumes:
      - powerdns_data:/var/lib/powerdns
      - ./pdns.conf:/etc/powerdns/pdns.d/pdns.conf
    ports:
      - 53:53
      - 53:53/udp

  pdns-ui:
    image: ghcr.io/cyr-ius/pdns-ui:latest
    restart: unless-stopped
    depends_on: [pdns]
    environment:
      - ADMIN_PASSWORD=changeme
      - SECRET_KEY=change-this-secret-key-in-production
      - PDNS_AUTH_API_URL=http://pdns:8081
      - PDNS_AUTH_API_KEY=change-this-api-key-in-production
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

## OIDC Authentication

SSO configuration (Keycloak, Authentik, …) is done entirely from the web interface: **Administration → OIDC**. No environment variables are required — settings are stored in the database.

Configurable fields: enable/disable, Client ID, Client Secret, Discovery URL, Redirect URI, scopes, disable local login.

## Roles and Permissions

| Role              | Zones       | Records      | Members            |
| ----------------- | ----------- | ------------ | ------------------ |
| **Super Admin**   | All         | Read / Write | Full management    |
| **Account Admin** | Own account | Read / Write | Account management |
| **Manager**       | Own account | Read / Write | —                  |
| **Viewer**        | Own account | Read only    | —                  |

Users are grouped by **accounts**. Each account is associated with zones and users with their role.

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

## License

MIT — see [LICENSE](LICENSE)

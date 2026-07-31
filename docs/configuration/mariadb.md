# MariaDB Backend (gmysql)

When PowerDNS is configured with the `gmysql` backend, the database schema must be present **before** the server starts. The PowerDNS UI container bundles the official PDNS schema and exposes a one-shot script to apply it.

## When to run it

- **First deployment** — before starting `pdns` for the first time.
- **After recreating the database volume** — the schema is lost along with the data.

!!! info "Idempotent"
    The script is idempotent: if the `domains` table already exists it exits immediately without touching anything. It is safe to run it again, e.g. as a startup init-container.

## Usage

```text
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

### Via `docker compose run` (one-shot, before or after `up`)

```bash
docker compose run --rm pdns-ui \
  python /app/backend/scripts/init_pdns_schema.py \
  --host pdns-db --password pdns
```

### Local development

```bash
python backend/scripts/init_pdns_schema.py \
  --host localhost --user powerdns --password pdns --database powerdns
```

## `--schema` — custom SQL file

When `--schema` is omitted, the script uses the file bundled in the image (`/var/lib/powerdns/schema.sql`), then falls back to `docker/pdns_schema.sql` in the repository.

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

```text
INFO: Connecting to MariaDB powerdns@pdns-db:3306/powerdns ...
INFO: Using bundled schema: /var/lib/powerdns/schema.sql
INFO: PDNS schema successfully created in 'powerdns'.
```

## Recommended startup order

```text
pdns-db  →  init_pdns_schema  →  pdns  →  pdns-ui
```

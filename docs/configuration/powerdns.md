# PowerDNS Configuration

PowerDNS UI is a client of the PowerDNS Authoritative REST API — it never accesses the PowerDNS database directly. The API must be enabled and reachable from the PowerDNS UI container.

## Enable the REST API

In `pdns.conf`:

```ini
webserver=yes
webserver-address=0.0.0.0
webserver-port=8081
webserver-allow-from=127.0.0.1,172.16.0.0/12,192.168.0.0/16
api=yes
api-key=change-this-api-key-in-production
```

`webserver-allow-from` must include the network PowerDNS UI runs on (e.g. the Docker Compose bridge network). Point PowerDNS UI at this endpoint with [`PDNS_AUTH_API_URL` and `PDNS_AUTH_API_KEY`](environment-variables.md).

## DNS Views and Networks (LMDB backend only)

[DNS Views](../features/views-networks.md) and [Networks](../features/views-networks.md) are an LMDB-specific PowerDNS feature (split-horizon DNS). To use them, PowerDNS must run with the `lmdb` backend and views enabled:

```ini
launch=lmdb
lmdb-filename=/var/lib/powerdns/pdns.lmdb
views=yes
```

!!! note
    The **Views** and **Networks** menus only appear in the PowerDNS UI interface if the detected backend is `lmdb`. With any other backend (e.g. `gmysql`), these menus are hidden automatically.

## Lua Records

To allow [Lua Records](../features/lua-records.md) to be activated from PowerDNS UI, enable them at the server level too:

```ini
enable-lua-records=yes
# PowerDNS >= 5.1: required to allow writes to LUA records via the API, AXFR/IXFR or DNS Update
enable-lua-record-updates=yes
```

Without `enable-lua-record-updates=yes`, resolution of existing Lua records keeps working, but PowerDNS UI (and any other client) will not be able to write new ones.

## gmysql backend

If PowerDNS is configured with the `gmysql` backend, the database schema must exist before PowerDNS starts. PowerDNS UI bundles a helper script for this — see [MariaDB Backend (gmysql)](mariadb.md).

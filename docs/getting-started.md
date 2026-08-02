# Getting Started

The fastest way to run PowerDNS UI is Docker Compose, alongside a PowerDNS Authoritative Server container.

## Docker Compose

```yaml title="docker-compose.yaml"
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
      - "--loglevel=6"
      - "--loglevel-show=yes"
      - "--logging-structured=yes"

  pdns-ui:
    image: ghcr.io/cyr-ius/pdns-ui:latest
    restart: unless-stopped
    depends_on: [pdns]
    environment:
      # The admin password is always auto-generated: a one-time password is
      # printed in the logs on first start. Leave SECRET_KEY unset to
      # auto-generate and persist a random key under DATA_DIR.
      - PDNS_AUTH_API_URL=http://pdns:8081
      - PDNS_AUTH_API_KEY=change-this-api-key-in-production
      # Set to false to disable the Swagger UI and OpenAPI schema in production.
      - SWAGGER_ENABLED=true
    volumes:
      - powerdns-ui_data:/var/lib/powerdns-ui
    ports:
      - 8080:8080/tcp

volumes:
  powerdns_data:
  powerdns-ui_data:
```

```bash
docker compose up -d
```

Then open **http://localhost:8080**.

!!! tip "First login"
    Log in as `admin` using the one-time password printed in the `pdns-ui` container logs on first start (`docker compose logs pdns-ui`), then change it immediately from the profile page.

## Build from Source

If you'd rather build the image yourself instead of pulling `ghcr.io/cyr-ius/pdns-ui`:

```bash
# Build with an explicit version
docker build --build-arg VERSION=1.2.0 -t powerdns-ui .

# Without a version (defaults to 1.0.0)
docker build -t powerdns-ui .
```

## Next steps

- Make sure the PowerDNS REST API is reachable and correctly configured — see [PowerDNS Configuration](configuration/powerdns.md).
- Review the available [Environment Variables](configuration/environment-variables.md) to tune authentication, rate limiting and connectors.
- If PowerDNS uses the `gmysql` backend, initialize the schema first — see [MariaDB Backend](configuration/mariadb.md).
- Running PowerDNS UI behind a reverse proxy? Check [Rate Limiting & Reverse Proxy](configuration/rate-limiting.md) for the `TRUSTED_PROXIES` setting.

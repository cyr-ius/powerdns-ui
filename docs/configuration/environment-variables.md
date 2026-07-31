# Environment Variables

## Core

| Variable                          | Default                             | Description                                                                                                                |
| --------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `ADMIN_USERNAME`                  | `admin`                             | Super-administrator account name created at startup                                                                        |
| `SECRET_KEY`                      | _(empty)_                           | JWT signing key — when unset, a random key is generated and persisted under `DATA_DIR`                                     |
| `ACCESS_TOKEN_EXPIRE_MINUTES`     | `480`                               | Token validity duration (minutes)                                                                                          |
| `PDNS_AUTH_API_URL`               | `http://pdns:8081`                  | PowerDNS REST API URL                                                                                                      |
| `PDNS_AUTH_API_KEY`               | `change-this-api-key-in-production` | PowerDNS API key (`api-key` in pdns.conf)                                                                                  |
| `DATABASE_URL`                    | `sqlite+aiosqlite:///…/database.db` | Database URL                                                                                                               |
| `DATA_DIR`                        | `/var/lib/powerdns-ui`              | Data directory (SQLite)                                                                                                    |
| `LOG_LEVEL`                       | `INFO`                              | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                                                                            |
| `SWAGGER_ENABLED`                 | `true`                              | Expose the Swagger UI (`/api/docs`) and OpenAPI schema                                                                     |
| `API_KEYS_ENABLED`                | `true`                              | Allow personal access tokens; when `false` the API refuses them and the UI hides their management                          |
| `APP_VERSION`                     | `1.0.0`                             | Application version (injected via `--build-arg VERSION=x.y.z`)                                                             |
| `TRUSTED_PROXIES`                 | _(empty)_                           | Comma-separated proxy IPs/CIDRs whose `X-Forwarded-For` is trusted — see [Rate Limiting & Reverse Proxy](rate-limiting.md) |
| `RATE_LIMIT_ENABLED`              | `true`                              | Enable the in-memory per-IP rate limiter on `/api/*` routes                                                                |
| `RATE_LIMIT_MAX_REQUESTS`         | `300`                               | Max requests per IP within the global window                                                                               |
| `RATE_LIMIT_WINDOW_SECONDS`       | `60`                                | Global sliding-window duration (seconds)                                                                                   |
| `RATE_LIMIT_LOGIN_MAX_ATTEMPTS`   | `10`                                | Max login attempts per IP within the login window                                                                          |
| `RATE_LIMIT_LOGIN_WINDOW_SECONDS` | `300`                               | Login sliding-window duration (seconds)                                                                                    |
| `RATE_LIMIT_LOGIN_PATH`           | `/api/auth/login`                   | Path the stricter login budget applies to                                                                                  |

## OIDC & Mail connectors

Both connectors can be configured entirely from the settings screens and are stored in the database — no environment variable is strictly required. Any variable below **overrides** the stored value and is shown read-only in the interface, so all or part of the configuration can be pinned from the deployment manifest (e.g. to keep a client secret out of the database, or to enforce SSO in an immutable infrastructure setup).

| Variable                        | Default                | Description                                                                   |
| ------------------------------- | ---------------------- | ----------------------------------------------------------------------------- |
| `OIDC_ENABLED`                  | `false`                | Enable OIDC single sign-on                                                    |
| `OIDC_CLIENT_ID`                | _(empty)_              | OIDC client identifier                                                        |
| `OIDC_CLIENT_SECRET`            | _(empty)_              | OIDC client secret                                                            |
| `OIDC_DISCOVERY_URL`            | _(empty)_              | Provider discovery document (`…/.well-known/openid-configuration`)            |
| `OIDC_REDIRECT_URI`             | _(empty)_              | Callback URL (`https://<host>/api/auth/oidc/callback`)                        |
| `OIDC_SCOPES`                   | `openid email profile` | Requested scopes                                                              |
| `OIDC_LOCAL_LOGIN_DISABLED`     | `false`                | Refuse local accounts; sign-in through OIDC only                              |
| `OIDC_LOGOUT_ENABLED`           | `false`                | RP-initiated logout: also end the session at the provider on sign-out         |
| `OIDC_POST_LOGOUT_REDIRECT_URI` | _(empty)_              | Page the provider redirects to after logout (e.g. `https://<host>/login`)     |
| `SMTP_ENABLED`                  | `false`                | Enable e-mail notifications                                                   |
| `SMTP_HOST`                     | `localhost`            | SMTP relay host                                                               |
| `SMTP_PORT`                     | `587`                  | SMTP relay port                                                               |
| `SMTP_USERNAME`                 | _(empty)_              | SMTP username (empty = no authentication)                                     |
| `SMTP_PASSWORD`                 | _(empty)_              | SMTP password                                                                 |
| `SMTP_FROM_EMAIL`               | _(empty)_              | Sender address                                                                |
| `SMTP_RECIPIENT_EMAIL`          | _(empty)_              | Recipient of the notifications                                                |
| `SMTP_USE_TLS`                  | `false`                | Implicit TLS (SMTPS, usually port 465)                                        |
| `SMTP_USE_STARTTLS`             | `true`                 | STARTTLS upgrade (usually port 587)                                           |
| `SMTP_ALERT_ACTIONS`            | _(empty)_              | Comma-separated actions to alert on, e.g. `login,logout,delete` (empty = all) |
| `SMTP_ALERT_RESOURCES`          | _(empty)_              | Comma-separated resource types to alert on (empty = all)                      |
| `SMTP_ALERT_STATUSES`           | _(empty)_              | Comma-separated statuses to alert on, e.g. `failure` (empty = all)            |

See [OIDC & Mail Connectors](oidc-mail.md) for behaviour details and safety guarantees.

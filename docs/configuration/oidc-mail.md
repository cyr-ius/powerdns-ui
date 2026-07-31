# OIDC & Mail Connectors

## OIDC single sign-on

SSO configuration (Keycloak, Authentik, and any OpenID Connect–compliant provider) is done entirely from the web interface: **Administration → OIDC**. No environment variables are required — settings are stored in the database, and can optionally be overridden/pinned via the [environment variables](environment-variables.md#oidc-mail-connectors) documented above.

Configurable fields: enable/disable, Client ID, Client Secret, Discovery URL, Redirect URI, scopes, disable local login, RP-initiated logout. See the full list of overridable variables in [Environment Variables](environment-variables.md#oidc-mail-connectors).

### Safety guarantees

- **`OIDC_LOCAL_LOGIN_DISABLED`** is only honoured while at least one **active OIDC administrator** exists — the application refuses any change that would lock everyone out of the interface.
- An OIDC identity can **never take over an existing local account** — accounts are matched explicitly, not silently merged by e-mail or username.
- **`OIDC_LOGOUT_ENABLED`** requires the provider to advertise an `end_session_endpoint` in its discovery document. The `id_token` received at sign-in is kept in an HttpOnly cookie and replayed as `id_token_hint` on logout. `OIDC_POST_LOGOUT_REDIRECT_URI` must be registered with the provider as an allowed post-logout redirect URI.

## Mail (SMTP) connector

Configured from **Administration → Mail**, used to send audit alert notifications by e-mail (login failures, deletions, etc. — filterable via `SMTP_ALERT_*`).

The Mail settings screen offers a **Send a test e-mail** button that probes the relay with the settings as currently displayed on screen, without saving them first — useful to validate credentials and TLS mode before committing a configuration change.

Choose exactly one of:

- `SMTP_USE_TLS=true` for implicit TLS (SMTPS, typically port 465).
- `SMTP_USE_STARTTLS=true` for a STARTTLS upgrade over a plaintext connection (typically port 587, the default).

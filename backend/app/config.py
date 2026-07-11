import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_DIR", "/var/lib/powerdns-ui")
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/database.db"
GITHUB_REPOSITORY = "cyr-ius/powerdns-ui"

# Placeholder values shipped in the repository. They are public and therefore
# MUST never be used as live credentials/keys: each one is treated as "unset"
# and replaced by a securely generated value at runtime.
DEFAULT_SECRET_KEY = "change-this-secret-key-in-production"  # noqa: S105
_SECRET_KEY_FILE = Path(DATA_DIR) / ".secret_key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    app_name: str = "PowerDNS UI"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Name of the HttpOnly cookie carrying the JWT for browser sessions. The
    # token is never exposed to JavaScript, which neutralises XSS token theft.
    auth_cookie_name: str = "pdns_token"

    admin_username: str = "admin"

    database_url: str = DEFAULT_DATABASE_URL

    pdns_auth_api_url: str = "http://pdns:8081"
    pdns_auth_api_key: str = "change-this-api-key-in-production"  # noqa: S105

    swagger_enabled: bool = True

    # When disabled, personal access tokens are refused by the API and the
    # frontend hides the whole key-management surface.
    api_keys_enabled: bool = True

    # OIDC / SMTP connectors are configured from the settings screens and stored
    # in the database. Any field supplied here (environment or .env) overrides
    # the stored value and is exposed as read-only in the UI, so an operator can
    # pin all or part of the configuration from the deployment manifest.
    oidc_enabled: bool = False
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_discovery_url: str = ""
    oidc_redirect_uri: str = ""
    oidc_scopes: str = "openid email profile"
    oidc_local_login_disabled: bool = False

    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_recipient_email: str = ""
    smtp_use_tls: bool = False
    smtp_use_starttls: bool = True
    # Comma-separated filters, e.g. SMTP_ALERT_ACTIONS="login,logout,delete".
    smtp_alert_actions: str = ""
    smtp_alert_resources: str = ""
    smtp_alert_statuses: str = ""

    # Reverse proxy: comma-separated trusted proxy IPs/CIDRs (e.g.
    # "10.0.0.0/8,172.16.0.0/12"). X-Forwarded-For is honoured only when the
    # direct peer matches one of these; otherwise it is ignored to prevent
    # client IP spoofing. Leave empty when not behind a proxy.
    trusted_proxies: str = ""

    # Global in-memory rate limiting (per-process; front with a shared store
    # such as Redis for multi-worker / multi-instance deployments). A stricter
    # window is applied to the login endpoint to slow credential brute-forcing.
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = 300
    rate_limit_window_seconds: int = 60
    rate_limit_login_max_attempts: int = 10
    rate_limit_login_window_seconds: int = 300
    rate_limit_login_path: str = "/api/auth/login"


def _resolve_secret_key(value: str) -> str:
    """Return a strong JWT signing key, never the public default.

    If ``SECRET_KEY`` was supplied (env/.env) we trust it. Otherwise we generate
    a random key once and persist it under ``DATA_DIR`` so that already-issued
    tokens survive restarts — we never fall back to the placeholder shipped in
    the repository, which an attacker could use to forge admin tokens.
    """
    if value and value != DEFAULT_SECRET_KEY:
        return value
    try:
        if _SECRET_KEY_FILE.is_file():
            existing = _SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
            if existing:
                return existing
    except OSError:
        pass
    generated = secrets.token_urlsafe(64)
    try:
        _SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SECRET_KEY_FILE.write_text(generated, encoding="utf-8")
        os.chmod(_SECRET_KEY_FILE, 0o600)
        logger.warning(
            "SECRET_KEY not configured — generated a random signing key and "
            "persisted it to %s. Set SECRET_KEY explicitly for multi-instance "
            "deployments.",
            _SECRET_KEY_FILE,
        )
    except OSError:
        logger.warning(
            "SECRET_KEY not configured and a generated key could not be "
            "persisted to %s — using an ephemeral key (tokens will be "
            "invalidated on restart).",
            _SECRET_KEY_FILE,
        )
    return generated


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.secret_key = _resolve_secret_key(s.secret_key)
    return s


settings = get_settings()


def env_overrides(prefix: str) -> dict[str, object]:
    """Return the ``prefix``-scoped settings explicitly supplied by the operator.

    ``model_fields_set`` only holds fields fed by the environment or ``.env``,
    never the class defaults — so an untouched connector yields ``{}`` and keeps
    its database-backed configuration. Keys are returned without the prefix, i.e.
    ready to be applied onto the matching ``OidcSettings``/``SmtpSettings`` row.
    """
    return {
        name[len(prefix) :]: getattr(settings, name)
        for name in settings.model_fields_set
        if name.startswith(prefix)
    }

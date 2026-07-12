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
SECRET_KEY_FILE = Path(DATA_DIR) / ".secret_key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    access_token_expire_minutes: int = 480
    admin_username: str = "admin"
    algorithm: str = "HS256"
    api_keys_enabled: bool = True
    app_name: str = "PowerDNS UI"
    app_version: str = "Development"
    auth_cookie_name: str = "pdns_token"
    # Cookie carrying the OIDC id_token, replayed as id_token_hint on logout.
    # Not named with the `oidc_` prefix: that namespace is reserved for the
    # connector fields mirrored onto the OidcSettings row (see env_overrides).
    id_token_cookie_name: str = "pdns_id_token"
    database_url: str = DEFAULT_DATABASE_URL
    log_level: str = "INFO"
    pdns_auth_api_key: str = "change-this-api-key-in-production"  # noqa: S105
    pdns_auth_api_url: str = "http://pdns:8081"
    secret_key: str = ""
    swagger_enabled: bool = False

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
    # RP-initiated logout: when enabled the browser is sent to the provider's
    # end_session_endpoint so the SSO session is terminated too, not just ours.
    oidc_logout_enabled: bool = False
    oidc_post_logout_redirect_uri: str = ""

    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_recipient_email: str = ""
    smtp_use_tls: bool = False
    smtp_use_starttls: bool = True
    smtp_alert_actions: str = ""  # Comma-separated filters, e.g. "login,logout,delete".
    smtp_alert_resources: str = ""
    smtp_alert_statuses: str = ""

    # Reverse proxy: comma-separated trusted proxy IPs/CIDRs (e.g.
    # "10.0.0.0/8,172.16.0.0/12"). X-Forwarded-For is honoured only when the
    # direct peer matches one of these; otherwise it is ignored to prevent
    # client IP spoofing. Leave empty when not behind a proxy.
    trusted_proxies: str = ""
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = 300
    rate_limit_window_seconds: int = 60
    rate_limit_login_max_attempts: int = 10
    rate_limit_login_window_seconds: int = 300
    rate_limit_login_path: str = "/api/auth/login"


def _resolve_secret_key(value: str) -> str:
    """Return a strong JWT signing key.

    If ``SECRET_KEY`` was supplied (env/.env) we trust it. Otherwise we generate
    a random key once and persist it under ``DATA_DIR`` so that already-issued
    tokens survive restarts.
    """
    if value:
        return value
    try:
        if SECRET_KEY_FILE.is_file():
            existing = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
            if existing:
                return existing
    except OSError:
        pass
    generated = secrets.token_urlsafe(64)
    try:
        SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        SECRET_KEY_FILE.write_text(generated, encoding="utf-8")
        os.chmod(SECRET_KEY_FILE, 0o600)
        logger.warning(
            "SECRET_KEY not configured — generated a random signing key and "
            "persisted it to %s. Set SECRET_KEY explicitly for multi-instance "
            "deployments.",
            SECRET_KEY_FILE,
        )
    except OSError:
        logger.warning(
            "SECRET_KEY not configured and a generated key could not be "
            "persisted to %s — using an ephemeral key (tokens will be "
            "invalidated on restart).",
            SECRET_KEY_FILE,
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

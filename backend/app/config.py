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

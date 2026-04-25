import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = os.getenv("DATA_DIR", "/var/lib/powerdns-ui")
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/database.db"
GITHUB_REPOSITORY = "cyr-ius/powerdns-ui"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    app_name: str = "PowerDNS UI"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    admin_username: str = "admin"
    admin_password: str = "changeme"

    database_url: str = DEFAULT_DATABASE_URL

    pdns_auth_api_url: str = "http://pdns:8081"
    pdns_auth_api_key: str = "change-this-api-key-in-production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

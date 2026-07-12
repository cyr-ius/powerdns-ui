import json
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Import all models so SQLModel.metadata is complete before create_all
from app.models import (  # noqa: F401, E402
    account,
    acme_key,
    audit_log,
    oidc_settings,
    record_type,
    smtp_settings,
    syslog_settings,
    token,
    user,
    zone_record_type,
)

DEFAULT_RECORD_TYPES = [
    ("A", True, "direct"),
    ("AAAA", True, "direct"),
    ("CAA", True, "direct"),
    ("CNAME", True, "direct"),
    ("DNAME", True, "both"),
    ("LOC", True, "both"),
    ("MX", True, "direct"),
    ("NS", True, "both"),
    ("PTR", True, "both"),
    ("SOA", True, "both"),
    ("SPF", True, "direct"),
    ("SRV", True, "direct"),
    ("TXT", True, "both"),
]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda conn: SQLModel.metadata.create_all(conn, checkfirst=True)
        )
        # SQLite schema migration: add columns added after initial schema
        result = await conn.execute(text("PRAGMA table_info(user)"))
        columns = {row[1] for row in result.fetchall()}
        if "is_admin" not in columns:
            await conn.execute(
                text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
            )
        result = await conn.execute(text("PRAGMA table_info(oidcsettings)"))
        oidc_columns = {row[1] for row in result.fetchall()}
        if "local_login_disabled" not in oidc_columns:
            await conn.execute(
                text(
                    "ALTER TABLE oidcsettings ADD COLUMN local_login_disabled BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        if "post_logout_redirect_uri" not in oidc_columns:
            await conn.execute(
                text(
                    "ALTER TABLE oidcsettings ADD COLUMN post_logout_redirect_uri VARCHAR NOT NULL DEFAULT ''"
                )
            )
        result = await conn.execute(text("PRAGMA table_info(useraccount)"))
        ua_columns = {row[1] for row in result.fetchall()}
        if "role" not in ua_columns:
            await conn.execute(
                text(
                    "ALTER TABLE useraccount ADD COLUMN role VARCHAR NOT NULL DEFAULT 'admin'"
                )
            )
        result = await conn.execute(text("PRAGMA table_info(acmeapikey)"))
        acme_columns = {row[1] for row in result.fetchall()}
        if "key_type" not in acme_columns:
            await conn.execute(
                text(
                    "ALTER TABLE acmeapikey ADD COLUMN key_type VARCHAR(10) NOT NULL DEFAULT 'acme'"
                )
            )
        if "comment" not in acme_columns:
            await conn.execute(text("ALTER TABLE acmeapikey ADD COLUMN comment TEXT"))
        if "zone_name" not in acme_columns:
            await conn.execute(
                text("ALTER TABLE acmeapikey ADD COLUMN zone_name VARCHAR(255)")
            )
            # Migrate existing ACME keys: zone_name = first zone from the zones list
            rows = (
                await conn.execute(
                    text("SELECT id, zones FROM acmeapikey WHERE key_type = 'acme'")
                )
            ).fetchall()
            for key_id, zones_json in rows:
                try:
                    zones = json.loads(zones_json) if zones_json else []
                except Exception:
                    zones = []
                if zones:
                    zone = zones[0].rstrip(".") + "."
                    await conn.execute(
                        text("UPDATE acmeapikey SET zone_name = :zone WHERE id = :id"),
                        {"zone": zone, "id": key_id},
                    )
        # Make acmeapikey.user_id nullable so ACME keys survive the deletion of
        # their creator (authorization is carried by the zone, not the user).
        # SQLite cannot ALTER a column's nullability, so rebuild the table.
        acme_info = (
            await conn.execute(text("PRAGMA table_info(acmeapikey)"))
        ).fetchall()
        user_id_notnull = any(row[1] == "user_id" and row[3] == 1 for row in acme_info)
        if user_id_notnull:
            await conn.execute(text("ALTER TABLE acmeapikey RENAME TO acmeapikey_old"))
            await conn.execute(
                text(
                    """
                    CREATE TABLE acmeapikey (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        zone_name VARCHAR(255),
                        name VARCHAR(100) NOT NULL,
                        key_prefix VARCHAR(12) NOT NULL,
                        key_hash VARCHAR NOT NULL,
                        zones VARCHAR NOT NULL DEFAULT '[]',
                        key_type VARCHAR(10) NOT NULL DEFAULT 'acme',
                        comment TEXT,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES user (id)
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO acmeapikey (id, user_id, zone_name, name, "
                    "key_prefix, key_hash, zones, key_type, comment, created_at) "
                    "SELECT id, user_id, zone_name, name, key_prefix, key_hash, "
                    "zones, key_type, comment, created_at FROM acmeapikey_old"
                )
            )
            await conn.execute(text("DROP TABLE acmeapikey_old"))
            await conn.execute(
                text("CREATE INDEX ix_acmeapikey_user_id ON acmeapikey (user_id)")
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX ix_acmeapikey_key_hash "
                    "ON acmeapikey (key_hash)"
                )
            )

        # Personal access tokens used to live in acmeapikey (key_type='api').
        # Move any such row into the dedicated personalaccesstoken table so
        # existing tokens keep working, then drop them from acmeapikey.
        legacy_pat_rows = (
            await conn.execute(
                text(
                    "SELECT id, user_id, name, key_prefix, key_hash, comment, "
                    "created_at FROM acmeapikey WHERE key_type = 'api' "
                    "AND user_id IS NOT NULL"
                )
            )
        ).fetchall()
        for (
            row_id,
            user_id,
            name,
            key_prefix,
            key_hash,
            comment,
            created_at,
        ) in legacy_pat_rows:
            await conn.execute(
                text(
                    "INSERT INTO personalaccesstoken (user_id, name, token_prefix, "
                    "token_hash, comment, created_at) VALUES (:user_id, :name, "
                    ":token_prefix, :token_hash, :comment, :created_at)"
                ),
                {
                    "user_id": user_id,
                    "name": name,
                    "token_prefix": key_prefix,
                    "token_hash": key_hash,
                    "comment": comment,
                    "created_at": created_at,
                },
            )
        if legacy_pat_rows:
            await conn.execute(text("DELETE FROM acmeapikey WHERE key_type = 'api'"))

        result = await conn.execute(text("PRAGMA table_info(smtpsettings)"))
        smtp_columns = {row[1] for row in result.fetchall()}
        if "alert_actions" not in smtp_columns:
            await conn.execute(
                text(
                    "ALTER TABLE smtpsettings ADD COLUMN alert_actions VARCHAR NOT NULL DEFAULT ''"
                )
            )
        if "alert_resources" not in smtp_columns:
            await conn.execute(
                text(
                    "ALTER TABLE smtpsettings ADD COLUMN alert_resources VARCHAR NOT NULL DEFAULT ''"
                )
            )
        if "alert_statuses" not in smtp_columns:
            await conn.execute(
                text(
                    "ALTER TABLE smtpsettings ADD COLUMN alert_statuses VARCHAR NOT NULL DEFAULT ''"
                )
            )
        # Seed default record types if the table is empty
        result = await conn.execute(text("SELECT COUNT(*) FROM recordtype"))
        if result.scalar() == 0:
            for name, enabled, applicable_to in DEFAULT_RECORD_TYPES:
                await conn.execute(
                    text(
                        "INSERT INTO recordtype (name, enabled, applicable_to) VALUES (:name, :enabled, :applicable_to)"
                    ),
                    {
                        "name": name,
                        "enabled": int(enabled),
                        "applicable_to": applicable_to,
                    },
                )


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

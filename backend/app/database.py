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
            # Migrer les clés ACME existantes : zone_name = première zone de la liste zones
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

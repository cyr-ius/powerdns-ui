from collections.abc import AsyncGenerator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Import all models so SQLModel.metadata is complete (Alembic autogenerate)
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
from app.models.record_type import RecordType  # noqa: E402

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


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _run_migrations(connection: Connection) -> None:
    """Bring the schema to the latest Alembic revision on the given connection."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.attributes["connection"] = connection
    command.upgrade(config, "head")


async def init_db() -> None:
    """Migrate the schema and seed the default record types."""
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)
    async with async_session() as session:
        if (await session.exec(select(RecordType))).first() is None:
            session.add_all(
                RecordType(name=name, enabled=enabled, applicable_to=applicable_to)
                for name, enabled, applicable_to in DEFAULT_RECORD_TYPES
            )
            await session.commit()


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

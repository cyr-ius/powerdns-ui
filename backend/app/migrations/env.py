"""Alembic environment of the PowerDNS UI database.

The application runs the migrations at startup (``app.database.init_db``) and
hands its own connection over through ``config.attributes["connection"]``. The
``alembic`` command line (run from the repository root) has no connection and
opens one from ``DATABASE_URL``.
"""

import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

import app.database  # noqa: F401  # imports every model onto SQLModel.metadata
from app.config import settings

target_metadata = SQLModel.metadata


def _run(connection: Connection) -> None:
    """Run the pending migrations on an open connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite cannot ALTER most column properties: recreate the table instead.
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_from_url() -> None:
    """Open a connection from DATABASE_URL and run the migrations on it."""
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_run)
    finally:
        await engine.dispose()


def run_migrations_offline() -> None:
    """Print the SQL of the migrations instead of running them."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
elif (connection := context.config.attributes.get("connection")) is not None:
    _run(connection)
else:
    asyncio.run(_run_from_url())

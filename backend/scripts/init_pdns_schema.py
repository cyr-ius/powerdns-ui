#!/usr/bin/env python3
"""
Initialize PowerDNS MariaDB schema.

Checks whether the PDNS schema (table 'domains') exists in the target database.
If not, fetches the SQL schema and applies it.

Usage:
    python /app/backend/scripts/init_pdns_schema.py --host pdns-db --password pdns
    docker exec <container> python /app/backend/scripts/init_pdns_schema.py --host pdns-db

    # Custom schema — local file:
    ... --schema /path/to/schema.mysql.sql

    # Custom schema — filename from PowerDNS GitHub (branch: master):
    ... --schema schema.mysql.sql

    # Custom schema — explicit URL:
    ... --schema https://raw.githubusercontent.com/.../schema.mysql.sql
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_PDNS_GITHUB_BASE = (
    "https://raw.githubusercontent.com/PowerDNS/pdns/refs/heads/master"
    "/modules/gmysqlbackend/"
)

# Default local candidates when --schema is not provided.
_DEFAULT_SCHEMA_CANDIDATES = [
    Path("/var/lib/powerdns/schema.sql"),
    Path(__file__).resolve().parents[3] / "docker" / "pdns_schema.sql",
]


def _parse_sql_statements(sql: str) -> list[str]:
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return [s.strip() for s in sql.split(";") if s.strip()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize the PowerDNS MariaDB schema."
    )
    parser.add_argument("--host", required=True, help="MariaDB host")
    parser.add_argument(
        "--port", type=int, default=3306, help="MariaDB port (default: 3306)"
    )
    parser.add_argument(
        "--user", default="powerdns", help="MariaDB user (default: powerdns)"
    )
    parser.add_argument(
        "--password", default="pdns", help="MariaDB password (default: pdns)"
    )
    parser.add_argument(
        "--database", default="powerdns", help="MariaDB database (default: powerdns)"
    )
    parser.add_argument(
        "--schema",
        default=None,
        metavar="FILE_OR_URL",
        help=(
            "SQL schema to apply. Accepts: "
            "a local file path, "
            "a full URL, "
            "or a filename from the PowerDNS GitHub repo "
            f"(e.g. 'schema.mysql.sql' → {_PDNS_GITHUB_BASE}schema.mysql.sql)"
        ),
    )
    return parser.parse_args()


async def _fetch_schema(source: str | None) -> str:
    """Return SQL content from a local file, a URL, or the default candidates."""
    import httpx

    if source is not None:
        # Explicit URL
        if source.startswith("http://") or source.startswith("https://"):
            url = source
            logger.info("Downloading schema from %s ...", url)
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
            return resp.text

        # Local file path
        path = Path(source)
        if path.is_file():
            logger.info("Reading schema from %s ...", path)
            return path.read_text()

        # Filename from PowerDNS GitHub
        url = _PDNS_GITHUB_BASE + source
        logger.info("Local file '%s' not found — downloading from %s ...", source, url)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
        return resp.text

    # No --schema given: try default local candidates
    for candidate in _DEFAULT_SCHEMA_CANDIDATES:
        if candidate.is_file():
            logger.info("Using bundled schema: %s", candidate)
            return candidate.read_text()

    logger.error(
        "No schema file found. Use --schema to specify one. Paths tried: %s",
        _DEFAULT_SCHEMA_CANDIDATES,
    )
    sys.exit(1)


async def run(args: argparse.Namespace) -> None:
    import aiomysql

    logger.info(
        "Connecting to MariaDB %s@%s:%d/%s ...",
        args.user,
        args.host,
        args.port,
        args.database,
    )
    try:
        conn = await aiomysql.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            db=args.database,
        )
    except Exception as exc:
        logger.error("Connection failed: %s", exc)
        sys.exit(1)

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = 'domains'",
                (args.database,),
            )
            row = await cur.fetchone()
            if row and row[0] > 0:
                logger.info(
                    "PDNS schema already present in '%s' — nothing to do.",
                    args.database,
                )
                return

            sql = await _fetch_schema(args.schema)
            for statement in _parse_sql_statements(sql):
                await cur.execute(statement)
            await conn.commit()
            logger.info("PDNS schema successfully created in '%s'.", args.database)
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(run(_parse_args()))

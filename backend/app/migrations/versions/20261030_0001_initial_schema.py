"""initial schema

Creates the schema on an empty database. A database created before Alembic was
introduced (``create_all`` plus hand-written SQLite migrations, up to 2.3.x)
already holds some or all of these tables: only the missing ones are created,
then the former SQLite migrations bring the existing tables up to this schema.

Revision ID: 0001
Revises:
Create Date: 2026-10-30 15:04:43.503127
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    """Tell whether the table already exists (pre-Alembic database)."""
    return sa.inspect(op.get_bind()).has_table(name)


def _columns(table: str) -> dict[str, dict[str, object]]:
    """Return the current columns of a table, by name."""
    return {
        col["name"]: dict(col) for col in sa.inspect(op.get_bind()).get_columns(table)
    }


def _create_table(
    name: str, *columns: sa.SchemaItem, indexes: Sequence[tuple[str, bool]] = ()
) -> None:
    """Create a table and its single-column indexes unless the table exists."""
    if _has_table(name):
        return
    op.create_table(name, *columns)
    for column, unique in indexes:
        op.create_index(f"ix_{name}_{column}", name, [column], unique=unique)


def upgrade() -> None:
    """Upgrade the schema."""
    _create_table(
        "account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        indexes=[("name", True)],
    )
    _create_table(
        "auditlog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("resource_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("resource_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        indexes=[
            ("action", False),
            ("created_at", False),
            ("resource_type", False),
            ("user_id", False),
            ("username", False),
        ],
    )
    _create_table(
        "oidcsettings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("client_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("client_secret", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("discovery_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("redirect_uri", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("scopes", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("local_login_disabled", sa.Boolean(), nullable=False),
        sa.Column(
            "post_logout_redirect_uri",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table(
        "recordtype",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("applicable_to", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        indexes=[("name", True)],
    )
    _create_table(
        "smtpsettings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("host", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("from_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "recipient_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("use_tls", sa.Boolean(), nullable=False),
        sa.Column("use_starttls", sa.Boolean(), nullable=False),
        sa.Column("alert_actions", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "alert_resources", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("alert_statuses", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table(
        "syslogsettings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("host", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("facility", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("app_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "username", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False
        ),
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_oidc", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        indexes=[("username", True)],
    )
    _create_table(
        "zonerecordtype",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "zone_id", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False
        ),
        sa.Column(
            "record_type_name",
            sqlmodel.sql.sqltypes.AutoString(length=20),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        indexes=[("zone_id", False)],
    )
    _create_table(
        "acmeapikey",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "zone_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column(
            "key_prefix", sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False
        ),
        sa.Column("key_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("zones", sa.Text(), nullable=False),
        sa.Column(
            "key_type", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("last_used_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        indexes=[("key_hash", True), ("user_id", False)],
    )
    _create_table(
        "personalaccesstoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column(
            "token_prefix", sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False
        ),
        sa.Column("token_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("expires_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        indexes=[("token_hash", True), ("user_id", False)],
    )
    _create_table(
        "useraccount",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "manager", "viewer", name="zonerole"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "account_id"),
    )

    # Pre-Alembic databases only existed on SQLite: any other backend failed at
    # startup on the PRAGMA statements of the former migrations.
    if op.get_bind().dialect.name == "sqlite":
        _upgrade_legacy_sqlite()


def _add_missing_columns(table: str, *columns: sa.Column[object]) -> set[str]:
    """Add the columns the table lacks and return the names of those added."""
    existing = _columns(table)
    added = set()
    for column in columns:
        if column.name not in existing:
            op.add_column(table, column)
            added.add(column.name)
    return added


def _upgrade_legacy_sqlite() -> None:
    """Apply the hand-written migrations of the versions before Alembic."""
    bind = op.get_bind()
    false = sa.text("0")
    empty = sa.text("''")

    _add_missing_columns(
        "user",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=false),
    )
    _add_missing_columns(
        "oidcsettings",
        sa.Column(
            "local_login_disabled", sa.Boolean(), nullable=False, server_default=false
        ),
        sa.Column(
            "post_logout_redirect_uri",
            sa.String(),
            nullable=False,
            server_default=empty,
        ),
    )
    _add_missing_columns(
        "useraccount",
        sa.Column(
            "role", sa.String(), nullable=False, server_default=sa.text("'admin'")
        ),
    )
    added = _add_missing_columns(
        "acmeapikey",
        sa.Column(
            "key_type", sa.String(10), nullable=False, server_default=sa.text("'acme'")
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("zone_name", sa.String(255), nullable=True),
    )
    if "zone_name" in added:
        # An ACME key is now bound to one zone: keep the first of its zones.
        rows = bind.execute(
            sa.text("SELECT id, zones FROM acmeapikey WHERE key_type = 'acme'")
        ).fetchall()
        for key_id, zones_json in rows:
            try:
                zones = json.loads(zones_json) if zones_json else []
            except ValueError:
                zones = []
            if zones:
                bind.execute(
                    sa.text("UPDATE acmeapikey SET zone_name = :zone WHERE id = :id"),
                    {"zone": zones[0].rstrip(".") + ".", "id": key_id},
                )
    # ACME keys survive the deletion of their creator: user_id becomes nullable.
    if not _columns("acmeapikey")["user_id"]["nullable"]:
        with op.batch_alter_table("acmeapikey") as batch_op:
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)

    _add_missing_columns(
        "personalaccesstoken", sa.Column("expires_at", sa.DateTime(), nullable=True)
    )
    # Personal access tokens used to live in acmeapikey (key_type='api').
    legacy_tokens = bind.execute(
        sa.text(
            "SELECT user_id, name, key_prefix, key_hash, comment, created_at "
            "FROM acmeapikey WHERE key_type = 'api' AND user_id IS NOT NULL"
        )
    ).fetchall()
    for user_id, name, key_prefix, key_hash, comment, created_at in legacy_tokens:
        bind.execute(
            sa.text(
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
    if legacy_tokens:
        bind.execute(sa.text("DELETE FROM acmeapikey WHERE key_type = 'api'"))

    _add_missing_columns(
        "smtpsettings",
        sa.Column("alert_actions", sa.String(), nullable=False, server_default=empty),
        sa.Column("alert_resources", sa.String(), nullable=False, server_default=empty),
        sa.Column("alert_statuses", sa.String(), nullable=False, server_default=empty),
    )

    # Free-length columns were VARCHAR before they became TEXT. Both mean the
    # same to SQLite, but align them so autogenerate reports no difference.
    for table, columns in (
        ("account", ["description"]),
        ("acmeapikey", ["zones", "comment"]),
        ("auditlog", ["details"]),
        ("personalaccesstoken", ["comment"]),
    ):
        existing = _columns(table)
        to_text = [c for c in columns if not isinstance(existing[c]["type"], sa.Text)]
        if to_text:
            with op.batch_alter_table(table) as batch_op:
                for column in to_text:
                    batch_op.alter_column(column, type_=sa.Text())


def downgrade() -> None:
    """Downgrade the schema."""
    for table in (
        "useraccount",
        "personalaccesstoken",
        "acmeapikey",
        "zonerecordtype",
        "user",
        "syslogsettings",
        "smtpsettings",
        "recordtype",
        "oidcsettings",
        "auditlog",
        "account",
    ):
        op.drop_table(table)
    sa.Enum(name="zonerole").drop(op.get_bind(), checkfirst=True)

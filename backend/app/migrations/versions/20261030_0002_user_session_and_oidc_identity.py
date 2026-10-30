"""user session version and OIDC identity

Adds ``token_version`` (revocation of the session JWTs) and the stable OIDC
identity ``(oidc_issuer, oidc_subject)`` to the ``user`` table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 15:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the session version and the OIDC identity columns."""
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "oidc_issuer",
                sqlmodel.sql.sqltypes.AutoString(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "oidc_subject",
                sqlmodel.sql.sqltypes.AutoString(length=255),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_user_oidc_identity", ["oidc_issuer", "oidc_subject"], unique=True
        )


def downgrade() -> None:
    """Drop the session version and the OIDC identity columns."""
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_index("ix_user_oidc_identity")
        batch_op.drop_column("oidc_subject")
        batch_op.drop_column("oidc_issuer")
        batch_op.drop_column("token_version")

"""Initial schema — all 5 tables

Revision ID: 001
Revises:
Create Date: 2026-05-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "config",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("ip", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip"),
    )

    op.create_table(
        "exploits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("period", sa.Integer(), server_default="120", nullable=False),
        sa.Column("timeout", sa.Integer(), server_default="30", nullable=False),
        sa.Column("last_run", DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "flags",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("flag", sa.Text(), nullable=False),
        sa.Column(
            "exploit_id",
            sa.Integer(),
            sa.ForeignKey("exploits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column(
            "captured_at",
            DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("submitted_at", DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag"),
    )
    op.create_index("idx_flags_status", "flags", ["status"])
    op.create_index("idx_flags_captured_at", "flags", ["captured_at"])

    op.create_table(
        "exploit_runs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "exploit_id",
            sa.Integer(),
            sa.ForeignKey("exploits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("flags_found", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exploit_runs")
    op.drop_index("idx_flags_captured_at", table_name="flags")
    op.drop_index("idx_flags_status", table_name="flags")
    op.drop_table("flags")
    op.drop_table("exploits")
    op.drop_table("teams")
    op.drop_table("config")

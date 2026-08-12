"""Add usage_counters table backing the cost ceilings.

One row per (scope, meter, period_key) triple. The unique constraint is
load-bearing: the atomic INSERT .. ON CONFLICT .. DO UPDATE upsert in
``alchymine/db/usage_counters.py`` infers its conflict target from it.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_counters",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("meter", sa.String(64), nullable=False),
        sa.Column(
            "period_key",
            sa.String(16),
            nullable=False,
            comment="UTC calendar date, YYYY-MM-DD",
        ),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("scope", "meter", "period_key", name="uq_usage_counters_key"),
    )


def downgrade() -> None:
    op.drop_table("usage_counters")

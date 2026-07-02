"""Add birth_timezone column to intake_data.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-02

Stores the IANA timezone name of the birth location (e.g.
"America/Toronto") so astrology calculations can resolve the exact UTC
birth moment.  Plaintext — a timezone name is low sensitivity, matching
how birth_date/birth_time are stored.

This migration is fully idempotent — safe to run on databases that
already have the column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "intake_data" not in existing_tables:
        return

    cols = {c["name"] for c in inspector.get_columns("intake_data")}
    if "birth_timezone" not in cols:
        op.add_column(
            "intake_data",
            sa.Column(
                "birth_timezone",
                sa.Text(),
                nullable=True,
                comment="IANA timezone of birth location, e.g. 'America/Toronto'",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("intake_data")}
    if "birth_timezone" in cols:
        op.drop_column("intake_data", "birth_timezone")

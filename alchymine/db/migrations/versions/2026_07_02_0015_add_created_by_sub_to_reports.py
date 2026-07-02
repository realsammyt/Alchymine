"""Add created_by_sub column to reports.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-02

Reports created while the JWT subject had no users row fall back to
``user_id = NULL`` (orphan reports).  The old ownership check skipped
NULL owners, so any authenticated user could read them (IDOR).  This
column records the creator's JWT sub on every report so orphan rows
stay readable by their creator and nobody else.  Legacy orphan rows
(both columns NULL) become inaccessible — intended.

This migration is fully idempotent — safe to run on databases that
already have the column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "reports" not in existing_tables:
        return

    cols = {c["name"] for c in inspector.get_columns("reports")}
    if "created_by_sub" not in cols:
        op.add_column(
            "reports",
            sa.Column(
                "created_by_sub",
                sa.Text(),
                nullable=True,
                comment="JWT subject that created the report — ownership check for orphan rows",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("reports")}
    if "created_by_sub" in cols:
        op.drop_column("reports", "created_by_sub")

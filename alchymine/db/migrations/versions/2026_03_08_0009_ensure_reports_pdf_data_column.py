"""Ensure pdf_data column exists on reports table.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-08

Production databases where the reports table was created by
``Base.metadata.create_all()`` before the ``pdf_data`` column was added
to the ORM model are missing this column.  Migration 0004 added it,
but that migration may have been stamped-over without actually running
on production.

This migration is fully idempotent — safe to run on databases that
already have the column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "reports" not in existing_tables:
        # If the reports table doesn't exist at all, nothing to do —
        # migration 0004/0006 should have created it.
        return

    report_cols = {c["name"] for c in inspector.get_columns("reports")}
    if "pdf_data" not in report_cols:
        op.add_column("reports", sa.Column("pdf_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    report_cols = {c["name"] for c in inspector.get_columns("reports")}
    if "pdf_data" in report_cols:
        op.drop_column("reports", "pdf_data")

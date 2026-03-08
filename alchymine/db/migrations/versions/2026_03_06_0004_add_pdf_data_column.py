"""Add pdf_data column to reports table for persistent PDF storage.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-06

Adds:
- ``pdf_data`` LargeBinary column to ``reports`` for storing PDF bytes in DB,
  replacing the former in-memory ``pdf_store`` dict which was lost on restart.

Note: The ``reports`` table was originally created by ``Base.metadata.create_all()``
and had no migration.  This migration now creates it if missing (for fresh Alembic-
only databases) before adding the ``pdf_data`` column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # Create reports table if it doesn't exist yet (was created by create_all()
    # on existing databases, but missing from the migration chain).
    if "reports" not in existing_tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("report_type", sa.String(100), server_default="full"),
            sa.Column("status", sa.String(50), server_default="pending", index=True),
            sa.Column("user_input", sa.Text, nullable=True),
            sa.Column("user_profile", sa.Text, nullable=True, comment="SENSITIVE — encrypted"),
            sa.Column("result", sa.JSON, nullable=True),
            sa.Column("html_content", sa.Text, nullable=True),
            sa.Column("pdf_path", sa.String(500), nullable=True),
            sa.Column("error", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # Add pdf_data column (the original purpose of this migration)
    report_cols = {c["name"] for c in inspect(conn).get_columns("reports")}
    if "pdf_data" not in report_cols:
        op.add_column("reports", sa.Column("pdf_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "pdf_data")

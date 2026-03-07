"""Add pdf_data column to reports table for persistent PDF storage.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-06

Adds:
- ``pdf_data`` LargeBinary column to ``reports`` for storing PDF bytes in DB,
  replacing the former in-memory ``pdf_store`` dict which was lost on restart.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("pdf_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "pdf_data")

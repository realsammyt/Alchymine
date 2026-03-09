"""Add kegan_dimension_scores and kegan_description columns to perspective_profiles.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-09

Stores raw Kegan dimension scores (for re-assessment) and the enriched
stage description dict alongside the existing kegan_stage column.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = set(inspector.get_table_names())
    if "perspective_profiles" not in existing_tables:
        return

    cols = {c["name"] for c in inspector.get_columns("perspective_profiles")}

    if "kegan_dimension_scores" not in cols:
        op.add_column(
            "perspective_profiles",
            sa.Column("kegan_dimension_scores", sa.JSON(), nullable=True,
                      comment="Raw dimension scores for re-assessment"),
        )
    if "kegan_description" not in cols:
        op.add_column(
            "perspective_profiles",
            sa.Column("kegan_description", sa.JSON(), nullable=True,
                      comment="Stage description dict (name, description, strengths, growth_edges)"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("perspective_profiles")}
    if "kegan_description" in cols:
        op.drop_column("perspective_profiles", "kegan_description")
    if "kegan_dimension_scores" in cols:
        op.drop_column("perspective_profiles", "kegan_dimension_scores")

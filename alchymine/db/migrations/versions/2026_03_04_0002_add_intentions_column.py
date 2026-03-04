"""Add intentions JSON column to intake_data.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-04

Adds a JSON column ``intentions`` to the ``intake_data`` table to store
the full list of 1-3 user intentions.  Existing rows keep
``intentions=NULL`` and fall back to the single ``intention`` column
via the ``resolved_intentions`` property on the ORM model.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("intake_data", sa.Column("intentions", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("intake_data", "intentions")

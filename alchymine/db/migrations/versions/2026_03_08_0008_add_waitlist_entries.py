"""Add waitlist_entries table for public waitlist signups.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column(
            "invite_code_id",
            sa.Integer,
            sa.ForeignKey("invite_codes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_waitlist_entries_email", "waitlist_entries", ["email"])
    op.create_index("ix_waitlist_entries_status", "waitlist_entries", ["status"])
    op.create_index("ix_waitlist_entries_created_at", "waitlist_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_created_at", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_status", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_email", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")

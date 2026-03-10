"""Add feedback_entries table for user feedback submissions.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("category", sa.String(50), server_default="general", nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("admin_note", sa.Text, nullable=True),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_feedback_entries_user_id", "feedback_entries", ["user_id"])
    op.create_index("ix_feedback_entries_category", "feedback_entries", ["category"])
    op.create_index("ix_feedback_entries_status", "feedback_entries", ["status"])
    op.create_index("ix_feedback_entries_created_at", "feedback_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_entries_created_at", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_status", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_category", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_user_id", table_name="feedback_entries")
    op.drop_table("feedback_entries")

"""Add missing tables (reports, journal_entries) and user auth columns.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-07

Tables ``reports`` and ``journal_entries`` were previously created only by
``Base.metadata.create_all()`` and had no Alembic migration.  User auth
columns (email, password_hash, password reset fields) were likewise missing
from migration 0001.

This migration uses introspection so it is safe to run on databases that
already have these objects (created by ``create_all()``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # ── reports table ─────────────────────────────────────────────────
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
            # user_profile is EncryptedJSON → stored as Text (ciphertext)
            sa.Column("user_profile", sa.Text, nullable=True, comment="SENSITIVE — encrypted"),
            sa.Column("result", sa.JSON, nullable=True),
            sa.Column("html_content", sa.Text, nullable=True),
            sa.Column("pdf_path", sa.String(500), nullable=True),
            sa.Column("pdf_data", sa.LargeBinary, nullable=True),
            sa.Column("error", sa.Text, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    # ── journal_entries table ─────────────────────────────────────────
    if "journal_entries" not in existing_tables:
        op.create_table(
            "journal_entries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("system", sa.String(50), server_default="general"),
            sa.Column("entry_type", sa.String(50), server_default="reflection"),
            sa.Column("title", sa.String(200), nullable=False),
            # content is EncryptedString → stored as Text (ciphertext)
            sa.Column("content", sa.Text, nullable=False, comment="SENSITIVE — encrypted"),
            sa.Column("tags", sa.JSON, nullable=True),
            sa.Column("mood_score", sa.Integer, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                index=True,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )

    # ── missing user auth columns ─────────────────────────────────────
    user_columns = {col["name"] for col in inspector.get_columns("users")}

    if "email" not in user_columns:
        op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "password_hash" not in user_columns:
        op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))

    if "password_reset_token" not in user_columns:
        op.add_column("users", sa.Column("password_reset_token", sa.String(255), nullable=True))

    if "password_reset_expires" not in user_columns:
        op.add_column(
            "users",
            sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
        )

    if "password_changed_at" not in user_columns:
        op.add_column(
            "users",
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # Remove user columns (reverse order)
    user_columns = {col["name"] for col in inspector.get_columns("users")}
    for col_name in (
        "password_changed_at",
        "password_reset_expires",
        "password_reset_token",
        "password_hash",
    ):
        if col_name in user_columns:
            op.drop_column("users", col_name)

    if "email" in user_columns:
        op.drop_index("ix_users_email", table_name="users")
        op.drop_column("users", "email")

    if "journal_entries" in existing_tables:
        op.drop_table("journal_entries")

    if "reports" in existing_tables:
        op.drop_table("reports")

"""Add chat_messages table for the Growth Assistant chat history.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        # content is encrypted at rest via Fernet (see alchymine/db/encryption.py).
        # The underlying storage is a Text column holding a base64 ciphertext blob.
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("system_key", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_system_key", "chat_messages", ["system_key"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
    # Composite index for the common history query: filter by user_id +
    # optional system_key, ordered by created_at desc.
    op.create_index(
        "ix_chat_messages_user_system_created",
        "chat_messages",
        ["user_id", "system_key", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_user_system_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_system_key", table_name="chat_messages")
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_table("chat_messages")

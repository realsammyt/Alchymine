"""Add the practice layer: the log, recommender state, the integration link.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-14

Three tables:

1. ``practice_log`` — one row per logged practice event. This is what
   turns completion from a client-side checkbox into a fact, and it is
   the recommender's only input.
2. ``ecology_state`` — one row per user, recommender state only. The
   primary key *is* the foreign key, so one-row-per-user is a schema
   fact rather than an application rule. No writers until slice 3.
3. ``integration_entries`` — the link between an intention, an
   experience and a reflection. No writers until slice 4.

All three use ``String(36)`` uuid primary keys, matching
``journal_entries`` and ``outcome_metrics``. The ``_pk_type()``
BigInteger/Integer SQLite variant that 0017 needed does not apply here
and is deliberately absent: it exists because SQLite only aliases a
primary key to its rowid when the declared type is exactly INTEGER,
which is a problem autoincrement keys have and uuid keys do not.

WHAT IS ENCRYPTED, and what is not. ``practice_log.reflection``,
``practice_log.self_check_response`` and ``integration_entries.note``
hold what the user actually wrote, and are Fernet-encrypted through
``EncryptedString`` on the model. Everything else stays plaintext on
purpose: Fernet is non-deterministic, so an encrypted column cannot be
grouped or compared in SQL, and the recommender aggregates by
``primary_purpose``, ``day_key``, ``pack_id``, ``practice_slug``,
``status`` and ``occurred_at``. Encrypting those would move the whole
recommender into Python over a full table scan. They are pack
identifiers and timestamps, not content.

FORWARD-ONLY. ``downgrade()`` drops all three tables, which destroys
practice history. Treat a merged 0018 as forward-only in production.

Idempotent throughout, matching 0015 and 0017: every ``create_table``
is guarded on the inspected table list, so a partially applied
migration replayed after a deploy completes instead of raising.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SENSITIVE = "SENSITIVE — encrypted"


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # ── practice_log: one row per logged practice event ──────────────
    if "practice_log" not in tables:
        op.create_table(
            "practice_log",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("pack_id", sa.String(64), nullable=False),
            sa.Column("practice_slug", sa.String(64), nullable=False),
            sa.Column(
                "primary_purpose",
                sa.String(32),
                nullable=False,
                comment="first declared purpose, denormalized at write",
            ),
            sa.Column(
                "purposes",
                sa.JSON(),
                nullable=False,
                comment="full declared list, kept readable after a pack is unmounted",
            ),
            sa.Column("category", sa.String(32), nullable=False),
            sa.Column(
                "status",
                sa.String(16),
                nullable=False,
                server_default="completed",
                comment="completed | skipped | started",
            ),
            sa.Column(
                "protocol_slot",
                sa.String(16),
                nullable=True,
                comment="morning | day | evening | unscheduled",
            ),
            sa.Column(
                "duration_minutes",
                sa.Integer(),
                nullable=True,
                comment="actual, if the user reports it",
            ),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "day_key",
                sa.String(10),
                nullable=False,
                comment="YYYY-MM-DD in the user's local day, client-supplied",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("reflection", sa.Text(), nullable=True, comment=_SENSITIVE),
            sa.Column("self_check_response", sa.Text(), nullable=True, comment=_SENSITIVE),
        )
        op.create_index("ix_practice_log_user_id", "practice_log", ["user_id"])
        op.create_index("ix_practice_log_occurred_at", "practice_log", ["occurred_at"])
        # The three the recommender reads. Without them slice 3 scans the
        # table on every /practice/today.
        op.create_index("ix_practice_log_user_day", "practice_log", ["user_id", "day_key"])
        op.create_index(
            "ix_practice_log_user_purpose_time",
            "practice_log",
            ["user_id", "primary_purpose", "occurred_at"],
        )
        op.create_index(
            "ix_practice_log_user_practice_time",
            "practice_log",
            ["user_id", "pack_id", "practice_slug", "occurred_at"],
        )

    # ── ecology_state: recommender state, one row per user ───────────
    if "ecology_state" not in tables:
        op.create_table(
            "ecology_state",
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "protocol_size",
                sa.Integer(),
                nullable=False,
                server_default="5",
                comment="clamped 3-7 at the API layer",
            ),
            sa.Column(
                "active_pack_ids",
                sa.JSON(),
                nullable=True,
                comment="user opt-in subset; NULL means all mounted packs",
            ),
            sa.Column("last_recommended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "last_recommendation",
                sa.JSON(),
                nullable=True,
                comment="the emitted set, for the stable-day rule",
            ),
            sa.Column(
                "rotation_cursor",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="round-robin start offset",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── integration_entries: intention / experience / reflection ─────
    #
    # The cascade asymmetry is deliberate. Deleting the practice_log row
    # destroys the link, because the link has no meaning without the
    # experience. Deleting a journal entry is a user-facing action and
    # must NOT destroy the integration record, so those two SET NULL.
    if "integration_entries" not in tables:
        op.create_table(
            "integration_entries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "practice_log_id",
                sa.String(36),
                sa.ForeignKey("practice_log.id", ondelete="CASCADE"),
                nullable=True,
                comment="the experience",
            ),
            sa.Column(
                "intention_entry_id",
                sa.String(36),
                sa.ForeignKey("journal_entries.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "reflection_entry_id",
                sa.String(36),
                sa.ForeignKey("journal_entries.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("purpose", sa.String(32), nullable=False),
            sa.Column(
                "capacity_delta",
                sa.Integer(),
                nullable=True,
                comment="user self-report, -2..+2, optional",
            ),
            sa.Column("note", sa.Text(), nullable=True, comment=_SENSITIVE),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_integration_entries_user_created",
            "integration_entries",
            ["user_id", "created_at"],
        )
        op.create_index(
            "ix_integration_entries_user_purpose_created",
            "integration_entries",
            ["user_id", "purpose", "created_at"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # integration_entries first: it holds the FK into practice_log.
    if "integration_entries" in tables:
        op.drop_table("integration_entries")
    if "ecology_state" in tables:
        op.drop_table("ecology_state")
    if "practice_log" in tables:
        op.drop_table("practice_log")

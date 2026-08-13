"""Add the entitlement schema: plan columns, the cost ledger, the Stripe inbox.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-13

Three pieces:

1. Seven entitlement columns on ``users``. Every one is nullable or carries
   a server_default, so Postgres 11+ adds them as a metadata-only operation
   with no table rewrite and no lock that matters.
2. ``usage_records`` — one row per delivered paid call. This is the source
   of truth for what things cost; ``usage_counters`` holds gates, not
   history.
3. ``billing_events`` — the Stripe webhook inbox. Zero writers until the
   billing router lands; built here so that slice is a router and a handler
   rather than a router, a handler and a migration on a live billing path.

FORWARD-ONLY. ``upgrade()`` runs ``UPDATE users SET plan='beta'`` after the
column add, because every account on the system today arrived through an
invite code and is a beta tester. Without that line the whole invite cohort
lands on the free allowance and loses chat, art and reports the moment the
per-plan gates ship. ``downgrade()`` drops the seven columns and the two
tables; the plan assignment is not recoverable from the dropped columns, and
neither is the ledger. Downgrading in production means losing spend history.

Idempotent throughout, matching 0015: safe to re-run against a database that
already has some of this schema.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ``BigInteger`` autoincrement needs a SQLite variant: SQLite only aliases a
# primary key to its rowid when the declared type is exactly INTEGER, so a
# BIGINT PK cannot autoincrement there and inserts fail on a NULL id. The
# variant keeps Postgres on BIGINT and lets the SQLite test suite write rows.
def _pk_type() -> sa.types.TypeEngine:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    # ── users: entitlement columns ───────────────────────────────────
    if "users" in tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        added_plan = False

        if "plan" not in cols:
            op.add_column(
                "users",
                sa.Column(
                    "plan",
                    sa.String(20),
                    nullable=False,
                    server_default="free",
                    comment="free | beta | blueprint | pro | founding",
                ),
            )
            added_plan = True
        if "plan_status" not in cols:
            op.add_column(
                "users",
                sa.Column(
                    "plan_status",
                    sa.String(20),
                    nullable=False,
                    server_default="active",
                    comment="active | trialing | past_due | canceled | expired",
                ),
            )
        if "stripe_customer_id" not in cols:
            op.add_column(
                "users",
                sa.Column(
                    "stripe_customer_id",
                    sa.Text(),
                    nullable=True,
                    comment="SENSITIVE — encrypted. Fernet is non-deterministic: never "
                    "queryable by equality. Resolve the user by users.id.",
                ),
            )
        if "stripe_subscription_id" not in cols:
            op.add_column(
                "users",
                sa.Column(
                    "stripe_subscription_id",
                    sa.Text(),
                    nullable=True,
                    comment="SENSITIVE — encrypted. Fernet is non-deterministic: never "
                    "queryable by equality. Resolve the user by users.id.",
                ),
            )
        if "plan_period_end" not in cols:
            op.add_column(
                "users",
                sa.Column("plan_period_end", sa.DateTime(timezone=True), nullable=True),
            )
        if "cancel_at_period_end" not in cols:
            op.add_column(
                "users",
                sa.Column(
                    "cancel_at_period_end",
                    sa.Boolean(),
                    nullable=False,
                    server_default="false",
                ),
            )
        if "trial_ends_at" not in cols:
            op.add_column(
                "users",
                sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
            )

        # The data migration. Gated on having just created the column so a
        # re-run cannot re-grant beta to accounts a later slice moved off it.
        if added_plan:
            op.execute(sa.text("UPDATE users SET plan = 'beta', plan_status = 'active'"))

    # ── usage_records: the cost ledger ───────────────────────────────
    if "usage_records" not in tables:
        op.create_table(
            "usage_records",
            sa.Column("id", _pk_type(), primary_key=True, autoincrement=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
                comment="NULL means unattributed spend",
            ),
            sa.Column("scope", sa.String(64), nullable=False),
            sa.Column(
                "surface",
                sa.String(32),
                nullable=False,
                comment="chat | report_narrative | art | brand_logo | unknown",
            ),
            sa.Column("meter", sa.String(64), nullable=False),
            sa.Column("provider", sa.String(16), nullable=False),
            sa.Column("model", sa.String(100), nullable=False),
            sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
            sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
            sa.Column("cache_read_input_tokens", sa.Integer, nullable=False, server_default="0"),
            sa.Column(
                "cache_creation_input_tokens", sa.Integer, nullable=False, server_default="0"
            ),
            sa.Column("images", sa.Integer, nullable=False, server_default="0"),
            sa.Column(
                "cost_micros",
                sa.Integer,
                nullable=False,
                server_default="0",
                comment="micro-dollars",
            ),
            sa.Column(
                "estimated",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="true when tokens were inferred, not reported",
            ),
            sa.Column(
                "period_key",
                sa.String(16),
                nullable=False,
                comment="UTC calendar date, YYYY-MM-DD",
            ),
            sa.Column(
                "month_key",
                sa.String(7),
                nullable=False,
                comment="UTC calendar month, YYYY-MM",
            ),
            sa.Column("request_id", sa.String(64), nullable=True),
        )
        # The last two are what /admin/usage reads. Without them the daily
        # rollup table-scans within a month of launch.
        op.create_index("ix_usage_records_created_at", "usage_records", ["created_at"])
        op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"])
        op.create_index(
            "ix_usage_records_period_surface", "usage_records", ["period_key", "surface"]
        )
        op.create_index("ix_usage_records_user_month", "usage_records", ["user_id", "month_key"])

    # ── billing_events: the Stripe inbox ─────────────────────────────
    if "billing_events" not in tables:
        op.create_table(
            "billing_events",
            sa.Column("id", _pk_type(), primary_key=True, autoincrement=True),
            sa.Column(
                "stripe_event_id",
                sa.String(255),
                nullable=False,
                comment="idempotency key — a duplicate delivery hits the constraint",
            ),
            sa.Column("event_type", sa.String(100), nullable=False),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "payload",
                sa.Text(),
                nullable=True,
                comment="SENSITIVE — encrypted. Stripe payloads carry email and "
                "payment identifiers.",
            ),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="received",
                comment="received | processed | failed | ignored",
            ),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("stripe_event_id", name="uq_billing_events_stripe_event_id"),
        )
        op.create_index("ix_billing_events_event_type", "billing_events", ["event_type"])
        op.create_index("ix_billing_events_created_at", "billing_events", ["created_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "billing_events" in tables:
        op.drop_table("billing_events")
    if "usage_records" in tables:
        op.drop_table("usage_records")

    if "users" in tables:
        cols = {c["name"] for c in inspector.get_columns("users")}
        for name in (
            "trial_ends_at",
            "cancel_at_period_end",
            "plan_period_end",
            "stripe_subscription_id",
            "stripe_customer_id",
            "plan_status",
            "plan",
        ):
            if name in cols:
                op.drop_column("users", name)

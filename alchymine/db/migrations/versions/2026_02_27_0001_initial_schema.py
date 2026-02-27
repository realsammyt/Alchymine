"""Initial schema — UserProfile v2.0 tables.

Revision ID: 0001
Revises: None
Create Date: 2026-02-27

Creates all seven tables for the five-system Alchymine profile:
- users
- intake_data
- identity_profiles
- healing_profiles
- wealth_profiles (encrypted columns)
- creative_profiles
- perspective_profiles
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
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
        sa.Column("version", sa.String(10), nullable=False, server_default="2.0"),
        sa.Column("active_plan_day", sa.Integer, nullable=True),
        sa.Column("systems_engaged", sa.JSON, nullable=True),
        sa.Column("quality_gate_results", sa.JSON, nullable=True),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])

    # ── intake_data ──────────────────────────────────────────────────
    op.create_table(
        "intake_data",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("birth_date", sa.Date, nullable=False),
        sa.Column("birth_time", sa.Time, nullable=True),
        sa.Column("birth_city", sa.String(200), nullable=True),
        sa.Column("intention", sa.String(50), nullable=False),
        sa.Column("assessment_responses", sa.JSON, nullable=True),
        sa.Column("family_structure", sa.String(200), nullable=True),
    )
    op.create_index("ix_intake_data_user_id", "intake_data", ["user_id"])

    # ── identity_profiles ────────────────────────────────────────────
    op.create_table(
        "identity_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("numerology", sa.JSON, nullable=True),
        sa.Column("astrology", sa.JSON, nullable=True),
        sa.Column("archetype", sa.JSON, nullable=True),
        sa.Column("personality", sa.JSON, nullable=True),
        sa.Column("strengths_map", sa.JSON, nullable=True),
    )
    op.create_index("ix_identity_profiles_user_id", "identity_profiles", ["user_id"])

    # ── healing_profiles ─────────────────────────────────────────────
    op.create_table(
        "healing_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("selected_modalities", sa.JSON, nullable=True),
        sa.Column("practice_history", sa.JSON, nullable=True),
        sa.Column(
            "max_difficulty",
            sa.String(50),
            nullable=False,
            server_default="foundation",
        ),
        sa.Column("crisis_protocol_active", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("contraindications", sa.JSON, nullable=True),
    )
    op.create_index("ix_healing_profiles_user_id", "healing_profiles", ["user_id"])

    # ── wealth_profiles (SENSITIVE — encrypted columns) ──────────────
    op.create_table(
        "wealth_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "risk_tolerance",
            sa.String(50),
            nullable=False,
            server_default="moderate",
        ),
        # SENSITIVE — encrypted at application level (Fernet)
        sa.Column("wealth_context", sa.Text, nullable=True, comment="SENSITIVE — encrypted"),
        sa.Column("income_range", sa.Text, nullable=True, comment="SENSITIVE — encrypted"),
        sa.Column("debt_level", sa.Text, nullable=True, comment="SENSITIVE — encrypted"),
        sa.Column("financial_goal", sa.Text, nullable=True, comment="SENSITIVE — encrypted"),
        sa.Column("wealth_archetype", sa.String(100), nullable=True),
        sa.Column("lever_priorities", sa.JSON, nullable=True),
        sa.Column(
            "financial_distress_detected",
            sa.Boolean,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "disclaimer_acknowledged",
            sa.Boolean,
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index("ix_wealth_profiles_user_id", "wealth_profiles", ["user_id"])

    # ── creative_profiles ────────────────────────────────────────────
    op.create_table(
        "creative_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("guilford_scores", sa.JSON, nullable=True),
        sa.Column("creative_dna", sa.JSON, nullable=True),
        sa.Column("creative_orientation", sa.String(200), nullable=True),
        sa.Column("medium_affinities", sa.JSON, nullable=True),
        sa.Column("active_projects", sa.Integer, nullable=False, server_default="0"),
        sa.Column("preferred_production_mode", sa.String(50), nullable=True),
        sa.Column("block_history", sa.JSON, nullable=True),
        sa.Column("assessment_date", sa.Date, nullable=True),
    )
    op.create_index("ix_creative_profiles_user_id", "creative_profiles", ["user_id"])

    # ── perspective_profiles ─────────────────────────────────────────
    op.create_table(
        "perspective_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("kegan_stage", sa.String(50), nullable=True),
        sa.Column("mental_models_applied", sa.JSON, nullable=True),
        sa.Column("distortions_identified", sa.JSON, nullable=True),
        sa.Column("reframes_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("strategic_clarity_score", sa.Float, nullable=True),
        sa.Column("network_bridges", sa.Integer, nullable=False, server_default="0"),
        sa.Column("crisis_flag", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("assessment_date", sa.Date, nullable=True),
    )
    op.create_index("ix_perspective_profiles_user_id", "perspective_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_table("perspective_profiles")
    op.drop_table("creative_profiles")
    op.drop_table("wealth_profiles")
    op.drop_table("healing_profiles")
    op.drop_table("identity_profiles")
    op.drop_table("intake_data")
    op.drop_table("users")

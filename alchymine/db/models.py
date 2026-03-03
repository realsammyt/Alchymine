"""SQLAlchemy ORM models mapping to UserProfile v2.0.

Table layout mirrors the five-system architecture:

- ``User``              — top-level entity (id, timestamps, version)
- ``IntakeData``        — raw intake-form data (PII)
- ``IdentityProfile``   — numerology, astrology, archetype, personality (JSON)
- ``HealingProfile``    — modalities, practice history, crisis flags
- ``WealthProfile``     — financial context, risk tolerance (SENSITIVE — encrypted)
- ``CreativeProfile``   — Guilford scores, Creative DNA, orientation
- ``PerspectiveProfile``— Kegan stage, mental models, distortions

Design decisions
~~~~~~~~~~~~~~~~
- Complex nested Pydantic sub-models are stored as JSON columns to keep the
  schema manageable while preserving the full fidelity of the profile.
- All WealthProfile columns that contain financial data are encrypted at rest
  using Fernet (see ``encryption.py``).
- Every child table has a ``user_id`` FK with an index for fast lookups.
- ``created_at`` / ``updated_at`` timestamps are auto-managed.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alchymine.db.base import Base
from alchymine.db.encryption import EncryptedJSON, EncryptedString

# ─── Helpers ────────────────────────────────────────────────────────────

# Use dialect-agnostic JSON so SQLite (tests) works too.
# PostgreSQL will use its native JSONB via PG_JSON; SQLite stores as TEXT.
try:
    from sqlalchemy import JSON as SA_JSON
except ImportError:  # pragma: no cover
    SA_JSON = PG_JSON  # type: ignore[misc]

JSONColumn = SA_JSON


def _uuid() -> str:
    """Generate a new UUID-4 string for use as a primary key."""
    return str(uuid.uuid4())


# ─── User ───────────────────────────────────────────────────────────────


class User(Base):
    """Top-level user entity."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[str] = mapped_column(String(10), default="2.0")

    # Authentication (nullable for backward compatibility)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Password reset
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Cross-system fields
    active_plan_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    systems_engaged: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    quality_gate_results: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)

    # Relationships (one-to-one)
    intake: Mapped[IntakeData | None] = relationship(
        "IntakeData", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    identity: Mapped[IdentityProfile | None] = relationship(
        "IdentityProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    healing: Mapped[HealingProfile | None] = relationship(
        "HealingProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    wealth: Mapped[WealthProfile | None] = relationship(
        "WealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    creative: Mapped[CreativeProfile | None] = relationship(
        "CreativeProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    perspective: Mapped[PerspectiveProfile | None] = relationship(
        "PerspectiveProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} version={self.version!r}>"


# ─── IntakeData ─────────────────────────────────────────────────────────


class IntakeData(Base):
    """Raw data from the user intake form.

    Contains PII (name, birth date) — private classification.
    """

    __tablename__ = "intake_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    full_name: Mapped[str] = mapped_column(EncryptedString(), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_city: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    intention: Mapped[str] = mapped_column(String(50), nullable=False)
    assessment_responses: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    family_structure: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="intake")

    def __repr__(self) -> str:
        return f"<IntakeData user_id={self.user_id!r} name={self.full_name!r}>"


# ─── IdentityProfile ───────────────────────────────────────────────────


class IdentityProfile(Base):
    """Layer 1 — Personal intelligence data.

    Numerology, astrology, archetype, and personality sub-models are
    stored as JSON columns to preserve their full nested structure.
    """

    __tablename__ = "identity_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    numerology: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="NumerologyProfile as JSON"
    )
    astrology: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="AstrologyProfile as JSON"
    )
    archetype: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="ArchetypeProfile as JSON"
    )
    personality: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="PersonalityProfile as JSON"
    )
    strengths_map: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Top strengths list as JSON array"
    )

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="identity")

    def __repr__(self) -> str:
        return f"<IdentityProfile user_id={self.user_id!r}>"


# ─── HealingProfile ────────────────────────────────────────────────────


class HealingProfile(Base):
    """Layer 2 — Healing system data.

    Stores modality preferences, practice history, and safety flags.
    """

    __tablename__ = "healing_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    selected_modalities: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="List of HealingPreference dicts"
    )
    practice_history: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Modality -> session count mapping"
    )
    max_difficulty: Mapped[str] = mapped_column(
        String(50), default="foundation", comment="Highest difficulty opted into"
    )
    crisis_protocol_active: Mapped[bool] = mapped_column(Boolean, default=False)
    contraindications: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Known contraindications list"
    )

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="healing")

    def __repr__(self) -> str:
        return f"<HealingProfile user_id={self.user_id!r}>"


# ─── WealthProfile ─────────────────────────────────────────────────────


class WealthProfile(Base):
    """Layer 3 — Wealth Engine data.

    ALL financial columns are encrypted at rest using Fernet.
    Per ADR: "Financial data classified as Sensitive — encrypted,
    isolated, never sent to LLM."
    """

    __tablename__ = "wealth_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    risk_tolerance: Mapped[str] = mapped_column(
        EncryptedString(),
        default="moderate",
        comment="SENSITIVE — encrypted risk tolerance (conservative | moderate | aggressive)",
    )

    # SENSITIVE — encrypted
    wealth_context: Mapped[str | None] = mapped_column(
        EncryptedJSON(), nullable=True, comment="SENSITIVE — encrypted WealthContext JSON"
    )
    # SENSITIVE — encrypted
    income_range: Mapped[str | None] = mapped_column(
        EncryptedString(), nullable=True, comment="SENSITIVE — encrypted income range"
    )
    # SENSITIVE — encrypted
    debt_level: Mapped[str | None] = mapped_column(
        EncryptedString(), nullable=True, comment="SENSITIVE — encrypted debt level"
    )
    # SENSITIVE — encrypted
    financial_goal: Mapped[str | None] = mapped_column(
        EncryptedString(), nullable=True, comment="SENSITIVE — encrypted financial goal"
    )

    wealth_archetype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lever_priorities: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Ordered WealthLever list"
    )
    # SENSITIVE — encrypted; stored as "true" / "false" strings
    financial_distress_detected: Mapped[str] = mapped_column(
        EncryptedString(), default="false", comment="SENSITIVE — encrypted boolean flag"
    )
    disclaimer_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="wealth")

    def __repr__(self) -> str:
        return f"<WealthProfile user_id={self.user_id!r}>"


# ─── CreativeProfile ───────────────────────────────────────────────────


class CreativeProfile(Base):
    """Layer 4 — Creative Forge data.

    Guilford divergent-thinking scores, Creative DNA dimensions,
    and production preferences.
    """

    __tablename__ = "creative_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    guilford_scores: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="GuilfordScores as JSON"
    )
    creative_dna: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="CreativeDNA as JSON"
    )
    creative_orientation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    medium_affinities: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Top creative modality tracks"
    )
    active_projects: Mapped[int] = mapped_column(Integer, default=0)
    preferred_production_mode: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="sprint | marathon | harvest | polish"
    )
    block_history: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Past creative block types"
    )
    assessment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="creative")

    def __repr__(self) -> str:
        return f"<CreativeProfile user_id={self.user_id!r}>"


# ─── PerspectiveProfile ────────────────────────────────────────────────


class PerspectiveProfile(Base):
    """Layer 5 — Perspective Prism data.

    Kegan developmental stage, mental models, cognitive distortions,
    and strategic clarity tracking.
    """

    __tablename__ = "perspective_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    kegan_stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Kegan developmental stage"
    )
    mental_models_applied: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Mental models engaged with"
    )
    distortions_identified: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Cognitive distortions surfaced"
    )
    reframes_completed: Mapped[int] = mapped_column(Integer, default=0)
    strategic_clarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_bridges: Mapped[int] = mapped_column(Integer, default=0)
    crisis_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    assessment_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="perspective")

    def __repr__(self) -> str:
        return f"<PerspectiveProfile user_id={self.user_id!r}>"


# ─── Report ───────────────────────────────────────────────────────────


class Report(Base):
    """Report generation job tracking.

    Persists report status, orchestrator result data, and rendered HTML
    content.  Replaces the former in-memory ``report_store`` dict.
    """

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    report_type: Mapped[str] = mapped_column(
        String(100), default="full", comment="e.g. full, numerology, astrology"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        index=True,
        comment="pending | generating | complete | failed",
    )
    user_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_profile: Mapped[dict | None] = mapped_column(
        EncryptedJSON(), nullable=True, comment="Encrypted — may contain PII from intake"
    )
    result: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id!r} status={self.status!r}>"


# ─── JournalEntry ──────────────────────────────────────────────────────


class JournalEntry(Base):
    """Journal entry — user reflections, reframes, gratitude, and progress notes.

    Content is encrypted at rest (PII classification).
    """

    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    system: Mapped[str] = mapped_column(String(50), default="general")
    entry_type: Mapped[str] = mapped_column(String(50), default="reflection")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(EncryptedString(), nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    mood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<JournalEntry id={self.id!r} user_id={self.user_id!r}>"

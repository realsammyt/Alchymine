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
from datetime import UTC, date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    Time,
    UniqueConstraint,
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

    # Admin panel
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invite_code_used: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Entitlements (migration 0017). Source of truth for what this account is
    # allowed to spend. Deliberately NOT mirrored into the JWT: access tokens
    # live 30 minutes and refresh tokens 7 days, so a plan claim in a token
    # would hand a cancelled subscriber a week of inference we pay for.
    plan: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="free",
        server_default="free",
        comment="free | beta | blueprint | pro | founding",
    )
    plan_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        comment="active | trialing | past_due | canceled | expired",
    )
    # Fernet is non-deterministic, so these two columns cannot be indexed and
    # cannot be matched by equality in SQL. That is a constraint the Stripe
    # slice must respect, not a defect to work around: the webhook handler
    # resolves the user from metadata.user_id (which we set ourselves at
    # checkout-session creation) and never issues a
    # WHERE stripe_customer_id = ... . Reads are always keyed by users.id.
    stripe_customer_id: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    plan_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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


# ─── InviteCode ─────────────────────────────────────────────────────────


class InviteCode(Base):
    """Invite code for gated registration."""

    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<InviteCode code={self.code!r} uses={self.uses_count}/{self.max_uses}>"


# ─── AdminAuditLog ──────────────────────────────────────────────────────


class AdminAuditLog(Base):
    """Audit trail for admin actions."""

    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<AdminAuditLog id={self.id!r} action={self.action!r}>"


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
    birth_timezone: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="IANA timezone of birth location, e.g. 'America/Toronto'",
    )
    intention: Mapped[str] = mapped_column(String(50), nullable=False)
    intentions: Mapped[list | None] = mapped_column(JSONColumn, nullable=True)
    assessment_responses: Mapped[dict | None] = mapped_column(JSONColumn, nullable=True)
    family_structure: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationship
    user: Mapped[User] = relationship("User", back_populates="intake")

    @property
    def resolved_intentions(self) -> list[str]:
        """Return the full intentions list, falling back to the single intention."""
        if self.intentions and isinstance(self.intentions, list):
            return self.intentions
        return [self.intention]

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
    Per ADR: financial data is classified as Sensitive — encrypted,
    isolated; the server pipeline never sends it to any LLM.
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
    active_projects: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
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
    kegan_dimension_scores: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="Raw dimension scores for re-assessment"
    )
    kegan_description: Mapped[dict | None] = mapped_column(
        JSONColumn,
        nullable=True,
        comment="Stage description dict (name, description, strengths, growth_edges)",
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
    created_by_sub: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JWT subject that created the report — ownership check for orphan rows",
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
    pdf_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
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


# ─── OutcomeMetricRecord ──────────────────────────────────────────────


class OutcomeMetricRecord(Base):
    """Persisted outcome metric measurement."""

    __tablename__ = "outcome_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[str] = mapped_column(String(20), default="weekly")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<OutcomeMetricRecord id={self.id!r} system={self.system!r} metric={self.metric_name!r}>"


# ─── MilestoneRecord (ORM) ────────────────────────────────────────────


class MilestoneDBRecord(Base):
    """Persisted milestone completion record."""

    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<MilestoneDBRecord id={self.id!r} system={self.system!r} name={self.name!r}>"


# ─── WaitlistEntry ────────────────────────────────────────────────────


class WaitlistEntry(Base):
    """Waitlist signup entry.

    Tracks email signups for the public waitlist form.  Status progresses
    from ``pending`` → ``invited`` (when an admin sends an invite code) →
    ``registered`` (when the user completes account creation).
    """

    __tablename__ = "waitlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    invite_code_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("invite_codes.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<WaitlistEntry id={self.id!r} email={self.email!r} status={self.status!r}>"


# --- FeedbackEntry ────────────────────────────────────────────────────


class FeedbackEntry(Base):
    """User-submitted feedback entry.

    Status progresses: new -> reviewed -> resolved | dismissed.
    """

    __tablename__ = "feedback_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        default="general",
        nullable=False,
        index=True,
        comment="general | bug | feature | praise | other",
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="new",
        nullable=False,
        index=True,
        comment="new | reviewed | resolved | dismissed",
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<FeedbackEntry id={self.id!r} category={self.category!r} status={self.status!r}>"


# ─── ChatMessage ───────────────────────────────────────────────────────


class ChatMessage(Base):
    """Persisted chat message for the Growth Assistant.

    Stores the running conversation between a user and the AI Growth
    Assistant across all five Alchymine systems.  Each row is a single
    message turn (user, assistant, or system).

    The ``content`` column is encrypted at rest because chat history may
    contain sensitive personal disclosures (PII classification — same
    treatment as ``JournalEntry.content``).

    Columns
    -------
    id:
        UUID primary key.
    user_id:
        FK to ``users.id`` with ``ON DELETE CASCADE``.
    role:
        One of ``"user"``, ``"assistant"``, ``"system"``.
    content:
        Message body — encrypted via Fernet at rest.
    system_key:
        Optional system scope (``"intelligence" | "healing" | "wealth" |
        "creative" | "perspective"``) or ``NULL`` for general chat.
    created_at:
        UTC timestamp of message creation.
    """

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="user | assistant | system"
    )
    content: Mapped[str] = mapped_column(EncryptedString(), nullable=False)
    system_key: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="intelligence | healing | wealth | creative | perspective | NULL",
    )
    # Use a Python-side default in addition to the server default so that
    # rows inserted in rapid succession (especially in SQLite tests, where
    # ``func.now()`` resolves to whole-second precision) get unique
    # microsecond-resolution timestamps for stable ordering.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ChatMessage id={self.id!r} user_id={self.user_id!r} "
            f"role={self.role!r} system_key={self.system_key!r}>"
        )


# --- GeneratedImage ────────────────────────────────────────────────────


class GeneratedImage(Base):
    """A single Gemini-generated image owned by a user.

    Image bytes are stored on the filesystem (under ``ART_CACHE_DIR``)
    keyed by ``id``; only the metadata and relative path live in this
    table. The router serves bytes by reading the file at request time
    after verifying ownership.
    """

    __tablename__ = "generated_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="image/png")
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Filesystem path relative to ART_CACHE_DIR",
    )
    style_preset: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<GeneratedImage id={self.id!r} user_id={self.user_id!r}>"


# ─── Usage Counters ─────────────────────────────────────────────────────


class UsageCounter(Base):
    """One rolling count of metered usage, keyed by scope, meter, and period.

    Backs every cost ceiling in the app (the global LLM spend breaker and
    the per-user art cap). Rows are written only through
    ``alchymine.db.usage_counters`` so the atomic upsert stays the single
    way a count can change.

    ``scope`` is ``"global"`` for system-wide breakers or a user id for
    per-user caps; ``period_key`` is the UTC calendar date the count
    belongs to, which is what makes ceilings reset at UTC midnight.

    There is no FK from ``scope`` to ``users.id`` on purpose: the column
    holds both user ids and the ``"global"`` sentinel, and a deleted user
    should not take their spend history with them.
    """

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("scope", "meter", "period_key", name="uq_usage_counters_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    meter: Mapped[str] = mapped_column(String(64), nullable=False)
    period_key: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="UTC calendar date, YYYY-MM-DD"
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<UsageCounter scope={self.scope!r} meter={self.meter!r} "
            f"period={self.period_key!r} count={self.count!r}>"
        )


# ─── Cost Ledger ────────────────────────────────────────────────────────

# SQLite only aliases a primary key to its rowid when the declared type is
# exactly INTEGER, so a BIGINT primary key cannot autoincrement there and
# inserts fail on a NULL id. The variant keeps Postgres on BIGINT (these two
# tables grow one row per paid call) and lets the SQLite test suite write.
_LedgerPK = BigInteger().with_variant(Integer, "sqlite")


class UsageRecord(Base):
    """One row per delivered paid call. The source of truth for spend.

    ``usage_counters`` answers "are we blocked"; this table answers "what did
    it cost". Rows are written after the call returns, never before, because
    a ledger that counts money we did not spend is simply wrong.

    ``user_id`` is nullable and ``ON DELETE SET NULL`` for the same reason
    ``UsageCounter`` has no FK at all: a deleted user should not take the
    spend history with them, and nulling the id satisfies erasure while
    keeping the aggregate honest. A NULL id also covers calls that reached an
    egress site with no attribution set, which are logged loudly and still
    charged to the global meter.

    ``period_key`` and ``month_key`` are denormalized off ``created_at`` so
    the rollups the admin usage view runs are plain indexed equality reads.
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_period_surface", "period_key", "surface"),
        Index("ix_usage_records_user_month", "user_id", "month_key"),
    )

    id: Mapped[int] = mapped_column(_LedgerPK, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="NULL means unattributed spend",
    )
    scope: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="user id, or 'unattributed'"
    )
    surface: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="chat | report_narrative | art | brand_logo | unknown",
    )
    meter: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cache_read_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cache_creation_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    images: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost_micros: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="micro-dollars"
    )
    estimated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="true when tokens were inferred, not reported",
    )
    period_key: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="UTC calendar date, YYYY-MM-DD"
    )
    month_key: Mapped[str] = mapped_column(
        String(7), nullable=False, comment="UTC calendar month, YYYY-MM"
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<UsageRecord id={self.id!r} surface={self.surface!r} "
            f"model={self.model!r} cost_micros={self.cost_micros!r}>"
        )


# ─── Billing Events ─────────────────────────────────────────────────────


class BillingEvent(Base):
    """Inbox for Stripe webhook deliveries. No writers until billing ships.

    ``stripe_event_id`` is the idempotency key: Stripe retries deliveries, and
    a duplicate hits the unique constraint and is discarded rather than
    granting a plan twice.

    ``payload`` is encrypted because Stripe payloads carry an email address
    and payment identifiers.
    """

    __tablename__ = "billing_events"
    __table_args__ = (
        UniqueConstraint("stripe_event_id", name="uq_billing_events_stripe_event_id"),
    )

    id: Mapped[int] = mapped_column(_LedgerPK, primary_key=True, autoincrement=True)
    stripe_event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="idempotency key — a duplicate delivery hits the constraint",
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    payload: Mapped[dict | None] = mapped_column(EncryptedJSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="received",
        server_default="received",
        comment="received | processed | failed | ignored",
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<BillingEvent id={self.id!r} type={self.event_type!r} status={self.status!r}>"


# ─── Practice Layer ─────────────────────────────────────────────────────
#
# What is encrypted here, and what is not, is a decision worth stating
# where somebody editing these classes will read it. ``reflection``,
# ``self_check_response`` and ``IntegrationEntry.note`` hold what the
# user wrote and are Fernet-encrypted. Everything else stays plaintext
# because the ecology recommender groups by it in SQL, and Fernet is
# non-deterministic: an encrypted ``primary_purpose`` or ``day_key``
# cannot be grouped or compared, so encrypting them would move the whole
# recommender into Python over a full table scan. Identifiers and
# timestamps are not content.


class PracticeLogEntry(Base):
    """One logged practice event. The recommender's only input.

    ``purposes`` and ``category`` are denormalized off the registry
    definition at write time rather than joined back to it, so a row
    stays interpretable after its pack is unmounted or revised.

    ``day_key`` is the user's *local* calendar day and arrives from the
    client. It is stored exactly as sent: deriving it server-side from
    ``occurred_at`` in UTC would file an evening practice in Auckland
    under the wrong day, every day.

    There is deliberately no boolean or score on the self-check.
    ``self_check_response`` is free text the recommender never reads;
    scoring a reflective question would make it a diagnosis by another
    name.
    """

    __tablename__ = "practice_log"
    __table_args__ = (
        Index("ix_practice_log_user_day", "user_id", "day_key"),
        Index("ix_practice_log_user_purpose_time", "user_id", "primary_purpose", "occurred_at"),
        Index(
            "ix_practice_log_user_practice_time",
            "user_id",
            "pack_id",
            "practice_slug",
            "occurred_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pack_id: Mapped[str] = mapped_column(String(64), nullable=False)
    practice_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_purpose: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="first declared purpose, denormalized at write"
    )
    purposes: Mapped[list] = mapped_column(JSONColumn, nullable=False, default=list)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="completed",
        server_default="completed",
        comment="completed | skipped | started",
    )
    protocol_slot: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="morning | day | evening | unscheduled"
    )
    duration_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="actual, if the user reports it"
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    day_key: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="YYYY-MM-DD in the user's local day, client-supplied"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reflection: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    self_check_response: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<PracticeLogEntry id={self.id!r} practice={self.pack_id!r}/"
            f"{self.practice_slug!r} status={self.status!r} day={self.day_key!r}>"
        )


class EcologyState(Base):
    """Per-user recommender state. No writers until slice 3.

    ``user_id`` is both the primary key and the foreign key, so
    one-row-per-user is a schema fact rather than an application rule.

    Practice-scoped only: this models nothing about the alchemical
    spiral. ``route_user`` stays pure and unpersisted, and persisted
    spiral state would be its own table and its own decision.
    """

    __tablename__ = "ecology_state"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    protocol_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
        comment="clamped 3-7 by the recommender",
    )
    active_pack_ids: Mapped[list | None] = mapped_column(
        JSONColumn, nullable=True, comment="user opt-in subset; NULL means all mounted packs"
    )
    last_recommended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_recommendation: Mapped[dict | None] = mapped_column(
        JSONColumn, nullable=True, comment="the emitted set, for the stable-day rule"
    )
    rotation_cursor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="round-robin start offset",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<EcologyState user_id={self.user_id!r} protocol_size={self.protocol_size!r}>"


class IntegrationEntry(Base):
    """Links an intention, an experience and a reflection. Writers in slice 4.

    The cascade rules are asymmetric on purpose. Deleting the
    ``practice_log`` row destroys the link, because the link means
    nothing without the experience. Deleting a journal entry is
    something a user does deliberately and must not take the integration
    record with it, so both journal references SET NULL.
    """

    __tablename__ = "integration_entries"
    __table_args__ = (
        Index("ix_integration_entries_user_created", "user_id", "created_at"),
        Index("ix_integration_entries_user_purpose_created", "user_id", "purpose", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    practice_log_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("practice_log.id", ondelete="CASCADE"),
        nullable=True,
        comment="the experience",
    )
    intention_entry_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )
    reflection_entry_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity_delta: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="user self-report, -2..+2, optional"
    )
    note: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<IntegrationEntry id={self.id!r} user_id={self.user_id!r} purpose={self.purpose!r}>"
        )

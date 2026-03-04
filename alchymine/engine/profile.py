"""UserProfile v2.0 — Unified five-system data contract.

This is the shared schema that flows through all 5 Alchymine systems.
Every engine, agent, skill, and quality gate reads from and writes to
fields defined here. Changes to this schema require an RFC.

Five layers:
  1. Identity — numerology, astrology, archetype, personality
  2. Healing — modality preferences, practice history, safety flags
  3. Wealth — financial context, risk tolerance, lever priorities
  4. Creative — Blueprint, Guilford scores, Creative DNA, projects
  5. Perspective — Kegan stage, mental models, reframing history
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ─── Enums ──────────────────────────────────────────────────────────────


class ArchetypeType(StrEnum):
    CREATOR = "creator"
    SAGE = "sage"
    EXPLORER = "explorer"
    MYSTIC = "mystic"
    RULER = "ruler"
    LOVER = "lover"
    HERO = "hero"
    CAREGIVER = "caregiver"
    JESTER = "jester"
    INNOCENT = "innocent"
    REBEL = "rebel"
    EVERYMAN = "everyman"


class AttachmentStyle(StrEnum):
    SECURE = "secure"
    ANXIOUS = "anxious"
    AVOIDANT = "avoidant"
    DISORGANIZED = "disorganized"
    ANXIOUS_SECURE = "anxious-secure"
    AVOIDANT_SECURE = "avoidant-secure"


class RiskTolerance(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class WealthLever(StrEnum):
    EARN = "EARN"
    KEEP = "KEEP"
    GROW = "GROW"
    PROTECT = "PROTECT"
    TRANSFER = "TRANSFER"


class Intention(StrEnum):
    CAREER = "career"
    LOVE = "love"
    PURPOSE = "purpose"
    MONEY = "money"
    HEALTH = "health"
    FAMILY = "family"
    BUSINESS = "business"
    LEGACY = "legacy"


class PracticeDifficulty(StrEnum):
    FOUNDATION = "foundation"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    ADVANCED = "advanced"
    INTENSIVE = "intensive"


class KeganStage(StrEnum):
    IMPULSIVE = "impulsive"  # Stage 1
    IMPERIAL = "imperial"  # Stage 2
    SOCIALIZED = "socialized"  # Stage 3
    SELF_AUTHORING = "self-authoring"  # Stage 4
    SELF_TRANSFORMING = "self-transforming"  # Stage 5


class CreativeProductionMode(StrEnum):
    SPRINT = "sprint"
    MARATHON = "marathon"
    HARVEST = "harvest"
    POLISH = "polish"


# ─── Sub-models ─────────────────────────────────────────────────────────


class NumerologyProfile(BaseModel):
    """Pythagorean and Chaldean numerology calculations."""

    life_path: int = Field(..., ge=1, le=33, description="Life Path number (1-9, 11, 22, 33)")
    expression: int = Field(..., ge=1, le=33, description="Expression/Destiny number")
    soul_urge: int = Field(..., ge=1, le=33, description="Soul Urge/Heart's Desire number")
    personality: int = Field(..., ge=1, le=33, description="Personality/Outer number")
    personal_year: int = Field(..., ge=1, le=9, description="Current Personal Year cycle")
    personal_month: int = Field(..., ge=1, le=9, description="Current Personal Month")
    maturity: int | None = Field(None, ge=1, le=33, description="Maturity number")
    is_master_number: bool = Field(False, description="Whether Life Path is 11, 22, or 33")
    chaldean_name: int | None = Field(None, description="Chaldean name number")
    calculation_system: str = Field("pythagorean", description="Primary system used")


class AstrologyProfile(BaseModel):
    """Natal chart data from Swiss Ephemeris."""

    sun_sign: str = Field(..., description="Sun sign (e.g., 'Pisces')")
    moon_sign: str = Field(..., description="Moon sign")
    rising_sign: str | None = Field(None, description="Rising/Ascendant (requires birth time)")
    sun_degree: float = Field(..., description="Sun position in degrees")
    moon_degree: float = Field(..., description="Moon position in degrees")
    rising_degree: float | None = Field(None, description="Rising degree")
    house_placements: dict[str, int] | None = Field(
        None, description="Planet-to-house mapping (requires birth time)"
    )
    current_transits: dict[str, str] | None = Field(
        None, description="Active transits at time of generation"
    )
    venus_retrograde: bool = Field(False, description="Whether Venus is retrograde")
    mercury_retrograde: bool = Field(False, description="Whether Mercury is retrograde")


class ArchetypeProfile(BaseModel):
    """Jungian archetype analysis."""

    primary: ArchetypeType = Field(..., description="Primary archetype")
    secondary: ArchetypeType | None = Field(None, description="Secondary archetype")
    shadow: str = Field(..., description="Primary shadow pattern (e.g., 'Perfectionism')")
    shadow_secondary: str | None = Field(None, description="Secondary shadow pattern")
    light_qualities: list[str] = Field(default_factory=list, description="Light/strength qualities")
    shadow_qualities: list[str] = Field(
        default_factory=list, description="Shadow/growth-edge qualities"
    )


class BigFiveScores(BaseModel):
    """Big Five personality traits (mini-IPIP)."""

    openness: float = Field(..., ge=0, le=100)
    conscientiousness: float = Field(..., ge=0, le=100)
    extraversion: float = Field(..., ge=0, le=100)
    agreeableness: float = Field(..., ge=0, le=100)
    neuroticism: float = Field(..., ge=0, le=100)


class PersonalityProfile(BaseModel):
    """Combined personality assessments."""

    big_five: BigFiveScores
    attachment_style: AttachmentStyle
    enneagram_type: int | None = Field(None, ge=1, le=9, description="Enneagram type")
    enneagram_wing: int | None = Field(None, ge=1, le=9, description="Enneagram wing")


# ─── Layer 1: Identity ──────────────────────────────────────────────────


class IdentityLayer(BaseModel):
    """Personal intelligence data — who you are."""

    numerology: NumerologyProfile
    astrology: AstrologyProfile
    archetype: ArchetypeProfile
    personality: PersonalityProfile
    strengths_map: list[str] = Field(
        default_factory=list, max_length=10, description="Top strengths derived from all systems"
    )


# ─── Layer 2: Healing ───────────────────────────────────────────────────


class HealingPreference(BaseModel):
    """Individual healing modality preference."""

    modality: str = Field(..., description="Modality name (e.g., 'breathwork')")
    skill_trigger: str = Field(..., description="Skill trigger (e.g., '/breathwork')")
    preference_score: float = Field(0.5, ge=0, le=1, description="0=low, 1=high preference")
    contraindicated: bool = Field(False, description="Whether contraindicated for this user")
    difficulty_level: PracticeDifficulty = Field(PracticeDifficulty.FOUNDATION)


class HealingLayer(BaseModel):
    """Healing system data — how you heal and grow."""

    selected_modalities: list[HealingPreference] = Field(
        default_factory=list,
        max_length=7,
        description="User's selected healing modalities (5-7)",
    )
    practice_history: dict[str, int] = Field(
        default_factory=dict, description="Modality → session count"
    )
    max_difficulty: PracticeDifficulty = Field(
        PracticeDifficulty.FOUNDATION,
        description="Highest difficulty the user has opted into",
    )
    crisis_protocol_active: bool = Field(False)
    contraindications: list[str] = Field(
        default_factory=list, description="Known contraindications"
    )


# ─── Layer 3: Wealth ────────────────────────────────────────────────────


class WealthContext(BaseModel):
    """Financial context — voluntarily provided."""

    income_range: str | None = Field(None, description="e.g., '$50k-$75k'")
    has_investments: bool | None = None
    has_business: bool | None = None
    has_real_estate: bool | None = None
    dependents: int | None = Field(None, ge=0)
    debt_level: str | None = Field(None, description="e.g., 'low', 'moderate', 'high'")
    financial_goal: str | None = None


class WealthLayer(BaseModel):
    """Wealth Engine data — how you build generational prosperity."""

    risk_tolerance: RiskTolerance = Field(RiskTolerance.MODERATE)
    wealth_context: WealthContext | None = None
    wealth_archetype: str | None = Field(None, description="Derived wealth archetype")
    lever_priorities: list[WealthLever] = Field(
        default_factory=list, description="Ordered lever priorities"
    )
    financial_distress_detected: bool = Field(False)
    disclaimer_acknowledged: bool = Field(False)

    @field_validator("financial_distress_detected", mode="before")
    @classmethod
    def _coerce_distress_flag(cls, v: object) -> bool:
        """Accept encrypted-string values ("true"/"false") from the ORM layer.

        The WealthProfile ORM model stores this flag as an EncryptedString
        to protect sensitive financial information.  When the value is
        deserialized from the database it arrives as a plain string;
        this validator normalises it back to a Python bool.
        """
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)


# ─── Layer 4: Creative (v7) ─────────────────────────────────────────────


class GuilfordScores(BaseModel):
    """Guilford's six divergent thinking components."""

    fluency: float = Field(0, ge=0, le=100, description="Quantity of ideas")
    flexibility: float = Field(0, ge=0, le=100, description="Category variety")
    originality: float = Field(0, ge=0, le=100, description="Statistical rarity")
    elaboration: float = Field(0, ge=0, le=100, description="Detail development")
    sensitivity: float = Field(0, ge=0, le=100, description="Problem detection")
    redefinition: float = Field(0, ge=0, le=100, description="Repurposing ability")


class CreativeDNA(BaseModel):
    """Tharp-inspired creative preference dimensions."""

    structure_vs_improvisation: float = Field(
        0.5, ge=0, le=1, description="0=structured, 1=improvisational"
    )
    collaboration_vs_solitude: float = Field(
        0.5, ge=0, le=1, description="0=collaborative, 1=solitary"
    )
    primary_sensory_mode: str = Field(
        "visual", description="visual | verbal | kinesthetic | musical"
    )
    convergent_vs_divergent: float = Field(0.5, ge=0, le=1, description="0=convergent, 1=divergent")
    creative_peak: str = Field("morning", description="morning | evening")


class CreativeLayer(BaseModel):
    """Creative Forge data — how you create and produce."""

    guilford_scores: GuilfordScores | None = None
    creative_dna: CreativeDNA | None = None
    creative_orientation: str | None = Field(None, description="Life Path → Creative orientation")
    medium_affinities: list[str] = Field(
        default_factory=list, description="Top creative modality tracks"
    )
    active_projects: int = Field(0, ge=0, description="Number of active creative projects")
    preferred_production_mode: CreativeProductionMode | None = None
    block_history: list[str] = Field(
        default_factory=list, description="Past creative block types encountered"
    )
    assessment_date: date | None = Field(None, description="Last Guilford assessment date")


# ─── Layer 5: Perspective (v7) ──────────────────────────────────────────


class PerspectiveLayer(BaseModel):
    """Perspective Prism data — how you see and position."""

    kegan_stage: KeganStage | None = None
    mental_models_applied: list[str] = Field(
        default_factory=list, description="Mental models the user has engaged with"
    )
    distortions_identified: list[str] = Field(
        default_factory=list, description="Cognitive distortions surfaced"
    )
    reframes_completed: int = Field(0, ge=0)
    strategic_clarity_score: float | None = Field(None, ge=0, le=100)
    network_bridges: int = Field(0, ge=0, description="Structural hole bridges identified")
    crisis_flag: bool = Field(False, description="Whether crisis detection has been triggered")
    assessment_date: date | None = None


# ─── Intake Data ────────────────────────────────────────────────────────


class IntakeData(BaseModel):
    """Raw data from user intake form."""

    full_name: str = Field(..., min_length=2, max_length=200)
    birth_date: date
    birth_time: time | None = Field(None, description="Optional: enables Rising sign")
    birth_city: str | None = Field(None, description="Optional: enables house calculations")
    intention: Intention
    intentions: list[Intention] = Field(default_factory=list, description="1-3 user intentions")
    assessment_responses: dict[str, Any] = Field(
        default_factory=dict, description="20-question assessment raw responses"
    )
    wealth_context: WealthContext | None = None
    family_structure: str | None = None

    @model_validator(mode="after")
    def _auto_populate_intentions(self) -> IntakeData:
        """Ensure intentions is populated from the single intention if empty."""
        if not self.intentions:
            self.intentions = [self.intention]
        return self


# ─── UserProfile v2.0 ──────────────────────────────────────────────────


class UserProfile(BaseModel):
    """Unified five-system user profile.

    This is the core data contract for Alchymine. All systems read from
    and contribute to this profile. The profile is built incrementally:

    - Phase 1: identity layer populated from intake
    - Phase 2: healing + wealth layers populated
    - Phase 7: creative layer populated
    - Phase 8: perspective layer populated

    Data classification:
    - Public: generated insights (can be shared)
    - Private: PII (name, birth date) — AES-256 encrypted
    - Sensitive: financial context — isolated encrypted partition
    """

    # Metadata
    id: str = Field(..., description="Unique profile identifier (UUID)")
    created_at: datetime
    updated_at: datetime
    version: str = Field("2.0", description="Schema version")

    # Intake
    intake: IntakeData

    # Five system layers
    identity: IdentityLayer | None = None
    healing: HealingLayer = Field(default_factory=HealingLayer)  # type: ignore[arg-type]
    wealth: WealthLayer = Field(default_factory=WealthLayer)  # type: ignore[arg-type]
    creative: CreativeLayer = Field(default_factory=CreativeLayer)  # type: ignore[arg-type]
    perspective: PerspectiveLayer = Field(default_factory=PerspectiveLayer)  # type: ignore[arg-type]

    # Cross-system
    active_plan_day: int | None = Field(None, ge=0, le=90, description="Current day in 90-day plan")
    systems_engaged: list[str] = Field(
        default_factory=list, description="Which systems the user has activated"
    )
    quality_gate_results: dict[str, bool] = Field(
        default_factory=dict, description="Last quality gate pass/fail per gate"
    )

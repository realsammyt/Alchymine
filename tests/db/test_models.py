"""Tests for SQLAlchemy ORM models.

Covers:
- Model creation and persistence
- JSON column serialization round-trip
- Encryption round-trip for WealthProfile sensitive columns
- Relationship traversal (User → child tables)
- Default values and constraints
"""

from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db.models import (
    CreativeProfile,
    HealingProfile,
    IdentityProfile,
    IntakeData,
    PerspectiveProfile,
    User,
    WealthProfile,
)

# ─── User ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_creation(session: AsyncSession) -> None:
    """A User row can be created with auto-generated id and defaults."""
    user = User()
    session.add(user)
    await session.flush()

    assert user.id is not None
    assert len(user.id) == 36  # UUID format
    assert user.version == "2.0"
    assert user.active_plan_day is None


@pytest.mark.asyncio
async def test_user_timestamps(session: AsyncSession) -> None:
    """created_at and updated_at are populated via server defaults."""
    user = User()
    session.add(user)
    await session.flush()

    # SQLite + aiosqlite: server_default=func.now() works
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_user_cross_system_json(session: AsyncSession) -> None:
    """systems_engaged and quality_gate_results store JSON correctly."""
    user = User(
        systems_engaged=["identity", "healing"],
        quality_gate_results={"bias_check": True, "harm_check": True},
    )
    session.add(user)
    await session.flush()

    result = await session.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one()
    assert fetched.systems_engaged == ["identity", "healing"]
    assert fetched.quality_gate_results["bias_check"] is True


# ─── IntakeData ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_intake_creation(session: AsyncSession) -> None:
    """IntakeData stores name, dates, and intention."""
    user = User()
    session.add(user)
    await session.flush()

    intake = IntakeData(
        user_id=user.id,
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        birth_time=time(14, 14),
        birth_city="Mexico City",
        intention="family",
        assessment_responses={"big_five_1": 4},
    )
    session.add(intake)
    await session.flush()

    result = await session.execute(select(IntakeData).where(IntakeData.user_id == user.id))
    fetched = result.scalar_one()
    assert fetched.full_name == "Maria Elena Vasquez"
    assert fetched.birth_date == date(1992, 3, 15)
    assert fetched.birth_time == time(14, 14)
    assert fetched.birth_city == "Mexico City"
    assert fetched.intention == "family"
    assert fetched.assessment_responses == {"big_five_1": 4}


@pytest.mark.asyncio
async def test_intake_optional_fields(session: AsyncSession) -> None:
    """IntakeData works with only required fields."""
    user = User()
    session.add(user)
    await session.flush()

    intake = IntakeData(
        user_id=user.id,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="career",
    )
    session.add(intake)
    await session.flush()

    assert intake.birth_time is None
    assert intake.birth_city is None
    assert intake.family_structure is None


# ─── IdentityProfile ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_identity_json_roundtrip(session: AsyncSession) -> None:
    """IdentityProfile JSON columns round-trip complex nested data."""
    user = User()
    session.add(user)
    await session.flush()

    numerology = {
        "life_path": 3,
        "expression": 6,
        "soul_urge": 5,
        "personality": 1,
        "personal_year": 7,
        "personal_month": 3,
        "is_master_number": False,
    }
    astrology = {
        "sun_sign": "Pisces",
        "moon_sign": "Scorpio",
        "rising_sign": "Leo",
        "sun_degree": 354.5,
    }
    archetype = {
        "primary": "creator",
        "shadow": "Perfectionism",
        "light_qualities": ["imagination", "vision"],
    }
    personality = {
        "big_five": {"openness": 75.0, "conscientiousness": 55.0},
        "attachment_style": "anxious-secure",
        "enneagram_type": 2,
    }

    identity = IdentityProfile(
        user_id=user.id,
        numerology=numerology,
        astrology=astrology,
        archetype=archetype,
        personality=personality,
        strengths_map=["imagination", "empathy", "adaptability"],
    )
    session.add(identity)
    await session.flush()

    result = await session.execute(
        select(IdentityProfile).where(IdentityProfile.user_id == user.id)
    )
    fetched = result.scalar_one()
    assert fetched.numerology["life_path"] == 3
    assert fetched.astrology["sun_sign"] == "Pisces"
    assert fetched.archetype["primary"] == "creator"
    assert fetched.personality["big_five"]["openness"] == 75.0
    assert "imagination" in fetched.strengths_map


# ─── HealingProfile ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_healing_profile(session: AsyncSession) -> None:
    """HealingProfile stores modalities, history, and crisis flags."""
    user = User()
    session.add(user)
    await session.flush()

    healing = HealingProfile(
        user_id=user.id,
        selected_modalities=[
            {"modality": "breathwork", "preference_score": 0.8},
            {"modality": "journaling", "preference_score": 0.6},
        ],
        practice_history={"breathwork": 5, "journaling": 3},
        max_difficulty="developing",
        crisis_protocol_active=False,
        contraindications=["hyperventilation"],
    )
    session.add(healing)
    await session.flush()

    result = await session.execute(select(HealingProfile).where(HealingProfile.user_id == user.id))
    fetched = result.scalar_one()
    assert len(fetched.selected_modalities) == 2
    assert fetched.practice_history["breathwork"] == 5
    assert fetched.max_difficulty == "developing"
    assert fetched.crisis_protocol_active is False
    assert "hyperventilation" in fetched.contraindications


# ─── WealthProfile — Encryption ────────────────────────────────────────


@pytest.mark.asyncio
async def test_wealth_encryption_roundtrip(session: AsyncSession) -> None:
    """Sensitive WealthProfile columns encrypt on write, decrypt on read."""
    user = User()
    session.add(user)
    await session.flush()

    wealth = WealthProfile(
        user_id=user.id,
        risk_tolerance="moderate",
        wealth_context={
            "income_range": "$50k-$75k",
            "has_investments": False,
            "dependents": 1,
        },
        income_range="$50k-$75k",  # SENSITIVE — encrypted
        debt_level="low",  # SENSITIVE — encrypted
        financial_goal="retirement",  # SENSITIVE — encrypted
        lever_priorities=["EARN", "KEEP", "GROW"],
    )
    session.add(wealth)
    await session.flush()

    # Read back via ORM — should be decrypted transparently
    result = await session.execute(select(WealthProfile).where(WealthProfile.user_id == user.id))
    fetched = result.scalar_one()
    assert fetched.income_range == "$50k-$75k"
    assert fetched.debt_level == "low"
    assert fetched.financial_goal == "retirement"
    assert fetched.wealth_context["income_range"] == "$50k-$75k"
    assert fetched.wealth_context["dependents"] == 1


@pytest.mark.asyncio
async def test_wealth_encrypted_at_rest(session: AsyncSession) -> None:
    """Encrypted columns store ciphertext (not plaintext) in the database."""
    user = User()
    session.add(user)
    await session.flush()

    wealth = WealthProfile(
        user_id=user.id,
        income_range="$100k-$150k",  # SENSITIVE — encrypted
    )
    session.add(wealth)
    await session.flush()

    # Read the raw column value using text() — bypasses the TypeDecorator
    raw_result = await session.execute(
        text("SELECT income_range FROM wealth_profiles WHERE user_id = :uid"),
        {"uid": user.id},
    )
    raw_value = raw_result.scalar_one()

    # The stored value should NOT be the plaintext
    assert raw_value != "$100k-$150k"
    assert raw_value is not None
    assert len(raw_value) > len("$100k-$150k")  # ciphertext is longer


@pytest.mark.asyncio
async def test_wealth_null_encrypted_fields(session: AsyncSession) -> None:
    """Null values in encrypted columns remain null."""
    user = User()
    session.add(user)
    await session.flush()

    wealth = WealthProfile(user_id=user.id)
    session.add(wealth)
    await session.flush()

    result = await session.execute(select(WealthProfile).where(WealthProfile.user_id == user.id))
    fetched = result.scalar_one()
    assert fetched.income_range is None
    assert fetched.debt_level is None
    assert fetched.wealth_context is None


@pytest.mark.asyncio
async def test_wealth_defaults(session: AsyncSession) -> None:
    """WealthProfile defaults are applied correctly."""
    user = User()
    session.add(user)
    await session.flush()

    wealth = WealthProfile(user_id=user.id)
    session.add(wealth)
    await session.flush()

    assert wealth.risk_tolerance == "moderate"
    assert wealth.financial_distress_detected is False
    assert wealth.disclaimer_acknowledged is False


# ─── CreativeProfile ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_creative_profile(session: AsyncSession) -> None:
    """CreativeProfile stores Guilford scores and Creative DNA as JSON."""
    user = User()
    session.add(user)
    await session.flush()

    creative = CreativeProfile(
        user_id=user.id,
        guilford_scores={
            "fluency": 72.0,
            "flexibility": 65.0,
            "originality": 80.0,
            "elaboration": 55.0,
            "sensitivity": 68.0,
            "redefinition": 40.0,
        },
        creative_dna={
            "structure_vs_improvisation": 0.7,
            "collaboration_vs_solitude": 0.3,
            "primary_sensory_mode": "visual",
        },
        creative_orientation="expressive-intuitive",
        medium_affinities=["writing", "visual art"],
        active_projects=2,
        preferred_production_mode="marathon",
        assessment_date=date(2026, 2, 27),
    )
    session.add(creative)
    await session.flush()

    result = await session.execute(
        select(CreativeProfile).where(CreativeProfile.user_id == user.id)
    )
    fetched = result.scalar_one()
    assert fetched.guilford_scores["originality"] == 80.0
    assert fetched.creative_dna["primary_sensory_mode"] == "visual"
    assert fetched.active_projects == 2
    assert fetched.assessment_date == date(2026, 2, 27)


# ─── PerspectiveProfile ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_perspective_profile(session: AsyncSession) -> None:
    """PerspectiveProfile stores Kegan stage, models, and distortions."""
    user = User()
    session.add(user)
    await session.flush()

    perspective = PerspectiveProfile(
        user_id=user.id,
        kegan_stage="self-authoring",
        mental_models_applied=["second-order thinking", "inversion"],
        distortions_identified=["catastrophizing", "black-and-white thinking"],
        reframes_completed=5,
        strategic_clarity_score=72.5,
        network_bridges=3,
        crisis_flag=False,
    )
    session.add(perspective)
    await session.flush()

    result = await session.execute(
        select(PerspectiveProfile).where(PerspectiveProfile.user_id == user.id)
    )
    fetched = result.scalar_one()
    assert fetched.kegan_stage == "self-authoring"
    assert "inversion" in fetched.mental_models_applied
    assert fetched.reframes_completed == 5
    assert fetched.strategic_clarity_score == 72.5


# ─── Relationships ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_relationships(session: AsyncSession) -> None:
    """User.intake, .identity, etc. relationships work bi-directionally."""
    user = User()
    session.add(user)
    await session.flush()

    intake = IntakeData(
        user_id=user.id,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="purpose",
    )
    identity = IdentityProfile(
        user_id=user.id,
        numerology={"life_path": 7},
    )
    session.add_all([intake, identity])
    await session.flush()

    # Re-fetch user to populate relationships
    result = await session.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one()

    # Access via await for async lazy loading
    loaded_intake = await fetched.awaitable_attrs.intake
    loaded_identity = await fetched.awaitable_attrs.identity

    assert loaded_intake is not None
    assert loaded_intake.full_name == "Test User"
    assert loaded_identity is not None
    assert loaded_identity.numerology["life_path"] == 7


@pytest.mark.asyncio
async def test_cascade_delete(session: AsyncSession) -> None:
    """Deleting a User cascades to all child rows."""
    user = User()
    session.add(user)
    await session.flush()

    intake = IntakeData(
        user_id=user.id,
        full_name="Delete Me",
        birth_date=date(2000, 1, 1),
        intention="career",
    )
    healing = HealingProfile(user_id=user.id)
    session.add_all([intake, healing])
    await session.flush()

    user_id = user.id
    await session.delete(user)
    await session.flush()

    # Verify child rows are gone
    intake_result = await session.execute(select(IntakeData).where(IntakeData.user_id == user_id))
    assert intake_result.scalar_one_or_none() is None

    healing_result = await session.execute(
        select(HealingProfile).where(HealingProfile.user_id == user_id)
    )
    assert healing_result.scalar_one_or_none() is None


# ─── Repr ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_model_repr(session: AsyncSession) -> None:
    """Model __repr__ methods return useful strings."""
    user = User()
    session.add(user)
    await session.flush()

    assert "User" in repr(user)
    assert user.id in repr(user)

    intake = IntakeData(
        user_id=user.id,
        full_name="Repr Test",
        birth_date=date(2000, 1, 1),
        intention="career",
    )
    session.add(intake)
    await session.flush()

    assert "IntakeData" in repr(intake)
    assert "Repr Test" in repr(intake)

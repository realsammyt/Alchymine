"""Tests for UserProfile v2.0 schema."""

from __future__ import annotations

from datetime import date, datetime

from alchymine.engine.profile import (
    ArchetypeProfile,
    ArchetypeType,
    AstrologyProfile,
    AttachmentStyle,
    BigFiveScores,
    CreativeLayer,
    GuilfordScores,
    IdentityLayer,
    IntakeData,
    Intention,
    NumerologyProfile,
    PersonalityProfile,
    PerspectiveLayer,
    UserProfile,
)


def test_intake_data_creation() -> None:
    intake = IntakeData(
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        intention=Intention.FAMILY,
    )
    assert intake.full_name == "Maria Elena Vasquez"
    assert intake.birth_date == date(1992, 3, 15)
    assert intake.intention == Intention.FAMILY


def test_numerology_profile_master_numbers() -> None:
    profile = NumerologyProfile(
        life_path=11,
        expression=22,
        soul_urge=33,
        personality=5,
        personal_year=7,
        personal_month=3,
        is_master_number=True,
    )
    assert profile.is_master_number is True
    assert profile.life_path == 11


def test_full_user_profile() -> None:
    now = datetime.utcnow()
    profile = UserProfile(
        id="test-uuid",
        created_at=now,
        updated_at=now,
        intake=IntakeData(
            full_name="Test User",
            birth_date=date(1990, 6, 15),
            intention=Intention.CAREER,
        ),
        identity=IdentityLayer(
            numerology=NumerologyProfile(
                life_path=7,
                expression=3,
                soul_urge=5,
                personality=8,
                personal_year=4,
                personal_month=1,
            ),
            astrology=AstrologyProfile(
                sun_sign="Gemini",
                sun_degree=85.0,
                moon_sign="Aries",
                moon_degree=15.0,
            ),
            archetype=ArchetypeProfile(
                primary=ArchetypeType.SAGE,
                secondary=ArchetypeType.EXPLORER,
                shadow="Cynicism",
            ),
            personality=PersonalityProfile(
                big_five=BigFiveScores(
                    openness=80.0,
                    conscientiousness=60.0,
                    extraversion=40.0,
                    agreeableness=65.0,
                    neuroticism=35.0,
                ),
                attachment_style=AttachmentStyle.SECURE,
            ),
        ),
    )
    assert profile.version == "2.0"
    assert profile.identity is not None
    assert profile.identity.numerology.life_path == 7
    assert profile.identity.archetype.primary == ArchetypeType.SAGE
    assert profile.healing is not None  # default factory
    assert profile.wealth is not None
    assert profile.creative is not None
    assert profile.perspective is not None


def test_guilford_scores() -> None:
    scores = GuilfordScores(
        fluency=75.0,
        flexibility=60.0,
        originality=85.0,
        elaboration=50.0,
        sensitivity=70.0,
        redefinition=65.0,
    )
    assert scores.originality == 85.0


def test_creative_layer_defaults() -> None:
    creative = CreativeLayer()
    assert creative.guilford_scores is None
    assert creative.active_projects == 0


def test_perspective_layer_defaults() -> None:
    perspective = PerspectiveLayer()
    assert perspective.kegan_stage is None
    assert perspective.crisis_flag is False
    assert perspective.reframes_completed == 0


def test_profile_systems_engaged() -> None:
    now = datetime.utcnow()
    profile = UserProfile(
        id="test",
        created_at=now,
        updated_at=now,
        intake=IntakeData(
            full_name="Test",
            birth_date=date(2000, 1, 1),
            intention=Intention.PURPOSE,
        ),
        systems_engaged=["core", "healing", "wealth"],
    )
    assert len(profile.systems_engaged) == 3

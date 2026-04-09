"""Tests for the Growth Assistant context builder.

The context builder converts a :class:`UserProfile` into a compact
natural-language summary that the chat endpoint injects into the LLM
system prompt so every reply is grounded in the user's actual data.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from alchymine.agents.growth.context_builder import build_user_context
from alchymine.engine.profile import (
    ArchetypeProfile,
    ArchetypeType,
    AstrologyProfile,
    AttachmentStyle,
    BigFiveScores,
    IdentityLayer,
    IntakeData,
    Intention,
    NumerologyProfile,
    PersonalityProfile,
    UserProfile,
    WealthContext,
)


def _make_profile(*, with_identity: bool = True, active_plan_day: int | None = None) -> UserProfile:
    """Build a UserProfile fixture for the tests."""
    intake = IntakeData(
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        birth_time=time(14, 14),
        birth_city="Mexico City",
        intention=Intention.FAMILY,
        wealth_context=WealthContext(income_range="$50k-$75k"),
    )

    identity: IdentityLayer | None = None
    if with_identity:
        identity = IdentityLayer(
            numerology=NumerologyProfile(
                life_path=7,
                expression=3,
                soul_urge=5,
                personality=1,
                personal_year=4,
                personal_month=2,
                is_master_number=False,
            ),
            astrology=AstrologyProfile(
                sun_sign="Pisces",
                moon_sign="Scorpio",
                rising_sign="Leo",
                sun_degree=354.5,
                moon_degree=218.3,
                rising_degree=120.7,
            ),
            archetype=ArchetypeProfile(
                primary=ArchetypeType.SAGE,
                secondary=ArchetypeType.CAREGIVER,
                shadow="Perfectionism",
                light_qualities=["wise", "patient"],
                shadow_qualities=["overthinking"],
            ),
            personality=PersonalityProfile(
                big_five=BigFiveScores(
                    openness=82.0,
                    conscientiousness=64.0,
                    extraversion=45.0,
                    agreeableness=78.0,
                    neuroticism=40.0,
                ),
                attachment_style=AttachmentStyle.SECURE,
            ),
            strengths_map=["wisdom", "empathy", "patience"],
        )

    return UserProfile(
        id="user-test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        intake=intake,
        identity=identity,
        active_plan_day=active_plan_day,
    )


def test_build_user_context_returns_empty_when_profile_none() -> None:
    """No profile means no context block."""
    assert build_user_context(None) == ""


def test_build_user_context_includes_identity_summary() -> None:
    """A populated identity layer surfaces life path, sun sign, archetype, traits."""
    profile = _make_profile()
    result = build_user_context(profile)

    assert "[User Profile Summary]" in result
    assert "Life Path: 7" in result
    assert "Pisces" in result
    assert "Scorpio" in result
    assert "Sage" in result.lower() or "sage" in result.lower()
    assert "openness" in result.lower()


def test_build_user_context_includes_top_big_five_traits() -> None:
    """The two highest Big Five scores are surfaced."""
    profile = _make_profile()
    result = build_user_context(profile)
    # Openness=82 is the top trait, agreeableness=78 is second.
    assert "openness" in result.lower()
    assert "82" in result
    assert "agreeableness" in result.lower()


def test_build_user_context_includes_attachment_style() -> None:
    profile = _make_profile()
    result = build_user_context(profile)
    assert "secure" in result.lower()


def test_build_user_context_includes_intention() -> None:
    profile = _make_profile()
    result = build_user_context(profile)
    assert "family" in result.lower()


def test_build_user_context_includes_active_plan_day() -> None:
    profile = _make_profile(active_plan_day=12)
    result = build_user_context(profile)
    assert "12/90" in result


def test_build_user_context_handles_intake_only_profile() -> None:
    """A profile with no identity layer still produces a useful summary."""
    profile = _make_profile(with_identity=False)
    result = build_user_context(profile)
    assert "[User Profile Summary]" in result
    assert "Maria Elena Vasquez" in result
    assert "family" in result.lower()
    # No identity-layer fields should appear
    assert "Life Path" not in result
    assert "Pisces" not in result


def test_build_user_context_top_traits_are_sorted_descending() -> None:
    """Top traits are ordered highest score first."""
    profile = _make_profile()
    result = build_user_context(profile)
    # Find the top-traits line and verify openness comes before agreeableness.
    lines = [line for line in result.splitlines() if "Big Five" in line]
    assert lines, "Big Five line not found"
    line = lines[0].lower()
    assert line.index("openness") < line.index("agreeableness")

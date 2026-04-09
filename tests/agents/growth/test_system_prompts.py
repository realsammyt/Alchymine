"""Tests for the Growth Assistant system prompts.

The system prompts must:
- Default to the main coach prompt for unknown system keys.
- Provide a specialist for each of the five Alchymine systems.
- Include explicit safety guardrails (no diagnosis, no specific
  medical/legal/financial advice, crisis referrals).
- Use warm, non-judgemental language.
- Interpolate the user's profile context when one is supplied.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from alchymine.agents.growth.system_prompts import (
    MAIN_COACH_PROMPT,
    SYSTEM_PROMPTS,
    build_system_prompt,
    get_system_prompt,
)
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
)


# ─── Constants ──────────────────────────────────────────────────────────


SYSTEM_KEYS = ("intelligence", "healing", "wealth", "creative", "perspective")


def _profile() -> UserProfile:
    return UserProfile(
        id="user-test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        intake=IntakeData(
            full_name="Maria Elena Vasquez",
            birth_date=date(1992, 3, 15),
            birth_time=time(14, 14),
            intention=Intention.HEALTH,
        ),
        identity=IdentityLayer(
            numerology=NumerologyProfile(
                life_path=7,
                expression=3,
                soul_urge=5,
                personality=1,
                personal_year=4,
                personal_month=2,
            ),
            astrology=AstrologyProfile(
                sun_sign="Pisces",
                moon_sign="Scorpio",
                sun_degree=354.5,
                moon_degree=218.3,
            ),
            archetype=ArchetypeProfile(
                primary=ArchetypeType.SAGE,
                shadow="Perfectionism",
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
        ),
    )


# ─── MAIN_COACH_PROMPT ──────────────────────────────────────────────────


def test_main_coach_prompt_identifies_growth_assistant() -> None:
    assert "Growth Assistant" in MAIN_COACH_PROMPT


def test_main_coach_prompt_mentions_all_five_systems() -> None:
    text = MAIN_COACH_PROMPT.lower()
    assert "intelligence" in text
    assert "healing" in text
    assert "wealth" in text
    assert "creative" in text
    assert "perspective" in text


def test_main_coach_prompt_has_safety_guardrails() -> None:
    text = MAIN_COACH_PROMPT.lower()
    # Diagnosis disclaimer
    assert "diagnose" in text
    # Professional referral
    assert "professional" in text or "clinician" in text
    # Crisis support
    assert "crisis" in text or "988" in text


def test_main_coach_prompt_has_non_judgemental_language() -> None:
    text = MAIN_COACH_PROMPT.lower()
    # Look for explicit non-judgemental language
    assert "non-judgemental" in text or "non-judgmental" in text or "warm" in text


# ─── SYSTEM_PROMPTS dict ────────────────────────────────────────────────


def test_system_prompts_has_all_five_systems() -> None:
    for key in SYSTEM_KEYS:
        assert key in SYSTEM_PROMPTS, f"missing specialist prompt for {key!r}"


@pytest.mark.parametrize("key", SYSTEM_KEYS)
def test_system_prompt_extends_main_coach(key: str) -> None:
    """Each specialist must include the full main coach prompt."""
    assert MAIN_COACH_PROMPT in SYSTEM_PROMPTS[key]


@pytest.mark.parametrize("key", SYSTEM_KEYS)
def test_system_prompt_has_specialist_focus(key: str) -> None:
    """Each specialist must mention its own domain explicitly."""
    text = SYSTEM_PROMPTS[key].lower()
    assert key in text


def test_wealth_specialist_blocks_specific_investment_advice() -> None:
    """The wealth specialist must explicitly forbid specific investment advice."""
    text = SYSTEM_PROMPTS["wealth"].lower()
    assert "never give specific investment advice" in text or "never give" in text


def test_healing_specialist_mentions_trauma_safety() -> None:
    text = SYSTEM_PROMPTS["healing"].lower()
    assert "trauma" in text


# ─── get_system_prompt ──────────────────────────────────────────────────


def test_get_system_prompt_none_returns_main_coach() -> None:
    assert get_system_prompt(None) == MAIN_COACH_PROMPT


def test_get_system_prompt_unknown_returns_main_coach() -> None:
    assert get_system_prompt("nonsense") == MAIN_COACH_PROMPT


@pytest.mark.parametrize("key", SYSTEM_KEYS)
def test_get_system_prompt_returns_specialist(key: str) -> None:
    assert get_system_prompt(key) == SYSTEM_PROMPTS[key]


# ─── build_system_prompt (with profile context) ─────────────────────────


def test_build_system_prompt_no_profile_returns_base() -> None:
    assert build_system_prompt(None, None) == MAIN_COACH_PROMPT


def test_build_system_prompt_appends_profile_context() -> None:
    """The user's profile summary is appended to the prompt."""
    result = build_system_prompt(None, _profile())
    assert MAIN_COACH_PROMPT in result
    assert "[User Profile Summary]" in result
    assert "Life Path: 7" in result
    assert "Pisces" in result


def test_build_system_prompt_uses_specialist_when_key_provided() -> None:
    result = build_system_prompt("healing", _profile())
    assert SYSTEM_PROMPTS["healing"][:200] in result
    assert "Life Path: 7" in result


def test_build_system_prompt_with_unknown_key_falls_back_to_main() -> None:
    result = build_system_prompt("xyz", _profile())
    assert MAIN_COACH_PROMPT in result
    assert "Life Path: 7" in result

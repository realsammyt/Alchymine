"""Shared test fixtures for Alchymine."""

from __future__ import annotations

import os

# Enable Celery eager mode before any Celery imports — tasks execute
# synchronously in-process so tests never need a running Redis broker.
os.environ.setdefault("CELERY_ALWAYS_EAGER", "true")

# Set required secrets before any module that imports get_settings() is loaded.
# The JWT key must be at least 32 chars and not the default dev value.
# The promo code must be at least 6 chars.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-minimum-32-characters-long")
os.environ.setdefault("SIGNUP_PROMO_CODE", "alchyours")

from datetime import date, time

import pytest

from alchymine.engine.profile import (
    AstrologyProfile,
    AttachmentStyle,
    BigFiveScores,
    IntakeData,
    Intention,
    NumerologyProfile,
    PersonalityProfile,
    WealthContext,
)


@pytest.fixture
def sample_intake() -> IntakeData:
    """Maria Elena Vasquez — the sample user from the PRD."""
    return IntakeData(
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        birth_time=time(14, 14),
        birth_city="Mexico City",
        intention=Intention.FAMILY,
        assessment_responses={
            "big_five_1": 4,
            "big_five_2": 2,
            "big_five_3": 3,
            "big_five_4": 2,
            "big_five_5": 4,
            "big_five_6": 2,
            "big_five_7": 5,
            "big_five_8": 1,
            "big_five_9": 3,
            "big_five_10": 3,
            "big_five_11": 4,
            "big_five_12": 2,
            "big_five_13": 3,
            "big_five_14": 3,
            "big_five_15": 4,
            "big_five_16": 2,
            "big_five_17": 4,
            "big_five_18": 2,
            "big_five_19": 2,
            "big_five_20": 2,
            "attachment_1": 4,
            "attachment_2": 3,
            "attachment_3": 4,
            "attachment_4": 2,
            "risk_1": 3,
            "risk_2": 3,
            "risk_3": 2,
        },
        wealth_context=WealthContext(
            income_range="$50k-$75k",
            has_investments=False,
            has_business=False,
            dependents=1,
        ),
    )


@pytest.fixture
def sample_numerology() -> NumerologyProfile:
    """Pre-calculated numerology for Maria Elena Vasquez, born 1992-03-15."""
    return NumerologyProfile(
        life_path=3,
        expression=6,
        soul_urge=5,
        personality=1,
        personal_year=7,
        personal_month=3,
        maturity=9,
        is_master_number=False,
        chaldean_name=None,
        calculation_system="pythagorean",
    )


@pytest.fixture
def sample_astrology() -> AstrologyProfile:
    """Approximate astrology for Maria born March 15, 1992."""
    return AstrologyProfile(
        sun_sign="Pisces",
        moon_sign="Scorpio",
        rising_sign="Leo",
        sun_degree=354.5,
        moon_degree=218.3,
        rising_degree=120.7,
    )


@pytest.fixture
def sample_big_five() -> BigFiveScores:
    """Sample Big Five scores."""
    return BigFiveScores(
        openness=75.0,
        conscientiousness=55.0,
        extraversion=60.0,
        agreeableness=80.0,
        neuroticism=45.0,
    )


@pytest.fixture
def sample_personality(sample_big_five: BigFiveScores) -> PersonalityProfile:
    """Sample personality profile."""
    return PersonalityProfile(
        big_five=sample_big_five,
        attachment_style=AttachmentStyle.ANXIOUS_SECURE,
        enneagram_type=2,
        enneagram_wing=3,
    )

"""Tests for generative art prompt builders."""

from __future__ import annotations

import pytest

from alchymine.llm.art_prompts import (
    STYLE_PRESETS,
    ArtSystem,
    build_report_hero_prompt,
)


def test_style_presets_cover_all_systems() -> None:
    systems = {s.value for s in ArtSystem}
    assert set(STYLE_PRESETS.keys()) == systems


def test_build_report_hero_prompt_returns_string() -> None:
    profile: dict = {
        "archetype": "The Visionary",
        "zodiac_sign": "Pisces",
        "big_five": {"openness": 85, "conscientiousness": 60},
    }
    prompt = build_report_hero_prompt(profile)
    assert isinstance(prompt, str)
    assert len(prompt) > 20


def test_build_report_hero_prompt_includes_archetype() -> None:
    profile: dict = {"archetype": "The Alchemist"}
    prompt = build_report_hero_prompt(profile)
    assert "alchemist" in prompt.lower() or "transformation" in prompt.lower()


def test_build_report_hero_prompt_includes_zodiac_themes() -> None:
    profile: dict = {"zodiac_sign": "Aries"}
    prompt = build_report_hero_prompt(profile)
    # Fire element should appear for Aries
    assert any(word in prompt.lower() for word in ["fire", "flame", "aries", "ram", "warrior"])


def test_build_report_hero_prompt_high_openness_mood() -> None:
    profile: dict = {"big_five": {"openness": 90}}
    prompt = build_report_hero_prompt(profile)
    assert any(
        word in prompt.lower()
        for word in ["surreal", "imaginative", "dreamlike", "abstract", "creative", "vivid"]
    )


def test_build_report_hero_prompt_low_openness_mood() -> None:
    profile: dict = {"big_five": {"openness": 20}}
    prompt = build_report_hero_prompt(profile)
    assert any(
        word in prompt.lower()
        for word in ["grounded", "structured", "classical", "serene", "calm"]
    )


def test_build_report_hero_prompt_system_preset() -> None:
    profile: dict = {"system": "wealth"}
    prompt = build_report_hero_prompt(profile)
    assert any(
        word in prompt.lower()
        for word in ["wealth", "gold", "abundance", "prosperity", "financial"]
    )


def test_build_report_hero_prompt_empty_profile() -> None:
    """Empty profile should still produce a valid prompt."""
    prompt = build_report_hero_prompt({})
    assert isinstance(prompt, str)
    assert len(prompt) > 10


@pytest.mark.parametrize("system", [s.value for s in ArtSystem])
def test_style_preset_each_system(system: str) -> None:
    profile: dict = {"system": system}
    prompt = build_report_hero_prompt(profile)
    assert isinstance(prompt, str)
    assert len(prompt) > 20

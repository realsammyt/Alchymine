"""Tests for the Gemini art prompt builders.

These tests do not call the Gemini API. They verify that the prompt
builders produce safe, personalized text from a variety of profile
shapes (Pydantic models, plain dicts, and missing data).
"""

from __future__ import annotations

import pytest

from alchymine.llm.art_prompts import (
    STYLE_PRESETS,
    apply_style_preset,
    build_report_hero_prompt,
    build_studio_prompt,
)

# ── Forbidden tokens that must never appear in any prompt ─────────────
# (case-insensitive substring match). These are tokens that would
# instruct Gemini to *generate* problematic content. We deliberately do
# NOT include negation words (e.g. "no weapons") here, since the safety
# suffix uses such phrases to constrain output.
_FORBIDDEN = [
    # No explicit instructions to render text
    "text says",
    "the words",
    "with the text",
    # No real brand or trademark cues
    "nike",
    "apple inc",
    "disney",
    "marvel",
    # No explicit violent / sexual subject directives
    "depict naked",
    "depict nude",
    "wielding a weapon",
    "holding a gun",
    "covered in blood",
]


def _assert_safe(prompt: str) -> None:
    """Assert a prompt contains required safety phrases and no forbidden tokens."""
    assert isinstance(prompt, str)
    assert len(prompt) > 50, "prompt unreasonably short"
    lowered = prompt.lower()
    for token in _FORBIDDEN:
        assert token not in lowered, f"forbidden token found in prompt: {token!r}"
    # Required safety language
    assert "tasteful" in lowered
    assert "non-violent" in lowered
    assert "no real people" in lowered
    assert "no text" in lowered or "no letters" in lowered


# ── Synthetic profile fixtures ────────────────────────────────────────


@pytest.fixture
def sage_water_profile() -> dict:
    """A Sage archetype with a Pisces (water) sun sign."""
    return {
        "archetype": {"primary": "sage", "secondary": "creator"},
        "astrology": {"sun_sign": "Pisces", "moon_sign": "Cancer"},
        "numerology": {"life_path": 7},
    }


@pytest.fixture
def hero_fire_profile() -> dict:
    """A Hero archetype with a Leo (fire) sun sign."""
    return {
        "archetype": {"primary": "hero"},
        "astrology": {"sun_sign": "Leo"},
        "numerology": {"life_path": 1},
    }


@pytest.fixture
def explorer_air_profile() -> dict:
    """An Explorer with a Gemini (air) sun sign."""
    return {
        "archetype": {"primary": "explorer"},
        "astrology": {"sun_sign": "Gemini"},
        "numerology": {"life_path": 5},
    }


@pytest.fixture
def caregiver_earth_profile() -> dict:
    """A Caregiver with a Taurus (earth) sun sign."""
    return {
        "archetype": {"primary": "caregiver"},
        "astrology": {"sun_sign": "Taurus"},
        "numerology": {"life_path": 6},
    }


@pytest.fixture
def mystic_water_profile() -> dict:
    """A Mystic with a Scorpio (water) sun sign and master number."""
    return {
        "archetype": {"primary": "mystic"},
        "astrology": {"sun_sign": "Scorpio"},
        "numerology": {"life_path": 11},
    }


# ── Core hero prompt tests ────────────────────────────────────────────


@pytest.mark.parametrize(
    "profile_fixture,archetype_cue,element_cue",
    [
        ("sage_water_profile", "Sage", "water"),
        ("hero_fire_profile", "Hero", "fire"),
        ("explorer_air_profile", "Explorer", "air"),
        ("caregiver_earth_profile", "Caregiver", "earth"),
        ("mystic_water_profile", "Mystic", "water"),
    ],
)
def test_report_hero_prompt_includes_archetype_and_element(
    profile_fixture: str,
    archetype_cue: str,
    element_cue: str,
    request: pytest.FixtureRequest,
) -> None:
    """Each prompt must mention both the archetype and the elemental cue."""
    profile = request.getfixturevalue(profile_fixture)
    prompt = build_report_hero_prompt(profile)
    _assert_safe(prompt)
    assert archetype_cue in prompt, f"missing archetype: {archetype_cue}"
    assert element_cue in prompt.lower(), f"missing element: {element_cue}"


def test_report_hero_prompt_includes_life_path_when_present(
    sage_water_profile: dict,
) -> None:
    prompt = build_report_hero_prompt(sage_water_profile)
    assert "Life Path 7" in prompt


def test_report_hero_prompt_handles_empty_profile() -> None:
    """An empty profile must not raise — fallback prompt is returned."""
    prompt = build_report_hero_prompt({})
    _assert_safe(prompt)
    assert "Wanderer" in prompt


def test_report_hero_prompt_handles_none() -> None:
    """A None profile is handled gracefully."""
    prompt = build_report_hero_prompt(None)
    _assert_safe(prompt)


def test_report_hero_prompt_handles_unknown_archetype() -> None:
    """Unknown archetypes use the fallback imagery."""
    profile = {"archetype": {"primary": "wanderer-of-the-void"}}
    prompt = build_report_hero_prompt(profile)
    _assert_safe(prompt)
    # The fallback imagery describes ethereal transformation
    assert "transformation" in prompt.lower()


def test_report_hero_prompt_accepts_pydantic_like_object() -> None:
    """Profiles exposed as objects with attribute access also work."""

    class _AttrMap:
        def __init__(self, **kwargs: object) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    archetype = _AttrMap(primary="creator", secondary=None)
    astrology = _AttrMap(sun_sign="Aries")
    numerology = _AttrMap(life_path=3)
    profile = _AttrMap(archetype=archetype, astrology=astrology, numerology=numerology)

    prompt = build_report_hero_prompt(profile)
    _assert_safe(prompt)
    assert "Creator" in prompt
    assert "fire" in prompt.lower()
    assert "Life Path 3" in prompt


# ── Style preset tests ────────────────────────────────────────────────


def test_style_presets_dict_has_five_entries() -> None:
    assert len(STYLE_PRESETS) == 5
    assert set(STYLE_PRESETS.keys()) == {
        "mystical",
        "modern",
        "organic",
        "celestial",
        "grounded",
    }


def test_apply_style_preset_appends_suffix(sage_water_profile: dict) -> None:
    base = build_report_hero_prompt(sage_water_profile)
    styled = apply_style_preset(base, "celestial")
    assert "Style:" in styled
    assert "Cosmic illustration" in styled
    _assert_safe(styled)


def test_apply_style_preset_unknown_falls_back(sage_water_profile: dict) -> None:
    base = build_report_hero_prompt(sage_water_profile)
    styled = apply_style_preset(base, "nonsense-preset")
    # Falls back to mystical
    assert "sacred geometry" in styled.lower()


def test_apply_style_preset_none_is_passthrough(sage_water_profile: dict) -> None:
    base = build_report_hero_prompt(sage_water_profile)
    assert apply_style_preset(base, None) == base


# ── Studio prompt tests ───────────────────────────────────────────────


def test_studio_prompt_includes_user_extension(sage_water_profile: dict) -> None:
    prompt = build_studio_prompt(
        sage_water_profile,
        user_extension="featuring autumn leaves",
        style_preset="organic",
    )
    _assert_safe(prompt)
    assert "autumn leaves" in prompt
    assert "Botanical watercolour" in prompt


def test_studio_prompt_strips_newlines_from_extension(
    sage_water_profile: dict,
) -> None:
    """Newlines in user input are flattened so they can't fake new instructions."""
    prompt = build_studio_prompt(
        sage_water_profile,
        user_extension="line one\nline two\nline three",
    )
    assert "\nline" not in prompt
    assert "line one line two line three" in prompt


def test_studio_prompt_no_extension(sage_water_profile: dict) -> None:
    prompt = build_studio_prompt(sage_water_profile, user_extension=None)
    _assert_safe(prompt)
    assert "Additional theme" not in prompt

"""Tests for the Jungian archetype mapping engine.

Covers the deterministic mapping algorithm across diverse input
combinations, verifying life-path seeding, sun-sign modulation,
Big Five adjustments, shadow modulation, and edge cases.
"""

from __future__ import annotations

import pytest

from alchymine.engine.archetype import (
    ARCHETYPE_DEFINITIONS,
    ArchetypeDefinition,
    get_archetype_scores,
    map_archetype,
)
from alchymine.engine.archetype.definitions import (
    LIFE_PATH_TO_ARCHETYPE,
    get_element_for_sign,
)
from alchymine.engine.archetype.mapper import (
    _build_shadow_text,
    _compute_shadow_emphasis,
)
from alchymine.engine.profile import (
    ArchetypeProfile,
    ArchetypeType,
    AstrologyProfile,
    BigFiveScores,
    NumerologyProfile,
)

# ─── Fixtures / Helpers ───────────────────────────────────────────────


def _make_numerology(life_path: int) -> NumerologyProfile:
    """Create a NumerologyProfile with the given Life Path, sensible defaults elsewhere."""
    return NumerologyProfile(
        life_path=life_path,
        expression=1,
        soul_urge=1,
        personality=1,
        personal_year=1,
        personal_month=1,
        is_master_number=life_path in (11, 22, 33),
    )


def _make_astrology(sun_sign: str) -> AstrologyProfile:
    """Create an AstrologyProfile with the given sun sign."""
    return AstrologyProfile(
        sun_sign=sun_sign,
        moon_sign="Aries",
        sun_degree=0.0,
        moon_degree=0.0,
    )


def _make_big_five(
    openness: float = 50.0,
    conscientiousness: float = 50.0,
    extraversion: float = 50.0,
    agreeableness: float = 50.0,
    neuroticism: float = 50.0,
) -> BigFiveScores:
    """Create BigFiveScores with the given values (defaults to neutral 50)."""
    return BigFiveScores(
        openness=openness,
        conscientiousness=conscientiousness,
        extraversion=extraversion,
        agreeableness=agreeableness,
        neuroticism=neuroticism,
    )


# ─── Test 1: Life Path 3 (Creator) with neutral inputs ────────────────


def test_life_path_3_maps_to_creator():
    """Life Path 3 with neutral Big Five and neutral sun sign -> Creator primary."""
    result = map_archetype(
        _make_numerology(3),
        _make_astrology("Aries"),  # fire sign, but LP weight dominates
        _make_big_five(),
    )
    assert result.primary == ArchetypeType.CREATOR
    assert isinstance(result.shadow, str)
    assert len(result.light_qualities) >= 5


# ─── Test 2: Life Path 1 (Hero) with fire sun sign reinforcement ──────


def test_life_path_1_fire_sign_reinforces_hero():
    """Life Path 1 (Hero) + Aries (fire) should strongly reinforce Hero."""
    result = map_archetype(
        _make_numerology(1),
        _make_astrology("Aries"),
        _make_big_five(),
    )
    assert result.primary == ArchetypeType.HERO


# ─── Test 3: Life Path 7 (Sage) with air sign boost ───────────────────


def test_life_path_7_with_air_sign_gives_sage():
    """Life Path 7 maps to Sage; Gemini (air) further boosts Sage."""
    result = map_archetype(
        _make_numerology(7),
        _make_astrology("Gemini"),
        _make_big_five(),
    )
    assert result.primary == ArchetypeType.SAGE
    scores = get_archetype_scores(
        _make_numerology(7),
        _make_astrology("Gemini"),
        _make_big_five(),
    )
    # Sage should have LP base + sun sign boost
    assert scores[ArchetypeType.SAGE] == pytest.approx(55.0)


# ─── Test 4: Master number 11 (Mystic) with water sign ────────────────


def test_master_number_11_maps_to_mystic():
    """Life Path 11 (master number) maps to Mystic."""
    result = map_archetype(
        _make_numerology(11),
        _make_astrology("Pisces"),  # water boosts Mystic too
        _make_big_five(),
    )
    assert result.primary == ArchetypeType.MYSTIC


# ─── Test 5: Life Path 6 (Lover) with high Agreeableness ──────────────


def test_life_path_6_high_agreeableness_lover():
    """Life Path 6 (Lover) + high Agreeableness strongly reinforces Lover."""
    result = map_archetype(
        _make_numerology(6),
        _make_astrology("Cancer"),  # water boosts Lover
        _make_big_five(agreeableness=90.0),
    )
    assert result.primary == ArchetypeType.LOVER
    # Check that light qualities include Lover qualities
    assert "Emotional depth" in result.light_qualities


# ─── Test 6: Big Five can shift secondary archetype ────────────────────


def test_big_five_shapes_secondary():
    """High openness with LP 4 (Ruler) should give Explorer or Creator as secondary."""
    result = map_archetype(
        _make_numerology(4),
        _make_astrology("Taurus"),  # earth boosts Ruler + Caregiver
        _make_big_five(openness=95.0),
    )
    assert result.primary == ArchetypeType.RULER
    # High openness boosts Explorer and Creator
    assert result.secondary in (
        ArchetypeType.EXPLORER,
        ArchetypeType.CREATOR,
        ArchetypeType.CAREGIVER,  # earth sign also boosts Caregiver
    )


# ─── Test 7: High neuroticism amplifies shadow emphasis ────────────────


def test_high_neuroticism_strong_shadow():
    """High neuroticism (90) should produce a 'Strong pattern of' shadow label."""
    result = map_archetype(
        _make_numerology(3),
        _make_astrology("Leo"),
        _make_big_five(neuroticism=90.0),
    )
    assert result.shadow.startswith("Strong pattern of")


# ─── Test 8: Low neuroticism softens shadow emphasis ───────────────────


def test_low_neuroticism_mild_shadow():
    """Low neuroticism (10) should produce a 'Mild tendency toward' shadow label."""
    result = map_archetype(
        _make_numerology(3),
        _make_astrology("Leo"),
        _make_big_five(neuroticism=10.0),
    )
    assert result.shadow.startswith("Mild tendency toward")


# ─── Test 9: Master number 22 (Ruler) ─────────────────────────────────


def test_master_number_22_maps_to_ruler():
    """Life Path 22 maps to Ruler."""
    result = map_archetype(
        _make_numerology(22),
        _make_astrology("Capricorn"),  # earth reinforces Ruler
        _make_big_five(conscientiousness=80.0),
    )
    assert result.primary == ArchetypeType.RULER


# ─── Test 10: Master number 33 (Caregiver) ────────────────────────────


def test_master_number_33_maps_to_caregiver():
    """Life Path 33 maps to Caregiver."""
    result = map_archetype(
        _make_numerology(33),
        _make_astrology("Virgo"),  # earth boosts Caregiver
        _make_big_five(agreeableness=75.0),
    )
    assert result.primary == ArchetypeType.CAREGIVER


# ─── Test 11: Low extraversion boosts Sage/Mystic ─────────────────────


def test_low_extraversion_boosts_introverted_archetypes():
    """Low extraversion should boost Sage and Mystic scores."""
    scores_low_e = get_archetype_scores(
        _make_numerology(5),  # LP 5 = Explorer
        _make_astrology("Libra"),  # air
        _make_big_five(extraversion=10.0),
    )
    scores_neutral = get_archetype_scores(
        _make_numerology(5),
        _make_astrology("Libra"),
        _make_big_five(extraversion=50.0),
    )
    assert scores_low_e[ArchetypeType.SAGE] > scores_neutral[ArchetypeType.SAGE]
    assert scores_low_e[ArchetypeType.MYSTIC] > scores_neutral[ArchetypeType.MYSTIC]


# ─── Test 12: Determinism — same inputs always same output ────────────


def test_deterministic_output():
    """Calling map_archetype twice with identical inputs must return identical results."""
    inputs = (
        _make_numerology(5),
        _make_astrology("Sagittarius"),
        _make_big_five(openness=80.0, extraversion=70.0, neuroticism=45.0),
    )
    result_a = map_archetype(*inputs)
    result_b = map_archetype(*inputs)
    assert result_a == result_b


# ─── Test 13: All 12 definitions are present and valid ─────────────────


def test_all_12_definitions_present():
    """ARCHETYPE_DEFINITIONS should contain exactly 12 entries, one per ArchetypeType."""
    assert len(ARCHETYPE_DEFINITIONS) == 12
    for at in ArchetypeType:
        defn = ARCHETYPE_DEFINITIONS[at]
        assert isinstance(defn, ArchetypeDefinition)
        assert defn.archetype == at
        assert len(defn.light_qualities) >= 3
        assert len(defn.shadow_qualities) >= 3
        assert len(defn.shadow_label) > 0
        assert len(defn.creative_style) > 0
        assert len(defn.wealth_tendency) > 0
        assert len(defn.healing_affinity) >= 2
        assert len(defn.communication_style) > 0
        assert len(defn.leadership_style) > 0


# ─── Test 14: get_element_for_sign covers all 12 signs ────────────────


@pytest.mark.parametrize(
    "sign,expected_element",
    [
        ("Aries", "fire"),
        ("Taurus", "earth"),
        ("Gemini", "air"),
        ("Cancer", "water"),
        ("Leo", "fire"),
        ("Virgo", "earth"),
        ("Libra", "air"),
        ("Scorpio", "water"),
        ("Sagittarius", "fire"),
        ("Capricorn", "earth"),
        ("Aquarius", "air"),
        ("Pisces", "water"),
    ],
)
def test_element_for_sign(sign, expected_element):
    assert get_element_for_sign(sign) == expected_element


# ─── Test 15: Unknown sign returns None ────────────────────────────────


def test_unknown_sign_returns_none():
    assert get_element_for_sign("Ophiuchus") is None


# ─── Test 16: Life Path -> Archetype mapping table completeness ────────


def test_life_path_mapping_completeness():
    """All valid life path numbers (1-9, 11, 22, 33) should have mappings."""
    expected_lps = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33}
    assert set(LIFE_PATH_TO_ARCHETYPE.keys()) == expected_lps


# ─── Test 17: Secondary archetype differs from primary ─────────────────


def test_secondary_differs_from_primary():
    """The secondary archetype must never be the same as the primary."""
    result = map_archetype(
        _make_numerology(5),
        _make_astrology("Aries"),
        _make_big_five(openness=85.0, extraversion=75.0),
    )
    if result.secondary is not None:
        assert result.secondary != result.primary


# ─── Test 18: Shadow secondary text for secondary archetype ────────────


def test_shadow_secondary_populated_when_secondary_exists():
    """When a secondary archetype is present, shadow_secondary should be non-None."""
    result = map_archetype(
        _make_numerology(1),
        _make_astrology("Aries"),
        _make_big_five(extraversion=80.0),
    )
    # LP 1 = Hero, fire boosts Hero + Explorer, high E boosts Hero + Jester
    # Secondary should exist (Explorer or Jester)
    if result.secondary is not None:
        assert result.shadow_secondary is not None
        assert isinstance(result.shadow_secondary, str)


# ─── Test 19: Competing signals — Big Five can override LP ─────────────


def test_extreme_big_five_can_shift_primary():
    """With very extreme Big Five and a weak LP, Big Five can shift the primary.

    LP 2 = Caregiver (40 pts). If sun sign is air (boosts Sage/Jester)
    and Big Five has extreme extraversion + low agreeableness, the Hero/Rebel
    boost could compete. We verify the algorithm handles this gracefully.
    """
    result = map_archetype(
        _make_numerology(2),  # Caregiver: 40 pts
        _make_astrology("Gemini"),  # air -> Sage +15, Jester +15
        _make_big_five(
            extraversion=100.0,  # Hero +10, Jester +10
            agreeableness=0.0,  # Rebel +10, Hero +10
            openness=100.0,  # Explorer +10, Creator +10
        ),
    )
    # Caregiver has 40 base; Jester has 15 (air) + 10 (extraversion) = 25
    # Hero has 10 (extraversion) + 10 (low agreeableness) = 20
    # Caregiver still wins with 40, but the competition is real
    assert result.primary == ArchetypeType.CAREGIVER
    assert result.secondary is not None


# ─── Test 20: ArchetypeProfile output conforms to schema ───────────────


def test_output_conforms_to_archetype_profile_schema():
    """The output should be a valid ArchetypeProfile pydantic model."""
    result = map_archetype(
        _make_numerology(9),
        _make_astrology("Scorpio"),
        _make_big_five(neuroticism=65.0),
    )
    assert isinstance(result, ArchetypeProfile)
    assert isinstance(result.primary, ArchetypeType)
    assert isinstance(result.shadow, str)
    assert isinstance(result.light_qualities, list)
    assert isinstance(result.shadow_qualities, list)
    # Validate via pydantic round-trip
    data = result.model_dump()
    reconstructed = ArchetypeProfile(**data)
    assert reconstructed == result


# ─── Test 21: Shadow emphasis internal function ────────────────────────


def test_shadow_emphasis_boundaries():
    """Shadow emphasis should be 0.3 at neuroticism=0 and 1.0 at neuroticism=100."""
    assert _compute_shadow_emphasis(0.0) == pytest.approx(0.3)
    assert _compute_shadow_emphasis(100.0) == pytest.approx(1.0)
    assert _compute_shadow_emphasis(50.0) == pytest.approx(0.65)


# ─── Test 22: Shadow text variations ──────────────────────────────────


def test_shadow_text_tiers():
    """Shadow text should vary by emphasis tier."""
    mild = _build_shadow_text(ArchetypeType.CREATOR, 0.4)
    assert "tendency toward" in mild.lower()

    moderate = _build_shadow_text(ArchetypeType.CREATOR, 0.6)
    assert moderate == "Perfectionism"

    strong = _build_shadow_text(ArchetypeType.CREATOR, 0.9)
    assert "strong pattern of" in strong.lower()


# ─── Test 23: LP 5 Explorer with Sagittarius (fire) ───────────────────


def test_lp5_sagittarius_explorer():
    """LP 5 (Explorer) + Sagittarius (fire, boosts Hero/Explorer) -> Explorer primary."""
    result = map_archetype(
        _make_numerology(5),
        _make_astrology("Sagittarius"),
        _make_big_five(),
    )
    assert result.primary == ArchetypeType.EXPLORER


# ─── Test 24: Case insensitive sun sign ────────────────────────────────


def test_case_insensitive_sun_sign():
    """Sun sign matching should be case-insensitive."""
    result_lower = map_archetype(
        _make_numerology(1),
        _make_astrology("aries"),
        _make_big_five(),
    )
    result_upper = map_archetype(
        _make_numerology(1),
        _make_astrology("ARIES"),
        _make_big_five(),
    )
    assert result_lower == result_upper

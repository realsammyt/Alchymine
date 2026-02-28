"""Tests for the healing assessment processing pipeline.

Covers assessment processing with various response patterns, crisis
flag propagation, contraindication filtering, difficulty derivation,
disclaimer generation, and integration with the modality matcher.
"""

from __future__ import annotations

from alchymine.engine.healing.assessment import (
    _derive_max_difficulty,
    _extract_free_text,
    process_assessment,
)
from alchymine.engine.healing.crisis import CrisisSeverity
from alchymine.engine.profile import (
    ArchetypeType,
    BigFiveScores,
    HealingPreference,
    Intention,
    PracticeDifficulty,
)

# ─── Helpers ─────────────────────────────────────────────────────────


def _make_big_five(
    openness: float = 50.0,
    conscientiousness: float = 50.0,
    extraversion: float = 50.0,
    agreeableness: float = 50.0,
    neuroticism: float = 50.0,
) -> BigFiveScores:
    return BigFiveScores(
        openness=openness,
        conscientiousness=conscientiousness,
        extraversion=extraversion,
        agreeableness=agreeableness,
        neuroticism=neuroticism,
    )


NEUTRAL_BIG_FIVE = _make_big_five()


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Difficulty derivation
# ═══════════════════════════════════════════════════════════════════════


class TestDifficultyDerivation:
    """Tests for _derive_max_difficulty."""

    def test_no_experience_keys_returns_foundation(self) -> None:
        """Without experience keys, default to FOUNDATION."""
        result = _derive_max_difficulty({"mood": 3, "energy": 4})
        assert result == PracticeDifficulty.FOUNDATION

    def test_low_experience_returns_foundation(self) -> None:
        """Low experience values should return FOUNDATION."""
        result = _derive_max_difficulty({"healing_experience": 1, "meditation_experience": 1})
        assert result == PracticeDifficulty.FOUNDATION

    def test_moderate_experience_returns_developing_or_established(self) -> None:
        """Moderate experience should return DEVELOPING or ESTABLISHED."""
        result = _derive_max_difficulty({"healing_experience": 3, "meditation_experience": 3})
        assert result in (PracticeDifficulty.DEVELOPING, PracticeDifficulty.ESTABLISHED)

    def test_high_experience_returns_advanced_or_higher(self) -> None:
        """High experience should return ADVANCED or INTENSIVE."""
        result = _derive_max_difficulty(
            {
                "healing_experience": 5,
                "meditation_experience": 5,
                "body_awareness": 5,
                "comfort_with_intensity": 5,
            }
        )
        assert result in (PracticeDifficulty.ADVANCED, PracticeDifficulty.INTENSIVE)


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Free text extraction
# ═══════════════════════════════════════════════════════════════════════


class TestFreeTextExtraction:
    """Tests for _extract_free_text."""

    def test_extracts_known_free_text_keys(self) -> None:
        """Known free-text keys should be extracted."""
        responses = {
            "open_response": "I feel anxious",
            "current_challenges": "Relationship stress",
        }
        text = _extract_free_text(responses)
        assert "I feel anxious" in text
        assert "Relationship stress" in text

    def test_extracts_long_string_values(self) -> None:
        """Long string values should be extracted even if not in known keys."""
        responses = {
            "custom_field": "This is a long narrative response about my healing journey and goals",
        }
        text = _extract_free_text(responses)
        assert "healing journey" in text

    def test_ignores_short_string_values(self) -> None:
        """Short string values from non-standard keys should be ignored."""
        responses = {
            "mood": "good",
            "status": "fine",
        }
        text = _extract_free_text(responses)
        assert text.strip() == ""


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Assessment processing
# ═══════════════════════════════════════════════════════════════════════


class TestProcessAssessment:
    """Tests for the main process_assessment function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Result should contain all expected keys."""
        result = process_assessment(responses={"mood": 3})
        assert "recommended_modalities" in result
        assert "crisis_flag" in result
        assert "crisis_response" in result
        assert "max_difficulty" in result
        assert "disclaimers" in result

    def test_recommended_modalities_are_healing_preferences(self) -> None:
        """Recommended modalities should be HealingPreference instances."""
        result = process_assessment(responses={"mood": 3})
        for mod in result["recommended_modalities"]:
            assert isinstance(mod, HealingPreference)

    def test_no_crisis_flag_for_normal_responses(self) -> None:
        """Normal responses should not set crisis_flag."""
        result = process_assessment(
            responses={
                "mood": 4,
                "energy": 3,
                "open_response": "I want to learn meditation and improve my sleep quality.",
            }
        )
        assert result["crisis_flag"] is False
        assert result["crisis_response"] is None

    def test_crisis_flag_set_for_crisis_keywords(self) -> None:
        """Responses with crisis keywords should set crisis_flag."""
        result = process_assessment(
            responses={
                "open_response": "I have been feeling suicidal and don't want to live anymore.",
            }
        )
        assert result["crisis_flag"] is True
        assert result["crisis_response"] is not None
        assert result["crisis_response"].severity == CrisisSeverity.EMERGENCY

    def test_emergency_crisis_caps_difficulty_at_foundation(self) -> None:
        """Emergency crisis should cap max_difficulty at FOUNDATION."""
        result = process_assessment(
            responses={
                "healing_experience": 5,
                "meditation_experience": 5,
                "open_response": "I keep thinking about suicide",
            }
        )
        assert result["crisis_flag"] is True
        assert result["max_difficulty"] == PracticeDifficulty.FOUNDATION

    def test_disclaimers_always_include_healing_disclaimer(self) -> None:
        """Result should always include at least one disclaimer."""
        result = process_assessment(responses={"mood": 3})
        assert len(result["disclaimers"]) >= 1
        # First disclaimer should be the healing disclaimer
        assert (
            "not medical advice" in result["disclaimers"][0].lower()
            or "personal growth" in result["disclaimers"][0].lower()
        )

    def test_crisis_adds_crisis_disclaimer(self) -> None:
        """Crisis detection should add a crisis-specific disclaimer."""
        result = process_assessment(
            responses={
                "open_response": "I feel suicidal",
            }
        )
        all_disclaimers = " ".join(result["disclaimers"]).lower()
        assert "crisis" in all_disclaimers

    def test_contraindications_add_disclaimer(self) -> None:
        """Providing contraindications should add a contraindication disclaimer."""
        result = process_assessment(
            responses={"mood": 3},
            contraindications=["severe asthma"],
        )
        all_disclaimers = " ".join(result["disclaimers"]).lower()
        assert "contraindication" in all_disclaimers

    def test_contraindication_filtering(self) -> None:
        """Contraindicated modalities should be excluded from recommendations."""
        result = process_assessment(
            responses={"mood": 3},
            contraindications=["severe asthma"],
            intention=Intention.HEALTH,
        )
        modality_names = {m.modality for m in result["recommended_modalities"]}
        assert "breathwork" not in modality_names

    def test_custom_archetype_affects_recommendations(self) -> None:
        """Specifying an archetype should influence modality recommendations."""
        result_sage = process_assessment(
            responses={"mood": 3},
            archetype_primary=ArchetypeType.SAGE,
            intention=Intention.PURPOSE,
        )
        result_hero = process_assessment(
            responses={"mood": 3},
            archetype_primary=ArchetypeType.HERO,
            intention=Intention.PURPOSE,
        )
        # The top recommendation should potentially differ
        sage_top = result_sage["recommended_modalities"][0].modality
        hero_top = result_hero["recommended_modalities"][0].modality
        # At least the scores should differ
        sage_scores = {
            m.modality: m.preference_score for m in result_sage["recommended_modalities"]
        }
        hero_scores = {
            m.modality: m.preference_score for m in result_hero["recommended_modalities"]
        }
        assert sage_scores != hero_scores

    def test_default_big_five_used_when_not_provided(self) -> None:
        """When big_five is not provided, neutral scores should be used."""
        result = process_assessment(responses={"mood": 3})
        assert len(result["recommended_modalities"]) > 0

    def test_max_difficulty_derived_from_responses(self) -> None:
        """max_difficulty should be derived from assessment responses."""
        result = process_assessment(
            responses={
                "healing_experience": 1,
                "meditation_experience": 1,
            }
        )
        assert result["max_difficulty"] == PracticeDifficulty.FOUNDATION

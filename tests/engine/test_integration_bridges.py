"""Tests for the cross-system integration bridge engine.

Covers XS-01 through XS-07 bridge functions.
"""

from __future__ import annotations

import pytest

from alchymine.engine.integration.bridges import (
    archetype_to_creative_style,
    check_coherence,
    cycle_to_timing,
    healing_to_perspective_sequence,
    shadow_to_block_mapping,
    synthesize_profile,
    wealth_creative_alignment,
)


class TestArchetypeToCreativeStyle:
    """XS-01: Archetype → Creative Style mapping."""

    def test_known_archetype_maps(self) -> None:
        result = archetype_to_creative_style("Creator")
        assert result.source_system == "intelligence"
        assert result.target_system == "creative"
        assert result.bridge_type == "archetype_to_creative"
        assert "generative" in result.insight.lower()
        assert result.confidence > 0.5

    def test_explorer_archetype(self) -> None:
        result = archetype_to_creative_style("Explorer")
        assert "experimental" in result.insight.lower()

    def test_sage_archetype(self) -> None:
        result = archetype_to_creative_style("Sage")
        assert "analytical" in result.insight.lower()

    def test_unknown_archetype_low_confidence(self) -> None:
        result = archetype_to_creative_style("Unknown")
        assert result.confidence < 0.5

    @pytest.mark.parametrize(
        "archetype",
        [
            "Creator",
            "Explorer",
            "Sage",
            "Hero",
            "Magician",
            "Ruler",
            "Caregiver",
            "Innocent",
            "Jester",
            "Everyperson",
            "Rebel",
            "Lover",
        ],
    )
    def test_all_archetypes_have_mappings(self, archetype: str) -> None:
        result = archetype_to_creative_style(archetype)
        assert result.confidence > 0.5
        assert len(result.insight) > 20
        assert len(result.action) > 5


class TestShadowToBlock:
    """XS-02: Shadow → Creative Block mapping."""

    def test_creator_shadow_perfectionism(self) -> None:
        result = shadow_to_block_mapping("Creator")
        assert "perfectionism" in result.insight.lower()

    def test_explorer_shadow_distraction(self) -> None:
        result = shadow_to_block_mapping("Explorer")
        assert "distraction" in result.insight.lower()

    def test_unknown_shadow_low_confidence(self) -> None:
        result = shadow_to_block_mapping("Unknown")
        assert result.confidence < 0.5

    def test_has_intervention(self) -> None:
        result = shadow_to_block_mapping("Sage")
        assert len(result.action) > 10


class TestCycleToTiming:
    """XS-03: Numerology Cycle → Timing mapping."""

    def test_year_1_start(self) -> None:
        result = cycle_to_timing(1)
        assert "start" in result.action.lower() or "launch" in result.action.lower()

    def test_year_8_scale(self) -> None:
        result = cycle_to_timing(8)
        assert "scale" in result.action.lower() or "monetize" in result.action.lower()

    def test_year_9_complete(self) -> None:
        result = cycle_to_timing(9)
        assert "complete" in result.action.lower() or "review" in result.action.lower()

    @pytest.mark.parametrize("year", range(1, 10))
    def test_all_years_have_insights(self, year: int) -> None:
        result = cycle_to_timing(year)
        assert len(result.insight) > 10
        assert result.bridge_type == "cycle_to_timing"


class TestWealthCreativeAlignment:
    """XS-04: Wealth ↔ Creative alignment."""

    def test_returns_insight(self) -> None:
        result = wealth_creative_alignment("Builder", "generative")
        assert result.source_system == "wealth"
        assert result.target_system == "creative"
        assert "generative" in result.insight.lower()

    def test_known_style_has_streams(self) -> None:
        result = wealth_creative_alignment("Achiever", "analytical")
        assert "consulting" in result.insight.lower() or "courses" in result.insight.lower()

    def test_unknown_style_still_works(self) -> None:
        result = wealth_creative_alignment("Custom", "custom_style")
        assert result.confidence > 0


class TestHealingToPerspective:
    """XS-05: Healing → Perspective sequencing."""

    def test_low_kegan_gentle(self) -> None:
        result = healing_to_perspective_sequence("breathwork", 2)
        assert "gentle" in result.insight.lower() or "grounding" in result.insight.lower()

    def test_mid_kegan_supported(self) -> None:
        result = healing_to_perspective_sequence("meditation", 3)
        assert "support" in result.insight.lower()

    def test_high_kegan_autonomous(self) -> None:
        result = healing_to_perspective_sequence("somatic", 4)
        assert "autonomous" in result.insight.lower() or "integrate" in result.insight.lower()

    def test_highest_kegan_synthesis(self) -> None:
        result = healing_to_perspective_sequence("breathwork", 5)
        assert "meta" in result.insight.lower() or "synthesis" in result.insight.lower()


class TestCoherence:
    """XS-06: Cross-system coherence check."""

    def test_no_recommendations_full_coherence(self) -> None:
        result = check_coherence([])
        assert result.coherence_score == 1.0
        assert len(result.conflicts) == 0

    def test_conflicting_rest_and_action(self) -> None:
        recs = [
            {"system": "healing", "action": "Rest and recover today"},
            {"system": "wealth", "action": "Launch your new business now"},
        ]
        result = check_coherence(recs)
        assert len(result.conflicts) > 0
        assert result.coherence_score < 1.0

    def test_too_many_recommendations(self) -> None:
        recs = [
            {"system": "intelligence", "action": "Do A"},
            {"system": "healing", "action": "Do B"},
            {"system": "wealth", "action": "Do C"},
            {"system": "creative", "action": "Do D"},
        ]
        result = check_coherence(recs)
        assert any("Too many" in c for c in result.conflicts)

    def test_three_or_fewer_no_excess_conflict(self) -> None:
        recs = [
            {"system": "intelligence", "action": "Study something"},
            {"system": "healing", "action": "Meditate today"},
            {"system": "wealth", "action": "Review budget"},
        ]
        result = check_coherence(recs)
        assert not any("Too many" in c for c in result.conflicts)


class TestSynthesizeProfile:
    """XS-07: User profile synthesis."""

    def test_empty_profile_no_insights(self) -> None:
        result = synthesize_profile()
        assert len(result) == 0

    def test_archetype_generates_xs01(self) -> None:
        result = synthesize_profile(archetype={"primary": "Creator", "shadow": "Creator"})
        assert len(result) >= 2  # XS-01 + XS-02
        types = [i.bridge_type for i in result]
        assert "archetype_to_creative" in types
        assert "shadow_to_block" in types

    def test_numerology_generates_xs03(self) -> None:
        result = synthesize_profile(numerology={"personal_year": 3})
        assert len(result) >= 1
        assert any(i.bridge_type == "cycle_to_timing" for i in result)

    def test_wealth_creative_generates_xs04(self) -> None:
        result = synthesize_profile(
            wealth_archetype="Builder",
            creative_style="generative",
        )
        assert any(i.bridge_type == "wealth_creative_alignment" for i in result)

    def test_kegan_generates_xs05(self) -> None:
        result = synthesize_profile(kegan_stage=3)
        assert any(i.bridge_type == "healing_to_perspective" for i in result)

    def test_full_profile_many_insights(self) -> None:
        result = synthesize_profile(
            numerology={"personal_year": 5},
            archetype={"primary": "Magician", "shadow": "Ruler"},
            wealth_archetype="Achiever",
            creative_style="transformative",
            kegan_stage=4,
        )
        # Should have XS-01 + XS-02 + XS-03 + XS-04 + XS-05 = 5 insights
        assert len(result) >= 5

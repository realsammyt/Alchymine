"""Tests for Creative DNA proxy derivation and production mode functions.

Covers:
- derive_creative_dna_from_proxy() with typical/edge Big Five values
- derive_creative_dna_from_proxy() with Guilford data
- derive_production_mode() for each branch (POLISH, SPRINT, MARATHON, HARVEST)
"""

from __future__ import annotations

from alchymine.engine.creative.assessment import (
    derive_creative_dna_from_proxy,
    derive_production_mode,
)
from alchymine.engine.profile import CreativeDNA, CreativeProductionMode, GuilfordScores

# ═══════════════════════════════════════════════════════════════════════════
# derive_creative_dna_from_proxy Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDeriveCreativeDnaFromProxy:
    """Tests for derive_creative_dna_from_proxy()."""

    def test_typical_big_five_produces_valid_dna(self) -> None:
        """Typical Big Five scores produce a valid CreativeDNA with values in [0,1]."""
        big_five = {
            "openness": 70,
            "conscientiousness": 60,
            "extraversion": 50,
            "agreeableness": 55,
            "neuroticism": 40,
        }
        result = derive_creative_dna_from_proxy(big_five)
        assert isinstance(result, CreativeDNA)
        assert 0.0 <= result.structure_vs_improvisation <= 1.0
        assert 0.0 <= result.collaboration_vs_solitude <= 1.0
        assert 0.0 <= result.convergent_vs_divergent <= 1.0

    def test_high_conscientiousness_is_structured(self) -> None:
        """High conscientiousness maps to low structure_vs_improvisation (structured)."""
        big_five = {"conscientiousness": 90, "extraversion": 50, "openness": 50}
        result = derive_creative_dna_from_proxy(big_five)
        assert result.structure_vs_improvisation < 0.2

    def test_low_conscientiousness_is_improvisational(self) -> None:
        """Low conscientiousness maps to high structure_vs_improvisation (improvisational)."""
        big_five = {"conscientiousness": 10, "extraversion": 50, "openness": 50}
        result = derive_creative_dna_from_proxy(big_five)
        assert result.structure_vs_improvisation > 0.8

    def test_high_extraversion_is_collaborative(self) -> None:
        """High extraversion maps to low collaboration_vs_solitude (collaborative)."""
        big_five = {"conscientiousness": 50, "extraversion": 90, "openness": 50}
        result = derive_creative_dna_from_proxy(big_five)
        assert result.collaboration_vs_solitude < 0.2

    def test_high_openness_is_divergent(self) -> None:
        """High openness maps to high convergent_vs_divergent (divergent)."""
        big_five = {"conscientiousness": 50, "extraversion": 50, "openness": 90}
        result = derive_creative_dna_from_proxy(big_five)
        assert result.convergent_vs_divergent > 0.8

    def test_with_guilford_uses_fluency_originality(self) -> None:
        """When Guilford scores provided, convergent_vs_divergent uses fluency+originality."""
        big_five = {"conscientiousness": 50, "extraversion": 50, "openness": 50}
        guilford = GuilfordScores(
            fluency=80,
            flexibility=50,
            originality=60,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )
        result = derive_creative_dna_from_proxy(big_five, guilford)
        # mean(80, 60) / 200 = 0.35 — wait, it should be (80 + 60) / 200 = 0.7
        assert abs(result.convergent_vs_divergent - 0.7) < 0.01

    def test_edge_values_all_zeros(self) -> None:
        """All-zero Big Five scores produce valid clamped values."""
        big_five = {
            "openness": 0,
            "conscientiousness": 0,
            "extraversion": 0,
            "agreeableness": 0,
            "neuroticism": 0,
        }
        result = derive_creative_dna_from_proxy(big_five)
        assert result.structure_vs_improvisation == 1.0  # (100 - 0) / 100
        assert result.collaboration_vs_solitude == 1.0  # (100 - 0) / 100
        assert result.convergent_vs_divergent == 0.0  # 0 / 100

    def test_edge_values_all_100s(self) -> None:
        """All-100 Big Five scores produce valid clamped values."""
        big_five = {
            "openness": 100,
            "conscientiousness": 100,
            "extraversion": 100,
            "agreeableness": 100,
            "neuroticism": 100,
        }
        result = derive_creative_dna_from_proxy(big_five)
        assert result.structure_vs_improvisation == 0.0
        assert result.collaboration_vs_solitude == 0.0
        assert result.convergent_vs_divergent == 1.0

    def test_defaults_for_missing_traits(self) -> None:
        """Missing Big Five traits default to 50."""
        result = derive_creative_dna_from_proxy({})
        assert result.structure_vs_improvisation == 0.5
        assert result.collaboration_vs_solitude == 0.5
        assert result.convergent_vs_divergent == 0.5

    def test_sensory_mode_defaults_to_visual(self) -> None:
        """Proxy always defaults sensory mode to visual."""
        result = derive_creative_dna_from_proxy({"openness": 70})
        assert result.primary_sensory_mode == "visual"

    def test_creative_peak_defaults_to_morning(self) -> None:
        """Proxy always defaults creative peak to morning."""
        result = derive_creative_dna_from_proxy({"openness": 70})
        assert result.creative_peak == "morning"

    def test_returns_creative_dna_type(self) -> None:
        """derive_creative_dna_from_proxy always returns a CreativeDNA instance."""
        result = derive_creative_dna_from_proxy({})
        assert isinstance(result, CreativeDNA)


# ═══════════════════════════════════════════════════════════════════════════
# derive_production_mode Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDeriveProductionMode:
    """Tests for derive_production_mode()."""

    def test_polish_mode(self) -> None:
        """High elaboration + high conscientiousness → POLISH."""
        guilford = GuilfordScores(
            fluency=50, flexibility=50, originality=50,
            elaboration=80, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=80)
        assert result == CreativeProductionMode.POLISH

    def test_sprint_mode(self) -> None:
        """High fluency + low conscientiousness → SPRINT."""
        guilford = GuilfordScores(
            fluency=80, flexibility=50, originality=50,
            elaboration=50, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=30)
        assert result == CreativeProductionMode.SPRINT

    def test_marathon_mode(self) -> None:
        """High conscientiousness + low fluency → MARATHON."""
        guilford = GuilfordScores(
            fluency=40, flexibility=50, originality=50,
            elaboration=50, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=70)
        assert result == CreativeProductionMode.MARATHON

    def test_harvest_mode(self) -> None:
        """No specific pattern → HARVEST (default)."""
        guilford = GuilfordScores(
            fluency=50, flexibility=50, originality=50,
            elaboration=50, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=50)
        assert result == CreativeProductionMode.HARVEST

    def test_polish_takes_priority_over_marathon(self) -> None:
        """When both polish and marathon conditions overlap, polish wins (checked first)."""
        guilford = GuilfordScores(
            fluency=40, flexibility=50, originality=50,
            elaboration=75, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=75)
        assert result == CreativeProductionMode.POLISH

    def test_returns_creative_production_mode_type(self) -> None:
        """derive_production_mode always returns a CreativeProductionMode."""
        guilford = GuilfordScores(
            fluency=50, flexibility=50, originality=50,
            elaboration=50, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=50)
        assert isinstance(result, CreativeProductionMode)

    def test_boundary_elaboration_70_conscientiousness_70_is_polish(self) -> None:
        """Exact boundary (elaboration=70, conscientiousness=70) → POLISH."""
        guilford = GuilfordScores(
            fluency=50, flexibility=50, originality=50,
            elaboration=70, sensitivity=50, redefinition=50,
        )
        result = derive_production_mode(guilford, conscientiousness=70)
        assert result == CreativeProductionMode.POLISH

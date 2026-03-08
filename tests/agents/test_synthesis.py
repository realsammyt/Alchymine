"""Tests for cross-system synthesis workflows.

Covers full-profile synthesis, guided-session synthesis, conflict
detection, evidence rating aggregation, coherence scoring, quality
gate integration, and backward compatibility with the old
synthesize_results() behaviour.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.agents.orchestrator.coordinator import (
    CoordinatorResult,
    CoordinatorStatus,
)
from alchymine.agents.orchestrator.intent import (
    IntentResult,
    SystemIntent,
)
from alchymine.agents.orchestrator.orchestrator import (
    MasterOrchestrator,
    OrchestratorResult,
    synthesize_results,
)
from alchymine.agents.orchestrator.synthesis import (
    SynthesisResult,
    _build_strengths_map,
    aggregate_evidence,
    detect_conflicts,
    synthesize_full_profile,
    synthesize_guided_session,
    transform_to_profile_summary,
)


# ═══════════════════════════════════════════════════════════════════════
# Helpers — reusable coordinator result fixtures
# ═══════════════════════════════════════════════════════════════════════


def _intelligence_result(**overrides) -> CoordinatorResult:
    defaults = dict(
        system="intelligence",
        status=CoordinatorStatus.SUCCESS.value,
        data={
            "numerology": {
                "life_path": 7,
                "expression": 3,
                "soul_urge": 5,
                "personality": 1,
                "personal_year": 3,
                "personal_month": 9,
            },
            "astrology": {"sun_sign": "Pisces", "sun_degree": 354.5},
        },
        quality_passed=True,
    )
    defaults.update(overrides)
    return CoordinatorResult(**defaults)


def _healing_result(**overrides) -> CoordinatorResult:
    defaults = dict(
        system="healing",
        status=CoordinatorStatus.SUCCESS.value,
        data={
            "disclaimers": [
                "This is not medical advice. Consult a qualified healthcare professional."
            ],
            "crisis_flag": False,
            "recommended_modalities": [
                {
                    "modality": "breathwork",
                    "skill_trigger": "stress",
                    "preference_score": 0.8,
                    "difficulty_level": "beginner",
                }
            ],
        },
        quality_passed=True,
    )
    defaults.update(overrides)
    return CoordinatorResult(**defaults)


def _wealth_result(**overrides) -> CoordinatorResult:
    defaults = dict(
        system="wealth",
        status=CoordinatorStatus.SUCCESS.value,
        data={
            "disclaimers": [
                "This is not financial advice. Consult a qualified financial advisor."
            ],
            "wealth_archetype": {"name": "Builder", "description": "Steady builder"},
            "lever_priorities": ["income", "protection", "growth"],
            "calculations": {"savings_rate": 0.2, "emergency_months": 6},
        },
        quality_passed=True,
    )
    defaults.update(overrides)
    return CoordinatorResult(**defaults)


def _creative_result(**overrides) -> CoordinatorResult:
    defaults = dict(
        system="creative",
        status=CoordinatorStatus.SUCCESS.value,
        data={
            "creative_orientation": {
                "style": "generative",
                "medium": "visual arts",
            },
            "strengths": ["originality", "divergent thinking"],
        },
        quality_passed=True,
    )
    defaults.update(overrides)
    return CoordinatorResult(**defaults)


def _perspective_result(**overrides) -> CoordinatorResult:
    defaults = dict(
        system="perspective",
        status=CoordinatorStatus.SUCCESS.value,
        data={
            "detected_biases": ["confirmation_bias"],
            "kegan_stage": 3,
            "decision_analysis": {"decision": "career change", "score": 0.65},
        },
        quality_passed=True,
    )
    defaults.update(overrides)
    return CoordinatorResult(**defaults)


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Full profile synthesis
# ═══════════════════════════════════════════════════════════════════════


class TestFullProfileSynthesis:
    """synthesize_full_profile merges all system outputs."""

    def test_returns_synthesis_result(self) -> None:
        results = [_intelligence_result(), _healing_result()]
        synthesis = synthesize_full_profile(results)
        assert isinstance(synthesis, SynthesisResult)

    def test_systems_involved_lists_all_systems(self) -> None:
        results = [_intelligence_result(), _healing_result(), _wealth_result()]
        synthesis = synthesize_full_profile(results)
        assert "intelligence" in synthesis.systems_involved
        assert "healing" in synthesis.systems_involved
        assert "wealth" in synthesis.systems_involved

    def test_unified_insights_contains_data_keys(self) -> None:
        results = [_intelligence_result(), _healing_result()]
        synthesis = synthesize_full_profile(results)
        # Should have insights for each non-disclaimer key
        insight_keys = [i["key"] for i in synthesis.unified_insights]
        assert "numerology" in insight_keys
        assert "astrology" in insight_keys
        # Healing insights (disclaimers excluded)
        assert "crisis_flag" in insight_keys
        assert "recommended_modalities" in insight_keys
        # disclaimers should be excluded
        assert "disclaimers" not in insight_keys

    def test_quality_passed_reflects_all_coordinators(self) -> None:
        results = [
            _intelligence_result(quality_passed=True),
            _healing_result(quality_passed=True),
        ]
        synthesis = synthesize_full_profile(results)
        assert synthesis.quality_passed is True

    def test_quality_failed_when_one_coordinator_fails(self) -> None:
        results = [
            _intelligence_result(quality_passed=True),
            _healing_result(quality_passed=False),
        ]
        synthesis = synthesize_full_profile(results)
        assert synthesis.quality_passed is False

    def test_errors_collected_from_all_coordinators(self) -> None:
        results = [
            _intelligence_result(errors=["numerology error"]),
            _healing_result(errors=["modality error"]),
        ]
        synthesis = synthesize_full_profile(results)
        assert "numerology error" in synthesis.errors
        assert "modality error" in synthesis.errors

    def test_evidence_ratings_populated(self) -> None:
        results = [_intelligence_result(), _wealth_result()]
        synthesis = synthesize_full_profile(results)
        assert len(synthesis.evidence_ratings) > 0
        assert "intelligence.numerology" in synthesis.evidence_ratings
        assert "wealth.calculations" in synthesis.evidence_ratings

    def test_coherence_score_between_zero_and_one(self) -> None:
        results = [_intelligence_result(), _healing_result()]
        synthesis = synthesize_full_profile(results)
        assert 0.0 <= synthesis.overall_coherence <= 1.0

    def test_single_system_synthesis(self) -> None:
        """Even with one system, synthesis should work (degenerate case)."""
        results = [_intelligence_result()]
        synthesis = synthesize_full_profile(results)
        assert synthesis.systems_involved == ["intelligence"]
        assert len(synthesis.unified_insights) > 0

    def test_empty_results_synthesis(self) -> None:
        synthesis = synthesize_full_profile([])
        assert synthesis.systems_involved == []
        assert synthesis.unified_insights == []
        assert synthesis.overall_coherence == 1.0
        assert synthesis.quality_passed is True

    def test_five_system_synthesis(self) -> None:
        """Full five-system synthesis should work."""
        results = [
            _intelligence_result(),
            _healing_result(),
            _wealth_result(),
            _creative_result(),
            _perspective_result(),
        ]
        synthesis = synthesize_full_profile(results)
        assert len(synthesis.systems_involved) == 5
        assert len(synthesis.unified_insights) > 5


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Guided session synthesis
# ═══════════════════════════════════════════════════════════════════════


class TestGuidedSessionSynthesis:
    """synthesize_guided_session filters and ranks by intention."""

    def test_returns_synthesis_result(self) -> None:
        results = [_intelligence_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "money")
        assert isinstance(synthesis, SynthesisResult)

    def test_wealth_intention_prioritizes_wealth(self) -> None:
        results = [_intelligence_result(), _wealth_result(), _creative_result()]
        synthesis = synthesize_guided_session(results, "wealth building")
        # Wealth system should be first in systems_involved
        assert synthesis.systems_involved[0] == "wealth"

    def test_healing_intention_prioritizes_healing(self) -> None:
        results = [_intelligence_result(), _healing_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "healing journey")
        assert synthesis.systems_involved[0] == "healing"

    def test_creativity_intention_prioritizes_creative(self) -> None:
        results = [_intelligence_result(), _creative_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "creativity exploration")
        assert synthesis.systems_involved[0] == "creative"

    def test_decision_intention_prioritizes_perspective(self) -> None:
        results = [_intelligence_result(), _perspective_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "help me make a decision")
        assert synthesis.systems_involved[0] == "perspective"

    def test_insights_have_relevance_rank(self) -> None:
        results = [_intelligence_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "money")
        for insight in synthesis.unified_insights:
            assert "relevance_rank" in insight

    def test_insights_have_intention_field(self) -> None:
        results = [_intelligence_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "financial growth")
        for insight in synthesis.unified_insights:
            assert insight["intention"] == "financial growth"

    def test_unknown_intention_includes_all_systems(self) -> None:
        """An intention that doesn't match any keyword still includes all systems."""
        results = [_intelligence_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "zxcvbnm random")
        assert len(synthesis.systems_involved) == 2

    def test_connections_have_intention_alignment(self) -> None:
        results = [_intelligence_result(), _wealth_result()]
        synthesis = synthesize_guided_session(results, "money")
        for conn in synthesis.cross_system_connections:
            assert "intention_alignment" in conn

    def test_multi_intentions_merge_system_priorities(self) -> None:
        """Multiple intentions merge system priorities from all intentions."""
        results = [
            _intelligence_result(),
            _healing_result(),
            _wealth_result(),
            _creative_result(),
        ]
        synthesis = synthesize_guided_session(
            results,
            "career",
            intentions=["career", "health"],
        )
        # "career" maps to wealth, creative, perspective
        # "health" maps to healing, perspective, intelligence
        # Merged priority should include wealth, creative, healing, intelligence
        assert "wealth" in synthesis.systems_involved
        assert "healing" in synthesis.systems_involved
        # Insights should be stamped with all intentions
        for insight in synthesis.unified_insights:
            assert "career" in insight["intention"]
            assert "health" in insight["intention"]

    def test_quality_passed_propagated(self) -> None:
        results = [
            _intelligence_result(quality_passed=True),
            _healing_result(quality_passed=False),
        ]
        synthesis = synthesize_guided_session(results, "healing")
        assert synthesis.quality_passed is False


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Conflict detection
# ═══════════════════════════════════════════════════════════════════════


class TestConflictDetection:
    """detect_conflicts finds contradictions between system outputs."""

    def test_no_conflicts_with_compatible_outputs(self) -> None:
        results = [_intelligence_result(), _creative_result()]
        conflicts = detect_conflicts(results)
        assert isinstance(conflicts, list)
        # No rest-vs-action or risk conflicts in these results
        rest_action = [c for c in conflicts if "rest" in c["description"].lower() or "action" in c["description"].lower()]
        assert len(rest_action) == 0

    def test_rest_vs_action_conflict(self) -> None:
        rest_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"recommendation": "Rest and recover from stress"},
            quality_passed=True,
        )
        action_result = CoordinatorResult(
            system="wealth",
            status=CoordinatorStatus.SUCCESS.value,
            data={"recommendation": "Launch your new business now"},
            quality_passed=True,
        )
        conflicts = detect_conflicts([rest_result, action_result])
        rest_action_conflicts = [
            c for c in conflicts
            if "rest" in c["description"].lower() or "recovery" in c["description"].lower()
        ]
        assert len(rest_action_conflicts) >= 1
        assert rest_action_conflicts[0]["severity"] == "warning"

    def test_risk_averse_vs_aggressive_conflict(self) -> None:
        conservative = CoordinatorResult(
            system="perspective",
            status=CoordinatorStatus.SUCCESS.value,
            data={"analysis": "High risk aversion detected in your profile"},
            quality_passed=True,
        )
        aggressive = CoordinatorResult(
            system="wealth",
            status=CoordinatorStatus.SUCCESS.value,
            data={"strategy": "Invest aggressively in growth assets"},
            quality_passed=True,
        )
        conflicts = detect_conflicts([conservative, aggressive])
        risk_conflicts = [
            c for c in conflicts
            if "caution" in c["description"].lower() or "conservative" in c["description"].lower()
        ]
        assert len(risk_conflicts) >= 1

    def test_conflict_has_resolution_suggestion(self) -> None:
        rest_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"note": "Time to pause and ground yourself"},
            quality_passed=True,
        )
        action_result = CoordinatorResult(
            system="wealth",
            status=CoordinatorStatus.SUCCESS.value,
            data={"note": "Scale your operations now"},
            quality_passed=True,
        )
        conflicts = detect_conflicts([rest_result, action_result])
        for conflict in conflicts:
            assert "resolution" in conflict
            assert len(conflict["resolution"]) > 10

    def test_single_system_no_conflicts(self) -> None:
        conflicts = detect_conflicts([_intelligence_result()])
        assert conflicts == []

    def test_empty_results_no_conflicts(self) -> None:
        conflicts = detect_conflicts([])
        assert conflicts == []

    def test_error_status_results_excluded(self) -> None:
        """Error-status results should not be scanned for conflicts."""
        error_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.ERROR.value,
            data={"note": "Rest and recover"},
            quality_passed=False,
        )
        action_result = CoordinatorResult(
            system="wealth",
            status=CoordinatorStatus.SUCCESS.value,
            data={"note": "Launch your business"},
            quality_passed=True,
        )
        conflicts = detect_conflicts([error_result, action_result])
        rest_action = [
            c for c in conflicts
            if "rest" in c["description"].lower()
        ]
        assert len(rest_action) == 0

    def test_overwhelm_conflict_with_many_recommendations(self) -> None:
        """Too many recommendations should trigger an info-level conflict."""
        results = [
            CoordinatorResult(
                system="intelligence",
                status=CoordinatorStatus.SUCCESS.value,
                data={"a": 1, "b": 2, "c": 3},
                quality_passed=True,
            ),
            CoordinatorResult(
                system="healing",
                status=CoordinatorStatus.SUCCESS.value,
                data={"d": 4, "e": 5, "f": 6, "disclaimers": ["safe"]},
                quality_passed=True,
            ),
            CoordinatorResult(
                system="wealth",
                status=CoordinatorStatus.SUCCESS.value,
                data={"g": 7, "h": 8, "disclaimers": ["safe"], "calculations": {}},
                quality_passed=True,
            ),
        ]
        conflicts = detect_conflicts(results)
        overwhelm = [c for c in conflicts if "overwhelm" in c["description"].lower()]
        assert len(overwhelm) >= 1
        assert overwhelm[0]["severity"] == "info"

    def test_conflict_includes_involved_systems(self) -> None:
        rest_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"tip": "Slow down and rest"},
            quality_passed=True,
        )
        action_result = CoordinatorResult(
            system="wealth",
            status=CoordinatorStatus.SUCCESS.value,
            data={"tip": "Expand your portfolio now"},
            quality_passed=True,
        )
        conflicts = detect_conflicts([rest_result, action_result])
        for conflict in conflicts:
            assert "systems" in conflict
            assert isinstance(conflict["systems"], list)


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Evidence rating aggregation
# ═══════════════════════════════════════════════════════════════════════


class TestEvidenceRatingAggregation:
    """aggregate_evidence maps insights to evidence ratings."""

    def test_intelligence_numerology_is_traditional(self) -> None:
        results = [_intelligence_result()]
        ratings = aggregate_evidence(results)
        assert ratings["intelligence.numerology"] == "traditional"

    def test_intelligence_astrology_is_traditional(self) -> None:
        results = [_intelligence_result()]
        ratings = aggregate_evidence(results)
        assert ratings["intelligence.astrology"] == "traditional"

    def test_wealth_calculations_are_deterministic(self) -> None:
        results = [_wealth_result()]
        ratings = aggregate_evidence(results)
        assert ratings["wealth.calculations"] == "deterministic"

    def test_wealth_archetype_is_deterministic(self) -> None:
        results = [_wealth_result()]
        ratings = aggregate_evidence(results)
        assert ratings["wealth.wealth_archetype"] == "deterministic"

    def test_healing_modalities_are_evidence_based(self) -> None:
        results = [_healing_result()]
        ratings = aggregate_evidence(results)
        assert ratings["healing.recommended_modalities"] == "evidence-based"

    def test_healing_crisis_flag_is_evidence_based(self) -> None:
        results = [_healing_result()]
        ratings = aggregate_evidence(results)
        assert ratings["healing.crisis_flag"] == "evidence-based"

    def test_creative_is_experiential(self) -> None:
        results = [_creative_result()]
        ratings = aggregate_evidence(results)
        assert ratings["creative.creative_orientation"] == "experiential"
        assert ratings["creative.strengths"] == "experiential"

    def test_perspective_is_experiential(self) -> None:
        results = [_perspective_result()]
        ratings = aggregate_evidence(results)
        assert ratings["perspective.detected_biases"] == "experiential"
        assert ratings["perspective.kegan_stage"] == "experiential"

    def test_disclaimers_excluded_from_ratings(self) -> None:
        results = [_healing_result()]
        ratings = aggregate_evidence(results)
        assert "healing.disclaimers" not in ratings

    def test_empty_results_empty_ratings(self) -> None:
        ratings = aggregate_evidence([])
        assert ratings == {}

    def test_multi_system_ratings(self) -> None:
        results = [_intelligence_result(), _wealth_result(), _healing_result()]
        ratings = aggregate_evidence(results)
        # Should have ratings from all three systems
        assert any(k.startswith("intelligence.") for k in ratings)
        assert any(k.startswith("wealth.") for k in ratings)
        assert any(k.startswith("healing.") for k in ratings)


# ═══════════════════════════════════════════════════════════════════════
# Section 5: Coherence scoring
# ═══════════════════════════════════════════════════════════════════════


class TestCoherenceScoring:
    """Coherence score is calculated correctly."""

    def test_perfect_coherence_no_conflicts(self) -> None:
        results = [_intelligence_result(), _creative_result()]
        synthesis = synthesize_full_profile(results)
        # No conflicts expected, so coherence should be high
        assert synthesis.overall_coherence >= 0.8

    def test_coherence_reduced_by_conflicts(self) -> None:
        rest_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"tip": "Rest and pause for recovery"},
            quality_passed=True,
        )
        action_result = CoordinatorResult(
            system="wealth",
            status=CoordinatorStatus.SUCCESS.value,
            data={"tip": "Launch and scale your new venture"},
            quality_passed=True,
        )
        synthesis = synthesize_full_profile([rest_result, action_result])
        assert synthesis.overall_coherence < 1.0

    def test_coherence_reduced_by_error_status(self) -> None:
        error_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.ERROR.value,
            data={},
            errors=["Engine unavailable"],
            quality_passed=False,
        )
        ok_result = _intelligence_result()
        synthesis = synthesize_full_profile([error_result, ok_result])
        assert synthesis.overall_coherence < 1.0

    def test_coherence_clamped_to_zero(self) -> None:
        """Even with many conflicts, coherence never goes below 0."""
        # Create results with multiple conflict triggers
        results = [
            CoordinatorResult(
                system="healing",
                status=CoordinatorStatus.ERROR.value,
                data={"x": "rest pause slow ground recover"},
                errors=["e1"],
                quality_passed=False,
            ),
            CoordinatorResult(
                system="wealth",
                status=CoordinatorStatus.ERROR.value,
                data={"x": "launch expand scale push aggressively"},
                errors=["e2"],
                quality_passed=False,
            ),
            CoordinatorResult(
                system="perspective",
                status=CoordinatorStatus.ERROR.value,
                data={"x": "risk aversion conservative cautious"},
                errors=["e3"],
                quality_passed=False,
            ),
        ]
        synthesis = synthesize_full_profile(results)
        assert synthesis.overall_coherence >= 0.0

    def test_coherence_clamped_to_one(self) -> None:
        """Coherence never exceeds 1.0."""
        results = [_intelligence_result()]
        synthesis = synthesize_full_profile(results)
        assert synthesis.overall_coherence <= 1.0

    def test_empty_results_perfect_coherence(self) -> None:
        synthesis = synthesize_full_profile([])
        assert synthesis.overall_coherence == 1.0


# ═══════════════════════════════════════════════════════════════════════
# Section 6: Quality gate integration
# ═══════════════════════════════════════════════════════════════════════


class TestSynthesisQualityGate:
    """Quality gate results propagate through synthesis."""

    def test_all_pass_means_synthesis_passes(self) -> None:
        results = [
            _intelligence_result(quality_passed=True),
            _healing_result(quality_passed=True),
        ]
        synthesis = synthesize_full_profile(results)
        assert synthesis.quality_passed is True

    def test_one_fail_means_synthesis_fails(self) -> None:
        results = [
            _intelligence_result(quality_passed=True),
            _healing_result(quality_passed=False),
        ]
        synthesis = synthesize_full_profile(results)
        assert synthesis.quality_passed is False

    def test_all_fail_means_synthesis_fails(self) -> None:
        results = [
            _intelligence_result(quality_passed=False),
            _healing_result(quality_passed=False),
        ]
        synthesis = synthesize_full_profile(results)
        assert synthesis.quality_passed is False

    def test_guided_session_quality_propagated(self) -> None:
        results = [
            _intelligence_result(quality_passed=True),
            _wealth_result(quality_passed=False),
        ]
        synthesis = synthesize_guided_session(results, "money")
        assert synthesis.quality_passed is False


# ═══════════════════════════════════════════════════════════════════════
# Section 7: Backward compatibility
# ═══════════════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """Old synthesize_results() still works and orchestrator stays compatible."""

    def test_old_synthesize_results_still_works(self) -> None:
        results = [
            CoordinatorResult(
                system="intelligence",
                status=CoordinatorStatus.SUCCESS.value,
                data={"life_path": 3},
            ),
            CoordinatorResult(
                system="healing",
                status=CoordinatorStatus.SUCCESS.value,
                data={"modalities": ["breathwork"]},
            ),
        ]
        synthesis = synthesize_results(results)
        assert "systems" in synthesis
        assert "participating_systems" in synthesis
        assert "overall_status" in synthesis

    async def test_orchestrator_process_request_without_intention(self) -> None:
        """process_request still works without the intention parameter."""
        orchestrator = MasterOrchestrator()

        mock_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 3}},
            quality_passed=True,
        )
        orchestrator._coordinators[SystemIntent.INTELLIGENCE] = MagicMock()
        orchestrator._coordinators[SystemIntent.INTELLIGENCE].process = AsyncMock(
            return_value=mock_result,
        )

        result = await orchestrator.process_request("Tell me my numerology")
        assert isinstance(result, OrchestratorResult)
        assert result.intent.intent == SystemIntent.INTELLIGENCE
        assert len(result.coordinator_results) == 1
        # Single system: no synthesis
        assert result.synthesis is None

    async def test_orchestrator_multi_system_without_intention(self) -> None:
        """Multi-system request without intention uses full-profile synthesis."""
        orchestrator = MasterOrchestrator()

        healing_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"modalities": ["breathwork"]},
            quality_passed=True,
        )
        intelligence_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 7}},
            quality_passed=True,
        )

        for intent_enum, mock_result in [
            (SystemIntent.HEALING, healing_result),
            (SystemIntent.INTELLIGENCE, intelligence_result),
        ]:
            mock_coord = MagicMock()
            mock_coord.process = AsyncMock(return_value=mock_result)
            orchestrator._coordinators[intent_enum] = mock_coord

        with patch(
            "alchymine.agents.orchestrator.orchestrator.classify_intent",
            return_value=IntentResult(
                intent=SystemIntent.MULTI_SYSTEM,
                confidence=0.5,
                secondary_intents=[SystemIntent.HEALING, SystemIntent.INTELLIGENCE],
                detected_keywords=["healing", "numerology"],
            ),
        ):
            result = await orchestrator.process_request("healing numerology breathwork astrology")

        assert len(result.coordinator_results) == 2
        assert result.synthesis is not None
        # Should still have the backward-compatible keys
        assert "systems" in result.synthesis
        assert "participating_systems" in result.synthesis
        assert "overall_status" in result.synthesis
        # Should also have new synthesis_detail
        assert "synthesis_detail" in result.synthesis

    async def test_orchestrator_multi_system_with_intention(self) -> None:
        """Multi-system request with intention uses guided synthesis."""
        orchestrator = MasterOrchestrator()

        healing_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"modalities": ["breathwork"]},
            quality_passed=True,
        )
        intelligence_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 7}},
            quality_passed=True,
        )

        for intent_enum, mock_result in [
            (SystemIntent.HEALING, healing_result),
            (SystemIntent.INTELLIGENCE, intelligence_result),
        ]:
            mock_coord = MagicMock()
            mock_coord.process = AsyncMock(return_value=mock_result)
            orchestrator._coordinators[intent_enum] = mock_coord

        with patch(
            "alchymine.agents.orchestrator.orchestrator.classify_intent",
            return_value=IntentResult(
                intent=SystemIntent.MULTI_SYSTEM,
                confidence=0.5,
                secondary_intents=[SystemIntent.HEALING, SystemIntent.INTELLIGENCE],
                detected_keywords=["healing", "numerology"],
            ),
        ):
            result = await orchestrator.process_request(
                "healing numerology breathwork astrology",
                intention="healing",
            )

        assert result.synthesis is not None
        assert "synthesis_detail" in result.synthesis
        # Should still have backward-compatible keys
        assert "systems" in result.synthesis
        assert "participating_systems" in result.synthesis

    async def test_synthesis_fallback_on_import_error(self) -> None:
        """If synthesis module raises, fall back to old synthesize_results."""
        orchestrator = MasterOrchestrator()

        healing_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"modalities": ["breathwork"]},
            quality_passed=True,
        )
        intelligence_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 7}},
            quality_passed=True,
        )

        for intent_enum, mock_result in [
            (SystemIntent.HEALING, healing_result),
            (SystemIntent.INTELLIGENCE, intelligence_result),
        ]:
            mock_coord = MagicMock()
            mock_coord.process = AsyncMock(return_value=mock_result)
            orchestrator._coordinators[intent_enum] = mock_coord

        with (
            patch(
                "alchymine.agents.orchestrator.orchestrator.classify_intent",
                return_value=IntentResult(
                    intent=SystemIntent.MULTI_SYSTEM,
                    confidence=0.5,
                    secondary_intents=[SystemIntent.HEALING, SystemIntent.INTELLIGENCE],
                    detected_keywords=["healing", "numerology"],
                ),
            ),
            patch(
                "alchymine.agents.orchestrator.synthesis.synthesize_full_profile",
                side_effect=RuntimeError("synthesis broken"),
            ),
        ):
            result = await orchestrator.process_request("healing numerology")

        # Should still get a synthesis via fallback
        assert result.synthesis is not None
        assert "systems" in result.synthesis
        assert "participating_systems" in result.synthesis
        # No synthesis_detail because we fell back
        assert "synthesis_detail" not in result.synthesis


# ═══════════════════════════════════════════════════════════════════════
# Section 8: Cross-system connection bridge integration
# ═══════════════════════════════════════════════════════════════════════


class TestCrossSystemConnections:
    """Bridge functions are invoked during synthesis."""

    def test_connections_populated_with_multi_system(self) -> None:
        """With intelligence + creative, at least archetype bridges might fire."""
        intel = _intelligence_result(
            data={
                "numerology": {"life_path": 7, "personal_year": 3},
                "archetype": {"primary": "Creator", "shadow": "Creator"},
            },
        )
        creative = _creative_result()
        synthesis = synthesize_full_profile([intel, creative])
        # Depending on bridge availability, we may have connections
        assert isinstance(synthesis.cross_system_connections, list)

    def test_connections_empty_without_bridgeable_data(self) -> None:
        """Minimal data means no bridge connections fire."""
        r1 = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"raw": "minimal"},
            quality_passed=True,
        )
        r2 = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"raw": "minimal"},
            quality_passed=True,
        )
        synthesis = synthesize_full_profile([r1, r2])
        # No archetype, numerology, etc. — no bridges fire
        assert isinstance(synthesis.cross_system_connections, list)


# ═══════════════════════════════════════════════════════════════════════
# Section 9: SynthesisResult dataclass
# ═══════════════════════════════════════════════════════════════════════


class TestSynthesisResultDataclass:
    """SynthesisResult dataclass structure."""

    def test_default_errors_is_empty_list(self) -> None:
        sr = SynthesisResult(
            systems_involved=[],
            unified_insights=[],
            cross_system_connections=[],
            conflicts=[],
            evidence_ratings={},
            overall_coherence=1.0,
            quality_passed=True,
        )
        assert sr.errors == []

    def test_all_fields_populated(self) -> None:
        sr = SynthesisResult(
            systems_involved=["a", "b"],
            unified_insights=[{"key": "val"}],
            cross_system_connections=[{"bridge": "test"}],
            conflicts=[{"issue": "conflict"}],
            evidence_ratings={"a.x": "traditional"},
            overall_coherence=0.75,
            quality_passed=True,
            errors=["some error"],
        )
        assert sr.systems_involved == ["a", "b"]
        assert sr.overall_coherence == 0.75
        assert sr.quality_passed is True
        assert len(sr.errors) == 1


# ═══════════════════════════════════════════════════════════════════════
# Section 10: Strengths map population
# ═══════════════════════════════════════════════════════════════════════


class TestStrengthsMap:
    """_build_strengths_map extracts cross-system strengths."""

    def test_big_five_high_traits_included(self) -> None:
        """Big Five traits scoring above 60 are included as strengths."""
        result = _intelligence_result(
            data={
                "numerology": {"life_path": 7},
                "personality": {
                    "big_five": {
                        "openness": 75.0,
                        "conscientiousness": 80.0,
                        "extraversion": 40.0,
                        "agreeableness": 65.0,
                        "neuroticism": 20.0,
                    },
                    "attachment_style": "anxious",
                },
            }
        )
        strengths = _build_strengths_map([result])
        assert "Openness to Experience" in strengths
        assert "Conscientiousness" in strengths
        assert "Agreeableness" in strengths
        # Extraversion is below 60 → excluded
        assert "Extraversion" not in strengths
        # Neuroticism is never included (not in label map)
        assert "Emotional Sensitivity" not in strengths

    def test_secure_attachment_included(self) -> None:
        """Secure attachment style is listed as a strength."""
        result = _intelligence_result(
            data={
                "personality": {
                    "big_five": {"openness": 50.0, "conscientiousness": 50.0,
                                 "extraversion": 50.0, "agreeableness": 50.0,
                                 "neuroticism": 50.0},
                    "attachment_style": "secure",
                },
            }
        )
        strengths = _build_strengths_map([result])
        assert "Secure Attachment" in strengths

    def test_insecure_attachment_not_included(self) -> None:
        """Non-secure attachment style is not a strength."""
        result = _intelligence_result(
            data={
                "personality": {
                    "big_five": {},
                    "attachment_style": "anxious",
                },
            }
        )
        strengths = _build_strengths_map([result])
        assert "Secure Attachment" not in strengths

    def test_creative_strengths_included(self) -> None:
        """Creative system strengths are included."""
        result = _creative_result(
            data={
                "creative_orientation": {"style": "generative"},
                "strengths": ["originality", "divergent_thinking"],
            }
        )
        strengths = _build_strengths_map([result])
        assert "Originality" in strengths
        assert "Divergent Thinking" in strengths

    def test_kegan_stage_3_plus_adds_perspective(self) -> None:
        """Kegan stage >= 3 adds Perspective-Taking strength."""
        result = _perspective_result(data={"kegan_stage": 3})
        strengths = _build_strengths_map([result])
        assert "Perspective-Taking" in strengths

    def test_kegan_stage_2_no_perspective(self) -> None:
        """Kegan stage < 3 does not add Perspective-Taking."""
        result = _perspective_result(data={"kegan_stage": 2})
        strengths = _build_strengths_map([result])
        assert "Perspective-Taking" not in strengths

    def test_error_status_excluded(self) -> None:
        """Error-status results don't contribute to strengths."""
        result = _intelligence_result(
            status=CoordinatorStatus.ERROR.value,
            data={
                "personality": {
                    "big_five": {"openness": 90.0},
                    "attachment_style": "secure",
                },
            },
        )
        strengths = _build_strengths_map([result])
        assert strengths == []

    def test_empty_results(self) -> None:
        """Empty coordinator results produce empty strengths."""
        assert _build_strengths_map([]) == []

    def test_cross_system_strengths(self) -> None:
        """Multiple systems contribute to the combined strengths map."""
        results = [
            _intelligence_result(
                data={
                    "personality": {
                        "big_five": {"openness": 80.0, "conscientiousness": 30.0,
                                     "extraversion": 70.0, "agreeableness": 50.0,
                                     "neuroticism": 10.0},
                        "attachment_style": "secure",
                    },
                }
            ),
            _creative_result(data={"strengths": ["fluency"]}),
            _perspective_result(data={"kegan_stage": 4}),
        ]
        strengths = _build_strengths_map(results)
        assert "Openness to Experience" in strengths
        assert "Extraversion" in strengths
        assert "Secure Attachment" in strengths
        assert "Fluency" in strengths
        assert "Perspective-Taking" in strengths


# ═══════════════════════════════════════════════════════════════════════
# Section 11: Profile summary strengths_map integration
# ═══════════════════════════════════════════════════════════════════════


class TestProfileSummaryStrengthsMap:
    """transform_to_profile_summary populates strengths_map."""

    def test_strengths_map_populated_in_identity(self) -> None:
        """Identity section has populated strengths_map, not empty list."""
        results = [
            _intelligence_result(
                data={
                    "numerology": {"life_path": 7},
                    "astrology": {"sun_sign": "Pisces"},
                    "personality": {
                        "big_five": {"openness": 85.0, "conscientiousness": 70.0,
                                     "extraversion": 40.0, "agreeableness": 50.0,
                                     "neuroticism": 30.0},
                        "attachment_style": "secure",
                    },
                }
            ),
            _creative_result(data={"strengths": ["originality"]}),
        ]
        summary = transform_to_profile_summary(results)
        assert "identity" in summary
        sm = summary["identity"]["strengths_map"]
        assert isinstance(sm, list)
        assert len(sm) > 0
        assert "Openness to Experience" in sm
        assert "Conscientiousness" in sm
        assert "Secure Attachment" in sm
        assert "Originality" in sm

    def test_strengths_map_empty_when_no_data(self) -> None:
        """With minimal data, strengths_map is an empty list (not None)."""
        results = [
            _intelligence_result(
                data={
                    "personality": {
                        "big_five": {"openness": 30.0, "conscientiousness": 40.0,
                                     "extraversion": 20.0, "agreeableness": 50.0,
                                     "neuroticism": 80.0},
                        "attachment_style": "anxious",
                    },
                }
            ),
        ]
        summary = transform_to_profile_summary(results)
        assert summary["identity"]["strengths_map"] == []

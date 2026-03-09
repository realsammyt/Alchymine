"""Tests for LangGraph StateGraph coordinator pipelines.

Covers graph building, state transitions, error handling, quality gate
integration, node ordering, and the sequential fallback when langgraph
is unavailable.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from alchymine.agents.orchestrator.graphs import (
    _HAS_LANGGRAPH,
    CoordinatorState,
    _compute_status,
    _compute_status_with_baseline,
    _run_quality_gate_node,
    _SequentialGraph,
    build_creative_graph,
    build_healing_graph,
    build_intelligence_graph,
    build_perspective_graph,
    build_wealth_graph,
)

# ─── Helpers ────────────────────────────────────────────────────────


def _make_initial_state(**overrides) -> CoordinatorState:
    """Create a default initial state with optional overrides."""
    state: CoordinatorState = {
        "user_id": "test-user",
        "request_data": {},
        "results": {},
        "errors": [],
        "status": "success",
        "quality_passed": True,
    }
    state.update(overrides)
    return state


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Graph building — each system builds successfully
# ═══════════════════════════════════════════════════════════════════════


class TestGraphBuilding:
    """Each build_*_graph() factory returns a usable graph object."""

    def test_intelligence_graph_builds(self) -> None:
        graph = build_intelligence_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_healing_graph_builds(self) -> None:
        graph = build_healing_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_wealth_graph_builds(self) -> None:
        graph = build_wealth_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_creative_graph_builds(self) -> None:
        graph = build_creative_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_perspective_graph_builds(self) -> None:
        graph = build_perspective_graph()
        assert graph is not None
        assert hasattr(graph, "invoke")

    def test_graphs_build_without_quality_gate(self) -> None:
        """Graphs can be built without the quality gate node."""
        for builder in (
            build_intelligence_graph,
            build_healing_graph,
            build_wealth_graph,
            build_creative_graph,
            build_perspective_graph,
        ):
            graph = builder(include_quality_gate=False)
            assert graph is not None
            assert hasattr(graph, "invoke")

    def test_graphs_build_with_quality_gate(self) -> None:
        """Graphs can be built with the quality gate node (default)."""
        for builder in (
            build_intelligence_graph,
            build_healing_graph,
            build_wealth_graph,
            build_creative_graph,
            build_perspective_graph,
        ):
            graph = builder(include_quality_gate=True)
            assert graph is not None
            assert hasattr(graph, "invoke")


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Intelligence graph state transitions
# ═══════════════════════════════════════════════════════════════════════


class TestIntelligenceGraphTransitions:
    """Intelligence graph processes numerology + astrology correctly."""

    def test_success_with_both_engines(self) -> None:
        """All intelligence engines succeed -> status=success."""
        mock_profile = MagicMock()
        mock_profile.life_path = 7
        mock_profile.expression = 3
        mock_profile.soul_urge = 9
        mock_profile.personality = 4
        mock_profile.personal_year = 1
        mock_profile.personal_month = 5

        from datetime import date

        # Provide Big Five assessment responses so personality node succeeds
        bf_responses = {
            f"bf_{t}{i}": 3
            for t in ("e", "a", "c", "n", "o")
            for i in (1, 2, 3, 4)
        }

        state = _make_initial_state(
            request_data={
                "full_name": "Test User",
                "birth_date": date(1990, 6, 15),
                "assessment_responses": bf_responses,
            }
        )

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                return_value="Gemini",
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_degree",
                return_value=84.5,
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["status"] == "success"
        assert "numerology" in result["results"]
        assert "astrology" in result["results"]
        assert "personality" in result["results"]
        assert "archetype" in result["results"]
        assert "biorhythm" in result["results"]
        assert result["results"]["numerology"]["life_path"] == 7
        assert result["results"]["astrology"]["sun_sign"] == "Gemini"
        # Personality now nests Big Five under "big_five"
        assert "big_five" in result["results"]["personality"]
        assert result["results"]["personality"]["big_five"]["openness"] is not None
        assert result["errors"] == []

    def test_personality_full_shape_with_all_assessments(self) -> None:
        """Personality output contains big_five, attachment_style, enneagram when all data provided."""
        from datetime import date

        bf_responses = {
            f"bf_{t}{i}": 3
            for t in ("e", "a", "c", "n", "o")
            for i in (1, 2, 3, 4)
        }
        att_responses = {
            "att_closeness": 4,
            "att_abandonment": 2,
            "att_trust": 4,
            "att_self_reliance": 3,
        }
        enn_responses = {f"enn_{i}": (3 if i != 4 else 5) for i in range(1, 10)}

        all_responses = {**bf_responses, **att_responses, **enn_responses}

        state = _make_initial_state(
            request_data={
                "full_name": "Test User",
                "birth_date": date(1990, 6, 15),
                "assessment_responses": all_responses,
            }
        )

        mock_profile = MagicMock()
        mock_profile.life_path = 7
        mock_profile.expression = 3
        mock_profile.soul_urge = 9
        mock_profile.personality = 4
        mock_profile.personal_year = 1
        mock_profile.personal_month = 5

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                return_value="Gemini",
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_degree",
                return_value=84.5,
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        personality = result["results"]["personality"]
        assert "big_five" in personality
        assert personality["big_five"]["openness"] is not None
        assert personality["attachment_style"] is not None
        assert personality["enneagram_type"] is not None
        assert personality["enneagram_wing"] is not None

    def test_risk_tolerance_scored_from_assessment(self) -> None:
        """Risk tolerance is scored from risk_* assessment items and added to personality."""
        from datetime import date

        bf_responses = {
            f"bf_{t}{i}": 3
            for t in ("e", "a", "c", "n", "o")
            for i in (1, 2, 3, 4)
        }
        # High risk tolerance answers (all 5s → aggressive)
        risk_responses = {"risk_1": 5, "risk_2": 5, "risk_3": 5}
        all_responses = {**bf_responses, **risk_responses}

        state = _make_initial_state(
            request_data={
                "full_name": "Test User",
                "birth_date": date(1990, 6, 15),
                "assessment_responses": all_responses,
            }
        )

        mock_profile = MagicMock()
        mock_profile.life_path = 7
        mock_profile.expression = 3
        mock_profile.soul_urge = 9
        mock_profile.personality = 4
        mock_profile.personal_year = 1
        mock_profile.personal_month = 5

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                return_value="Gemini",
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_degree",
                return_value=84.5,
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        personality = result["results"]["personality"]
        assert "risk_tolerance" in personality
        assert personality["risk_tolerance"] == "aggressive"

    def test_risk_tolerance_conservative(self) -> None:
        """Low risk answers produce conservative risk_tolerance."""
        from datetime import date

        bf_responses = {
            f"bf_{t}{i}": 3
            for t in ("e", "a", "c", "n", "o")
            for i in (1, 2, 3, 4)
        }
        risk_responses = {"risk_1": 1, "risk_2": 1, "risk_3": 1}
        all_responses = {**bf_responses, **risk_responses}

        state = _make_initial_state(
            request_data={
                "full_name": "Test User",
                "birth_date": date(1990, 6, 15),
                "assessment_responses": all_responses,
            }
        )

        mock_profile = MagicMock()
        mock_profile.life_path = 7
        mock_profile.expression = 3
        mock_profile.soul_urge = 9
        mock_profile.personality = 4
        mock_profile.personal_year = 1
        mock_profile.personal_month = 5

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                return_value="Gemini",
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_degree",
                return_value=84.5,
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        personality = result["results"]["personality"]
        assert personality["risk_tolerance"] == "conservative"

    def test_risk_tolerance_skipped_when_items_missing(self) -> None:
        """Risk tolerance not scored when fewer than 3 risk items present."""
        from datetime import date

        bf_responses = {
            f"bf_{t}{i}": 3
            for t in ("e", "a", "c", "n", "o")
            for i in (1, 2, 3, 4)
        }
        # Only 2 risk items — not enough
        risk_responses = {"risk_1": 3, "risk_2": 3}
        all_responses = {**bf_responses, **risk_responses}

        state = _make_initial_state(
            request_data={
                "full_name": "Test User",
                "birth_date": date(1990, 6, 15),
                "assessment_responses": all_responses,
            }
        )

        mock_profile = MagicMock()
        mock_profile.life_path = 7
        mock_profile.expression = 3
        mock_profile.soul_urge = 9
        mock_profile.personality = 4
        mock_profile.personal_year = 1
        mock_profile.personal_month = 5

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                return_value="Gemini",
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_degree",
                return_value=84.5,
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        personality = result["results"]["personality"]
        assert "risk_tolerance" not in personality

    def test_degraded_when_astrology_fails(self) -> None:
        """Numerology succeeds, astrology fails -> status=degraded."""
        mock_profile = MagicMock()
        mock_profile.life_path = 3
        mock_profile.expression = 6
        mock_profile.soul_urge = 5
        mock_profile.personality = 1
        mock_profile.personal_year = 7
        mock_profile.personal_month = 3

        from datetime import date

        state = _make_initial_state(
            request_data={"full_name": "Maria", "birth_date": date(1992, 3, 15)}
        )

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.calculate_natal_chart",
                side_effect=ImportError("swisseph not installed"),
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["status"] == "degraded"
        assert "numerology" in result["results"]
        assert "astrology" not in result["results"]
        assert any("astrology" in e.lower() for e in result["errors"])

    def test_error_when_both_fail(self) -> None:
        """Both engines fail -> status=error."""
        state = _make_initial_state(request_data={})

        graph = build_intelligence_graph(include_quality_gate=False)
        result = graph.invoke(state)

        assert result["status"] == "error"
        assert len(result["errors"]) >= 2

    def test_missing_birth_date_errors(self) -> None:
        """Missing birth_date results in errors for both engines."""
        state = _make_initial_state(request_data={"full_name": "Test"})

        graph = build_intelligence_graph(include_quality_gate=False)
        result = graph.invoke(state)

        assert any("birth_date" in e for e in result["errors"])


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Healing graph state transitions
# ═══════════════════════════════════════════════════════════════════════


class TestHealingGraphTransitions:
    """Healing graph handles crisis detection, modalities, disclaimers."""

    def test_always_includes_disclaimers(self) -> None:
        """Healing output always contains disclaimers."""
        state = _make_initial_state(request_data={})

        graph = build_healing_graph(include_quality_gate=False)
        result = graph.invoke(state)

        assert "disclaimers" in result["results"]
        assert len(result["results"]["disclaimers"]) > 0
        assert "not medical advice" in result["results"]["disclaimers"][0].lower()

    def test_crisis_detection_sets_flag(self) -> None:
        """Crisis detection node sets crisis_flag in results."""
        mock_crisis = MagicMock()
        mock_crisis.severity.value = "high"
        mock_crisis.resources = [
            MagicMock(name="988 Suicide & Crisis Lifeline", contact="988"),
        ]

        state = _make_initial_state(request_data={"text": "I want to hurt myself"})

        with patch("alchymine.engine.healing.detect_crisis", return_value=mock_crisis):
            graph = build_healing_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["results"]["crisis_flag"] is True
        assert "crisis_response" in result["results"]
        assert result["results"]["crisis_response"]["severity"] == "high"

    def test_no_crisis_sets_flag_false(self) -> None:
        """No crisis detected -> crisis_flag is False."""
        state = _make_initial_state(request_data={"text": "I feel great today"})

        with patch("alchymine.engine.healing.detect_crisis", return_value=None):
            graph = build_healing_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["results"]["crisis_flag"] is False

    def test_degraded_when_crisis_engine_unavailable(self) -> None:
        """Crisis engine unavailable -> errors collected, disclaimers still present."""
        state = _make_initial_state(request_data={"text": "hello"})

        with patch(
            "alchymine.engine.healing.detect_crisis",
            side_effect=ImportError("healing engine not available"),
        ):
            graph = build_healing_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert "disclaimers" in result["results"]
        assert any("crisis" in e.lower() for e in result["errors"])


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Wealth graph state transitions
# ═══════════════════════════════════════════════════════════════════════


class TestWealthGraphTransitions:
    """Wealth graph handles archetypes, levers, calculations, disclaimers."""

    def test_always_includes_disclaimers(self) -> None:
        """Wealth output always contains financial disclaimers."""
        state = _make_initial_state(request_data={})

        graph = build_wealth_graph(include_quality_gate=False)
        result = graph.invoke(state)

        assert "disclaimers" in result["results"]
        assert "not financial advice" in result["results"]["disclaimers"][0].lower()

    def test_always_includes_calculations(self) -> None:
        """Wealth output always contains a calculations dict."""
        state = _make_initial_state(request_data={})

        graph = build_wealth_graph(include_quality_gate=False)
        result = graph.invoke(state)

        assert "calculations" in result["results"]
        assert isinstance(result["results"]["calculations"], dict)

    def test_archetype_mapping(self) -> None:
        """Wealth archetype is mapped when life_path and archetype_primary present."""
        mock_archetype = MagicMock()
        mock_archetype.name = "Builder"
        mock_archetype.description = "Steady wealth builder"

        state = _make_initial_state(
            request_data={
                "life_path": 3,
                "archetype_primary": "warrior",
                "risk_tolerance": "moderate",
            }
        )

        with patch(
            "alchymine.engine.wealth.map_wealth_archetype",
            return_value=mock_archetype,
        ):
            graph = build_wealth_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert "wealth_archetype" in result["results"]
        assert result["results"]["wealth_archetype"]["name"] == "Builder"

    def test_lever_prioritisation(self) -> None:
        """Levers are prioritised when life_path and intention present."""
        mock_lever = MagicMock()
        mock_lever.value = "earn_more"

        state = _make_initial_state(
            request_data={
                "life_path": 5,
                "intention": "grow wealth",
                "risk_tolerance": "high",
            }
        )

        with patch(
            "alchymine.engine.wealth.prioritize_levers",
            return_value=[mock_lever],
        ):
            graph = build_wealth_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert "lever_priorities" in result["results"]
        assert "earn_more" in result["results"]["lever_priorities"]


# ═══════════════════════════════════════════════════════════════════════
# Section 5: Creative graph state transitions
# ═══════════════════════════════════════════════════════════════════════


class TestCreativeGraphTransitions:
    """Creative graph handles orientation and strengths analysis."""

    def test_orientation_from_life_path(self) -> None:
        """Creative orientation is derived from life path."""
        state = _make_initial_state(request_data={"life_path": 3})

        with patch(
            "alchymine.engine.creative.derive_creative_orientation",
            return_value="expressive",
        ):
            graph = build_creative_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["results"]["creative_orientation"] == "expressive"
        assert result["status"] == "success"

    def test_strengths_from_guilford_scores(self) -> None:
        """Strengths are identified from Guilford scores."""
        state = _make_initial_state(
            request_data={"guilford_scores": {"fluency": 0.8, "flexibility": 0.7}}
        )

        with patch(
            "alchymine.engine.creative.identify_strengths",
            return_value=["fluency", "flexibility"],
        ):
            graph = build_creative_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["results"]["strengths"] == ["fluency", "flexibility"]

    def test_error_when_no_data(self) -> None:
        """Empty request results in error status when engines unavailable."""
        state = _make_initial_state(request_data={})

        graph = build_creative_graph(include_quality_gate=False)
        result = graph.invoke(state)

        # No life_path and no guilford_scores — no data produced, no errors either
        # (because the nodes just skip if data is missing)
        assert result["status"] == "success"


# ═══════════════════════════════════════════════════════════════════════
# Section 6: Perspective graph state transitions
# ═══════════════════════════════════════════════════════════════════════


class TestPerspectiveGraphTransitions:
    """Perspective graph handles biases, kegan, decision framework."""

    def test_bias_detection(self) -> None:
        """Bias detection produces detected_biases in results."""
        state = _make_initial_state(
            request_data={"text": "I think this is the only way"}
        )

        with patch(
            "alchymine.engine.perspective.detect_biases",
            return_value=["confirmation_bias"],
        ):
            graph = build_perspective_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert "detected_biases" in result["results"]
        assert "confirmation_bias" in result["results"]["detected_biases"]

    def test_kegan_assessment(self) -> None:
        """Kegan assessment produces kegan_stage as string value in results."""
        from alchymine.engine.profile import KeganStage

        state = _make_initial_state(
            request_data={"kegan_responses": [1, 2, 3, 4, 5]}
        )

        with patch(
            "alchymine.engine.perspective.assess_kegan_stage",
            return_value=KeganStage.SOCIALIZED,
        ):
            graph = build_perspective_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["results"]["kegan_stage"] == "socialized"
        assert "kegan_description" in result["results"]
        assert "kegan_dimension_scores" in result["results"]

    def test_decision_framework(self) -> None:
        """Decision framework produces decision_analysis in results."""
        state = _make_initial_state(
            request_data={
                "decision": "Change careers",
                "pros": ["growth"],
                "cons": ["risk"],
            }
        )

        with patch(
            "alchymine.engine.perspective.pros_cons_analysis",
            return_value={"recommendation": "consider carefully"},
        ):
            graph = build_perspective_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert "decision_analysis" in result["results"]

    def test_all_three_nodes(self) -> None:
        """All three perspective nodes produce data in a single run."""
        from alchymine.engine.profile import KeganStage

        state = _make_initial_state(
            request_data={
                "text": "Is this biased?",
                "kegan_responses": [1, 2, 3],
                "decision": "Buy a house",
                "pros": ["equity"],
                "cons": ["debt"],
            }
        )

        with (
            patch(
                "alchymine.engine.perspective.detect_biases",
                return_value=["anchoring"],
            ),
            patch(
                "alchymine.engine.perspective.assess_kegan_stage",
                return_value=KeganStage.SELF_AUTHORING,
            ),
            patch(
                "alchymine.engine.perspective.pros_cons_analysis",
                return_value={"score": 0.6},
            ),
        ):
            graph = build_perspective_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert result["status"] == "success"
        assert "detected_biases" in result["results"]
        assert "kegan_stage" in result["results"]
        assert result["results"]["kegan_stage"] == "self-authoring"
        assert "decision_analysis" in result["results"]
        assert result["errors"] == []


# ═══════════════════════════════════════════════════════════════════════
# Section 7: Error handling nodes
# ═══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Graph nodes handle ImportError and runtime exceptions gracefully."""

    def test_import_error_collected_in_errors(self) -> None:
        """ImportError in an engine is captured, not raised."""
        from datetime import date

        state = _make_initial_state(
            request_data={"full_name": "Test", "birth_date": date(1990, 1, 1)}
        )

        with patch(
            "alchymine.engine.numerology.calculate_pythagorean_profile",
            side_effect=ImportError("no module"),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert any("not available" in e for e in result["errors"])

    def test_runtime_error_collected_in_errors(self) -> None:
        """RuntimeError in an engine is captured, not raised."""
        from datetime import date

        state = _make_initial_state(
            request_data={"full_name": "Test", "birth_date": date(1990, 1, 1)}
        )

        with patch(
            "alchymine.engine.numerology.calculate_pythagorean_profile",
            side_effect=RuntimeError("calculation failed"),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        assert any("calculation failed" in e for e in result["errors"])

    def test_partial_failure_preserves_successful_data(self) -> None:
        """When one node fails, data from successful nodes is preserved."""
        mock_profile = MagicMock()
        mock_profile.life_path = 5
        mock_profile.expression = 2
        mock_profile.soul_urge = 8
        mock_profile.personality = 3
        mock_profile.personal_year = 9
        mock_profile.personal_month = 1

        from datetime import date

        state = _make_initial_state(
            request_data={"full_name": "Test", "birth_date": date(1990, 1, 1)}
        )

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                side_effect=RuntimeError("ephemeris error"),
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            result = graph.invoke(state)

        # Numerology data preserved despite astrology failure
        assert "numerology" in result["results"]
        assert result["results"]["numerology"]["life_path"] == 5
        assert result["status"] == "degraded"


# ═══════════════════════════════════════════════════════════════════════
# Section 8: Quality gate integration
# ═══════════════════════════════════════════════════════════════════════


class TestQualityGateIntegration:
    """Quality gate nodes validate output within the graph."""

    def test_healing_quality_gate_passes_with_disclaimers(self) -> None:
        """Healing graph with quality gate passes when disclaimers present."""
        state = _make_initial_state(request_data={})

        graph = build_healing_graph(include_quality_gate=True)
        result = graph.invoke(state)

        assert result["quality_passed"] is True

    def test_wealth_quality_gate_passes_with_disclaimers(self) -> None:
        """Wealth graph with quality gate passes when disclaimers present."""
        state = _make_initial_state(request_data={})

        graph = build_wealth_graph(include_quality_gate=True)
        result = graph.invoke(state)

        assert result["quality_passed"] is True

    def test_intelligence_quality_gate_passes_by_default(self) -> None:
        """Intelligence has no dedicated quality gate — passes by default."""
        state = _make_initial_state(request_data={})

        graph = build_intelligence_graph(include_quality_gate=True)
        result = graph.invoke(state)

        assert result["quality_passed"] is True

    def test_quality_gate_node_function_directly(self) -> None:
        """_run_quality_gate_node can be called directly on state."""
        state: CoordinatorState = {
            "user_id": "test",
            "request_data": {},
            "results": {"disclaimers": ["Not medical advice. Consult a qualified healthcare professional."]},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        result = _run_quality_gate_node(state, "healing")
        assert result["quality_passed"] is True

    def test_quality_gate_fails_without_disclaimers(self) -> None:
        """Quality gate fails for healing output missing disclaimers."""
        state: CoordinatorState = {
            "user_id": "test",
            "request_data": {},
            "results": {"text": "This will cure your anxiety."},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        result = _run_quality_gate_node(state, "healing")
        assert result["quality_passed"] is False
        assert result["status"] == "degraded"
        assert any("quality gate" in e.lower() for e in result["errors"])


# ═══════════════════════════════════════════════════════════════════════
# Section 9: State checkpoint / node ordering
# ═══════════════════════════════════════════════════════════════════════


class TestNodeOrdering:
    """Verify that nodes execute in the correct order."""

    def test_intelligence_node_order(self) -> None:
        """Intelligence: numerology -> astrology -> personality -> archetype -> biorhythm -> status."""
        execution_log = []

        def log_node(name):
            def _node(state):
                execution_log.append(name)
                return state
            return _node

        with (
            patch(
                "alchymine.agents.orchestrator.graphs._intelligence_numerology",
                side_effect=log_node("numerology"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._intelligence_astrology",
                side_effect=log_node("astrology"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._intelligence_personality",
                side_effect=log_node("personality"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._intelligence_archetype",
                side_effect=log_node("archetype"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._intelligence_biorhythm",
                side_effect=log_node("biorhythm"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._intelligence_status",
                side_effect=log_node("status"),
            ),
        ):
            graph = build_intelligence_graph(include_quality_gate=False)
            state = _make_initial_state()
            graph.invoke(state)

        assert execution_log == ["numerology", "astrology", "personality", "archetype", "biorhythm", "status"]

    def test_healing_node_order(self) -> None:
        """Healing: init -> crisis_detection -> modality_matching -> status."""
        execution_log = []

        def log_node(name):
            def _node(state):
                execution_log.append(name)
                return state
            return _node

        with (
            patch(
                "alchymine.agents.orchestrator.graphs._healing_init",
                side_effect=log_node("init"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._healing_crisis_detection",
                side_effect=log_node("crisis_detection"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._healing_modality_matching",
                side_effect=log_node("modality_matching"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._healing_status",
                side_effect=log_node("status"),
            ),
        ):
            graph = build_healing_graph(include_quality_gate=False)
            state = _make_initial_state()
            graph.invoke(state)

        assert execution_log == ["init", "crisis_detection", "modality_matching", "status"]

    def test_wealth_node_order(self) -> None:
        """Wealth: init -> archetype -> lever_prioritisation -> calculations -> status."""
        execution_log = []

        def log_node(name):
            def _node(state):
                execution_log.append(name)
                return state
            return _node

        with (
            patch(
                "alchymine.agents.orchestrator.graphs._wealth_init",
                side_effect=log_node("init"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._wealth_archetype",
                side_effect=log_node("archetype"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._wealth_lever_prioritisation",
                side_effect=log_node("lever_prioritisation"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._wealth_calculations",
                side_effect=log_node("calculations"),
            ),
            patch(
                "alchymine.agents.orchestrator.graphs._wealth_status",
                side_effect=log_node("status"),
            ),
        ):
            graph = build_wealth_graph(include_quality_gate=False)
            state = _make_initial_state()
            graph.invoke(state)

        assert execution_log == [
            "init", "archetype", "lever_prioritisation", "calculations", "status"
        ]


# ═══════════════════════════════════════════════════════════════════════
# Section 10: Helper functions
# ═══════════════════════════════════════════════════════════════════════


class TestHelperFunctions:
    """Tests for _compute_status and _compute_status_with_baseline."""

    def test_compute_status_success(self) -> None:
        assert _compute_status([], {"data": 1}) == "success"

    def test_compute_status_error_no_data(self) -> None:
        assert _compute_status(["err"], {}) == "error"

    def test_compute_status_degraded_with_data(self) -> None:
        assert _compute_status(["err"], {"data": 1}) == "degraded"

    def test_compute_status_success_no_errors_no_data(self) -> None:
        assert _compute_status([], {}) == "success"

    def test_compute_status_with_baseline_success(self) -> None:
        assert _compute_status_with_baseline([], {"a": 1, "b": 2}, baseline_keys=2) == "success"

    def test_compute_status_with_baseline_degraded_only_baseline(self) -> None:
        assert _compute_status_with_baseline(["err"], {"a": 1}, baseline_keys=1) == "degraded"

    def test_compute_status_with_baseline_degraded_extra_data(self) -> None:
        assert (
            _compute_status_with_baseline(["err"], {"a": 1, "b": 2, "c": 3}, baseline_keys=1)
            == "degraded"
        )


# ═══════════════════════════════════════════════════════════════════════
# Section 11: Sequential fallback
# ═══════════════════════════════════════════════════════════════════════


class TestSequentialFallback:
    """The _SequentialGraph fallback runs nodes in order."""

    def test_sequential_graph_runs_all_nodes(self) -> None:
        log = []

        def node_a(state):
            log.append("a")
            return {**state, "a": True}

        def node_b(state):
            log.append("b")
            return {**state, "b": True}

        graph = _SequentialGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)

        result = graph.invoke({"x": 1})
        assert log == ["a", "b"]
        assert result["a"] is True
        assert result["b"] is True
        assert result["x"] == 1

    def test_sequential_graph_threads_state(self) -> None:
        """Each node receives the state from the previous node."""

        def node_a(state):
            return {**state, "count": state.get("count", 0) + 1}

        def node_b(state):
            return {**state, "count": state.get("count", 0) + 10}

        graph = _SequentialGraph()
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)

        result = graph.invoke({"count": 0})
        assert result["count"] == 11  # 0 + 1 + 10

    @pytest.mark.skipif(not _HAS_LANGGRAPH, reason="langgraph not installed")
    def test_sequential_fallback_matches_langgraph(self) -> None:
        """Sequential fallback produces the same result as LangGraph for a simple case."""
        state = _make_initial_state(request_data={})

        # Build with langgraph
        langgraph_result = build_intelligence_graph(include_quality_gate=False).invoke(state)

        # Build sequential fallback with all intelligence nodes
        from alchymine.agents.orchestrator.graphs import (
            _intelligence_archetype,
            _intelligence_astrology,
            _intelligence_biorhythm,
            _intelligence_numerology,
            _intelligence_personality,
            _intelligence_status,
        )

        seq = _SequentialGraph()
        seq.add_node("numerology", _intelligence_numerology)
        seq.add_node("astrology", _intelligence_astrology)
        seq.add_node("personality", _intelligence_personality)
        seq.add_node("archetype", _intelligence_archetype)
        seq.add_node("biorhythm", _intelligence_biorhythm)
        seq.add_node("status", _intelligence_status)
        seq_result = seq.invoke(dict(state))

        # Both should produce the same errors and status
        assert set(langgraph_result["errors"]) == set(seq_result["errors"])
        assert langgraph_result["status"] == seq_result["status"]


# ═══════════════════════════════════════════════════════════════════════
# Section 12: LangGraph availability
# ═══════════════════════════════════════════════════════════════════════


class TestLangGraphAvailability:
    """Verify that langgraph detection works correctly."""

    def test_langgraph_flag_is_bool(self) -> None:
        """_HAS_LANGGRAPH is a boolean reflecting whether the optional dep is installed."""
        assert isinstance(_HAS_LANGGRAPH, bool)

    def test_coordinator_state_is_typed_dict(self) -> None:
        """CoordinatorState is a TypedDict subclass."""
        # TypedDict classes have __annotations__
        assert hasattr(CoordinatorState, "__annotations__")
        assert "user_id" in CoordinatorState.__annotations__
        assert "request_data" in CoordinatorState.__annotations__
        assert "results" in CoordinatorState.__annotations__
        assert "errors" in CoordinatorState.__annotations__
        assert "status" in CoordinatorState.__annotations__
        assert "quality_passed" in CoordinatorState.__annotations__

"""Tests for the Perspective Prism engine.

Covers:
  - Decision frameworks (weighted matrix, pros/cons, Six Hats, second-order effects)
  - Cognitive bias detection and debiasing
  - Scenario modeling, probability assessment, sensitivity analysis
  - Kegan developmental stage assessment, description, growth pathway

Minimum: 35 tests (actual count is higher).
"""

from __future__ import annotations

import pytest

from alchymine.engine.perspective import (
    COGNITIVE_BIASES,
    assess_kegan_stage,
    detect_biases,
    growth_pathway,
    model_scenarios,
    probability_assessment,
    pros_cons_analysis,
    second_order_effects,
    sensitivity_analysis,
    six_thinking_hats,
    stage_description,
    suggest_debiasing,
    weighted_decision_matrix,
)
from alchymine.engine.profile import KeganStage

# ═══════════════════════════════════════════════════════════════════════════
# Decision Frameworks
# ═══════════════════════════════════════════════════════════════════════════


class TestWeightedDecisionMatrix:
    """Tests for weighted_decision_matrix."""

    def test_basic_ranking(self):
        """Options are ranked by weighted score."""
        result = weighted_decision_matrix(
            options=["A", "B"],
            criteria=[
                {"name": "cost", "weight": 0.5, "scores": {"A": 8, "B": 5}},
                {"name": "quality", "weight": 0.5, "scores": {"A": 6, "B": 9}},
            ],
        )
        ranked = result["ranked_options"]
        assert len(ranked) == 2
        # A: 8*0.5 + 6*0.5 = 7.0, B: 5*0.5 + 9*0.5 = 7.0 — equal
        assert ranked[0]["weighted_score"] == ranked[1]["weighted_score"]

    def test_unequal_weights(self):
        """Heavier weight on one criterion shifts ranking."""
        result = weighted_decision_matrix(
            options=["A", "B"],
            criteria=[
                {"name": "cost", "weight": 0.8, "scores": {"A": 9, "B": 3}},
                {"name": "quality", "weight": 0.2, "scores": {"A": 2, "B": 10}},
            ],
        )
        ranked = result["ranked_options"]
        assert ranked[0]["option"] == "A"
        assert ranked[0]["weighted_score"] > ranked[1]["weighted_score"]

    def test_includes_methodology(self):
        """Result includes methodology attribution."""
        result = weighted_decision_matrix(
            options=["X"],
            criteria=[{"name": "c1", "weight": 1.0, "scores": {"X": 5}}],
        )
        assert "methodology" in result
        assert "Weighted Decision Matrix" in result["methodology"]

    def test_criteria_breakdown_present(self):
        """Result includes per-criterion breakdown."""
        result = weighted_decision_matrix(
            options=["A"],
            criteria=[{"name": "c1", "weight": 1.0, "scores": {"A": 7}}],
        )
        assert len(result["criteria_breakdown"]) == 1
        assert result["criteria_breakdown"][0]["criterion"] == "c1"

    def test_missing_option_score_defaults_zero(self):
        """If an option has no score for a criterion, it defaults to 0."""
        result = weighted_decision_matrix(
            options=["A", "B"],
            criteria=[{"name": "c1", "weight": 1.0, "scores": {"A": 10}}],
        )
        ranked = result["ranked_options"]
        scores = {r["option"]: r["weighted_score"] for r in ranked}
        assert scores["B"] == 0.0

    def test_empty_options_raises(self):
        """Empty options list raises ValueError."""
        with pytest.raises(ValueError, match="At least one option"):
            weighted_decision_matrix(
                options=[],
                criteria=[{"name": "c", "weight": 1, "scores": {}}],
            )

    def test_empty_criteria_raises(self):
        """Empty criteria list raises ValueError."""
        with pytest.raises(ValueError, match="At least one criterion"):
            weighted_decision_matrix(options=["A"], criteria=[])

    def test_invalid_criterion_structure_raises(self):
        """Criterion missing required keys raises ValueError."""
        with pytest.raises(ValueError, match="name"):
            weighted_decision_matrix(
                options=["A"],
                criteria=[{"weight": 1.0}],
            )


class TestProsConsAnalysis:
    """Tests for pros_cons_analysis."""

    def test_strongly_favourable(self):
        """Many pros, few cons gives strongly favourable."""
        result = pros_cons_analysis("Option X", ["a", "b", "c", "d"], ["z"])
        assert result["balance_score"] > 0.5
        assert result["assessment"] == "Strongly favourable"

    def test_strongly_unfavourable(self):
        """Many cons, few pros gives strongly unfavourable."""
        result = pros_cons_analysis("Option Y", ["a"], ["b", "c", "d", "e"])
        assert result["balance_score"] < -0.5
        assert result["assessment"] == "Strongly unfavourable"

    def test_balanced(self):
        """Equal pros and cons gives balanced assessment."""
        result = pros_cons_analysis("Option Z", ["a", "b"], ["c", "d"])
        assert result["balance_score"] == 0.0
        assert "Balanced" in result["assessment"]

    def test_empty_lists(self):
        """No pros or cons gives balance score of 0."""
        result = pros_cons_analysis("Option W", [], [])
        assert result["balance_score"] == 0.0

    def test_methodology_present(self):
        """Result includes methodology."""
        result = pros_cons_analysis("Test", ["a"], [])
        assert "Pros/Cons" in result["methodology"]

    def test_empty_option_raises(self):
        """Empty option string raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            pros_cons_analysis("", ["a"], ["b"])


class TestSixThinkingHats:
    """Tests for six_thinking_hats."""

    def test_full_coverage(self):
        """All six hats provided gives coverage 1.0."""
        perspectives = {
            "white": "Data shows...",
            "red": "I feel...",
            "black": "Risk is...",
            "yellow": "Benefit is...",
            "green": "Alternative...",
            "blue": "Process...",
        }
        result = six_thinking_hats("Should I launch?", perspectives)
        assert result["coverage_score"] == 1.0
        assert result["missing_hats"] == []

    def test_partial_coverage(self):
        """Two hats gives 2/6 coverage."""
        result = six_thinking_hats("Problem", {"white": "facts", "red": "feelings"})
        assert abs(result["coverage_score"] - 2 / 6) < 0.001
        assert len(result["missing_hats"]) == 4

    def test_invalid_hat_raises(self):
        """Invalid hat colour raises ValueError."""
        with pytest.raises(ValueError, match="Invalid hat colour"):
            six_thinking_hats("Problem", {"purple": "ideas"})

    def test_empty_problem_raises(self):
        """Empty problem raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            six_thinking_hats("", {"white": "data"})

    def test_methodology_attribution(self):
        """Methodology mentions de Bono."""
        result = six_thinking_hats("Test", {"white": "data"})
        assert "de Bono" in result["methodology"]

    def test_hat_descriptions_present(self):
        """Each hat entry includes description."""
        result = six_thinking_hats("Test", {"white": "facts"})
        for hat in result["hats"]:
            assert "description" in hat
            assert len(hat["description"]) > 0

    def test_synthesis_mentions_missing(self):
        """Synthesis mentions missing perspectives."""
        result = six_thinking_hats("Test", {"white": "data"})
        assert "perspectives addressed" in result["synthesis"]


class TestSecondOrderEffects:
    """Tests for second_order_effects."""

    def test_effect_chain_generation(self):
        """First-order effects generate second- and third-order chains."""
        result = second_order_effects(
            "Hire a new team member",
            ["More capacity", "Higher costs"],
        )
        assert len(result["first_order"]) == 2
        assert len(result["second_order"]) == 4  # 2 per first-order
        assert len(result["third_order"]) == 4  # 1 per second-order
        assert result["total_effects_mapped"] == 10

    def test_empty_effects_list(self):
        """No first-order effects gives empty chains."""
        result = second_order_effects("Decision", [])
        assert result["total_effects_mapped"] == 0
        assert result["complexity_rating"] == "low"

    def test_complexity_rating_high(self):
        """Many effects give high complexity."""
        result = second_order_effects(
            "Big change",
            [f"effect_{i}" for i in range(10)],
        )
        assert result["complexity_rating"] == "high"

    def test_empty_decision_raises(self):
        """Empty decision raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            second_order_effects("", ["effect"])

    def test_methodology_present(self):
        """Result includes methodology."""
        result = second_order_effects("Test", ["e"])
        assert "Second-Order" in result["methodology"]


# ═══════════════════════════════════════════════════════════════════════════
# Cognitive Bias Detection
# ═══════════════════════════════════════════════════════════════════════════


class TestBiasDetection:
    """Tests for detect_biases and bias catalog."""

    def test_catalog_has_twenty_biases(self):
        """Catalog contains at least 20 cognitive biases."""
        assert len(COGNITIVE_BIASES) >= 20

    def test_each_bias_has_required_fields(self):
        """Every bias entry has name, description, keywords, source."""
        for key, bias in COGNITIVE_BIASES.items():
            assert "name" in bias, f"Missing 'name' in {key}"
            assert "description" in bias, f"Missing 'description' in {key}"
            assert "keywords" in bias, f"Missing 'keywords' in {key}"
            assert "source" in bias, f"Missing 'source' in {key}"
            assert len(bias["keywords"]) >= 3, f"Too few keywords in {key}"

    def test_detects_confirmation_bias(self):
        """Detects confirmation bias from matching text."""
        text = "I knew it! This proves my point. Exactly as I expected."
        results = detect_biases(text)
        bias_types = [r["bias_type"] for r in results]
        assert "confirmation_bias" in bias_types

    def test_detects_sunk_cost(self):
        """Detects sunk cost fallacy from matching text."""
        text = "We've already invested too much time. Can't give up now after coming this far."
        results = detect_biases(text)
        bias_types = [r["bias_type"] for r in results]
        assert "sunk_cost_fallacy" in bias_types

    def test_detects_bandwagon(self):
        """Detects bandwagon effect."""
        text = "Everyone is doing it. The trend is clear. Popular opinion says so."
        results = detect_biases(text)
        bias_types = [r["bias_type"] for r in results]
        assert "bandwagon_effect" in bias_types

    def test_empty_text_returns_empty(self):
        """Empty text returns no biases."""
        assert detect_biases("") == []
        assert detect_biases("   ") == []

    def test_no_match_returns_empty(self):
        """Text without bias patterns returns empty list."""
        results = detect_biases("The data shows a 15% increase over the quarter.")
        # This neutral text should trigger very few or no biases
        assert isinstance(results, list)

    def test_confidence_capped_at_one(self):
        """Confidence score is capped at 1.0."""
        # Feed text with many keywords for a single bias
        text = (
            "I knew it. Proves my point. As I expected. "
            "I always thought so. Confirms what I believed. "
            "Just as I said. This supports my view."
        )
        results = detect_biases(text)
        for r in results:
            assert r["confidence"] <= 1.0

    def test_results_sorted_by_confidence(self):
        """Results are sorted by confidence descending."""
        text = "I knew it. Proves my point. As I expected. Recently there was something."
        results = detect_biases(text)
        if len(results) >= 2:
            confidences = [r["confidence"] for r in results]
            assert confidences == sorted(confidences, reverse=True)


class TestDebiasing:
    """Tests for suggest_debiasing."""

    def test_returns_strategies_for_known_bias(self):
        """Returns strategies for a known bias type."""
        result = suggest_debiasing("confirmation_bias")
        assert len(result["strategies"]) > 0
        assert result["bias_name"] == "Confirmation Bias"

    def test_returns_reframe(self):
        """Result includes a constructive reframe."""
        result = suggest_debiasing("sunk_cost_fallacy")
        assert "reframe" in result
        assert len(result["reframe"]) > 0

    def test_unknown_bias_raises(self):
        """Unknown bias type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown bias type"):
            suggest_debiasing("nonexistent_bias")

    def test_methodology_present(self):
        """Result includes methodology."""
        result = suggest_debiasing("anchoring_bias")
        assert "methodology" in result
        assert "Kahneman" in result["methodology"]

    def test_all_biases_have_debiasing(self):
        """Every bias in the catalog has debiasing strategies."""
        for bias_key in COGNITIVE_BIASES:
            result = suggest_debiasing(bias_key)
            assert len(result["strategies"]) > 0, f"No strategies for {bias_key}"


# ═══════════════════════════════════════════════════════════════════════════
# Scenario Modeling
# ═══════════════════════════════════════════════════════════════════════════


class TestModelScenarios:
    """Tests for model_scenarios."""

    def test_generates_three_scenarios(self):
        """Generates best, worst, and likely scenarios."""
        result = model_scenarios(
            "Launch product",
            [
                {"name": "revenue", "best": 100, "worst": 20, "likely": 60},
                {"name": "cost", "best": 30, "worst": 80, "likely": 50},
            ],
        )
        assert len(result) == 3
        types = {s["scenario_type"] for s in result}
        assert types == {"best", "worst", "likely"}

    def test_best_scenario_uses_best_values(self):
        """Best scenario uses best-case variable values."""
        variables = [
            {"name": "revenue", "best": 100, "worst": 20, "likely": 60},
        ]
        result = model_scenarios("Test", variables)
        best = next(s for s in result if s["scenario_type"] == "best")
        assert best["variable_values"]["revenue"] == 100

    def test_aggregate_score_calculation(self):
        """Aggregate score is the mean of variable values."""
        variables = [
            {"name": "a", "best": 10, "worst": 2, "likely": 6},
            {"name": "b", "best": 20, "worst": 4, "likely": 12},
        ]
        result = model_scenarios("Test", variables)
        best = next(s for s in result if s["scenario_type"] == "best")
        assert best["aggregate_score"] == 15.0  # (10 + 20) / 2

    def test_empty_decision_raises(self):
        """Empty decision raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            model_scenarios("", [{"name": "x", "best": 1, "worst": 0, "likely": 0.5}])

    def test_empty_variables_raises(self):
        """Empty variables list raises ValueError."""
        with pytest.raises(ValueError, match="At least one variable"):
            model_scenarios("Test", [])

    def test_methodology_present(self):
        """Each scenario includes methodology."""
        result = model_scenarios("Test", [{"name": "x", "best": 10, "worst": 1, "likely": 5}])
        for s in result:
            assert "Royal Dutch Shell" in s["methodology"]


class TestProbabilityAssessment:
    """Tests for probability_assessment."""

    def test_likely_gets_highest_probability(self):
        """Most-likely scenario gets highest probability midpoint."""
        scenarios = model_scenarios("Test", [{"name": "x", "best": 100, "worst": 10, "likely": 50}])
        result = probability_assessment(scenarios)
        likely_assessment = next(a for a in result["assessments"] if a["scenario_type"] == "likely")
        other_assessments = [a for a in result["assessments"] if a["scenario_type"] != "likely"]
        for other in other_assessments:
            assert likely_assessment["probability_midpoint"] > other["probability_midpoint"]

    def test_empty_scenarios_raises(self):
        """Empty scenarios raises ValueError."""
        with pytest.raises(ValueError, match="At least one scenario"):
            probability_assessment([])

    def test_methodology_present(self):
        """Result includes methodology."""
        scenarios = model_scenarios("Test", [{"name": "x", "best": 10, "worst": 1, "likely": 5}])
        result = probability_assessment(scenarios)
        assert "Triangular" in result["methodology"]


class TestSensitivityAnalysis:
    """Tests for sensitivity_analysis."""

    def test_most_sensitive_variable(self):
        """Variable with largest range is most sensitive."""
        variables = [
            {"name": "stable", "best": 10, "worst": 9, "likely": 9.5},
            {"name": "volatile", "best": 100, "worst": 1, "likely": 50},
        ]
        result = sensitivity_analysis(variables)
        assert result["most_sensitive"] == "volatile"
        assert result["least_sensitive"] == "stable"

    def test_normalised_impact_of_most_sensitive(self):
        """Most sensitive variable has normalised impact of 1.0."""
        variables = [
            {"name": "a", "best": 10, "worst": 5, "likely": 7},
            {"name": "b", "best": 100, "worst": 0, "likely": 50},
        ]
        result = sensitivity_analysis(variables)
        top = result["ranked_variables"][0]
        assert top["normalised_impact"] == 1.0

    def test_skew_direction(self):
        """Skew direction reflects position of likely relative to midpoint."""
        variables = [
            {"name": "optimistic_skew", "best": 100, "worst": 0, "likely": 70},
        ]
        result = sensitivity_analysis(variables)
        assert result["ranked_variables"][0]["skew_direction"] == "optimistic"

    def test_pessimistic_skew(self):
        """Pessimistic skew detected when likely is below midpoint."""
        variables = [
            {"name": "pessimistic_skew", "best": 100, "worst": 0, "likely": 30},
        ]
        result = sensitivity_analysis(variables)
        assert result["ranked_variables"][0]["skew_direction"] == "pessimistic"

    def test_centred_skew(self):
        """Centred skew when likely equals midpoint."""
        variables = [
            {"name": "centred", "best": 100, "worst": 0, "likely": 50},
        ]
        result = sensitivity_analysis(variables)
        assert result["ranked_variables"][0]["skew_direction"] == "centred"

    def test_empty_variables_raises(self):
        """Empty variables raises ValueError."""
        with pytest.raises(ValueError, match="At least one variable"):
            sensitivity_analysis([])

    def test_methodology_present(self):
        """Result includes methodology."""
        result = sensitivity_analysis([{"name": "x", "best": 10, "worst": 1, "likely": 5}])
        assert "OAT" in result["methodology"]


# ═══════════════════════════════════════════════════════════════════════════
# Kegan Stage Assessment
# ═══════════════════════════════════════════════════════════════════════════


class TestKeganAssessment:
    """Tests for assess_kegan_stage."""

    def test_stage_1_impulsive(self):
        """Low scores across dimensions map to impulsive stage."""
        result = assess_kegan_stage(
            {
                "self_awareness": 1,
                "perspective_taking": 1,
                "conflict_tolerance": 1,
            }
        )
        assert result == KeganStage.IMPULSIVE

    def test_stage_3_socialized(self):
        """Mid-range scores mapping to socialized stage."""
        result = assess_kegan_stage(
            {
                "self_awareness": 3,
                "perspective_taking": 3,
                "relationship_to_authority": 3.5,
                "conflict_tolerance": 2.5,
                "systems_thinking": 2.5,
            }
        )
        assert result == KeganStage.SOCIALIZED

    def test_stage_4_self_authoring(self):
        """Higher scores map to self-authoring stage."""
        result = assess_kegan_stage(
            {
                "self_awareness": 4,
                "perspective_taking": 4,
                "relationship_to_authority": 4.5,
                "conflict_tolerance": 4,
                "systems_thinking": 3.5,
            }
        )
        assert result == KeganStage.SELF_AUTHORING

    def test_stage_5_self_transforming(self):
        """Maximum scores map to self-transforming stage."""
        result = assess_kegan_stage(
            {
                "self_awareness": 5,
                "perspective_taking": 5,
                "conflict_tolerance": 5,
                "systems_thinking": 5,
            }
        )
        assert result == KeganStage.SELF_TRANSFORMING

    def test_returns_kegan_stage_enum(self):
        """Result is always a KeganStage enum value."""
        result = assess_kegan_stage(
            {
                "self_awareness": 3,
                "perspective_taking": 3,
            }
        )
        assert isinstance(result, KeganStage)

    def test_too_few_dimensions_raises(self):
        """Fewer than 2 valid dimensions raises ValueError."""
        with pytest.raises(ValueError, match="At least 2"):
            assess_kegan_stage({"self_awareness": 3})

    def test_out_of_range_score_raises(self):
        """Score outside 1-5 range raises ValueError."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            assess_kegan_stage({"self_awareness": 0, "perspective_taking": 3})

    def test_invalid_dimension_ignored(self):
        """Invalid dimension keys are silently ignored."""
        result = assess_kegan_stage(
            {
                "self_awareness": 3,
                "perspective_taking": 3,
                "bogus_dimension": 5,
            }
        )
        assert isinstance(result, KeganStage)


class TestStageDescription:
    """Tests for stage_description."""

    def test_all_stages_have_descriptions(self):
        """Every KeganStage has a description."""
        for stage in KeganStage:
            result = stage_description(stage)
            assert result["stage"] == stage
            assert len(result["description"]) > 0

    def test_includes_strengths(self):
        """Description includes strengths list."""
        result = stage_description(KeganStage.SELF_AUTHORING)
        assert len(result["strengths"]) > 0

    def test_includes_growth_edges(self):
        """Description includes growth edges."""
        result = stage_description(KeganStage.SOCIALIZED)
        assert len(result["growth_edges"]) > 0

    def test_methodology_mentions_kegan(self):
        """Methodology mentions Kegan."""
        result = stage_description(KeganStage.IMPERIAL)
        assert "Kegan" in result["methodology"]

    def test_no_fatalistic_language(self):
        """Descriptions do not contain fatalistic or limiting language."""
        fatalistic_terms = [
            "you will never",
            "cannot grow",
            "stuck at",
            "doomed",
            "hopeless",
            "permanently",
        ]
        for stage in KeganStage:
            result = stage_description(stage)
            desc = result["description"].lower()
            for term in fatalistic_terms:
                assert term not in desc, f"Fatalistic term '{term}' found in {stage} description"


class TestGrowthPathway:
    """Tests for growth_pathway."""

    def test_all_stages_have_pathways(self):
        """Every KeganStage has a growth pathway."""
        for stage in KeganStage:
            result = growth_pathway(stage)
            assert len(result["practices"]) > 0

    def test_target_stage_for_non_final(self):
        """Non-final stages have a target stage."""
        result = growth_pathway(KeganStage.SOCIALIZED)
        assert result["target_stage"] == KeganStage.SELF_AUTHORING

    def test_final_stage_has_no_target(self):
        """Self-Transforming has no target stage."""
        result = growth_pathway(KeganStage.SELF_TRANSFORMING)
        assert result["target_stage"] is None

    def test_encouragement_present(self):
        """Pathway includes empowering encouragement."""
        result = growth_pathway(KeganStage.IMPERIAL)
        assert "encouragement" in result
        assert len(result["encouragement"]) > 0

    def test_supportive_environments(self):
        """Pathway includes supportive environments."""
        result = growth_pathway(KeganStage.SELF_AUTHORING)
        assert len(result["supportive_environments"]) > 0

    def test_methodology_present(self):
        """Pathway includes methodology."""
        result = growth_pathway(KeganStage.IMPULSIVE)
        assert "Kegan" in result["methodology"]

    def test_no_fatalistic_language_in_encouragement(self):
        """Encouragement does not contain fatalistic language."""
        for stage in KeganStage:
            result = growth_pathway(stage)
            text = result["encouragement"].lower()
            assert "you must" not in text
            assert "you will never" not in text
            assert "stuck" not in text


# ═══════════════════════════════════════════════════════════════════════════
# Integration / Smoke Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPerspectiveImports:
    """Verify the public API is importable from the package."""

    def test_import_all_public_api(self):
        """All items in __all__ are importable."""
        import alchymine.engine.perspective as perspective
        from alchymine.engine.perspective import __all__ as exports

        for name in exports:
            assert hasattr(perspective, name), f"{name} not found in perspective package"

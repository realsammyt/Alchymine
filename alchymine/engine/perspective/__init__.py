"""Perspective Prism engines — decision frameworks, bias detection, scenario modeling, Kegan assessment.

Public API:
    Decision Frameworks:
        weighted_decision_matrix   — Weighted scoring matrix for multi-criteria decisions
        pros_cons_analysis         — Structured pros/cons with balance scoring
        six_thinking_hats          — De Bono's Six Thinking Hats analysis
        second_order_effects       — Map 1st, 2nd, 3rd order consequences

    Cognitive Bias Detection:
        COGNITIVE_BIASES           — Reference catalog of ~20 common cognitive biases
        detect_biases              — Identify cognitive biases in reasoning text
        suggest_debiasing          — Debiasing strategies per bias type

    Scenario Modeling:
        model_scenarios            — Generate best/worst/likely scenarios
        probability_assessment     — Assign probability ranges to scenarios
        sensitivity_analysis       — Identify which variables matter most

    Kegan Developmental Assessment:
        assess_kegan_stage         — Determine developmental stage from responses
        stage_description          — Description, strengths, and growth edges per stage
        growth_pathway             — Suggested development practices
"""

from .biases import COGNITIVE_BIASES, detect_biases, suggest_debiasing
from .frameworks import (
    pros_cons_analysis,
    second_order_effects,
    six_thinking_hats,
    weighted_decision_matrix,
)
from .kegan import assess_kegan_stage, growth_pathway, stage_description
from .scenarios import model_scenarios, probability_assessment, sensitivity_analysis

__all__ = [
    # Frameworks
    "weighted_decision_matrix",
    "pros_cons_analysis",
    "six_thinking_hats",
    "second_order_effects",
    # Biases
    "COGNITIVE_BIASES",
    "detect_biases",
    "suggest_debiasing",
    # Scenarios
    "model_scenarios",
    "probability_assessment",
    "sensitivity_analysis",
    # Kegan
    "assess_kegan_stage",
    "stage_description",
    "growth_pathway",
]

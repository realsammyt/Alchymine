"""Perspective crew — 5 domain agents for the Perspective Enhancement system.

Agents:
    BiasDetector         — Cognitive bias detection
    KeganAssessor        — Developmental stage assessment
    FrameworkApplier     — Apply decision frameworks (pros/cons, six hats, etc.)
    ScenarioModeler      — Scenario analysis + second-order effects
    PerspectiveNarrative — Generate perspective insight narratives
"""

from __future__ import annotations

from typing import Any

from .base import AgentRole, AgentTask, DomainAgent, SystemCrew

_SYSTEM = "perspective"


# ─── BiasDetector ──────────────────────────────────────────────────


class BiasDetector(DomainAgent):
    """Detects cognitive biases in reasoning text."""

    def __init__(self) -> None:
        super().__init__(
            name="BiasDetector",
            role=AgentRole.DETECTOR,
            goal=(
                "Identify potential cognitive biases in the user's "
                "reasoning text and suggest debiasing strategies."
            ),
            backstory=(
                "Cognitive bias specialist trained in Kahneman & Tversky's "
                "heuristics and biases programme. Uses keyword pattern "
                "matching to surface potential blind spots in reasoning. "
                "Findings are presented as reflective aids, not judgments — "
                "detecting a bias pattern does not mean the reasoning is wrong."
            ),
            system=_SYSTEM,
            tools=["perspective.detect_biases", "perspective.suggest_debiasing"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Detect biases in reasoning text and suggest debiasing."""
        from alchymine.engine.perspective import detect_biases, suggest_debiasing

        reasoning_text: str = context.get("text", "")
        if not reasoning_text:
            return {"detected_biases": [], "debiasing_suggestions": []}

        biases = detect_biases(reasoning_text)

        # Generate debiasing suggestions for each detected bias
        suggestions = []
        for bias in biases:
            try:
                suggestion = suggest_debiasing(bias["bias_type"])
                suggestions.append(suggestion)
            except ValueError:
                pass

        return {
            "detected_biases": biases,
            "debiasing_suggestions": suggestions,
        }


# ─── KeganAssessor ─────────────────────────────────────────────────


class KeganAssessor(DomainAgent):
    """Assesses developmental stage using Kegan's framework."""

    def __init__(self) -> None:
        super().__init__(
            name="KeganAssessor",
            role=AgentRole.ANALYST,
            goal=(
                "Assess the user's developmental stage using Kegan's "
                "constructive-developmental framework and suggest a "
                "growth pathway."
            ),
            backstory=(
                "Developmental psychologist versed in Robert Kegan's "
                "five-stage model (The Evolving Self, 1982). Assesses "
                "stage from scored questionnaire dimensions. Stages "
                "describe capacity, not intelligence or worth — every "
                "stage has genuine strengths. Growth is supported, never "
                "forced."
            ),
            system=_SYSTEM,
            tools=[
                "perspective.assess_kegan_stage",
                "perspective.stage_description",
                "perspective.growth_pathway",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Assess Kegan developmental stage from dimension responses."""
        from alchymine.engine.perspective import (
            assess_kegan_stage,
            growth_pathway,
            stage_description,
        )

        responses = context.get("kegan_responses")
        if not responses or not isinstance(responses, dict):
            return {"kegan_stage": None, "kegan_error": "No Kegan responses provided"}

        stage = assess_kegan_stage(responses)
        description = stage_description(stage)
        pathway = growth_pathway(stage)

        return {
            "kegan_stage": stage.value,
            "kegan_description": description,
            "kegan_pathway": pathway,
        }


# ─── FrameworkApplier ──────────────────────────────────────────────


class FrameworkApplier(DomainAgent):
    """Applies structured decision frameworks to problems."""

    def __init__(self) -> None:
        super().__init__(
            name="FrameworkApplier",
            role=AgentRole.ANALYST,
            goal=(
                "Apply structured decision frameworks — pros/cons, "
                "weighted matrix, Six Thinking Hats — to the user's "
                "decision or problem."
            ),
            backstory=(
                "Decision framework specialist who applies structured "
                "analytical tools to help users think through decisions "
                "more completely. Draws on Edward de Bono's Six Thinking "
                "Hats, multi-criteria decision analysis, and pros/cons "
                "methodology. All analysis is deterministic."
            ),
            system=_SYSTEM,
            tools=[
                "perspective.pros_cons_analysis",
                "perspective.six_thinking_hats",
                "perspective.weighted_decision_matrix",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Apply the appropriate decision framework."""
        from alchymine.engine.perspective import (
            pros_cons_analysis,
            six_thinking_hats,
            weighted_decision_matrix,
        )

        results: dict[str, Any] = {}

        # Pros/Cons if data available
        decision = context.get("decision")
        pros = context.get("pros", [])
        cons = context.get("cons", [])
        if decision:
            pc_result = pros_cons_analysis(decision, pros, cons)
            results["pros_cons"] = pc_result

        # Six Hats if perspectives provided
        problem = context.get("problem")
        perspectives = context.get("perspectives")
        if problem and perspectives and isinstance(perspectives, dict):
            hats_result = six_thinking_hats(problem, perspectives)
            results["six_hats"] = hats_result

        # Weighted matrix if options and criteria provided
        options = context.get("options")
        criteria = context.get("criteria")
        if options and criteria:
            matrix_result = weighted_decision_matrix(options, criteria)
            results["decision_matrix"] = matrix_result

        if not results:
            return {
                "decision_analysis": None,
                "framework_error": "No decision/problem data provided",
            }

        return {"decision_analysis": results}


# ─── ScenarioModeler ──────────────────────────────────────────────


class ScenarioModeler(DomainAgent):
    """Models scenarios and second-order effects for decisions."""

    def __init__(self) -> None:
        super().__init__(
            name="ScenarioModeler",
            role=AgentRole.ANALYST,
            goal=(
                "Generate best/worst/likely scenarios and map first-, "
                "second-, and third-order effects of the user's decision."
            ),
            backstory=(
                "Scenario planner trained in the Royal Dutch Shell (1970s) "
                "scenario planning tradition and systems thinking. Maps "
                "causal chains to help users anticipate unintended "
                "consequences. All modeling is deterministic."
            ),
            system=_SYSTEM,
            tools=[
                "perspective.model_scenarios",
                "perspective.second_order_effects",
                "perspective.sensitivity_analysis",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Model scenarios and second-order effects."""
        from alchymine.engine.perspective import (
            model_scenarios,
            second_order_effects,
            sensitivity_analysis,
        )

        results: dict[str, Any] = {}

        # Scenario modeling
        scenario_decision = context.get("scenario_decision") or context.get("decision")
        variables = context.get("scenario_variables")
        if scenario_decision and variables:
            scenarios = model_scenarios(scenario_decision, variables)
            results["scenarios"] = scenarios

            # Sensitivity analysis on the same variables
            sensitivity = sensitivity_analysis(variables)
            results["sensitivity"] = sensitivity

        # Second-order effects
        effects_decision = context.get("effects_decision") or context.get("decision")
        effects = context.get("first_order_effects")
        if effects_decision and effects:
            effects_result = second_order_effects(effects_decision, effects)
            results["second_order_effects"] = effects_result

        if not results:
            return {
                "scenario_analysis": None,
                "scenario_error": "No scenario data provided",
            }

        return {"scenario_analysis": results}


# ─── PerspectiveNarrative ─────────────────────────────────────────


class PerspectiveNarrative(DomainAgent):
    """Generates perspective insight narratives."""

    def __init__(self) -> None:
        super().__init__(
            name="PerspectiveNarrative",
            role=AgentRole.GUIDE,
            goal=(
                "Generate a thoughtful perspective narrative that "
                "integrates bias detection, Kegan stage insights, "
                "decision framework results, and scenario analysis."
            ),
            backstory=(
                "Perspective guide who synthesizes cognitive bias findings, "
                "developmental stage awareness, decision analysis, and "
                "scenario modeling into an empowering narrative. Uses "
                "reflective language that encourages growth without "
                "judgment."
            ),
            system=_SYSTEM,
            tools=["narrative.generate"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a perspective insight narrative."""
        sections: list[str] = []

        # Bias detection
        biases = context.get("detected_biases")
        if biases and isinstance(biases, list) and len(biases) > 0:
            bias_names = [b.get("bias_name", "unknown") for b in biases[:3] if isinstance(b, dict)]
            sections.append(
                f"Potential cognitive patterns detected: {', '.join(bias_names)}. "
                f"These are reflective observations, not judgments — recognizing "
                f"patterns is the first step to seeing through them."
            )

        # Kegan stage
        kegan_stage = context.get("kegan_stage")
        kegan_desc = context.get("kegan_description")
        if kegan_stage:
            name = (
                kegan_desc.get("name", kegan_stage) if isinstance(kegan_desc, dict) else kegan_stage
            )
            sections.append(
                f"Your assessed developmental stage is {name}. "
                f"Every stage has genuine strengths. Growth is a journey, "
                f"not a destination."
            )

        # Decision analysis
        analysis = context.get("decision_analysis")
        if analysis and isinstance(analysis, dict):
            frameworks_used = list(analysis.keys())
            sections.append(
                f"Decision analysis applied {len(frameworks_used)} framework(s): "
                f"{', '.join(frameworks_used)}."
            )

        # Scenario analysis
        scenario = context.get("scenario_analysis")
        if scenario and isinstance(scenario, dict):
            if "scenarios" in scenario:
                sections.append(
                    "Scenario modeling generated best, worst, and likely "
                    "outcomes to help you anticipate potential paths."
                )

        narrative = (
            " ".join(sections)
            if sections
            else (
                "Your perspective profile is being assembled. "
                "Share a decision or reasoning to unlock deeper insights."
            )
        )

        return {
            "perspective_narrative": narrative,
            "perspective_sections": sections,
        }


# ─── Crew assembly ─────────────────────────────────────────────────


def build_perspective_crew() -> SystemCrew:
    """Assemble the Perspective system crew with all 5 agents and tasks."""
    bias_detector = BiasDetector()
    kegan_assessor = KeganAssessor()
    framework_applier = FrameworkApplier()
    scenario_modeler = ScenarioModeler()
    perspective_narrative = PerspectiveNarrative()

    agents = [
        bias_detector,
        kegan_assessor,
        framework_applier,
        scenario_modeler,
        perspective_narrative,
    ]

    tasks = [
        AgentTask(
            name="detect_biases",
            description="Scan reasoning text for cognitive bias patterns.",
            agent=bias_detector,
            expected_output="List of detected biases with debiasing suggestions.",
        ),
        AgentTask(
            name="assess_kegan_stage",
            description="Assess developmental stage from dimension responses.",
            agent=kegan_assessor,
            expected_output="Kegan stage with description and growth pathway.",
        ),
        AgentTask(
            name="apply_frameworks",
            description="Apply decision frameworks to the user's problem.",
            agent=framework_applier,
            expected_output="Dict with framework analysis results.",
        ),
        AgentTask(
            name="model_scenarios",
            description="Generate scenarios and map second-order effects.",
            agent=scenario_modeler,
            expected_output="Dict with scenario and effects analysis.",
        ),
        AgentTask(
            name="generate_perspective_narrative",
            description="Generate reflective perspective insight narrative.",
            agent=perspective_narrative,
            expected_output="Narrative text with perspective insights.",
        ),
    ]

    return SystemCrew(name=_SYSTEM, agents=agents, tasks=tasks)

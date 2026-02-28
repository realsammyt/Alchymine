"""Creative crew — 5 domain agents for the Creative Development system.

Agents:
    GuilfordAssessor      — Divergent thinking assessment
    StyleAnalyst          — Creative DNA / style fingerprint
    ProjectSuggester      — Project recommendations
    CreativeBlockDetector — Identify blocks and suggest exercises
    CreativeNarrative     — Generate creative development narratives
"""

from __future__ import annotations

from typing import Any

from .base import AgentRole, AgentTask, DomainAgent, SystemCrew

_SYSTEM = "creative"


# ─── GuilfordAssessor ──────────────────────────────────────────────


class GuilfordAssessor(DomainAgent):
    """Assesses divergent thinking using Guilford's six components."""

    def __init__(self) -> None:
        super().__init__(
            name="GuilfordAssessor",
            role=AgentRole.ANALYST,
            goal=(
                "Score the user's divergent thinking across Guilford's "
                "six components: fluency, flexibility, originality, "
                "elaboration, sensitivity, and redefinition."
            ),
            backstory=(
                "Creative assessment specialist versed in J. P. Guilford's "
                "Structure of Intellect model (1967). Scores each divergent "
                "thinking component from assessment responses. All scoring "
                "is deterministic — no LLM involvement."
            ),
            system=_SYSTEM,
            tools=["creative.assess_guilford"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Score Guilford components from assessment responses."""
        from alchymine.engine.creative import assess_guilford

        responses = context.get("guilford_responses") or context.get("assessment_responses", {})

        if not responses:
            return {"guilford_scores": None, "guilford_error": "No assessment responses provided"}

        scores = assess_guilford(responses)
        scores_dict = {
            "fluency": scores.fluency,
            "flexibility": scores.flexibility,
            "originality": scores.originality,
            "elaboration": scores.elaboration,
            "sensitivity": scores.sensitivity,
            "redefinition": scores.redefinition,
        }

        return {
            "guilford_scores": scores_dict,
            "_guilford_model": scores,
        }


# ─── StyleAnalyst ──────────────────────────────────────────────────


class StyleAnalyst(DomainAgent):
    """Generates a creative style fingerprint from Guilford + DNA."""

    def __init__(self) -> None:
        super().__init__(
            name="StyleAnalyst",
            role=AgentRole.ANALYST,
            goal=(
                "Generate a unified creative style fingerprint combining "
                "Guilford divergent thinking scores and Tharp-inspired "
                "Creative DNA dimensions."
            ),
            backstory=(
                "Creative profiler who synthesizes Guilford assessment "
                "scores with Twyla Tharp's creative habit dimensions to "
                "produce a holistic style fingerprint — including dominant "
                "strengths, growth areas, and recommended mediums."
            ),
            system=_SYSTEM,
            tools=[
                "creative.generate_style_fingerprint",
                "creative.identify_strengths",
                "creative.identify_growth_areas",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate style fingerprint from Guilford and DNA data."""
        from alchymine.engine.creative import (
            assess_creative_dna,
            generate_style_fingerprint,
            identify_growth_areas,
            identify_strengths,
        )
        from alchymine.engine.profile import GuilfordScores

        guilford_model = context.get("_guilford_model")
        guilford_dict = context.get("guilford_scores")

        if guilford_model is None and guilford_dict is not None:
            guilford_model = GuilfordScores(**guilford_dict)

        if guilford_model is None:
            return {"style_fingerprint": None, "style_error": "No Guilford scores available"}

        # Build Creative DNA from responses or defaults
        dna_responses = context.get("dna_responses", {})
        dna = assess_creative_dna(dna_responses) if dna_responses else assess_creative_dna({})

        fingerprint = generate_style_fingerprint(guilford_model, dna)
        strengths = identify_strengths(guilford_model)
        growth_areas = identify_growth_areas(guilford_model)

        return {
            "style_fingerprint": fingerprint,
            "creative_strengths": strengths,
            "creative_growth_areas": growth_areas,
            "_creative_dna": dna,
        }


# ─── ProjectSuggester ─────────────────────────────────────────────


class ProjectSuggester(DomainAgent):
    """Recommends creative projects based on style fingerprint."""

    def __init__(self) -> None:
        super().__init__(
            name="ProjectSuggester",
            role=AgentRole.GUIDE,
            goal=(
                "Recommend creative projects tailored to the user's "
                "style fingerprint and skill level."
            ),
            backstory=(
                "Creative project curator who matches project suggestions "
                "to the user's dominant Guilford components and skill level. "
                "Draws from a curated database of project templates across "
                "multiple creative mediums."
            ),
            system=_SYSTEM,
            tools=["creative.suggest_projects", "creative.estimate_project_scope"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Suggest projects based on style and skill level."""
        from alchymine.engine.creative import suggest_projects

        style = context.get("style_fingerprint")
        skill_level = context.get("skill_level", "beginner")

        if style is None:
            return {"project_suggestions": None, "project_error": "No style fingerprint available"}

        projects = suggest_projects(style, skill_level)

        return {
            "project_suggestions": projects,
        }


# ─── CreativeBlockDetector ─────────────────────────────────────────


class CreativeBlockDetector(DomainAgent):
    """Identifies creative blocks and suggests exercises to overcome them."""

    def __init__(self) -> None:
        super().__init__(
            name="CreativeBlockDetector",
            role=AgentRole.DETECTOR,
            goal=(
                "Identify creative blocks from the user's Guilford "
                "profile and suggest targeted exercises to overcome them."
            ),
            backstory=(
                "Creative coach who detects blocks by analyzing low-scoring "
                "Guilford components and the user's block history. "
                "Recommends specific exercises that target each weakness. "
                "Uses encouraging language — blocks are normal and "
                "temporary, not permanent limitations."
            ),
            system=_SYSTEM,
            tools=["creative.identify_growth_areas"],
        )

    # Common block types and corresponding exercises
    _BLOCK_EXERCISES: dict[str, list[str]] = {
        "fluency": [
            "Set a timer for 10 minutes and list as many ideas as possible without filtering.",
            "Practice stream-of-consciousness writing for 15 minutes daily.",
            "Try the SCAMPER technique on an existing idea.",
        ],
        "flexibility": [
            "Take one idea and reimagine it in 5 different genres or styles.",
            "Work in a completely unfamiliar medium for one week.",
            "Pair two unrelated concepts and find a creative connection.",
        ],
        "originality": [
            "Study work from an artist outside your usual influences.",
            "Apply a random constraint (e.g., use only 3 colors, write without the letter 'e').",
            "Practice the 'worst idea' technique — deliberately generate bad ideas to unlock creative flow.",
        ],
        "elaboration": [
            "Take a simple sketch and develop it into a fully realized piece over 3 sessions.",
            "Practice describing a single object in 500 words.",
            "Add three layers of detail to your next creative output.",
        ],
        "sensitivity": [
            "Take a 30-minute observation walk, noting problems and opportunities.",
            "Interview someone about a challenge they face and look for creative solutions.",
            "Keep a 'questions journal' — write 10 questions per day for a week.",
        ],
        "redefinition": [
            "Take a discarded object and find 3 new uses for it.",
            "Remix an existing work into something new (with attribution).",
            "Practice reframing: describe the same situation from 3 different perspectives.",
        ],
    }

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Detect creative blocks and suggest exercises."""
        guilford_scores = context.get("guilford_scores")
        block_history = context.get("block_history", [])

        if guilford_scores is None:
            return {"creative_blocks": None, "block_error": "No Guilford scores available"}

        blocks: list[dict[str, Any]] = []

        # Identify components scoring below 40 as potential blocks
        threshold = 40.0
        for component, score in guilford_scores.items():
            if isinstance(score, (int, float)) and score < threshold:
                exercises = self._BLOCK_EXERCISES.get(component, [])
                blocks.append(
                    {
                        "component": component,
                        "score": score,
                        "exercises": exercises,
                        "message": (
                            f"Your {component} score ({score}) suggests an opportunity "
                            f"for growth. Creative blocks in this area are common and "
                            f"temporary — targeted practice can make a significant difference."
                        ),
                    }
                )

        return {
            "creative_blocks": blocks,
            "block_count": len(blocks),
            "block_history": block_history,
        }


# ─── CreativeNarrative ────────────────────────────────────────────


class CreativeNarrative(DomainAgent):
    """Generates creative development narratives."""

    def __init__(self) -> None:
        super().__init__(
            name="CreativeNarrative",
            role=AgentRole.GUIDE,
            goal=(
                "Generate an encouraging creative development narrative "
                "that integrates style analysis, project suggestions, "
                "and block-overcoming strategies."
            ),
            backstory=(
                "Creative mentor who weaves assessment results, project "
                "ideas, and growth strategies into an encouraging, "
                "judgment-free narrative. Celebrates existing strengths "
                "while gently illuminating growth opportunities. "
                "Never discourages creative expression."
            ),
            system=_SYSTEM,
            tools=["narrative.generate"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a creative development narrative."""
        sections: list[str] = []

        # Style fingerprint
        fingerprint = context.get("style_fingerprint")
        if fingerprint and isinstance(fingerprint, dict):
            style = fingerprint.get("creative_style", "")
            if style:
                sections.append(f"Your creative style: {style}")

            overall = fingerprint.get("overall_score")
            if overall is not None:
                sections.append(f"Your overall creative assessment score is {overall}/100.")

        # Strengths
        strengths = context.get("creative_strengths")
        if strengths and isinstance(strengths, list):
            sections.append(f"Your top creative strengths are: {', '.join(strengths)}.")

        # Growth areas
        growth = context.get("creative_growth_areas")
        if growth and isinstance(growth, list):
            sections.append(
                f"Areas with growth potential: {', '.join(growth)}. "
                f"These represent exciting opportunities for development."
            )

        # Projects
        projects = context.get("project_suggestions")
        if projects and isinstance(projects, list):
            titles = [p.get("title", "") for p in projects[:3] if isinstance(p, dict)]
            if titles:
                sections.append(f"Recommended projects to explore: {', '.join(titles)}.")

        # Blocks
        blocks = context.get("creative_blocks")
        if blocks and isinstance(blocks, list) and len(blocks) > 0:
            sections.append(
                f"We identified {len(blocks)} area(s) where targeted "
                f"exercises could help unlock your creative potential."
            )

        narrative = (
            " ".join(sections)
            if sections
            else (
                "Your creative profile is being assembled. "
                "Complete a Guilford assessment to unlock detailed insights."
            )
        )

        return {
            "creative_narrative": narrative,
            "creative_sections": sections,
        }


# ─── Crew assembly ─────────────────────────────────────────────────


def build_creative_crew() -> SystemCrew:
    """Assemble the Creative system crew with all 5 agents and tasks."""
    guilford_assessor = GuilfordAssessor()
    style_analyst = StyleAnalyst()
    project_suggester = ProjectSuggester()
    block_detector = CreativeBlockDetector()
    creative_narrative = CreativeNarrative()

    agents = [
        guilford_assessor,
        style_analyst,
        project_suggester,
        block_detector,
        creative_narrative,
    ]

    tasks = [
        AgentTask(
            name="assess_guilford",
            description="Score divergent thinking from assessment responses.",
            agent=guilford_assessor,
            expected_output="Dict with Guilford scores for 6 components.",
        ),
        AgentTask(
            name="analyze_style",
            description="Generate style fingerprint from Guilford + Creative DNA.",
            agent=style_analyst,
            expected_output="Dict with style fingerprint, strengths, growth areas.",
        ),
        AgentTask(
            name="suggest_projects",
            description="Recommend creative projects by style and skill level.",
            agent=project_suggester,
            expected_output="List of project suggestion dicts.",
        ),
        AgentTask(
            name="detect_blocks",
            description="Identify creative blocks and suggest exercises.",
            agent=block_detector,
            expected_output="List of block dicts with exercises.",
        ),
        AgentTask(
            name="generate_creative_narrative",
            description="Generate encouraging creative development narrative.",
            agent=creative_narrative,
            expected_output="Narrative text celebrating strengths and growth.",
        ),
    ]

    return SystemCrew(name=_SYSTEM, agents=agents, tasks=tasks)

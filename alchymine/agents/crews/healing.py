"""Healing crew — 6 domain agents for the Ethical Healing system.

Agents:
    CrisisDetector     — Crisis keyword detection + resource routing
    ModalityMatcher    — Modality matching based on archetype/personality
    BreathworkGuide    — Breathwork pattern selection
    PracticeTracker    — Track practice streaks and engagement
    HealingValidator   — Ethics + safety validation
    HealingNarrative   — Generate healing guidance narratives
"""

from __future__ import annotations

from typing import Any

from .base import AgentRole, AgentTask, DomainAgent, SystemCrew

_SYSTEM = "healing"

_HEALING_DISCLAIMER = (
    "This is not medical advice. Please consult a qualified "
    "healthcare professional for medical concerns."
)


# ─── CrisisDetector ────────────────────────────────────────────────


class CrisisDetector(DomainAgent):
    """Detects crisis keywords in user text and routes to resources."""

    def __init__(self) -> None:
        super().__init__(
            name="CrisisDetector",
            role=AgentRole.DETECTOR,
            goal=(
                "Scan user text for crisis indicators and immediately "
                "surface appropriate crisis resources when detected."
            ),
            backstory=(
                "Safety-first agent trained to detect crisis language "
                "including suicidal ideation, self-harm, and acute "
                "distress. When triggered, always provides crisis "
                "hotline numbers and professional referral information "
                "before any other system output."
            ),
            system=_SYSTEM,
            tools=["healing.detect_crisis", "healing.get_crisis_resources"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Scan text for crisis keywords and return resources if detected."""
        from alchymine.engine.healing import detect_crisis

        user_text: str = context.get("text", "")
        if not user_text:
            return {"crisis_flag": False, "crisis_response": None}

        crisis = detect_crisis(user_text)
        if crisis is not None:
            return {
                "crisis_flag": True,
                "crisis_response": {
                    "severity": crisis.severity.value,
                    "resources": [{"name": r.name, "contact": r.contact} for r in crisis.resources],
                },
            }

        return {"crisis_flag": False, "crisis_response": None}


# ─── ModalityMatcher ───────────────────────────────────────────────


class ModalityMatcher(DomainAgent):
    """Matches healing modalities to user profile."""

    def __init__(self) -> None:
        super().__init__(
            name="ModalityMatcher",
            role=AgentRole.ANALYST,
            goal=(
                "Recommend healing modalities based on the user's "
                "archetype, personality traits, and stated intention."
            ),
            backstory=(
                "Healing modality specialist who combines archetype "
                "affinity mapping with Big Five personality scoring to "
                "recommend the most resonant practices. Respects user "
                "difficulty preferences and contraindications."
            ),
            system=_SYSTEM,
            tools=["healing.match_modalities"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Match modalities from archetype, big_five, and intention."""
        from alchymine.engine.healing import match_modalities

        archetype = context.get("archetype")
        archetype_secondary = context.get("archetype_secondary")
        big_five = context.get("big_five")
        intention = context.get("intention")

        if not archetype or not big_five or not intention:
            return {
                "recommended_modalities": None,
                "modality_error": "Missing archetype, big_five, or intention",
            }

        modalities = match_modalities(
            archetype,
            archetype_secondary,
            big_five,
            [intention] if not isinstance(intention, list) else intention,
        )
        return {
            "recommended_modalities": [
                {
                    "modality": m.modality,
                    "skill_trigger": m.skill_trigger,
                    "preference_score": m.preference_score,
                    "difficulty_level": (
                        m.difficulty_level.value
                        if hasattr(m.difficulty_level, "value")
                        else str(m.difficulty_level)
                    ),
                }
                for m in modalities
            ],
        }


# ─── BreathworkGuide ───────────────────────────────────────────────


class BreathworkGuide(DomainAgent):
    """Selects appropriate breathwork patterns for the user."""

    def __init__(self) -> None:
        super().__init__(
            name="BreathworkGuide",
            role=AgentRole.GUIDE,
            goal=(
                "Select the most appropriate breathwork pattern based on "
                "the user's difficulty level and stated intention."
            ),
            backstory=(
                "Breathwork facilitator versed in box breathing, coherence, "
                "4-7-8 relaxation, Wim Hof, alternate nostril (Nadi "
                "Shodhana), and holotropic techniques. Matches patterns "
                "to user readiness and goals."
            ),
            system=_SYSTEM,
            tools=["healing.get_breathwork_pattern"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Select a breathwork pattern from difficulty and intention."""
        from alchymine.engine.healing import get_breathwork_pattern
        from alchymine.engine.profile import PracticeDifficulty

        difficulty_str = context.get("difficulty", "foundation")
        intention = context.get("breathwork_intention") or context.get("intention")

        # Convert string to enum
        try:
            difficulty = PracticeDifficulty(difficulty_str)
        except ValueError:
            difficulty = PracticeDifficulty.FOUNDATION

        # intention for breathwork is a simple string like "calm", "energy"
        intention_str = None
        if intention is not None:
            intention_str = str(intention.value) if hasattr(intention, "value") else str(intention)

        pattern = get_breathwork_pattern(difficulty=difficulty, intention=intention_str)

        return {
            "breathwork_pattern": {
                "name": pattern.name,
                "inhale_seconds": pattern.inhale_seconds,
                "hold_seconds": pattern.hold_seconds,
                "exhale_seconds": pattern.exhale_seconds,
                "hold_empty_seconds": pattern.hold_empty_seconds,
                "cycles": pattern.cycles,
                "difficulty": pattern.difficulty.value,
                "description": pattern.description,
            },
        }


# ─── PracticeTracker ───────────────────────────────────────────────


class PracticeTracker(DomainAgent):
    """Tracks practice streaks and engagement metrics."""

    def __init__(self) -> None:
        super().__init__(
            name="PracticeTracker",
            role=AgentRole.CALCULATOR,
            goal=(
                "Calculate practice streak lengths, session counts, "
                "and engagement metrics from the user's practice history."
            ),
            backstory=(
                "Engagement analyst who tracks healing practice frequency, "
                "streak continuity, and modality diversity. Provides "
                "encouraging feedback on consistency without pressure."
            ),
            system=_SYSTEM,
            tools=["practice.calculate_streaks"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate practice metrics from practice history."""
        practice_history: dict[str, int] = context.get("practice_history", {})

        total_sessions = sum(practice_history.values())
        modalities_tried = len(practice_history)
        most_practiced = (
            max(practice_history, key=practice_history.get)  # type: ignore[arg-type]
            if practice_history
            else None
        )

        return {
            "practice_metrics": {
                "total_sessions": total_sessions,
                "modalities_tried": modalities_tried,
                "most_practiced": most_practiced,
                "history": practice_history,
            },
        }


# ─── HealingValidator ──────────────────────────────────────────────


class HealingValidator(DomainAgent):
    """Validates healing outputs for ethics and safety."""

    def __init__(self) -> None:
        super().__init__(
            name="HealingValidator",
            role=AgentRole.VALIDATOR,
            goal=(
                "Ensure all healing outputs include appropriate disclaimers, "
                "contain no diagnostic language, and pass ethics checks."
            ),
            backstory=(
                "Ethics guardian who enforces the 'First, Do No Harm' "
                "principle across all healing outputs. Checks for "
                "diagnostic language, missing disclaimers, and ensures "
                "crisis resources are present when crisis flags are set."
            ),
            system=_SYSTEM,
            tools=["quality.validate_healing_output"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate healing outputs against quality gates."""
        from alchymine.agents.quality.validators import validate_healing_output

        # Build the output dict from context
        output: dict[str, Any] = {
            "disclaimers": context.get("disclaimers", [_HEALING_DISCLAIMER]),
            "crisis_flag": context.get("crisis_flag", False),
            "crisis_response": context.get("crisis_response"),
            "recommended_modalities": context.get("recommended_modalities") or [],
        }

        gate_result = validate_healing_output(output)
        return {
            "healing_quality": {
                "passed": gate_result.passed,
                "details": gate_result.details,
                "gate_name": gate_result.gate_name,
            },
        }


# ─── HealingNarrative ─────────────────────────────────────────────


class HealingNarrative(DomainAgent):
    """Generates healing guidance narratives."""

    def __init__(self) -> None:
        super().__init__(
            name="HealingNarrative",
            role=AgentRole.GUIDE,
            goal=(
                "Generate an empowering healing guidance narrative that "
                "integrates modality recommendations, breathwork patterns, "
                "and practice metrics into a coherent story."
            ),
            backstory=(
                "Narrative healer who weaves modality recommendations, "
                "breathwork guidance, and practice tracking into an "
                "encouraging, safety-conscious narrative. Always includes "
                "disclaimers and uses non-diagnostic language."
            ),
            system=_SYSTEM,
            tools=["narrative.generate"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a healing narrative from upstream agent data."""
        sections: list[str] = [_HEALING_DISCLAIMER]

        # Crisis takes priority
        if context.get("crisis_flag"):
            crisis = context.get("crisis_response", {})
            resources = crisis.get("resources", []) if isinstance(crisis, dict) else []
            resource_lines = [
                f"  - {r['name']}: {r['contact']}" for r in resources if isinstance(r, dict)
            ]
            sections.append(
                "Important: We detected language that may indicate distress. "
                "Please reach out to one of these resources:\n" + "\n".join(resource_lines)
            )

        # Modalities
        modalities = context.get("recommended_modalities")
        if modalities and isinstance(modalities, list):
            mod_names = [
                m["modality"] for m in modalities[:3] if isinstance(m, dict) and "modality" in m
            ]
            if mod_names:
                sections.append(
                    f"Based on your profile, you may find resonance with: {', '.join(mod_names)}."
                )

        # Breathwork
        breathwork = context.get("breathwork_pattern")
        if breathwork and isinstance(breathwork, dict):
            name = breathwork.get("name", "a practice")
            sections.append(f"Consider exploring {name} as your breathwork practice.")

        # Practice metrics
        metrics = context.get("practice_metrics")
        if metrics and isinstance(metrics, dict):
            total = metrics.get("total_sessions", 0)
            if total > 0:
                sections.append(
                    f"You have completed {total} practice sessions so far. "
                    f"Consistency builds resilience."
                )

        narrative = "\n\n".join(sections)
        return {
            "healing_narrative": narrative,
            "disclaimers": [_HEALING_DISCLAIMER],
        }


# ─── Crew assembly ─────────────────────────────────────────────────


def build_healing_crew() -> SystemCrew:
    """Assemble the Healing system crew with all 6 agents and tasks."""
    crisis_detector = CrisisDetector()
    modality_matcher = ModalityMatcher()
    breathwork_guide = BreathworkGuide()
    practice_tracker = PracticeTracker()
    healing_validator = HealingValidator()
    healing_narrative = HealingNarrative()

    agents = [
        crisis_detector,
        modality_matcher,
        breathwork_guide,
        practice_tracker,
        healing_validator,
        healing_narrative,
    ]

    tasks = [
        AgentTask(
            name="detect_crisis",
            description="Scan user text for crisis indicators.",
            agent=crisis_detector,
            expected_output="Dict with crisis_flag and optional crisis_response.",
        ),
        AgentTask(
            name="match_modalities",
            description="Recommend healing modalities from user profile.",
            agent=modality_matcher,
            expected_output="Dict with recommended_modalities list.",
        ),
        AgentTask(
            name="select_breathwork",
            description="Select breathwork pattern for user's level and intention.",
            agent=breathwork_guide,
            expected_output="Dict with breathwork_pattern details.",
        ),
        AgentTask(
            name="track_practice",
            description="Calculate practice streak and engagement metrics.",
            agent=practice_tracker,
            expected_output="Dict with practice_metrics.",
        ),
        AgentTask(
            name="validate_healing",
            description="Run ethics and safety validation on healing outputs.",
            agent=healing_validator,
            expected_output="Dict with healing_quality gate result.",
        ),
        AgentTask(
            name="generate_healing_narrative",
            description="Generate empowering healing guidance narrative.",
            agent=healing_narrative,
            expected_output="Narrative text with disclaimers.",
        ),
    ]

    return SystemCrew(name=_SYSTEM, agents=agents, tasks=tasks)

"""Intelligence crew — 6 domain agents for the Personalized Intelligence system.

Agents:
    NumerologyAnalyst    — Pythagorean + Chaldean numerology calculations
    AstrologyAnalyst     — Natal chart, sun sign, aspects
    PersonalityAnalyst   — Big Five, Enneagram, attachment style synthesis
    BiorhythmCalculator  — Biorhythm cycle calculations
    ArchetypesSynthesizer — Cross-system archetype synthesis
    IntelligenceGuide    — Narrative generation for intelligence insights
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from .base import AgentRole, AgentTask, DomainAgent, SystemCrew

_SYSTEM = "intelligence"


# ─── NumerologyAnalyst ──────────────────────────────────────────────


class NumerologyAnalyst(DomainAgent):
    """Calculates Pythagorean and Chaldean numerology profiles."""

    def __init__(self) -> None:
        super().__init__(
            name="NumerologyAnalyst",
            role=AgentRole.ANALYST,
            goal=(
                "Calculate a complete numerology profile from the user's "
                "full name and birth date using both Pythagorean and "
                "Chaldean systems."
            ),
            backstory=(
                "Expert numerologist versed in both Western (Pythagorean) "
                "and Eastern (Chaldean) number systems. Calculates Life Path, "
                "Expression, Soul Urge, Personality, Personal Year/Month, "
                "and Chaldean name numbers with master-number awareness."
            ),
            system=_SYSTEM,
            tools=[
                "numerology.calculate_pythagorean_profile",
                "numerology.chaldean_name_number",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate numerology profile from name and birth date."""
        from alchymine.engine.numerology import (
            calculate_pythagorean_profile,
            chaldean_name_number,
        )

        full_name: str = context.get("full_name", "")
        birth_date = context.get("birth_date")

        if not full_name or birth_date is None:
            return {"numerology": None, "numerology_error": "Missing full_name or birth_date"}

        profile = calculate_pythagorean_profile(full_name, birth_date)
        chaldean = chaldean_name_number(full_name)

        return {
            "numerology": {
                "life_path": profile.life_path,
                "expression": profile.expression,
                "soul_urge": profile.soul_urge,
                "personality": profile.personality,
                "personal_year": profile.personal_year,
                "personal_month": profile.personal_month,
                "chaldean_name": chaldean,
            },
            "life_path": profile.life_path,
        }


# ─── AstrologyAnalyst ──────────────────────────────────────────────


class AstrologyAnalyst(DomainAgent):
    """Calculates natal chart data — sun sign, degree, and aspects."""

    def __init__(self) -> None:
        super().__init__(
            name="AstrologyAnalyst",
            role=AgentRole.ANALYST,
            goal=(
                "Calculate the user's natal chart data including sun sign, "
                "sun degree, and available aspects from birth date."
            ),
            backstory=(
                "Astrologer specializing in natal chart computation using "
                "Swiss Ephemeris data. Provides sun sign, ecliptic degree, "
                "and aspect calculations. Uses approximate methods when "
                "birth time is unavailable."
            ),
            system=_SYSTEM,
            tools=[
                "astrology.approximate_sun_sign",
                "astrology.approximate_sun_degree",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate astrology profile from birth date."""
        from alchymine.engine.astrology import (
            approximate_sun_degree,
            approximate_sun_sign,
        )

        birth_date = context.get("birth_date")
        if birth_date is None:
            return {"astrology": None, "astrology_error": "Missing birth_date"}

        sun_sign = approximate_sun_sign(birth_date)
        sun_degree = approximate_sun_degree(birth_date)

        return {
            "astrology": {
                "sun_sign": sun_sign,
                "sun_degree": sun_degree,
            },
        }


# ─── PersonalityAnalyst ────────────────────────────────────────────


class PersonalityAnalyst(DomainAgent):
    """Synthesizes Big Five, Enneagram, and attachment style data."""

    def __init__(self) -> None:
        super().__init__(
            name="PersonalityAnalyst",
            role=AgentRole.ANALYST,
            goal=(
                "Synthesize the user's personality profile from Big Five "
                "scores, Enneagram type, and attachment style data."
            ),
            backstory=(
                "Personality psychologist who integrates multiple validated "
                "frameworks — Big Five (NEO-PI-R), Enneagram, and attachment "
                "theory — into a coherent personality snapshot. Provides "
                "descriptive insights without diagnostic claims."
            ),
            system=_SYSTEM,
            tools=["profile.PersonalityProfile"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract and synthesize personality data from context."""
        big_five = context.get("big_five")
        enneagram = context.get("enneagram_type")
        attachment = context.get("attachment_style")

        result: dict[str, Any] = {}

        if big_five is not None:
            # big_five can be a dict or a BigFiveScores object
            if isinstance(big_five, dict):
                result["big_five"] = big_five
            else:
                result["big_five"] = {
                    "openness": big_five.openness,
                    "conscientiousness": big_five.conscientiousness,
                    "extraversion": big_five.extraversion,
                    "agreeableness": big_five.agreeableness,
                    "neuroticism": big_five.neuroticism,
                }

        if enneagram is not None:
            result["enneagram_type"] = enneagram

        if attachment is not None:
            result["attachment_style"] = (
                attachment.value if hasattr(attachment, "value") else str(attachment)
            )

        return {"personality": result if result else None}


# ─── BiorhythmCalculator ───────────────────────────────────────────


class BiorhythmCalculator(DomainAgent):
    """Calculates physical, emotional, and intellectual biorhythm cycles."""

    def __init__(self) -> None:
        super().__init__(
            name="BiorhythmCalculator",
            role=AgentRole.CALCULATOR,
            goal=(
                "Calculate the user's current biorhythm cycle positions "
                "for physical, emotional, and intellectual rhythms."
            ),
            backstory=(
                "Biorhythm analyst who calculates the three classical "
                "sine-wave cycles — physical (23 days), emotional (28 days), "
                "and intellectual (33 days) — from birth date. Presented as "
                "a reflective tool, not a predictive instrument."
            ),
            system=_SYSTEM,
            tools=["biorhythm.calculate_cycles"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate biorhythm cycles from birth date."""
        birth_date = context.get("birth_date")
        target_date = context.get("target_date", date.today())

        if birth_date is None:
            return {"biorhythm": None, "biorhythm_error": "Missing birth_date"}

        # Ensure we have date objects
        if isinstance(birth_date, str):
            birth_date = date.fromisoformat(birth_date)
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        days_alive = (target_date - birth_date).days

        # Classical biorhythm cycle lengths
        physical_cycle = 23
        emotional_cycle = 28
        intellectual_cycle = 33

        physical = round(math.sin(2 * math.pi * days_alive / physical_cycle), 4)
        emotional = round(math.sin(2 * math.pi * days_alive / emotional_cycle), 4)
        intellectual = round(math.sin(2 * math.pi * days_alive / intellectual_cycle), 4)

        return {
            "biorhythm": {
                "physical": physical,
                "emotional": emotional,
                "intellectual": intellectual,
                "days_alive": days_alive,
                "target_date": str(target_date),
            },
        }


# ─── ArchetypesSynthesizer ─────────────────────────────────────────


class ArchetypesSynthesizer(DomainAgent):
    """Synthesizes cross-system archetype patterns from numerology and astrology."""

    def __init__(self) -> None:
        super().__init__(
            name="ArchetypesSynthesizer",
            role=AgentRole.SYNTHESIZER,
            goal=(
                "Synthesize insights from numerology, astrology, and "
                "personality data into a unified archetype narrative."
            ),
            backstory=(
                "Pattern synthesizer who identifies resonances between "
                "numerological life path, astrological sun sign, and "
                "personality traits to surface the user's core archetype "
                "themes. Uses possibility language, never deterministic "
                "predictions."
            ),
            system=_SYSTEM,
            tools=["archetype.synthesis"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Synthesize archetype themes from upstream agent outputs."""
        numerology = context.get("numerology")
        astrology = context.get("astrology")
        personality = context.get("personality")

        themes: list[str] = []

        if numerology and isinstance(numerology, dict):
            life_path = numerology.get("life_path")
            if life_path is not None:
                themes.append(f"Life Path {life_path}")

        if astrology and isinstance(astrology, dict):
            sun_sign = astrology.get("sun_sign")
            if sun_sign:
                themes.append(f"Sun in {sun_sign}")

        if personality and isinstance(personality, dict):
            big_five = personality.get("big_five")
            if big_five and isinstance(big_five, dict):
                # Identify dominant trait
                dominant = max(big_five, key=lambda k: big_five[k])
                themes.append(f"Dominant trait: {dominant}")

        return {
            "archetype_synthesis": {
                "themes": themes,
                "theme_count": len(themes),
                "sources": [
                    s
                    for s in ["numerology", "astrology", "personality"]
                    if context.get(s) is not None
                ],
            },
        }


# ─── IntelligenceGuide ─────────────────────────────────────────────


class IntelligenceGuide(DomainAgent):
    """Generates narrative summaries of intelligence insights."""

    def __init__(self) -> None:
        super().__init__(
            name="IntelligenceGuide",
            role=AgentRole.GUIDE,
            goal=(
                "Generate a cohesive narrative summary of all intelligence "
                "insights for the user, using empowering and possibility-"
                "oriented language."
            ),
            backstory=(
                "Narrative guide who weaves numerological, astrological, "
                "personality, and biorhythm insights into a coherent, "
                "empowering story. Uses possibility language ('you may', "
                "'this suggests') rather than deterministic claims. Never "
                "predicts fate — always affirms agency."
            ),
            system=_SYSTEM,
            tools=["narrative.generate"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a narrative summary from all intelligence data."""
        sections: list[str] = []

        numerology = context.get("numerology")
        if numerology and isinstance(numerology, dict):
            lp = numerology.get("life_path")
            if lp is not None:
                sections.append(
                    f"Your Life Path number is {lp}, which may suggest "
                    f"themes of growth and potential in that direction."
                )

        astrology = context.get("astrology")
        if astrology and isinstance(astrology, dict):
            sun = astrology.get("sun_sign")
            if sun:
                sections.append(
                    f"With your Sun in {sun}, you may find resonance with "
                    f"qualities associated with this sign."
                )

        biorhythm = context.get("biorhythm")
        if biorhythm and isinstance(biorhythm, dict):
            sections.append(
                "Your current biorhythm cycles offer a reflective lens "
                "on your energy patterns today."
            )

        synthesis = context.get("archetype_synthesis")
        if synthesis and isinstance(synthesis, dict):
            themes = synthesis.get("themes", [])
            if themes:
                sections.append(f"Cross-system themes identified: {', '.join(themes)}.")

        narrative = (
            " ".join(sections)
            if sections
            else (
                "Your intelligence profile is being assembled. "
                "More data will unlock deeper insights."
            )
        )

        return {
            "intelligence_narrative": narrative,
            "intelligence_sections": sections,
        }


# ─── Crew assembly ─────────────────────────────────────────────────


def build_intelligence_crew() -> SystemCrew:
    """Assemble the Intelligence system crew with all 6 agents and tasks."""
    numerology_analyst = NumerologyAnalyst()
    astrology_analyst = AstrologyAnalyst()
    personality_analyst = PersonalityAnalyst()
    biorhythm_calculator = BiorhythmCalculator()
    archetypes_synthesizer = ArchetypesSynthesizer()
    intelligence_guide = IntelligenceGuide()

    agents = [
        numerology_analyst,
        astrology_analyst,
        personality_analyst,
        biorhythm_calculator,
        archetypes_synthesizer,
        intelligence_guide,
    ]

    tasks = [
        AgentTask(
            name="calculate_numerology",
            description="Calculate Pythagorean and Chaldean numerology profiles.",
            agent=numerology_analyst,
            expected_output="Dict with numerology profile data.",
        ),
        AgentTask(
            name="calculate_astrology",
            description="Calculate natal chart data — sun sign, degree.",
            agent=astrology_analyst,
            expected_output="Dict with astrology profile data.",
        ),
        AgentTask(
            name="analyze_personality",
            description="Synthesize Big Five, Enneagram, and attachment style.",
            agent=personality_analyst,
            expected_output="Dict with personality synthesis.",
        ),
        AgentTask(
            name="calculate_biorhythm",
            description="Calculate physical, emotional, and intellectual cycles.",
            agent=biorhythm_calculator,
            expected_output="Dict with biorhythm cycle values.",
        ),
        AgentTask(
            name="synthesize_archetypes",
            description="Cross-system archetype synthesis from all data.",
            agent=archetypes_synthesizer,
            expected_output="Dict with archetype themes and sources.",
        ),
        AgentTask(
            name="generate_intelligence_narrative",
            description="Generate empowering narrative from all intelligence data.",
            agent=intelligence_guide,
            expected_output="Narrative text summarizing intelligence insights.",
        ),
    ]

    return SystemCrew(name=_SYSTEM, agents=agents, tasks=tasks)

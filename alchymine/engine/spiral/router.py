"""Alchemical Spiral adaptive router.

Determines the highest-leverage system for each user based on their
intake data, engagement history, and current context. All routing
decisions are deterministic and explainable.

The Spiral model replaces linear journeys with a hub-and-spoke
architecture where users can enter at any point and receive
personalized recommendations for which system to engage next.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Models ──────────────────────────────────────────────────────────────


class SystemRecommendation(BaseModel):
    """A single system recommendation with reasoning."""

    system: str = Field(
        ..., description="System name: intelligence | healing | wealth | creative | perspective"
    )
    score: float = Field(..., ge=0, le=100, description="Relevance score (0-100)")
    reason: str = Field(..., description="Human-readable reason for recommendation")
    entry_action: str = Field(..., description="Suggested first action in this system")
    priority: int = Field(..., ge=1, le=5, description="Priority rank (1=highest)")


class SpiralRouteResult(BaseModel):
    """Complete routing result from the Alchemical Spiral."""

    primary_system: str = Field(..., description="Highest-leverage system for this user")
    recommendations: list[SystemRecommendation] = Field(
        ..., description="All 5 systems ranked by relevance"
    )
    for_you_today: str = Field(..., description="Personalized 'For You Today' suggestion")
    evidence_level: str = Field(default="strong")
    calculation_type: str = Field(default="deterministic")
    methodology: str = Field(
        default="Adaptive routing uses intention mapping, numerology life path, and personality profile to rank systems by leverage. No LLM involved."
    )


# ── Routing logic ───────────────────────────────────────────────────────

# Intention → system affinity weights
_INTENTION_WEIGHTS: dict[str, dict[str, float]] = {
    "career": {
        "intelligence": 30,
        "perspective": 30,
        "wealth": 20,
        "creative": 15,
        "healing": 5,
    },
    "love": {
        "healing": 35,
        "intelligence": 25,
        "perspective": 20,
        "creative": 15,
        "wealth": 5,
    },
    "purpose": {
        "perspective": 35,
        "intelligence": 25,
        "creative": 20,
        "healing": 15,
        "wealth": 5,
    },
    "money": {
        "wealth": 40,
        "perspective": 20,
        "intelligence": 20,
        "creative": 15,
        "healing": 5,
    },
    "health": {
        "healing": 40,
        "intelligence": 20,
        "perspective": 15,
        "creative": 15,
        "wealth": 10,
    },
    "family": {
        "wealth": 25,
        "healing": 25,
        "perspective": 20,
        "intelligence": 20,
        "creative": 10,
    },
    "business": {
        "wealth": 30,
        "creative": 25,
        "perspective": 20,
        "intelligence": 15,
        "healing": 10,
    },
    "legacy": {
        "wealth": 30,
        "perspective": 25,
        "intelligence": 20,
        "creative": 15,
        "healing": 10,
    },
}

# Life Path → additional system boost
_LIFE_PATH_BOOST: dict[int, str] = {
    1: "wealth",  # The Leader — wealth building
    2: "healing",  # The Peacemaker — healing relationships
    3: "creative",  # The Creator — creative expression
    4: "wealth",  # The Builder — systematic wealth
    5: "perspective",  # The Explorer — expanded viewpoints
    6: "healing",  # The Nurturer — healing & family
    7: "intelligence",  # The Seeker — deep self-knowledge
    8: "wealth",  # The Achiever — material mastery
    9: "perspective",  # The Humanitarian — worldview
    11: "intelligence",  # Master Intuitor
    22: "wealth",  # Master Builder
    33: "healing",  # Master Teacher
}

# System-specific entry actions
_ENTRY_ACTIONS: dict[str, dict[str, str]] = {
    "intelligence": {
        "career": "Explore your numerology profile and career archetypes",
        "love": "Discover your attachment style and relationship patterns",
        "purpose": "Map your Life Path number to your life purpose",
        "money": "Understand your wealth archetype from your numbers",
        "health": "Review your personal year cycle for health timing",
        "family": "Explore family numerology compatibility",
        "business": "Analyze your Expression number for business strengths",
        "legacy": "Map your Maturity number for legacy planning",
    },
    "healing": {
        "career": "Build resilience with breathwork for workplace stress",
        "love": "Practice heart-centered coherence meditation",
        "purpose": "Try a consciousness journey for clarity",
        "money": "Address financial anxiety with grounding practices",
        "health": "Start your personalized healing modality match",
        "family": "Explore family healing through somatic practice",
        "business": "Build entrepreneurial resilience through breathwork",
        "legacy": "Process generational patterns with contemplative inquiry",
    },
    "wealth": {
        "career": "Map your income levers and career capital",
        "love": "Align financial values with your partnership",
        "purpose": "Connect your purpose to sustainable income streams",
        "money": "Generate your 90-day wealth activation plan",
        "health": "Build your financial protection strategy",
        "family": "Start your family wealth vault and governance plan",
        "business": "Build your business canvas with wealth integration",
        "legacy": "Design your wealth transfer and legacy plan",
    },
    "creative": {
        "career": "Take the Guilford Creative Assessment for career innovation",
        "love": "Explore creative expression as emotional language",
        "purpose": "Discover your Creative DNA and medium affinities",
        "money": "Explore creative monetization pathways",
        "health": "Try expressive arts for therapeutic benefit",
        "family": "Start a family creative project together",
        "business": "Map your creative business opportunities",
        "legacy": "Build your creative portfolio and legacy works",
    },
    "perspective": {
        "career": "Assess your cognitive biases around career decisions",
        "love": "Explore your Kegan stage for relationship growth",
        "purpose": "Map your worldview using Spiral Dynamics",
        "money": "Detect financial decision biases with CBT tools",
        "health": "Reframe limiting beliefs about health and vitality",
        "family": "Assess family dynamics through developmental stages",
        "business": "Run a strategic positioning analysis for your business",
        "legacy": "Expand your perspective through Kegan stage assessment",
    },
}

_FOR_YOU_TODAY: dict[str, str] = {
    "intelligence": "Today is a great day to deepen your self-knowledge. Explore your numerology profile and discover patterns you haven't noticed before.",
    "healing": "Your body and mind are ready for renewal. Start with a short breathwork session to center yourself before diving deeper.",
    "wealth": "Small financial actions compound over time. Review your wealth levers today and take one step toward your 90-day goal.",
    "creative": "Your creative energy is calling. Whether it's 5 minutes of ideation or a full session, make space for your creative self today.",
    "perspective": "Fresh perspectives unlock new possibilities. Take a moment to examine one assumption you hold — you might find a breakthrough.",
}


def route_user(
    intention: str,
    life_path: int | None = None,
    personality_openness: float | None = None,
    personality_neuroticism: float | None = None,
    systems_engaged: list[str] | None = None,
) -> SpiralRouteResult:
    """Determine the highest-leverage system for a user.

    Parameters
    ----------
    intention:
        User's primary intention (career, love, purpose, money, health,
        family, business, legacy).
    life_path:
        Numerology Life Path number (1-33). Provides a boost to the
        system most aligned with that number's archetype.
    personality_openness:
        Big Five Openness score (0-100). High scores boost Creative.
    personality_neuroticism:
        Big Five Neuroticism score (0-100). High scores boost Healing.
    systems_engaged:
        Systems the user has already engaged with. Reduces those
        systems' scores slightly to encourage breadth.

    Returns
    -------
    SpiralRouteResult
        Ranked recommendations for all 5 systems.
    """
    intention = intention.lower()
    if intention not in _INTENTION_WEIGHTS:
        intention = "purpose"  # Default to purpose if unknown

    # Start with intention-based weights
    scores: dict[str, float] = dict(_INTENTION_WEIGHTS[intention])

    # Apply Life Path boost (+10 to the aligned system)
    if life_path is not None:
        boosted_system = _LIFE_PATH_BOOST.get(life_path % 9 or 9)
        if boosted_system and boosted_system in scores:
            scores[boosted_system] += 10

    # Apply personality-based adjustments
    if personality_openness is not None and personality_openness > 70:
        scores["creative"] += 8

    if personality_neuroticism is not None and personality_neuroticism > 60:
        scores["healing"] += 8

    # Reduce scores for already-engaged systems (encourage breadth)
    if systems_engaged:
        for sys in systems_engaged:
            if sys in scores:
                scores[sys] = max(5, scores[sys] - 5)

    # Normalize to 0-100 range
    max_score = max(scores.values()) if scores else 1
    if max_score > 0:
        for sys in scores:
            scores[sys] = round(scores[sys] / max_score * 100, 1)

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Build recommendations
    recommendations: list[SystemRecommendation] = []
    reasons = _build_reasons(intention, life_path, personality_openness, personality_neuroticism)

    for rank, (sys_name, score) in enumerate(ranked, 1):
        entry_action = _ENTRY_ACTIONS.get(sys_name, {}).get(
            intention, f"Explore the {sys_name} system"
        )
        recommendations.append(
            SystemRecommendation(
                system=sys_name,
                score=score,
                reason=reasons.get(sys_name, f"Aligned with your {intention} intention"),
                entry_action=entry_action,
                priority=rank,
            )
        )

    primary = ranked[0][0]

    return SpiralRouteResult(
        primary_system=primary,
        recommendations=recommendations,
        for_you_today=_FOR_YOU_TODAY.get(primary, "Explore something new today."),
    )


def _build_reasons(
    intention: str,
    life_path: int | None,
    openness: float | None,
    neuroticism: float | None,
) -> dict[str, str]:
    """Build human-readable reasons for each system's ranking."""
    reasons: dict[str, str] = {}

    # Intelligence reasons
    if intention in ("career", "purpose"):
        reasons["intelligence"] = (
            "Self-knowledge is the foundation for career clarity and purpose discovery."
        )
    else:
        reasons["intelligence"] = "Understanding yourself deeply supports all other growth."

    # Healing reasons
    if neuroticism is not None and neuroticism > 60:
        reasons["healing"] = (
            "Your personality profile suggests healing practices could provide grounding and stress relief."
        )
    elif intention == "health":
        reasons["healing"] = (
            "Your health intention aligns directly with the healing system's modalities."
        )
    else:
        reasons["healing"] = "Healing practices build resilience and emotional balance."

    # Wealth reasons
    if intention in ("money", "business", "legacy"):
        reasons["wealth"] = f"Your {intention} intention maps directly to wealth system strategies."
    else:
        reasons["wealth"] = "Financial stability supports all areas of life."

    # Creative reasons
    if openness is not None and openness > 70:
        reasons["creative"] = (
            "Your high Openness score suggests strong creative potential ready to be developed."
        )
    elif intention == "business":
        reasons["creative"] = "Creative thinking drives business innovation and differentiation."
    else:
        reasons["creative"] = "Creative expression enhances problem-solving and self-discovery."

    # Perspective reasons
    if intention in ("career", "purpose"):
        reasons["perspective"] = (
            "Strategic perspective helps clarify direction and identify opportunities."
        )
    else:
        reasons["perspective"] = "Expanded perspective reveals blind spots and new possibilities."

    # Life Path boost reason
    if life_path is not None:
        boosted = _LIFE_PATH_BOOST.get(life_path % 9 or 9)
        if boosted and boosted in reasons:
            reasons[boosted] += f" Your Life Path {life_path} amplifies this alignment."

    return reasons

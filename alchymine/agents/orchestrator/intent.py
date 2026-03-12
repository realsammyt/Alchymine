"""Deterministic keyword-based intent classification.

Maps user input to one of Alchymine's five systems (or MULTI_SYSTEM /
UNKNOWN) using keyword density scoring. No LLM is involved — this is
pure pattern matching for fast, reproducible routing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from alchymine.engine.intention_map import INTENTION_PRIMARY_SYSTEMS

# ─── System intent enum ──────────────────────────────────────────────


class SystemIntent(StrEnum):
    """The target system for a user request."""

    INTELLIGENCE = "intelligence"
    HEALING = "healing"
    WEALTH = "wealth"
    CREATIVE = "creative"
    PERSPECTIVE = "perspective"
    MULTI_SYSTEM = "multi_system"
    UNKNOWN = "unknown"


# ─── Intent result ───────────────────────────────────────────────────


@dataclass(frozen=True)
class IntentResult:
    """Result of intent classification.

    Attributes
    ----------
    intent:
        The primary detected intent.
    confidence:
        Confidence score between 0.0 and 1.0, based on keyword density.
    secondary_intents:
        Other systems detected at lower confidence.
    detected_keywords:
        The keywords that triggered the classification.
    """

    intent: SystemIntent
    confidence: float
    secondary_intents: list[SystemIntent] = field(default_factory=list)
    detected_keywords: list[str] = field(default_factory=list)


# ─── Keyword maps ────────────────────────────────────────────────────

# Each system maps to a set of keywords / short phrases that indicate
# the user is asking about that system.  Keywords are lowercase.

_SYSTEM_KEYWORDS: dict[SystemIntent, list[str]] = {
    SystemIntent.INTELLIGENCE: [
        "numerology",
        "astrology",
        "birth chart",
        "natal chart",
        "life path",
        "sun sign",
        "moon sign",
        "rising sign",
        "ascendant",
        "archetype",
        "personality",
        "enneagram",
        "big five",
        "soul urge",
        "expression number",
        "personal year",
        "chaldean",
        "pythagorean",
        "zodiac",
        "horoscope",
        "star sign",
        "transit",
        "venus retrograde",
        "mercury retrograde",
        "master number",
    ],
    SystemIntent.HEALING: [
        "healing",
        "breathwork",
        "meditation",
        "somatic",
        "energy healing",
        "chakra",
        "wellness",
        "modality",
        "practice",
        "mindfulness",
        "grounding",
        "trauma",
        "nervous system",
        "regulate",
        "self-care",
        "self care",
        "crisis",
        "emotional",
        "therapeutic",
        "recovery",
        "inner work",
        "shadow work",
        "journaling",
        "body scan",
        "yoga",
    ],
    SystemIntent.WEALTH: [
        "money",
        "debt",
        "wealth",
        "invest",
        "investment",
        "financial",
        "finance",
        "income",
        "savings",
        "budget",
        "retirement",
        "portfolio",
        "snowball",
        "avalanche",
        "lever",
        "earn",
        "generational wealth",
        "net worth",
        "cash flow",
        "expense",
        "spending",
        "credit",
        "mortgage",
        "loan",
        "wealth archetype",
    ],
    SystemIntent.CREATIVE: [
        "creative",
        "art",
        "music",
        "writing",
        "poetry",
        "painting",
        "drawing",
        "compose",
        "composition",
        "guilford",
        "divergent thinking",
        "creative dna",
        "style fingerprint",
        "medium",
        "creative block",
        "project",
        "collaboration",
        "artistic",
        "craft",
        "design",
        "photography",
        "sculpture",
        "dance",
        "creative forge",
    ],
    SystemIntent.PERSPECTIVE: [
        "decision",
        "perspective",
        "bias",
        "cognitive bias",
        "framework",
        "mental model",
        "reframe",
        "kegan",
        "thinking hats",
        "six hats",
        "pros and cons",
        "scenario",
        "second order",
        "strategic",
        "clarity",
        "distortion",
        "cognitive distortion",
        "debiasing",
        "structural hole",
        "network bridge",
        "sensitivity analysis",
        "probability",
        "weighted matrix",
        "perspective prism",
    ],
}

# ─── Intention → System mapping ──────────────────────────────────────

# Derived from the canonical mapping in alchymine.engine.intention_map.
# Converts the string-based INTENTION_PRIMARY_SYSTEMS into SystemIntent
# enums for type-safe orchestrator routing.

_INTENTION_TO_SYSTEMS: dict[str, list[SystemIntent]] = {
    intention: [SystemIntent(s) for s in systems]
    for intention, systems in INTENTION_PRIMARY_SYSTEMS.items()
}


def intentions_to_systems(intentions: list[str]) -> list[SystemIntent]:
    """Map a list of user intention strings to unique SystemIntents.

    Always includes all five systems so every report section is populated.
    Intention-based routing determines *priority* during synthesis, not
    which systems run.  Intelligence is always first (numerology/astrology
    are core), followed by intention-relevant systems, then the rest.

    Parameters
    ----------
    intentions:
        List of intention value strings (e.g. ``["health", "money"]``).

    Returns
    -------
    list[SystemIntent]
        All five systems, ordered with INTELLIGENCE first, then
        intention-relevant systems, then remaining systems.
    """
    systems: list[SystemIntent] = []
    seen: set[SystemIntent] = set()
    # Always include intelligence first (numerology/astrology are core)
    systems.append(SystemIntent.INTELLIGENCE)
    seen.add(SystemIntent.INTELLIGENCE)

    # Add intention-relevant systems first (higher priority in synthesis)
    for intention in intentions:
        for system in _INTENTION_TO_SYSTEMS.get(intention.lower(), []):
            if system not in seen:
                systems.append(system)
                seen.add(system)

    # Ensure all five systems are included so every report section is populated
    for system in SystemIntent:
        if system not in seen and system not in (SystemIntent.UNKNOWN, SystemIntent.MULTI_SYSTEM):
            systems.append(system)
            seen.add(system)

    return systems


# Threshold: if the top score and runner-up are within this ratio,
# classify as MULTI_SYSTEM.
_MULTI_SYSTEM_RATIO_THRESHOLD = 0.7


# ─── Classification logic ────────────────────────────────────────────


def classify_intent(user_input: str) -> IntentResult:
    """Classify user input into a system intent.

    Uses keyword density scoring: for each system, count how many of its
    keywords appear in the (lowercased) input, then normalise by the
    total keyword count across all systems to produce a confidence score.

    Parameters
    ----------
    user_input:
        Raw text from the user.

    Returns
    -------
    IntentResult
        Classification result with intent, confidence, secondary intents,
        and the keywords that were detected.
    """
    if not user_input or not user_input.strip():
        return IntentResult(
            intent=SystemIntent.UNKNOWN,
            confidence=0.0,
        )

    text = user_input.lower()

    # Score each system using word-boundary matching to avoid
    # substring false positives (e.g. "art" inside "birth chart").
    scores: dict[SystemIntent, float] = {}
    hits: dict[SystemIntent, list[str]] = {}

    for system, keywords in _SYSTEM_KEYWORDS.items():
        matched: list[str] = []
        for kw in keywords:
            # Use word boundaries so "art" does not match "chart"
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, text):
                matched.append(kw)
        scores[system] = float(len(matched))
        hits[system] = matched

    total_hits = sum(scores.values())

    # No keywords matched at all
    if total_hits == 0:
        return IntentResult(
            intent=SystemIntent.UNKNOWN,
            confidence=0.0,
        )

    # Sort systems by score descending
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_system, top_score = ranked[0]
    all_detected_keywords: list[str] = []
    for kw_list in hits.values():
        all_detected_keywords.extend(kw_list)

    # Check for multi-system: if runner-up is close to top
    secondary: list[SystemIntent] = []
    for system, score in ranked[1:]:
        if score > 0:
            secondary.append(system)

    # Determine if multi-system
    if len(ranked) >= 2:
        runner_up_score = ranked[1][1]
        if (
            runner_up_score > 0
            and top_score > 0
            and runner_up_score / top_score >= _MULTI_SYSTEM_RATIO_THRESHOLD
        ):
            # Multiple systems detected at similar confidence
            confidence = top_score / total_hits
            involved_systems = [
                s for s, sc in ranked if sc > 0 and sc / top_score >= _MULTI_SYSTEM_RATIO_THRESHOLD
            ]
            return IntentResult(
                intent=SystemIntent.MULTI_SYSTEM,
                confidence=confidence,
                secondary_intents=involved_systems,
                detected_keywords=sorted(set(all_detected_keywords)),
            )

    # Single dominant system
    confidence = top_score / total_hits
    return IntentResult(
        intent=top_system,
        confidence=confidence,
        secondary_intents=secondary,
        detected_keywords=sorted(set(hits[top_system])),
    )

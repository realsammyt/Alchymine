"""Healing assessment processing pipeline.

Takes intake assessment responses and produces a structured result
including recommended modalities, crisis detection, difficulty
derivation, and applicable disclaimers. This module bridges the gap
between raw user responses and the healing preference system.
"""

from __future__ import annotations

from alchymine.engine.profile import (
    ArchetypeType,
    BigFiveScores,
    HealingPreference,
    Intention,
    PracticeDifficulty,
)

from .crisis import CrisisResponse, CrisisSeverity, detect_crisis
from .matcher import match_modalities

# ─── Difficulty derivation from assessment responses ─────────────────

# Assessment keys that indicate the user's experience/comfort level.
# Higher values (1-5 scale) → higher difficulty tolerance.
_EXPERIENCE_KEYS: list[str] = [
    "healing_experience",
    "meditation_experience",
    "body_awareness",
    "comfort_with_intensity",
]

_DIFFICULTY_THRESHOLDS: list[tuple[float, PracticeDifficulty]] = [
    (4.5, PracticeDifficulty.INTENSIVE),
    (3.5, PracticeDifficulty.ADVANCED),
    (2.5, PracticeDifficulty.ESTABLISHED),
    (1.5, PracticeDifficulty.DEVELOPING),
    (0.0, PracticeDifficulty.FOUNDATION),
]

# ─── Standard disclaimers ───────────────────────────────────────────

_HEALING_DISCLAIMER: str = (
    "Alchymine healing recommendations are for personal growth and wellness "
    "exploration only. They are not medical advice, diagnosis, or treatment. "
    "Always consult a qualified healthcare professional for medical concerns."
)

_CRISIS_DISCLAIMER: str = (
    "Crisis indicators were detected in your responses. Please reach out to "
    "a professional crisis resource immediately. Your safety is the top priority."
)

_CONTRAINDICATION_DISCLAIMER: str = (
    "Some modalities have been excluded based on your reported contraindications. "
    "Always consult with a healthcare provider before starting any new practice."
)


# ─── Helpers ────────────────────────────────────────────────────────


def _derive_max_difficulty(responses: dict) -> PracticeDifficulty:
    """Derive the maximum practice difficulty from assessment responses.

    Looks for experience-related keys and averages their values to
    determine the appropriate difficulty ceiling.

    Parameters
    ----------
    responses:
        Raw assessment response dict with string keys and numeric values.

    Returns
    -------
    PracticeDifficulty
        The derived maximum difficulty level.
    """
    experience_values: list[float] = []
    for key in _EXPERIENCE_KEYS:
        if key in responses:
            try:
                val = float(responses[key])
                experience_values.append(val)
            except (ValueError, TypeError):
                continue

    if not experience_values:
        return PracticeDifficulty.FOUNDATION

    avg = sum(experience_values) / len(experience_values)

    for threshold, difficulty in _DIFFICULTY_THRESHOLDS:
        if avg >= threshold:
            return difficulty

    return PracticeDifficulty.FOUNDATION


def _extract_free_text(responses: dict) -> str:
    """Extract all free-text fields from assessment responses for crisis scanning.

    Concatenates values of known free-text keys, plus any string values
    that are longer than 20 characters (likely narrative responses).
    """
    free_text_keys = [
        "open_response",
        "current_challenges",
        "healing_goals",
        "emotional_state",
        "additional_notes",
        "concerns",
        "free_text",
    ]

    parts: list[str] = []
    for key in free_text_keys:
        if key in responses and isinstance(responses[key], str):
            parts.append(responses[key])

    # Also scan any long string values that might be narrative
    for key, value in responses.items():
        if key not in free_text_keys and isinstance(value, str) and len(value) > 20:
            parts.append(value)

    return " ".join(parts)


# ─── Main assessment processing function ────────────────────────────


def process_assessment(
    responses: dict,
    contraindications: list[str] | None = None,
    archetype_primary: ArchetypeType = ArchetypeType.EVERYMAN,
    archetype_secondary: ArchetypeType | None = None,
    big_five: BigFiveScores | None = None,
    intention: Intention = Intention.HEALTH,
) -> dict:
    """Process an intake assessment and return structured healing recommendations.

    This is the main entry point for the assessment-to-preference flow.
    It integrates crisis detection, modality matching, and disclaimer
    generation into a single coherent result.

    Parameters
    ----------
    responses:
        Raw assessment response dictionary from the intake form.
    contraindications:
        Optional list of user-reported contraindications.
    archetype_primary:
        User's primary archetype (defaults to EVERYMAN if not yet computed).
    archetype_secondary:
        Optional secondary archetype.
    big_five:
        Big Five personality scores. Defaults to neutral (50 across all).
    intention:
        User's stated life intention.

    Returns
    -------
    dict
        A structured result containing:
        - recommended_modalities: list[HealingPreference]
        - crisis_flag: bool
        - crisis_response: CrisisResponse | None
        - max_difficulty: PracticeDifficulty
        - disclaimers: list[str]
    """
    # Default Big Five if not provided
    if big_five is None:
        big_five = BigFiveScores(
            openness=50.0,
            conscientiousness=50.0,
            extraversion=50.0,
            agreeableness=50.0,
            neuroticism=50.0,
        )

    user_contraindications = contraindications or []

    # Step 1: Crisis detection
    free_text = _extract_free_text(responses)
    crisis_response: CrisisResponse | None = detect_crisis(free_text)
    crisis_flag = crisis_response is not None

    # Step 2: Derive max difficulty from assessment
    max_difficulty = _derive_max_difficulty(responses)

    # If crisis detected at emergency level, cap difficulty at FOUNDATION
    if crisis_response is not None and crisis_response.severity == CrisisSeverity.EMERGENCY:
        max_difficulty = PracticeDifficulty.FOUNDATION

    # Step 3: Match modalities
    recommended_modalities: list[HealingPreference] = match_modalities(
        archetype_primary=archetype_primary,
        archetype_secondary=archetype_secondary,
        big_five=big_five,
        intention=intention,
        max_difficulty=max_difficulty,
        contraindications=user_contraindications,
    )

    # Step 4: Build disclaimers
    disclaimers: list[str] = [_HEALING_DISCLAIMER]

    if crisis_flag:
        disclaimers.append(_CRISIS_DISCLAIMER)

    if user_contraindications:
        disclaimers.append(_CONTRAINDICATION_DISCLAIMER)

    return {
        "recommended_modalities": recommended_modalities,
        "crisis_flag": crisis_flag,
        "crisis_response": crisis_response,
        "max_difficulty": max_difficulty,
        "disclaimers": disclaimers,
    }

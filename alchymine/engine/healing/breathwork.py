"""Breathwork session engine.

Defines breathwork patterns with precise timing parameters and a
selector function that recommends appropriate patterns based on
the user's practice difficulty level and stated intention.
"""

from __future__ import annotations

from dataclasses import dataclass

from alchymine.engine.profile import PracticeDifficulty


@dataclass(frozen=True)
class BreathworkPattern:
    """Immutable definition of a single breathwork pattern.

    Timing is given in seconds per phase of a single breath cycle:
      inhale → hold_full → exhale → hold_empty

    A hold of 0.0 seconds means that phase is skipped.
    """

    name: str
    inhale_seconds: float
    hold_seconds: float  # hold after inhale (lungs full)
    exhale_seconds: float
    hold_empty_seconds: float  # hold after exhale (lungs empty)
    cycles: int
    difficulty: PracticeDifficulty
    description: str


# ─── Pattern definitions ─────────────────────────────────────────────


BOX_BREATHING = BreathworkPattern(
    name="box_breathing",
    inhale_seconds=4.0,
    hold_seconds=4.0,
    exhale_seconds=4.0,
    hold_empty_seconds=4.0,
    cycles=8,
    difficulty=PracticeDifficulty.FOUNDATION,
    description=(
        "Equal-ratio breathing used by Navy SEALs and first responders. "
        "Four equal phases create a stabilising, grounding rhythm that "
        "activates the parasympathetic nervous system."
    ),
)

COHERENCE = BreathworkPattern(
    name="coherence",
    inhale_seconds=5.5,
    hold_seconds=0.0,
    exhale_seconds=5.5,
    hold_empty_seconds=0.0,
    cycles=10,
    difficulty=PracticeDifficulty.FOUNDATION,
    description=(
        "Resonance-frequency breathing at approximately 5.5 breaths per "
        "minute. This rhythm maximises heart rate variability and promotes "
        "heart-brain coherence, as validated by HeartMath research."
    ),
)

RELAXING_4_7_8 = BreathworkPattern(
    name="relaxing_4_7_8",
    inhale_seconds=4.0,
    hold_seconds=7.0,
    exhale_seconds=8.0,
    hold_empty_seconds=0.0,
    cycles=6,
    difficulty=PracticeDifficulty.DEVELOPING,
    description=(
        "Dr. Andrew Weil's relaxing breath. The extended exhale and "
        "prolonged hold activate the vagus nerve and shift the nervous "
        "system toward deep relaxation. Excellent before sleep."
    ),
)

WIM_HOF_LITE = BreathworkPattern(
    name="wim_hof_lite",
    inhale_seconds=2.0,
    hold_seconds=15.0,
    exhale_seconds=2.0,
    hold_empty_seconds=0.0,
    cycles=3,
    difficulty=PracticeDifficulty.DEVELOPING,
    description=(
        "Simplified Wim Hof method: vigorous power inhales followed by "
        "a sustained breath hold. Builds stress resilience and alkalises "
        "the blood through controlled hyperventilation. Three rounds only."
    ),
)

ALTERNATE_NOSTRIL = BreathworkPattern(
    name="alternate_nostril",
    inhale_seconds=4.0,
    hold_seconds=4.0,
    exhale_seconds=4.0,
    hold_empty_seconds=4.0,
    cycles=10,
    difficulty=PracticeDifficulty.ESTABLISHED,
    description=(
        "Nadi Shodhana pranayama: alternating breath between left and "
        "right nostrils to balance the ida and pingala energy channels. "
        "Requires coordination and sustained focus."
    ),
)

HOLOTROPIC_LITE = BreathworkPattern(
    name="holotropic_lite",
    inhale_seconds=1.5,
    hold_seconds=0.0,
    exhale_seconds=1.5,
    hold_empty_seconds=0.0,
    cycles=20,
    difficulty=PracticeDifficulty.ADVANCED,
    description=(
        "Rapid circular breathing inspired by Stanislav Grof's holotropic "
        "breathwork. Continuous connected breathing without pauses creates "
        "an altered state. Requires prior breathwork experience and "
        "supervision for extended sessions."
    ),
)


# ─── Registry ────────────────────────────────────────────────────────


BREATHWORK_PATTERNS: dict[str, BreathworkPattern] = {
    "box_breathing": BOX_BREATHING,
    "coherence": COHERENCE,
    "relaxing_4_7_8": RELAXING_4_7_8,
    "wim_hof_lite": WIM_HOF_LITE,
    "alternate_nostril": ALTERNATE_NOSTRIL,
    "holotropic_lite": HOLOTROPIC_LITE,
}


# ─── Difficulty ordering ─────────────────────────────────────────────

_DIFFICULTY_ORDER: list[PracticeDifficulty] = list(PracticeDifficulty)


def _difficulty_index(d: PracticeDifficulty) -> int:
    return _DIFFICULTY_ORDER.index(d)


# ─── Intention → pattern affinity ────────────────────────────────────

_INTENTION_PATTERN_AFFINITY: dict[str, list[str]] = {
    "calm": ["coherence", "relaxing_4_7_8", "box_breathing"],
    "sleep": ["relaxing_4_7_8", "coherence"],
    "energy": ["wim_hof_lite", "holotropic_lite", "box_breathing"],
    "focus": ["box_breathing", "coherence", "alternate_nostril"],
    "resilience": ["wim_hof_lite", "box_breathing"],
    "balance": ["alternate_nostril", "coherence"],
    "stress": ["coherence", "relaxing_4_7_8", "box_breathing"],
    "clarity": ["alternate_nostril", "coherence", "box_breathing"],
    "grounding": ["box_breathing", "coherence"],
    "release": ["holotropic_lite", "wim_hof_lite", "relaxing_4_7_8"],
}


# ─── Selector function ───────────────────────────────────────────────


def get_breathwork_pattern(
    difficulty: PracticeDifficulty = PracticeDifficulty.FOUNDATION,
    intention: str | None = None,
) -> BreathworkPattern:
    """Select the best breathwork pattern for the given constraints.

    Parameters
    ----------
    difficulty:
        Maximum difficulty level the user is comfortable with.
    intention:
        Optional free-text intention hint (e.g., "calm", "energy",
        "focus", "sleep", "resilience"). Case-insensitive.

    Returns
    -------
    BreathworkPattern
        The best matching pattern. Falls back to box_breathing if
        no specific match is found.

    Selection logic:
    1. Filter patterns to those at or below the requested difficulty.
    2. If an intention is provided, find matching patterns from the
       affinity table and return the first one within difficulty range.
    3. If no intention match, return the highest-difficulty eligible
       pattern (most advanced practice the user can handle).
    4. Ultimate fallback: box_breathing.
    """
    max_idx = _difficulty_index(difficulty)

    # Build eligible set
    eligible = {
        name: pattern
        for name, pattern in BREATHWORK_PATTERNS.items()
        if _difficulty_index(pattern.difficulty) <= max_idx
    }

    if not eligible:
        # Should not happen since box_breathing is FOUNDATION, but be safe
        return BOX_BREATHING

    # Intention-based selection
    if intention is not None:
        intention_lower = intention.strip().lower()
        # Try exact key match first
        if intention_lower in _INTENTION_PATTERN_AFFINITY:
            for pattern_name in _INTENTION_PATTERN_AFFINITY[intention_lower]:
                if pattern_name in eligible:
                    return eligible[pattern_name]
        # Try substring match across all intention keys
        for key, pattern_names in _INTENTION_PATTERN_AFFINITY.items():
            if key in intention_lower or intention_lower in key:
                for pattern_name in pattern_names:
                    if pattern_name in eligible:
                        return eligible[pattern_name]

    # No intention match: return the most advanced eligible pattern
    ranked = sorted(
        eligible.values(),
        key=lambda p: _difficulty_index(p.difficulty),
        reverse=True,
    )
    return ranked[0]

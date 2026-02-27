"""Jungian archetype mapping engine.

Deterministic algorithm that maps a user's numerology, astrology, and
Big Five personality scores to a primary and secondary Jungian archetype.

No LLM involvement — pure weighted scoring.

Algorithm summary:
    1. Life Path number seeds the archetype score board (strongest signal).
    2. Sun sign element boosts two archetypes associated with that element.
    3. Big Five trait scores adjust multiple archetype weights.
    4. The highest-scoring archetype becomes primary; second-highest becomes secondary.
    5. Shadow text is derived from the primary archetype's shadow definition,
       modulated by the Big Five neuroticism score.
"""

from __future__ import annotations

from alchymine.engine.profile import (
    ArchetypeProfile,
    ArchetypeType,
    AstrologyProfile,
    BigFiveScores,
    NumerologyProfile,
)

from .definitions import (
    ARCHETYPE_DEFINITIONS,
    ELEMENT_ARCHETYPE_BOOSTS,
    LIFE_PATH_TO_ARCHETYPE,
    get_element_for_sign,
)

# ─── Weight constants ──────────────────────────────────────────────────
# These control how much each input contributes to the final score.

LIFE_PATH_BASE_WEIGHT: float = 40.0
SUN_SIGN_BOOST_WEIGHT: float = 15.0

# Big Five weights per trait — applied when trait is above 60 (notable) or below 40 (low).
BIG_FIVE_TRAIT_WEIGHT: float = 10.0

# Threshold above which a Big Five trait is considered "high"
BIG_FIVE_HIGH_THRESHOLD: float = 60.0
# Threshold below which a Big Five trait is considered "low"
BIG_FIVE_LOW_THRESHOLD: float = 40.0

# Neuroticism modulation range for shadow emphasis (0.0 to 1.0 scale)
NEUROTICISM_SHADOW_FLOOR: float = 0.3
NEUROTICISM_SHADOW_CEILING: float = 1.0

# Big Five -> archetype boost mapping (trait_name -> boosted archetypes when HIGH)
_BIG_FIVE_HIGH_BOOSTS: dict[str, tuple[ArchetypeType, ...]] = {
    "openness": (ArchetypeType.EXPLORER, ArchetypeType.CREATOR),
    "conscientiousness": (ArchetypeType.RULER,),
    "extraversion": (ArchetypeType.HERO, ArchetypeType.JESTER),
    "agreeableness": (ArchetypeType.CAREGIVER, ArchetypeType.LOVER),
}

# When a trait is LOW, different archetypes may be boosted
_BIG_FIVE_LOW_BOOSTS: dict[str, tuple[ArchetypeType, ...]] = {
    "openness": (ArchetypeType.RULER, ArchetypeType.EVERYMAN),
    "conscientiousness": (ArchetypeType.EXPLORER, ArchetypeType.JESTER),
    "extraversion": (ArchetypeType.SAGE, ArchetypeType.MYSTIC),
    "agreeableness": (ArchetypeType.REBEL, ArchetypeType.HERO),
}


def _init_scores() -> dict[ArchetypeType, float]:
    """Create a zeroed score dictionary for all 12 archetypes."""
    return {at: 0.0 for at in ArchetypeType}


def _apply_life_path(
    scores: dict[ArchetypeType, float],
    numerology: NumerologyProfile,
) -> None:
    """Apply Life Path number as the strongest archetype signal."""
    lp = numerology.life_path
    archetype = LIFE_PATH_TO_ARCHETYPE.get(lp)
    if archetype is not None:
        scores[archetype] += LIFE_PATH_BASE_WEIGHT


def _apply_sun_sign(
    scores: dict[ArchetypeType, float],
    astrology: AstrologyProfile,
) -> None:
    """Boost archetypes associated with the sun sign's element."""
    element = get_element_for_sign(astrology.sun_sign)
    if element is None:
        return
    boosted = ELEMENT_ARCHETYPE_BOOSTS.get(element, ())
    for archetype in boosted:
        scores[archetype] += SUN_SIGN_BOOST_WEIGHT


def _apply_big_five(
    scores: dict[ArchetypeType, float],
    big_five: BigFiveScores,
) -> None:
    """Adjust archetype scores based on Big Five personality traits.

    Each trait above the HIGH threshold boosts certain archetypes.
    Each trait below the LOW threshold boosts different archetypes.
    Neuroticism is handled separately for shadow modulation (not scoring).
    """
    trait_values: dict[str, float] = {
        "openness": big_five.openness,
        "conscientiousness": big_five.conscientiousness,
        "extraversion": big_five.extraversion,
        "agreeableness": big_five.agreeableness,
    }

    for trait_name, value in trait_values.items():
        if value >= BIG_FIVE_HIGH_THRESHOLD:
            # Scale the boost: a score of 100 gets full weight, 60 gets minimal
            intensity = (value - BIG_FIVE_HIGH_THRESHOLD) / (100.0 - BIG_FIVE_HIGH_THRESHOLD)
            for archetype in _BIG_FIVE_HIGH_BOOSTS.get(trait_name, ()):
                scores[archetype] += BIG_FIVE_TRAIT_WEIGHT * intensity
        elif value <= BIG_FIVE_LOW_THRESHOLD:
            # Scale inversely: 0 gets full weight, 40 gets minimal
            intensity = (BIG_FIVE_LOW_THRESHOLD - value) / BIG_FIVE_LOW_THRESHOLD
            for archetype in _BIG_FIVE_LOW_BOOSTS.get(trait_name, ()):
                scores[archetype] += BIG_FIVE_TRAIT_WEIGHT * intensity


def _select_top_two(
    scores: dict[ArchetypeType, float],
) -> tuple[ArchetypeType, ArchetypeType | None]:
    """Return the primary (highest) and secondary (second-highest) archetypes.

    If the secondary has a score of 0.0, it is returned as None.
    If there is a tie, the enum ordering (definition order) is used as a tiebreaker.
    """
    sorted_archetypes = sorted(
        scores.items(),
        key=lambda item: (-item[1], list(ArchetypeType).index(item[0])),
    )
    primary = sorted_archetypes[0][0]
    secondary_entry = sorted_archetypes[1]
    secondary = secondary_entry[0] if secondary_entry[1] > 0.0 else None
    return primary, secondary


def _compute_shadow_emphasis(neuroticism: float) -> float:
    """Map neuroticism (0-100) to a shadow emphasis factor (0.3-1.0).

    Higher neuroticism = stronger shadow emphasis in the profile text.
    """
    normalized = neuroticism / 100.0  # 0.0 to 1.0
    return NEUROTICISM_SHADOW_FLOOR + normalized * (
        NEUROTICISM_SHADOW_CEILING - NEUROTICISM_SHADOW_FLOOR
    )


def _build_shadow_text(archetype: ArchetypeType, emphasis: float) -> str:
    """Build the shadow description for the primary archetype.

    At low emphasis (<= 0.5), uses softer framing ("tendency toward").
    At high emphasis (> 0.5), uses direct framing ("pattern of").
    """
    definition = ARCHETYPE_DEFINITIONS[archetype]
    label = definition.shadow_label

    if emphasis <= 0.5:
        return f"Mild tendency toward {label.lower()}"
    if emphasis <= 0.75:
        return label
    return f"Strong pattern of {label.lower()}"


def _build_shadow_secondary_text(
    archetype: ArchetypeType | None,
    emphasis: float,
) -> str | None:
    """Build secondary shadow text if a secondary archetype exists."""
    if archetype is None:
        return None
    definition = ARCHETYPE_DEFINITIONS[archetype]
    label = definition.shadow_label

    if emphasis <= 0.5:
        return f"Latent tendency toward {label.lower()}"
    return f"Secondary pattern of {label.lower()}"


def map_archetype(
    numerology: NumerologyProfile,
    astrology: AstrologyProfile,
    big_five: BigFiveScores,
) -> ArchetypeProfile:
    """Map numerology, astrology, and personality data to a Jungian archetype profile.

    This is the main entry point for the archetype mapping engine.
    The algorithm is fully deterministic — same inputs always produce same outputs.

    Parameters
    ----------
    numerology : NumerologyProfile
        Numerological data including Life Path number.
    astrology : AstrologyProfile
        Astrological data including sun sign.
    big_five : BigFiveScores
        Big Five personality trait scores (0-100 each).

    Returns
    -------
    ArchetypeProfile
        Complete archetype profile with primary, secondary, shadow analysis,
        and light/shadow quality lists.
    """
    # Step 1: Initialize score board
    scores = _init_scores()

    # Step 2: Apply the three input layers
    _apply_life_path(scores, numerology)
    _apply_sun_sign(scores, astrology)
    _apply_big_five(scores, big_five)

    # Step 3: Select primary and secondary
    primary, secondary = _select_top_two(scores)

    # Step 4: Compute shadow emphasis from neuroticism
    shadow_emphasis = _compute_shadow_emphasis(big_five.neuroticism)

    # Step 5: Build shadow text
    shadow = _build_shadow_text(primary, shadow_emphasis)
    shadow_secondary = _build_shadow_secondary_text(secondary, shadow_emphasis)

    # Step 6: Gather light and shadow qualities from definitions
    primary_def = ARCHETYPE_DEFINITIONS[primary]
    light_qualities = list(primary_def.light_qualities)
    shadow_qualities = list(primary_def.shadow_qualities)

    # If secondary exists, add its top light and shadow quality
    if secondary is not None:
        secondary_def = ARCHETYPE_DEFINITIONS[secondary]
        if secondary_def.light_qualities:
            light_qualities.append(secondary_def.light_qualities[0])
        if secondary_def.shadow_qualities:
            shadow_qualities.append(secondary_def.shadow_qualities[0])

    return ArchetypeProfile(
        primary=primary,
        secondary=secondary,
        shadow=shadow,
        shadow_secondary=shadow_secondary,
        light_qualities=light_qualities,
        shadow_qualities=shadow_qualities,
    )


def get_archetype_scores(
    numerology: NumerologyProfile,
    astrology: AstrologyProfile,
    big_five: BigFiveScores,
) -> dict[ArchetypeType, float]:
    """Expose the raw scoring for debugging and transparency.

    Returns a dictionary of all 12 archetypes with their computed scores.
    Useful for tests, introspection, and building visual score breakdowns.
    """
    scores = _init_scores()
    _apply_life_path(scores, numerology)
    _apply_sun_sign(scores, astrology)
    _apply_big_five(scores, big_five)
    return scores

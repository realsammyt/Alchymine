"""Healing modality matching engine.

Recommends healing modalities based on the user's archetype, personality
traits, intention, and safety constraints. The algorithm combines archetype
healing affinities with Big Five personality scoring and intention-based
boosting to produce a ranked list of HealingPreference objects.
"""

from __future__ import annotations

from collections.abc import Sequence

from alchymine.engine.archetype.definitions import ARCHETYPE_DEFINITIONS
from alchymine.engine.profile import (
    ArchetypeType,
    BigFiveScores,
    HealingPreference,
    Intention,
    PracticeDifficulty,
)

from .modalities import MODALITY_REGISTRY, ModalityDefinition

# ─── Difficulty ordering ─────────────────────────────────────────────

_DIFFICULTY_ORDER: list[PracticeDifficulty] = list(PracticeDifficulty)


def _difficulty_index(d: PracticeDifficulty) -> int:
    """Return the ordinal index for a difficulty level."""
    return _DIFFICULTY_ORDER.index(d)


# ─── Archetype affinity → modality name mapping ─────────────────────
#
# The archetype definitions use free-text healing affinity strings such
# as "art therapy", "meditation", "nature immersion". We map those to
# our canonical modality names so they can seed the algorithm.

_AFFINITY_TO_MODALITY: dict[str, str] = {
    "art therapy": "expressive_healing",
    "journaling": "language_awareness",
    "movement": "somatic_practice",
    "sound healing": "sound_healing",
    "meditation": "coherence_meditation",
    "bibliotherapy": "language_awareness",
    "contemplative practice": "contemplative_inquiry",
    "breathwork": "breathwork",
    "nature immersion": "nature_healing",
    "adventure therapy": "nature_healing",
    "energy work": "coherence_meditation",
    "plant medicine": "consciousness_journey",
    "ritual": "consciousness_journey",
    "structured programs": "resilience_training",
    "executive coaching": "resilience_training",
    "somatic work": "somatic_practice",
    "physical challenge": "resilience_training",
    "martial arts": "somatic_practice",
    "couples work": "community_healing",
    "group work": "community_healing",
    "nurturing practices": "sleep_healing",
    "laughter therapy": "expressive_healing",
    "play therapy": "expressive_healing",
    "improvisation": "expressive_healing",
    "guided meditation": "coherence_meditation",
    "gentle yoga": "somatic_practice",
    "community practices": "community_healing",
    "walking meditation": "nature_healing",
    "expressive arts": "expressive_healing",
}

# ─── Intention → modality boost mapping ──────────────────────────────

_INTENTION_BOOSTS: dict[Intention, dict[str, float]] = {
    Intention.CAREER: {
        "resilience_training": 0.20,
        "language_awareness": 0.15,
        "coherence_meditation": 0.10,
    },
    Intention.LOVE: {
        "community_healing": 0.20,
        "somatic_practice": 0.15,
        "grief_healing": 0.10,
        "expressive_healing": 0.10,
    },
    Intention.PURPOSE: {
        "consciousness_journey": 0.20,
        "contemplative_inquiry": 0.20,
        "coherence_meditation": 0.10,
    },
    Intention.MONEY: {
        "resilience_training": 0.20,
        "language_awareness": 0.15,
        "pni_mapping": 0.10,
    },
    Intention.HEALTH: {
        "breathwork": 0.20,
        "sleep_healing": 0.20,
        "somatic_practice": 0.15,
        "pni_mapping": 0.15,
        "nature_healing": 0.10,
    },
    Intention.FAMILY: {
        "community_healing": 0.20,
        "grief_healing": 0.15,
        "language_awareness": 0.10,
        "somatic_practice": 0.10,
    },
    Intention.BUSINESS: {
        "resilience_training": 0.20,
        "language_awareness": 0.15,
        "coherence_meditation": 0.10,
        "community_healing": 0.10,
    },
    Intention.LEGACY: {
        "contemplative_inquiry": 0.20,
        "consciousness_journey": 0.15,
        "community_healing": 0.15,
        "grief_healing": 0.10,
    },
}


# ─── Big Five scoring ────────────────────────────────────────────────

# Category boosts keyed by Big Five dimension and trait direction.
# Each entry is (threshold_high, threshold_low, boosts_when_high, boosts_when_low).
# Scores 0-100; "high" means >= 60, "low" means <= 40.

_BIG_FIVE_CATEGORY_BOOSTS: dict[str, tuple[float, float, dict[str, float], dict[str, float]]] = {
    "neuroticism": (
        60.0,
        40.0,
        # High neuroticism → boost contemplative and somatic
        {"contemplative": 0.15, "somatic": 0.15},
        # Low neuroticism → slight boost to expressive/relational (comfort with intensity)
        {"expressive": 0.05, "relational": 0.05},
    ),
    "openness": (
        60.0,
        40.0,
        # High openness → boost expressive and nature
        {"expressive": 0.15, "nature": 0.15},
        # Low openness → boost somatic (concrete, body-based)
        {"somatic": 0.10},
    ),
    "extraversion": (
        60.0,
        40.0,
        # High extraversion → boost relational
        {"relational": 0.15, "expressive": 0.10},
        # Low extraversion → boost contemplative and nature (solitary practices)
        {"contemplative": 0.15, "nature": 0.15},
    ),
    "agreeableness": (
        60.0,
        40.0,
        # High agreeableness → boost relational and community
        {"relational": 0.15, "nature": 0.05},
        # Low agreeableness → boost somatic (individual practices)
        {"somatic": 0.10, "contemplative": 0.05},
    ),
    "conscientiousness": (
        60.0,
        40.0,
        # High conscientiousness → boost somatic (structured practices)
        {"somatic": 0.10},
        # Low conscientiousness → boost nature/expressive (unstructured, flow-based)
        {"nature": 0.10, "expressive": 0.10},
    ),
}


def _compute_big_five_category_boosts(big_five: BigFiveScores) -> dict[str, float]:
    """Compute per-category score boosts from Big Five traits.

    Returns a dict of category -> cumulative boost value.
    """
    category_boosts: dict[str, float] = {}
    scores = {
        "neuroticism": big_five.neuroticism,
        "openness": big_five.openness,
        "extraversion": big_five.extraversion,
        "agreeableness": big_five.agreeableness,
        "conscientiousness": big_five.conscientiousness,
    }
    for trait, value in scores.items():
        high_thresh, low_thresh, high_boosts, low_boosts = _BIG_FIVE_CATEGORY_BOOSTS[trait]
        if value >= high_thresh:
            for cat, boost in high_boosts.items():
                category_boosts[cat] = category_boosts.get(cat, 0.0) + boost
        elif value <= low_thresh:
            for cat, boost in low_boosts.items():
                category_boosts[cat] = category_boosts.get(cat, 0.0) + boost
    return category_boosts


# ─── Core matching algorithm ─────────────────────────────────────────


def _resolve_archetype_affinities(archetype: ArchetypeType) -> dict[str, float]:
    """Convert an archetype's healing_affinity strings to modality scores.

    Primary affinities get a base score of 0.40 for the first entry,
    0.35 for the second, 0.30 for the third, then 0.25 for any remaining.
    """
    definition = ARCHETYPE_DEFINITIONS.get(archetype)
    if definition is None:
        return {}

    scores: dict[str, float] = {}
    base_scores = [0.40, 0.35, 0.30, 0.25]
    for i, affinity_text in enumerate(definition.healing_affinity):
        modality_name = _AFFINITY_TO_MODALITY.get(affinity_text.lower())
        if modality_name and modality_name in MODALITY_REGISTRY:
            score = base_scores[min(i, len(base_scores) - 1)]
            # Keep the higher score if a modality appears via multiple affinities
            scores[modality_name] = max(scores.get(modality_name, 0.0), score)
    return scores


def _is_contraindicated(
    modality: ModalityDefinition,
    user_contraindications: list[str],
) -> bool:
    """Check if a modality is contraindicated for the user.

    Uses case-insensitive substring matching: if any user contraindication
    string appears within any modality contraindication string, it is flagged.
    """
    if not user_contraindications:
        return False
    for user_ci in user_contraindications:
        user_ci_lower = user_ci.strip().lower()
        if not user_ci_lower:
            continue
        for mod_ci in modality.contraindications:
            if user_ci_lower in mod_ci.lower():
                return True
    return False


def match_modalities(
    archetype_primary: ArchetypeType,
    archetype_secondary: ArchetypeType | None,
    big_five: BigFiveScores,
    intentions: Sequence[Intention],
    max_difficulty: PracticeDifficulty = PracticeDifficulty.FOUNDATION,
    contraindications: list[str] | None = None,
    max_results: int = 7,
) -> list[HealingPreference]:
    """Match and rank healing modalities for a user profile.

    Algorithm:
    1. Seed scores from archetype healing affinities (primary + secondary).
    2. Boost modalities that align with the user's stated intentions.
    3. Filter out modalities above the user's max difficulty.
    4. Filter out contraindicated modalities.
    5. Apply Big Five personality trait boosts by category.
    6. Return top N as HealingPreference objects, sorted by score descending.

    Parameters
    ----------
    archetype_primary:
        The user's primary Jungian archetype.
    archetype_secondary:
        Optional secondary archetype (contributes at 60% weight).
    big_five:
        Big Five personality scores (0-100 each).
    intentions:
        The user's life intentions (1-3). Boosts are applied for each.
    max_difficulty:
        Highest practice difficulty the user has opted into.
    contraindications:
        List of user-reported contraindications (free text).
    max_results:
        Maximum number of modalities to return (default 7).

    Returns
    -------
    list[HealingPreference]
        Ranked list of healing preferences, highest score first.
    """
    user_contraindications = contraindications or []
    max_diff_idx = _difficulty_index(max_difficulty)

    # Step 1: Seed from archetype affinities
    scores: dict[str, float] = {}
    primary_affinities = _resolve_archetype_affinities(archetype_primary)
    for modality_name, score in primary_affinities.items():
        scores[modality_name] = scores.get(modality_name, 0.0) + score

    if archetype_secondary is not None:
        secondary_affinities = _resolve_archetype_affinities(archetype_secondary)
        for modality_name, score in secondary_affinities.items():
            # Secondary archetype contributes at 60% weight
            scores[modality_name] = scores.get(modality_name, 0.0) + score * 0.6

    # Ensure all modalities have a baseline score
    for name in MODALITY_REGISTRY:
        if name not in scores:
            scores[name] = 0.10  # baseline

    # Step 2: Intention boosts (applied for each selected intention)
    for intention in intentions:
        intention_boosts = _INTENTION_BOOSTS.get(intention, {})
        for modality_name, boost in intention_boosts.items():
            if modality_name in scores:
                scores[modality_name] += boost

    # Step 3: Filter by difficulty
    eligible: dict[str, float] = {}
    for name, score in scores.items():
        modality = MODALITY_REGISTRY.get(name)
        if modality is None:
            continue
        if _difficulty_index(modality.min_difficulty) > max_diff_idx:
            continue
        eligible[name] = score

    # Step 4: Filter contraindications
    safe: dict[str, float] = {}
    contraindicated_set: set[str] = set()
    for name, score in eligible.items():
        modality = MODALITY_REGISTRY[name]
        if _is_contraindicated(modality, user_contraindications):
            contraindicated_set.add(name)
        else:
            safe[name] = score

    # Step 5: Big Five category boosts
    category_boosts = _compute_big_five_category_boosts(big_five)
    for name, score in safe.items():
        modality = MODALITY_REGISTRY[name]
        cat_boost = category_boosts.get(modality.category, 0.0)
        safe[name] = score + cat_boost

    # Step 6: Sort and return top N
    ranked = sorted(safe.items(), key=lambda x: x[1], reverse=True)
    results: list[HealingPreference] = []
    for name, raw_score in ranked[:max_results]:
        modality = MODALITY_REGISTRY[name]
        # Normalise score to 0-1 range
        clamped = max(0.0, min(1.0, raw_score))
        results.append(
            HealingPreference(
                modality=modality.name,
                skill_trigger=modality.skill_trigger,
                preference_score=round(clamped, 4),
                contraindicated=False,
                difficulty_level=modality.min_difficulty,
            )
        )

    return results

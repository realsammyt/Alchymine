"""Compatibility API endpoint.

Compares two user profiles for compatibility based on archetype alignment,
numerology life path compatibility, and Big Five personality similarity.
All calculations are deterministic — no LLM, no randomness.
"""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.profile import ArchetypeType

router = APIRouter()


# ─── Life path compatibility matrix ─────────────────────────────────────

# Compatibility scores (0-100) for life path pairs.
# Based on numerological harmony. Master numbers (11, 22, 33) are reduced
# to their root for lookup, then boosted if both are master numbers.

_LIFE_PATH_COMPAT: dict[tuple[int, int], float] = {
    # 1 with others
    (1, 1): 70.0,
    (1, 2): 60.0,
    (1, 3): 85.0,
    (1, 4): 55.0,
    (1, 5): 90.0,
    (1, 6): 65.0,
    (1, 7): 75.0,
    (1, 8): 80.0,
    (1, 9): 70.0,
    # 2 with others
    (2, 2): 75.0,
    (2, 3): 70.0,
    (2, 4): 80.0,
    (2, 5): 50.0,
    (2, 6): 90.0,
    (2, 7): 65.0,
    (2, 8): 75.0,
    (2, 9): 70.0,
    # 3 with others
    (3, 3): 80.0,
    (3, 4): 45.0,
    (3, 5): 90.0,
    (3, 6): 85.0,
    (3, 7): 60.0,
    (3, 8): 55.0,
    (3, 9): 85.0,
    # 4 with others
    (4, 4): 70.0,
    (4, 5): 40.0,
    (4, 6): 80.0,
    (4, 7): 75.0,
    (4, 8): 85.0,
    (4, 9): 50.0,
    # 5 with others
    (5, 5): 65.0,
    (5, 6): 45.0,
    (5, 7): 80.0,
    (5, 8): 60.0,
    (5, 9): 75.0,
    # 6 with others
    (6, 6): 85.0,
    (6, 7): 50.0,
    (6, 8): 70.0,
    (6, 9): 90.0,
    # 7 with others
    (7, 7): 80.0,
    (7, 8): 55.0,
    (7, 9): 70.0,
    # 8 with others
    (8, 8): 65.0,
    (8, 9): 60.0,
    # 9 with others
    (9, 9): 75.0,
}


def _reduce_master(lp: int) -> int:
    """Reduce a master number to its root for compatibility lookup."""
    if lp == 11:
        return 2
    if lp == 22:
        return 4
    if lp == 33:
        return 6
    return lp


def _is_master(lp: int) -> bool:
    """Check if a life path is a master number."""
    return lp in (11, 22, 33)


def _life_path_compatibility(lp1: int, lp2: int) -> float:
    """Calculate life path compatibility score (0-100).

    Looks up the base compatibility, then applies a bonus if both
    are master numbers.
    """
    r1, r2 = _reduce_master(lp1), _reduce_master(lp2)
    # Ensure ordered pair for lookup
    key = (min(r1, r2), max(r1, r2))
    base = _LIFE_PATH_COMPAT.get(key, 60.0)

    # Master number bonus: both master = +10, one master = +5
    if _is_master(lp1) and _is_master(lp2):
        base = min(100.0, base + 10.0)
    elif _is_master(lp1) or _is_master(lp2):
        base = min(100.0, base + 5.0)

    return base


# ─── Archetype compatibility ────────────────────────────────────────────

# Archetype pairs with natural synergy (high compatibility)
_SYNERGY_PAIRS: frozenset[frozenset[ArchetypeType]] = frozenset(
    {
        frozenset({ArchetypeType.CREATOR, ArchetypeType.SAGE}),
        frozenset({ArchetypeType.HERO, ArchetypeType.CAREGIVER}),
        frozenset({ArchetypeType.EXPLORER, ArchetypeType.CREATOR}),
        frozenset({ArchetypeType.RULER, ArchetypeType.SAGE}),
        frozenset({ArchetypeType.LOVER, ArchetypeType.CAREGIVER}),
        frozenset({ArchetypeType.MYSTIC, ArchetypeType.SAGE}),
        frozenset({ArchetypeType.JESTER, ArchetypeType.EXPLORER}),
        frozenset({ArchetypeType.EVERYMAN, ArchetypeType.CAREGIVER}),
        frozenset({ArchetypeType.REBEL, ArchetypeType.EXPLORER}),
        frozenset({ArchetypeType.INNOCENT, ArchetypeType.CAREGIVER}),
        frozenset({ArchetypeType.HERO, ArchetypeType.RULER}),
        frozenset({ArchetypeType.MYSTIC, ArchetypeType.LOVER}),
    }
)

# Archetype pairs with natural tension (lower compatibility)
_TENSION_PAIRS: frozenset[frozenset[ArchetypeType]] = frozenset(
    {
        frozenset({ArchetypeType.RULER, ArchetypeType.REBEL}),
        frozenset({ArchetypeType.HERO, ArchetypeType.JESTER}),
        frozenset({ArchetypeType.SAGE, ArchetypeType.JESTER}),
        frozenset({ArchetypeType.INNOCENT, ArchetypeType.REBEL}),
        frozenset({ArchetypeType.MYSTIC, ArchetypeType.EVERYMAN}),
        frozenset({ArchetypeType.RULER, ArchetypeType.EXPLORER}),
    }
)


def _archetype_compatibility(a1: ArchetypeType, a2: ArchetypeType) -> float:
    """Calculate archetype compatibility score (0-100).

    Same archetype = 80 (high affinity but potential blind spot reinforcement).
    Synergy pair = 85.
    Tension pair = 40.
    Default = 60.
    """
    if a1 == a2:
        return 80.0

    pair = frozenset({a1, a2})
    if pair in _SYNERGY_PAIRS:
        return 85.0
    if pair in _TENSION_PAIRS:
        return 40.0

    return 60.0


# ─── Big Five similarity ────────────────────────────────────────────────


def _big_five_similarity(
    scores_a: dict[str, float],
    scores_b: dict[str, float],
) -> float:
    """Calculate Big Five personality similarity (0-100).

    Uses Euclidean distance in 5-dimensional space, normalized to 0-100.
    Identical profiles = 100, maximally different = 0.

    Each trait is on a 0-100 scale, so max distance = sqrt(5 * 100^2) = ~223.6.
    """
    traits = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")

    sum_sq = 0.0
    for trait in traits:
        diff = scores_a.get(trait, 50.0) - scores_b.get(trait, 50.0)
        sum_sq += diff * diff

    distance = math.sqrt(sum_sq)
    max_distance = math.sqrt(5.0 * (100.0**2))  # ~223.6

    # Convert distance to similarity: 0 distance = 100, max distance = 0
    similarity = max(0.0, 100.0 * (1.0 - distance / max_distance))
    return round(similarity, 1)


# ─── Request / Response models ───────────────────────────────────────────


class ProfileInput(BaseModel):
    """Minimal profile data for compatibility comparison."""

    life_path: int = Field(..., ge=1, le=33, description="Life Path number")
    archetype_primary: ArchetypeType = Field(..., description="Primary Jungian archetype")
    big_five: dict[str, float] = Field(
        ...,
        description=(
            "Big Five scores: openness, conscientiousness, extraversion, "
            "agreeableness, neuroticism (each 0-100)"
        ),
    )


class CompatibilityRequest(BaseModel):
    """Request to compare two profiles for compatibility."""

    profile_a: ProfileInput
    profile_b: ProfileInput


class CompatibilityBreakdown(BaseModel):
    """Detailed breakdown of compatibility scoring."""

    life_path_score: float = Field(..., ge=0, le=100)
    archetype_score: float = Field(..., ge=0, le=100)
    big_five_score: float = Field(..., ge=0, le=100)


class CompatibilityResponse(BaseModel):
    """Compatibility analysis response."""

    overall_score: float = Field(..., ge=0, le=100, description="Overall compatibility (0-100)")
    breakdown: CompatibilityBreakdown
    summary: str = Field(..., description="Human-readable compatibility summary")


# ─── Scoring weights ────────────────────────────────────────────────────

_LIFE_PATH_WEIGHT: float = 0.30
_ARCHETYPE_WEIGHT: float = 0.35
_BIG_FIVE_WEIGHT: float = 0.35


def _compute_compatibility(
    profile_a: ProfileInput,
    profile_b: ProfileInput,
) -> tuple[float, CompatibilityBreakdown]:
    """Compute the overall compatibility and breakdown."""
    lp_score = _life_path_compatibility(profile_a.life_path, profile_b.life_path)
    arch_score = _archetype_compatibility(profile_a.archetype_primary, profile_b.archetype_primary)
    bf_score = _big_five_similarity(profile_a.big_five, profile_b.big_five)

    overall = round(
        _LIFE_PATH_WEIGHT * lp_score + _ARCHETYPE_WEIGHT * arch_score + _BIG_FIVE_WEIGHT * bf_score,
        1,
    )

    breakdown = CompatibilityBreakdown(
        life_path_score=round(lp_score, 1),
        archetype_score=round(arch_score, 1),
        big_five_score=round(bf_score, 1),
    )

    return overall, breakdown


def _generate_summary(overall: float, breakdown: CompatibilityBreakdown) -> str:
    """Generate a human-readable compatibility summary."""
    if overall >= 80:
        level = "Exceptional"
        description = (
            "a deeply resonant connection with natural alignment across multiple dimensions"
        )
    elif overall >= 65:
        level = "Strong"
        description = "significant compatibility with shared values and complementary strengths"
    elif overall >= 50:
        level = "Moderate"
        description = "a balanced connection with both areas of harmony and growth opportunities"
    elif overall >= 35:
        level = "Challenging"
        description = (
            "notable differences that can become growth catalysts with mutual understanding"
        )
    else:
        level = "Complex"
        description = "significant contrasts that require intentional bridge-building and patience"

    # Identify the strongest dimension
    scores = {
        "numerological alignment": breakdown.life_path_score,
        "archetypal resonance": breakdown.archetype_score,
        "personality similarity": breakdown.big_five_score,
    }
    strongest = max(scores, key=lambda k: scores[k])

    return (
        f"{level} compatibility ({overall:.0f}/100). "
        f"This pairing shows {description}. "
        f"The strongest dimension is {strongest} "
        f"({scores[strongest]:.0f}/100)."
    )


# ─── Endpoint ────────────────────────────────────────────────────────────


@router.post("/compatibility")
async def compare_profiles(
    request: CompatibilityRequest,
    current_user: dict = Depends(get_current_user),
) -> CompatibilityResponse:
    """Compare two profiles for compatibility.

    Analyzes numerology life path compatibility, Jungian archetype alignment,
    and Big Five personality similarity. Returns an overall score (0-100)
    with a detailed breakdown.

    All calculations are deterministic — no LLM, no randomness.
    """
    overall, breakdown = _compute_compatibility(request.profile_a, request.profile_b)
    summary = _generate_summary(overall, breakdown)

    return CompatibilityResponse(
        overall_score=overall,
        breakdown=breakdown,
        summary=summary,
    )

"""Healing Engine API endpoints.

Endpoints for healing modality listing, matching, breathwork pattern
selection, crisis detection, and spiral-based healing recommendations.
All calculations are deterministic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.healing import (
    MODALITY_REGISTRY,
    BreathworkPattern,
    detect_crisis,
    get_breathwork_pattern,
    match_modalities,
)
from alchymine.engine.healing import (
    CrisisResponse as EngineCrisisResponse,
)
from alchymine.engine.healing.modalities import (
    VALID_CATEGORIES,
    VALID_EVIDENCE_LEVELS,
)
from alchymine.engine.profile import (
    ArchetypeType,
    BigFiveScores,
    Intention,
    PracticeDifficulty,
)
from alchymine.engine.spiral.router import route_user

router = APIRouter()


# --- Request / Response models -----------------------------------------------


class ModalityResponse(BaseModel):
    """A single healing modality definition."""

    name: str
    skill_trigger: str
    category: str
    description: str
    contraindications: list[str]
    min_difficulty: str
    traditions: list[str]
    evidence_level: str


class ModalityListResponse(BaseModel):
    """List of healing modalities."""

    modalities: list[ModalityResponse]
    total: int


class MatchRequest(BaseModel):
    """Request to match healing modalities for a user profile."""

    archetype_primary: ArchetypeType = Field(
        ArchetypeType.SAGE,
        description="Primary Jungian archetype (default: sage — broadest healing affinity)",
    )
    archetype_secondary: ArchetypeType | None = Field(
        None, description="Optional secondary archetype"
    )
    big_five: BigFiveScores = Field(
        default_factory=lambda: BigFiveScores(
            openness=50.0,
            conscientiousness=50.0,
            extraversion=50.0,
            agreeableness=50.0,
            neuroticism=50.0,
        ),
        description="Big Five personality scores (0-100 each; defaults to neutral 50s)",
    )
    intention: Intention | None = Field(
        None, description="Primary life intention (backward compat)"
    )
    intentions: list[Intention] | None = Field(
        None,
        min_length=1,
        max_length=3,
        description="Life intentions (1-3). Overrides `intention` if both provided.",
    )
    contraindications: list[str] | None = Field(None, description="Known contraindications")
    max_difficulty: PracticeDifficulty = Field(
        PracticeDifficulty.FOUNDATION, description="Highest difficulty level to include"
    )
    top_n: int = Field(7, ge=1, le=15, description="Max number of results to return")

    def resolved_intentions(self) -> list[Intention]:
        """Return the consolidated intention list."""
        if self.intentions:
            return list(self.intentions)
        if self.intention:
            return [self.intention]
        return [Intention.HEALTH]  # safe default


class HealingPreferenceResponse(BaseModel):
    """A single matched healing preference."""

    modality: str
    skill_trigger: str
    preference_score: float
    contraindicated: bool
    difficulty_level: str


class MatchResponse(BaseModel):
    """Matched healing modalities response."""

    matches: list[HealingPreferenceResponse]
    total: int
    evidence_level: str = Field(default="moderate")
    calculation_type: str = Field(default="hybrid")
    methodology: str = Field(
        default="Modalities matched via deterministic scoring of archetype affinity, personality traits, and safety constraints. Evidence levels vary per modality.",
    )


class BreathworkResponse(BaseModel):
    """A breathwork pattern response."""

    name: str
    inhale_seconds: float
    hold_seconds: float
    exhale_seconds: float
    hold_empty_seconds: float
    cycles: int
    difficulty: str
    description: str
    evidence_level: str = Field(default="moderate")
    calculation_type: str = Field(default="deterministic")
    methodology: str = Field(
        default="Breathwork patterns use fixed timing cycles from established protocols (Box Breathing, Coherence, 4-7-8).",
    )


class CrisisDetectRequest(BaseModel):
    """Request to detect crisis in text."""

    text: str = Field(..., min_length=1, description="Text to scan for crisis indicators")


class CrisisResourceResponse(BaseModel):
    """A single crisis resource."""

    name: str
    contact: str
    description: str


class CrisisDetectResponse(BaseModel):
    """Crisis detection response."""

    crisis_detected: bool
    severity: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    resources: list[CrisisResourceResponse] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)


# --- Helper converters -------------------------------------------------------


def _breathwork_to_response(pattern: BreathworkPattern) -> BreathworkResponse:
    """Convert a BreathworkPattern to an API response."""
    return BreathworkResponse(
        name=pattern.name,
        inhale_seconds=pattern.inhale_seconds,
        hold_seconds=pattern.hold_seconds,
        exhale_seconds=pattern.exhale_seconds,
        hold_empty_seconds=pattern.hold_empty_seconds,
        cycles=pattern.cycles,
        difficulty=pattern.difficulty.value,
        description=pattern.description,
    )


def _crisis_to_response(result: EngineCrisisResponse | None) -> CrisisDetectResponse:
    """Convert an engine CrisisResponse to an API response."""
    if result is None:
        return CrisisDetectResponse(crisis_detected=False)

    return CrisisDetectResponse(
        crisis_detected=True,
        severity=result.severity.value,
        matched_keywords=list(result.matched_keywords),
        resources=[
            CrisisResourceResponse(
                name=r.name,
                contact=r.contact,
                description=r.description,
            )
            for r in result.resources
        ],
        disclaimers=list(result.disclaimers),
    )


# --- Endpoints ----------------------------------------------------------------


@router.get("/healing/modalities")
async def list_modalities(
    category: str | None = Query(None, description="Filter by category"),
    evidence_level: str | None = Query(None, description="Filter by evidence level"),
    current_user: dict = Depends(get_current_user),
) -> ModalityListResponse:
    """List all healing modalities with optional filters.

    Returns the complete modality registry, optionally filtered by
    category and/or evidence level.
    """
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Valid: {sorted(VALID_CATEGORIES)}",
        )
    if evidence_level is not None and evidence_level not in VALID_EVIDENCE_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid evidence_level '{evidence_level}'. Valid: {sorted(VALID_EVIDENCE_LEVELS)}",
        )

    modalities = list(MODALITY_REGISTRY.values())

    if category is not None:
        modalities = [m for m in modalities if m.category == category]
    if evidence_level is not None:
        modalities = [m for m in modalities if m.evidence_level == evidence_level]

    items = [
        ModalityResponse(
            name=m.name,
            skill_trigger=m.skill_trigger,
            category=m.category,
            description=m.description,
            contraindications=list(m.contraindications),
            min_difficulty=m.min_difficulty.value,
            traditions=list(m.traditions),
            evidence_level=m.evidence_level,
        )
        for m in modalities
    ]

    return ModalityListResponse(modalities=items, total=len(items))


@router.post("/healing/match")
async def match_healing_modalities(
    request: MatchRequest,
    current_user: dict = Depends(get_current_user),
) -> MatchResponse:
    """Match healing modalities for a user profile.

    Uses the deterministic matching engine to recommend modalities based
    on archetype, personality traits, intention, and safety constraints.
    """
    results = match_modalities(
        archetype_primary=request.archetype_primary,
        archetype_secondary=request.archetype_secondary,
        big_five=request.big_five,
        intentions=request.resolved_intentions(),
        max_difficulty=request.max_difficulty,
        contraindications=request.contraindications,
        max_results=request.top_n,
    )

    matches = [
        HealingPreferenceResponse(
            modality=hp.modality,
            skill_trigger=hp.skill_trigger,
            preference_score=hp.preference_score,
            contraindicated=hp.contraindicated,
            difficulty_level=hp.difficulty_level.value,
        )
        for hp in results
    ]

    return MatchResponse(matches=matches, total=len(matches))


@router.get("/healing/breathwork/{intention}")
async def get_breathwork(
    intention: str,
    difficulty: PracticeDifficulty = Query(
        PracticeDifficulty.FOUNDATION,
        description="Maximum difficulty level",
    ),
    current_user: dict = Depends(get_current_user),
) -> BreathworkResponse:
    """Get a breathwork pattern for a given intention and difficulty.

    Deterministic selection based on intention affinity and difficulty filter.
    """
    pattern = get_breathwork_pattern(
        difficulty=difficulty,
        intention=intention,
    )
    return _breathwork_to_response(pattern)


@router.post("/healing/crisis/detect")
async def detect_crisis_endpoint(
    request: CrisisDetectRequest,
    current_user: dict = Depends(get_current_user),
) -> CrisisDetectResponse:
    """Detect crisis indicators in free-text input.

    Scans the provided text for crisis-related keywords and returns
    severity, matched keywords, resources, and disclaimers.
    """
    result = detect_crisis(request.text)
    return _crisis_to_response(result)


# --- Healing spiral route models -------------------------------------------------


class HealingSpiralModality(BaseModel):
    """A healing modality recommendation from the spiral router."""

    modality: str
    category: str
    description: str
    evidence_level: str
    entry_action: str


class HealingSpiralRouteResponse(BaseModel):
    """Spiral-based healing recommendation response.

    Combines the user's current Alchemical Spiral stage with
    recommended healing modalities for that stage.
    """

    primary_system: str = Field(..., description="Highest-leverage system for this user")
    healing_rank: int = Field(
        ..., ge=1, le=5, description="Where healing ranks among the 5 systems (1=top)"
    )
    healing_score: float = Field(..., ge=0, le=100, description="Healing system relevance score")
    healing_reason: str = Field(..., description="Why healing is recommended at this stage")
    healing_entry_action: str = Field(
        ..., description="Suggested first action for the healing system"
    )
    for_you_today: str = Field(..., description="Personalized daily suggestion")
    recommended_modalities: list[HealingSpiralModality] = Field(
        ..., description="Healing modalities matched to the user's spiral stage"
    )
    evidence_level: str = Field(default="strong")
    calculation_type: str = Field(default="deterministic")


# ── Healing-stage → modality mapping ────────────────────────────────────
# Which modality categories are most useful given how healing ranks
# in the spiral. If healing is primary, offer deeper modalities; if
# it's secondary, focus on foundational ones.

_HEALING_RANK_MODALITIES: dict[str, list[str]] = {
    "primary": [
        "breathwork",
        "coherence_meditation",
        "somatic_practice",
        "consciousness_journey",
        "resilience_training",
    ],
    "secondary": [
        "breathwork",
        "coherence_meditation",
        "sleep_healing",
        "nature_healing",
        "sound_healing",
    ],
    "tertiary": [
        "breathwork",
        "sleep_healing",
        "nature_healing",
    ],
}


@router.get("/healing/spiral-route")
async def get_healing_spiral_route(
    intention: str = Query(
        "health",
        description="Primary intention (career, love, purpose, money, health, family, business, legacy)",
    ),
    life_path: int | None = Query(None, ge=1, le=33),
    personality_openness: float | None = Query(None, ge=0, le=100),
    personality_neuroticism: float | None = Query(None, ge=0, le=100),
    current_user: dict = Depends(get_current_user),
) -> HealingSpiralRouteResponse:
    """Return the user's current Spiral stage with healing-specific recommendations.

    Runs the full Spiral routing algorithm, then extracts the healing
    system rank and augments it with concrete modality recommendations
    based on the user's stage.
    """
    spiral = route_user(
        intention=intention,
        life_path=life_path,
        personality_openness=personality_openness,
        personality_neuroticism=personality_neuroticism,
    )

    # Find healing in the ranked recommendations
    healing_rec = next((r for r in spiral.recommendations if r.system == "healing"), None)
    healing_rank = healing_rec.priority if healing_rec else 5
    healing_score = healing_rec.score if healing_rec else 0.0
    healing_reason = healing_rec.reason if healing_rec else "Healing supports all areas of growth."
    healing_entry_action = (
        healing_rec.entry_action if healing_rec else "Start with a short breathwork session."
    )

    # Determine tier for modality selection
    if healing_rank <= 1:
        tier = "primary"
    elif healing_rank <= 3:
        tier = "secondary"
    else:
        tier = "tertiary"

    modality_keys = _HEALING_RANK_MODALITIES[tier]
    recommended: list[HealingSpiralModality] = []
    for key in modality_keys:
        mod_def = MODALITY_REGISTRY.get(key)
        if mod_def:
            recommended.append(
                HealingSpiralModality(
                    modality=mod_def.name,
                    category=mod_def.category,
                    description=mod_def.description,
                    evidence_level=mod_def.evidence_level,
                    entry_action=healing_entry_action,
                )
            )

    return HealingSpiralRouteResponse(
        primary_system=spiral.primary_system,
        healing_rank=healing_rank,
        healing_score=healing_score,
        healing_reason=healing_reason,
        healing_entry_action=healing_entry_action,
        for_you_today=spiral.for_you_today,
        recommended_modalities=recommended,
    )

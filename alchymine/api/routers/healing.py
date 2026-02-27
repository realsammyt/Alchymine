"""Healing Engine API endpoints.

Endpoints for healing modality listing, matching, breathwork pattern
selection, and crisis detection. All calculations are deterministic.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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

    archetype_primary: ArchetypeType = Field(..., description="Primary Jungian archetype")
    archetype_secondary: ArchetypeType | None = Field(
        None, description="Optional secondary archetype"
    )
    big_five: BigFiveScores = Field(..., description="Big Five personality scores (0-100 each)")
    intention: Intention = Field(..., description="Primary life intention")
    contraindications: list[str] | None = Field(None, description="Known contraindications")
    max_difficulty: PracticeDifficulty = Field(
        PracticeDifficulty.FOUNDATION, description="Highest difficulty level to include"
    )
    top_n: int = Field(7, ge=1, le=15, description="Max number of results to return")


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
async def match_healing_modalities(request: MatchRequest) -> MatchResponse:
    """Match healing modalities for a user profile.

    Uses the deterministic matching engine to recommend modalities based
    on archetype, personality traits, intention, and safety constraints.
    """
    results = match_modalities(
        archetype_primary=request.archetype_primary,
        archetype_secondary=request.archetype_secondary,
        big_five=request.big_five,
        intention=request.intention,
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
async def detect_crisis_endpoint(request: CrisisDetectRequest) -> CrisisDetectResponse:
    """Detect crisis indicators in free-text input.

    Scans the provided text for crisis-related keywords and returns
    severity, matched keywords, resources, and disclaimers.
    """
    result = detect_crisis(request.text)
    return _crisis_to_response(result)

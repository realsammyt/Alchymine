"""Biorhythm API endpoints — deterministic sine-wave calculations, no LLM.

Evidence rating: LOW
Methodology note: Biorhythm theory is not supported by scientific consensus.
Results are provided for entertainment and self-reflection.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from alchymine.engine.biorhythm import (
    EVIDENCE_RATING,
    METHODOLOGY_NOTE,
    BiorhythmResult,
    biorhythm_compatibility,
    calculate_biorhythm,
    calculate_range,
)

router = APIRouter()


# ─── Request models ───────────────────────────────────────────────────


class BiorhythmCalculateRequest(BaseModel):
    """Request for a single-day biorhythm calculation."""

    birth_date: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    target_date: date = Field(..., description="Date to calculate for (YYYY-MM-DD)")


class BiorhythmRangeRequest(BaseModel):
    """Request for a multi-day biorhythm range."""

    birth_date: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    start_date: date = Field(..., description="First day of the range (YYYY-MM-DD)")
    days: int = Field(30, ge=1, le=365, description="Number of days (1-365)")


class BiorhythmCompatibilityRequest(BaseModel):
    """Request for a two-person biorhythm comparison."""

    birth_date_a: date = Field(..., description="Person A's date of birth (YYYY-MM-DD)")
    birth_date_b: date = Field(..., description="Person B's date of birth (YYYY-MM-DD)")
    target_date: date = Field(..., description="Date to compare on (YYYY-MM-DD)")


# ─── Response models ──────────────────────────────────────────────────


class BiorhythmCalculateResponse(BaseModel):
    """Response for a single-day biorhythm calculation."""

    result: BiorhythmResult
    evidence_rating: str = EVIDENCE_RATING
    methodology_note: str = METHODOLOGY_NOTE


class BiorhythmRangeResponse(BaseModel):
    """Response for a multi-day biorhythm range."""

    results: list[BiorhythmResult]
    days_requested: int
    evidence_rating: str = EVIDENCE_RATING
    methodology_note: str = METHODOLOGY_NOTE


class BiorhythmCompatibilityResponse(BaseModel):
    """Response for a two-person biorhythm comparison."""

    person_a: BiorhythmResult
    person_b: BiorhythmResult
    physical_similarity: float
    emotional_similarity: float
    intellectual_similarity: float
    overall_sync: float
    evidence_rating: str = EVIDENCE_RATING
    methodology_note: str = METHODOLOGY_NOTE


# ─── Endpoints ────────────────────────────────────────────────────────


@router.post("/biorhythm/calculate", response_model=BiorhythmCalculateResponse)
async def calculate(request: BiorhythmCalculateRequest) -> BiorhythmCalculateResponse:
    """Calculate biorhythm values for a single day.

    Deterministic calculation — no AI involved.
    Evidence rating: LOW.
    """
    try:
        result = calculate_biorhythm(request.birth_date, request.target_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return BiorhythmCalculateResponse(result=result)


@router.post("/biorhythm/range", response_model=BiorhythmRangeResponse)
async def range_calculation(request: BiorhythmRangeRequest) -> BiorhythmRangeResponse:
    """Calculate biorhythm values for a date range (charting).

    Deterministic calculation — no AI involved.
    Evidence rating: LOW.
    """
    try:
        results = calculate_range(
            request.birth_date,
            request.start_date,
            request.days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return BiorhythmRangeResponse(
        results=results,
        days_requested=request.days,
    )


@router.post("/biorhythm/compatibility", response_model=BiorhythmCompatibilityResponse)
async def compatibility(
    request: BiorhythmCompatibilityRequest,
) -> BiorhythmCompatibilityResponse:
    """Compare two people's biorhythm cycles on a given date.

    Deterministic calculation — no AI involved.
    Evidence rating: LOW.
    """
    try:
        result = biorhythm_compatibility(
            request.birth_date_a,
            request.birth_date_b,
            request.target_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return BiorhythmCompatibilityResponse(
        person_a=result["person_a"],
        person_b=result["person_b"],
        physical_similarity=result["physical_similarity"],
        emotional_similarity=result["emotional_similarity"],
        intellectual_similarity=result["intellectual_similarity"],
        overall_sync=result["overall_sync"],
    )

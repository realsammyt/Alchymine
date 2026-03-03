"""Numerology API endpoints — deterministic calculations, no LLM."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.numerology import (
    calculate_pythagorean_profile,
    chaldean_name_number,
)

router = APIRouter()


class NumerologyRequest(BaseModel):
    """Request for numerology calculation."""

    full_name: str = Field(..., min_length=2, max_length=200, description="Full legal name")
    birth_date: date = Field(..., description="Birth date (YYYY-MM-DD)")
    system: str = Field("pythagorean", description="Calculation system: pythagorean | chaldean")
    treat_y_as_vowel: bool = Field(False, description="Treat Y as a vowel in name calculations")


class NumerologyResponse(BaseModel):
    """Numerology calculation results."""

    life_path: int
    expression: int
    soul_urge: int
    personality: int
    personal_year: int
    personal_month: int
    maturity: int
    is_master_number: bool
    chaldean_name: int | None = None
    system: str
    name_used: str
    birth_date: date
    evidence_level: str = Field(
        default="traditional",
        description="Evidence quality: strong | moderate | emerging | traditional",
    )
    calculation_type: str = Field(default="deterministic")
    methodology: str = Field(
        default="Pythagorean numerology uses standard letter-to-number mapping (A=1..I=9, cycling). All calculations are fully deterministic and reproducible.",
    )


@router.get("/numerology/{name}")
async def calculate_numerology(
    name: str,
    birth_date: date | None = None,
    system: str = "pythagorean",
    current_user: dict = Depends(get_current_user),
) -> NumerologyResponse:
    """Calculate numerology for a given name and optional birth date.

    Deterministic calculation — no AI involved.
    """
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

    if birth_date is None:
        birth_date = date(2000, 1, 1)  # Default for name-only calculations

    profile = calculate_pythagorean_profile(
        name,
        birth_date,
    )

    chaldean_name = None
    if system == "chaldean":
        chaldean_name = chaldean_name_number(name)

    return NumerologyResponse(
        life_path=profile.life_path,
        expression=profile.expression,
        soul_urge=profile.soul_urge,
        personality=profile.personality,
        personal_year=profile.personal_year,
        personal_month=profile.personal_month,
        maturity=profile.maturity,
        is_master_number=profile.is_master_number,
        chaldean_name=chaldean_name,
        system=system,
        name_used=name,
        birth_date=birth_date,
    )


@router.post("/numerology")
async def calculate_numerology_post(
    request: NumerologyRequest,
    current_user: dict = Depends(get_current_user),
) -> NumerologyResponse:
    """Calculate numerology from POST body."""
    return await calculate_numerology(
        name=request.full_name,
        birth_date=request.birth_date,
        system=request.system,
    )

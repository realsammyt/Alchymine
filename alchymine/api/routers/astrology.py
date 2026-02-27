"""Astrology API endpoints — Swiss Ephemeris calculations, no LLM."""

from __future__ import annotations

from datetime import date, time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class AstrologyResponse(BaseModel):
    """Astrological chart calculation results."""

    sun_sign: str
    sun_degree: float
    moon_sign: str
    moon_degree: float
    rising_sign: str | None = None
    rising_degree: float | None = None
    mercury_retrograde: bool = False
    venus_retrograde: bool = False
    birth_date: date
    calculation_note: str | None = None


@router.get("/astrology/{birth_date}")
async def calculate_chart(
    birth_date: date,
    birth_time: time | None = Query(None, description="Birth time for Rising sign accuracy"),
    birth_city: str | None = Query(None, description="Birth city for house calculations"),
) -> AstrologyResponse:
    """Calculate astrological natal chart.

    Deterministic calculation via Swiss Ephemeris — no AI involved.
    Birth time is optional but enables Rising sign calculation.
    """
    try:
        from alchymine.engine.astrology.chart import calculate_natal_chart

        result = calculate_natal_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            birth_city=birth_city,
        )
        return AstrologyResponse(**result)
    except ImportError:
        # Return a simplified response while pyswisseph is being integrated
        sun_sign = _approximate_sun_sign(birth_date)
        return AstrologyResponse(
            sun_sign=sun_sign,
            sun_degree=0.0,
            moon_sign="Unknown",
            moon_degree=0.0,
            birth_date=birth_date,
            calculation_note="Approximate — Swiss Ephemeris integration pending",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _approximate_sun_sign(birth_date: date) -> str:
    """Approximate sun sign from birth date (no ephemeris needed)."""
    month, day = birth_date.month, birth_date.day
    signs = [
        (1, 20, "Capricorn"), (2, 19, "Aquarius"), (3, 20, "Pisces"),
        (4, 20, "Aries"), (5, 21, "Taurus"), (6, 21, "Gemini"),
        (7, 23, "Cancer"), (8, 23, "Leo"), (9, 23, "Virgo"),
        (10, 23, "Libra"), (11, 22, "Scorpio"), (12, 22, "Sagittarius"),
    ]
    for end_month, end_day, sign in signs:
        if month == end_month and day <= end_day:
            return sign
        if month < end_month:
            return sign
    return "Capricorn"

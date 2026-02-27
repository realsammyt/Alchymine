"""Biorhythm calculation engine — pure deterministic sine-wave math.

Biorhythm theory proposes three innate cycles that begin at birth:
  - Physical:     23-day cycle
  - Emotional:    28-day cycle
  - Intellectual: 33-day cycle

Each cycle is modeled as sin(2*pi * days_alive / cycle_length).

Evidence rating: LOW
Methodology note: Biorhythm theory is not supported by scientific consensus.
Results are provided for entertainment and self-reflection.
"""

from __future__ import annotations

import math
from datetime import date

from pydantic import BaseModel, Field

# ─── Cycle lengths ────────────────────────────────────────────────────

PHYSICAL_CYCLE = 23
EMOTIONAL_CYCLE = 28
INTELLECTUAL_CYCLE = 33

# Critical-day threshold: value is within +/- this of zero
CRITICAL_THRESHOLD = 0.1

# Methodology disclosure (must be shown in any UI rendering these results)
METHODOLOGY_NOTE = (
    "Biorhythm theory is not supported by scientific consensus. "
    "Results are provided for entertainment and self-reflection."
)

EVIDENCE_RATING = "LOW"


# ─── Result model ─────────────────────────────────────────────────────


class BiorhythmResult(BaseModel):
    """Result of a single-day biorhythm calculation."""

    # Raw sine values (-1.0 to 1.0)
    physical: float = Field(..., ge=-1.0, le=1.0, description="Physical cycle value")
    emotional: float = Field(..., ge=-1.0, le=1.0, description="Emotional cycle value")
    intellectual: float = Field(..., ge=-1.0, le=1.0, description="Intellectual cycle value")

    # Human-friendly percentages (0-100, mapped from sine range)
    physical_percentage: int = Field(..., ge=0, le=100)
    emotional_percentage: int = Field(..., ge=0, le=100)
    intellectual_percentage: int = Field(..., ge=0, le=100)

    # Days since birth
    days_alive: int = Field(..., ge=0)

    # Critical-day flags (cycle crossing zero)
    is_physical_critical: bool = Field(False)
    is_emotional_critical: bool = Field(False)
    is_intellectual_critical: bool = Field(False)

    # Date this result corresponds to
    target_date: date

    # Transparency
    evidence_rating: str = Field(default=EVIDENCE_RATING)
    methodology_note: str = Field(default=METHODOLOGY_NOTE)


# ─── Core calculation ─────────────────────────────────────────────────


def _cycle_value(days_alive: int, cycle_length: int) -> float:
    """Compute sin(2*pi * days_alive / cycle_length), rounded to 10 decimals."""
    return round(math.sin(2 * math.pi * days_alive / cycle_length), 10)


def _to_percentage(value: float) -> int:
    """Map a sine value (-1..1) to a percentage (0..100)."""
    return round((value + 1.0) / 2.0 * 100)


def _is_critical(value: float) -> bool:
    """A cycle is critical when its value is within +/- CRITICAL_THRESHOLD of zero."""
    return abs(value) <= CRITICAL_THRESHOLD


def calculate_biorhythm(birth_date: date, target_date: date) -> BiorhythmResult:
    """Calculate biorhythm values for a single day.

    Args:
        birth_date: The person's date of birth.
        target_date: The date to calculate biorhythms for.

    Returns:
        BiorhythmResult with all cycle values, percentages, and critical flags.

    Raises:
        ValueError: If target_date is before birth_date.
    """
    if target_date < birth_date:
        raise ValueError("target_date cannot be before birth_date")

    days_alive = (target_date - birth_date).days

    physical = _cycle_value(days_alive, PHYSICAL_CYCLE)
    emotional = _cycle_value(days_alive, EMOTIONAL_CYCLE)
    intellectual = _cycle_value(days_alive, INTELLECTUAL_CYCLE)

    return BiorhythmResult(
        physical=physical,
        emotional=emotional,
        intellectual=intellectual,
        physical_percentage=_to_percentage(physical),
        emotional_percentage=_to_percentage(emotional),
        intellectual_percentage=_to_percentage(intellectual),
        days_alive=days_alive,
        is_physical_critical=_is_critical(physical),
        is_emotional_critical=_is_critical(emotional),
        is_intellectual_critical=_is_critical(intellectual),
        target_date=target_date,
    )

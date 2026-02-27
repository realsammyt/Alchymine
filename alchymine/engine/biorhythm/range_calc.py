"""Biorhythm range calculations — multi-day series for charting.

Provides utilities for computing biorhythm values across date ranges,
and for finding critical days (zero-crossings) and peak days (maxima/minima)
within a range.
"""

from __future__ import annotations

from datetime import date, timedelta

from alchymine.engine.biorhythm.calculator import (
    BiorhythmResult,
    calculate_biorhythm,
)

# Peak threshold: a cycle is at a peak when its absolute value is >= this
PEAK_THRESHOLD = 0.95


def calculate_range(
    birth_date: date,
    start_date: date,
    days: int,
) -> list[BiorhythmResult]:
    """Calculate biorhythm values for a range of consecutive days.

    Args:
        birth_date: The person's date of birth.
        start_date: First day of the range.
        days: Number of days to calculate (must be >= 1).

    Returns:
        List of BiorhythmResult, one per day, in chronological order.

    Raises:
        ValueError: If days < 1 or start_date is before birth_date.
    """
    if days < 1:
        raise ValueError("days must be >= 1")

    results: list[BiorhythmResult] = []
    for offset in range(days):
        target = start_date + timedelta(days=offset)
        results.append(calculate_biorhythm(birth_date, target))
    return results


def find_critical_days(
    birth_date: date,
    start_date: date,
    days: int,
) -> list[dict]:
    """Find all critical days (zero-crossings) in a date range.

    A critical day is when any cycle's value is within +/- CRITICAL_THRESHOLD
    of zero. These are considered unstable transition points.

    Args:
        birth_date: The person's date of birth.
        start_date: First day of the range.
        days: Number of days to scan.

    Returns:
        List of dicts with keys: date, cycle (str), value (float), days_alive (int).
    """
    critical_days: list[dict] = []
    results = calculate_range(birth_date, start_date, days)

    for result in results:
        if result.is_physical_critical:
            critical_days.append(
                {
                    "date": result.target_date,
                    "cycle": "physical",
                    "value": result.physical,
                    "days_alive": result.days_alive,
                }
            )
        if result.is_emotional_critical:
            critical_days.append(
                {
                    "date": result.target_date,
                    "cycle": "emotional",
                    "value": result.emotional,
                    "days_alive": result.days_alive,
                }
            )
        if result.is_intellectual_critical:
            critical_days.append(
                {
                    "date": result.target_date,
                    "cycle": "intellectual",
                    "value": result.intellectual,
                    "days_alive": result.days_alive,
                }
            )

    return critical_days


def find_peak_days(
    birth_date: date,
    start_date: date,
    days: int,
) -> list[dict]:
    """Find all peak days (maxima and minima) in a date range.

    A peak day is when any cycle's absolute value is >= PEAK_THRESHOLD.
    Positive peaks indicate high-energy days; negative peaks indicate
    low-energy days.

    Args:
        birth_date: The person's date of birth.
        start_date: First day of the range.
        days: Number of days to scan.

    Returns:
        List of dicts with keys: date, cycle (str), value (float),
        peak_type ("high" | "low"), days_alive (int).
    """
    peak_days: list[dict] = []
    results = calculate_range(birth_date, start_date, days)

    for result in results:
        for cycle_name, value in [
            ("physical", result.physical),
            ("emotional", result.emotional),
            ("intellectual", result.intellectual),
        ]:
            if abs(value) >= PEAK_THRESHOLD:
                peak_days.append(
                    {
                        "date": result.target_date,
                        "cycle": cycle_name,
                        "value": value,
                        "peak_type": "high" if value > 0 else "low",
                        "days_alive": result.days_alive,
                    }
                )

    return peak_days

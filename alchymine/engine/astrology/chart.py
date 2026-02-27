"""Astrological chart calculation engine.

Provides natal chart calculations using approximate ephemeris data.
When pyswisseph is available, uses Swiss Ephemeris for precise calculations.
Falls back to simplified approximations otherwise.

All calculations are deterministic.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any

# Zodiac sign boundaries (ecliptic longitude ranges)
ZODIAC_SIGNS: list[tuple[float, float, str]] = [
    (0, 30, "Aries"),
    (30, 60, "Taurus"),
    (60, 90, "Gemini"),
    (90, 120, "Cancer"),
    (120, 150, "Leo"),
    (150, 180, "Virgo"),
    (180, 210, "Libra"),
    (210, 240, "Scorpio"),
    (240, 270, "Sagittarius"),
    (270, 300, "Capricorn"),
    (300, 330, "Aquarius"),
    (330, 360, "Pisces"),
]

# Approximate sun entry dates for each sign (month, day)
# These are the dates when the sun enters each sign (approximate).
SUN_ENTRY_DATES: list[tuple[int, int, str]] = [
    (3, 21, "Aries"),
    (4, 20, "Taurus"),
    (5, 21, "Gemini"),
    (6, 21, "Cancer"),
    (7, 23, "Leo"),
    (8, 23, "Virgo"),
    (9, 23, "Libra"),
    (10, 23, "Scorpio"),
    (11, 22, "Sagittarius"),
    (12, 22, "Capricorn"),
    (1, 20, "Aquarius"),
    (2, 19, "Pisces"),
]


def _degree_to_sign(degree: float) -> str:
    """Convert ecliptic longitude to zodiac sign name."""
    degree = degree % 360
    for start, end, sign in ZODIAC_SIGNS:
        if start <= degree < end:
            return sign
    return "Pisces"  # 360 wraps to Pisces/Aries boundary


def approximate_sun_sign(birth_date: date) -> str:
    """Determine sun sign from birth date using date-based approximation.

    This is accurate for most dates but may be off by 1 day at sign boundaries.

    >>> approximate_sun_sign(date(1992, 3, 15))
    'Pisces'
    >>> approximate_sun_sign(date(1990, 7, 4))
    'Cancer'
    """
    month, day = birth_date.month, birth_date.day

    # Check each sign entry date in order
    # The sun is in the PREVIOUS sign until it reaches the entry date
    sign_order = [
        (1, 20, "Capricorn", "Aquarius"),
        (2, 19, "Aquarius", "Pisces"),
        (3, 21, "Pisces", "Aries"),
        (4, 20, "Aries", "Taurus"),
        (5, 21, "Taurus", "Gemini"),
        (6, 21, "Gemini", "Cancer"),
        (7, 23, "Cancer", "Leo"),
        (8, 23, "Leo", "Virgo"),
        (9, 23, "Virgo", "Libra"),
        (10, 23, "Libra", "Scorpio"),
        (11, 22, "Scorpio", "Sagittarius"),
        (12, 22, "Sagittarius", "Capricorn"),
    ]

    for entry_month, entry_day, before_sign, after_sign in sign_order:
        if month == entry_month:
            return before_sign if day < entry_day else after_sign

    return "Capricorn"


def approximate_sun_degree(birth_date: date) -> float:
    """Approximate the sun's ecliptic longitude for a birth date.

    Uses a simplified calculation based on the sun's average motion
    of ~0.9856 degrees per day, with the vernal equinox (0 Aries)
    at approximately March 20-21.

    >>> 350.0 < approximate_sun_degree(date(1992, 3, 15)) < 360.0
    True
    """
    # Days since vernal equinox (March 20 as reference)
    ref = date(birth_date.year, 3, 20)
    delta_days = (birth_date - ref).days
    # Sun moves ~0.9856 degrees/day
    degree = (delta_days * 0.9856) % 360
    return round(degree, 2)


def _approximate_moon_sign(birth_date: date) -> tuple[str, float]:
    """Very rough moon sign approximation.

    The moon moves ~13.2 degrees/day through the zodiac, completing
    a full cycle in ~27.3 days. Without exact time and ephemeris,
    this gives only a rough estimate.
    """
    # Use a known reference point: Jan 1, 2000, Moon was at ~120° (Cancer-Leo boundary)
    ref = date(2000, 1, 1)
    ref_moon_degree = 120.0
    delta_days = (birth_date - ref).days
    # Moon moves ~13.176 degrees/day
    moon_degree = (ref_moon_degree + delta_days * 13.176) % 360
    moon_sign = _degree_to_sign(moon_degree)
    return moon_sign, round(moon_degree, 2)


def calculate_natal_chart(
    birth_date: date,
    birth_time: time | None = None,
    birth_city: str | None = None,
) -> dict[str, Any]:
    """Calculate a natal chart for the given birth data.

    Attempts to use pyswisseph for precise calculations.
    Falls back to approximations if not available.

    Parameters
    ----------
    birth_date : date
        Date of birth.
    birth_time : time | None
        Time of birth (enables Rising sign). Optional.
    birth_city : str | None
        City of birth (enables house system). Optional.

    Returns
    -------
    dict with keys matching AstrologyResponse fields.
    """
    try:
        return _calculate_with_swisseph(birth_date, birth_time, birth_city)
    except ImportError:
        return _calculate_approximate(birth_date, birth_time)


def _calculate_approximate(
    birth_date: date,
    birth_time: time | None = None,
) -> dict[str, Any]:
    """Approximate natal chart without Swiss Ephemeris."""
    sun_sign = approximate_sun_sign(birth_date)
    sun_degree = approximate_sun_degree(birth_date)
    moon_sign, moon_degree = _approximate_moon_sign(birth_date)

    result: dict[str, Any] = {
        "sun_sign": sun_sign,
        "sun_degree": sun_degree,
        "moon_sign": moon_sign,
        "moon_degree": moon_degree,
        "rising_sign": None,
        "rising_degree": None,
        "mercury_retrograde": False,
        "venus_retrograde": False,
        "birth_date": birth_date,
        "calculation_note": "Approximate calculation — pyswisseph not installed",
    }

    return result


def _calculate_with_swisseph(
    birth_date: date,
    birth_time: time | None = None,
    birth_city: str | None = None,
) -> dict[str, Any]:
    """Calculate natal chart using Swiss Ephemeris (pyswisseph).

    Raises ImportError if swisseph is not installed.
    """
    import swisseph as swe  # type: ignore[import-untyped]

    # Convert birth date to Julian Day Number
    hour = 12.0  # Default to noon if no birth time
    if birth_time is not None:
        hour = birth_time.hour + birth_time.minute / 60.0 + birth_time.second / 3600.0

    jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, hour)

    # Calculate Sun position
    sun_pos = swe.calc_ut(jd, swe.SUN)[0]
    sun_degree = round(sun_pos[0], 2)
    sun_sign = _degree_to_sign(sun_degree)

    # Calculate Moon position
    moon_pos = swe.calc_ut(jd, swe.MOON)[0]
    moon_degree = round(moon_pos[0], 2)
    moon_sign = _degree_to_sign(moon_degree)

    # Mercury and Venus retrograde check (negative speed = retrograde)
    mercury_pos = swe.calc_ut(jd, swe.MERCURY)[0]
    mercury_retrograde = mercury_pos[3] < 0 if len(mercury_pos) > 3 else False

    venus_pos = swe.calc_ut(jd, swe.VENUS)[0]
    venus_retrograde = venus_pos[3] < 0 if len(venus_pos) > 3 else False

    result: dict[str, Any] = {
        "sun_sign": sun_sign,
        "sun_degree": sun_degree,
        "moon_sign": moon_sign,
        "moon_degree": moon_degree,
        "rising_sign": None,
        "rising_degree": None,
        "mercury_retrograde": mercury_retrograde,
        "venus_retrograde": venus_retrograde,
        "birth_date": birth_date,
        "calculation_note": None,
    }

    # Rising sign requires birth time and location
    if birth_time is not None and birth_city is not None:
        # TODO: geocode birth_city to lat/lon for house calculation
        # For now, use a placeholder
        result["calculation_note"] = "House system requires geocoding — Rising sign pending"

    return result

"""Astrological chart calculation engine.

Provides natal chart calculations using approximate ephemeris data.
When pyswisseph is available, uses Swiss Ephemeris for precise calculations.
Falls back to simplified approximations otherwise.

Includes:
- Sun, Moon, and planetary position approximations
- Rising sign / Ascendant calculation (requires birth time + latitude/longitude)
- Multiple house system support (Placidus, Koch, Equal, Whole Sign)
- Natal aspect calculation
- Transit overlay integration

All calculations are deterministic.
"""

from __future__ import annotations

import math
from datetime import date, time
from enum import Enum
from typing import Any

from .aspects import Aspect, AspectType, calculate_aspects
from .transits import (
    approximate_planet_longitude,
    get_current_positions,
    get_transit_overlay,
    PLANET_ELEMENTS,
)

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


# ─── House Systems ──────────────────────────────────────────────────────


class HouseSystem(str, Enum):
    """Supported astrological house systems."""

    PLACIDUS = "placidus"
    KOCH = "koch"
    EQUAL = "equal"
    WHOLE_SIGN = "whole_sign"


# Well-known city coordinates for rising sign calculation.
# This is a fallback lookup when geocoding is unavailable.
# Latitude / Longitude pairs (positive N/E, negative S/W).
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "new york": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
    "mumbai": (19.0760, 72.8777),
    "sao paulo": (-23.5505, -46.6333),
    "cape town": (-33.9249, 18.4241),
    "cairo": (30.0444, 31.2357),
    "beijing": (39.9042, 116.4074),
    "moscow": (55.7558, 37.6173),
    "berlin": (52.5200, 13.4050),
    "toronto": (43.6532, -79.3832),
    "mexico city": (19.4326, -99.1332),
    "buenos aires": (-34.6037, -58.3816),
    "johannesburg": (-26.2041, 28.0473),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "hong kong": (22.3193, 114.1694),
    "nairobi": (-1.2921, 36.8219),
    "lagos": (6.5244, 3.3792),
    "seoul": (37.5665, 126.9780),
    "bangkok": (13.7563, 100.5018),
    "miami": (25.7617, -80.1918),
    "san francisco": (37.7749, -122.4194),
    "atlanta": (33.7490, -84.3880),
    "denver": (39.7392, -104.9903),
    "seattle": (47.6062, -122.3321),
    "houston": (29.7604, -95.3698),
    "phoenix": (33.4484, -112.0740),
    "philadelphia": (39.9526, -75.1652),
    "dallas": (32.7767, -96.7970),
    "boston": (42.3601, -71.0589),
    "detroit": (42.3314, -83.0458),
    "minneapolis": (44.9778, -93.2650),
    "portland": (45.5152, -122.6784),
    "auckland": (-36.8485, 174.7633),
    "melbourne": (-37.8136, 144.9631),
    "perth": (-31.9505, 115.8605),
    "rio de janeiro": (-22.9068, -43.1729),
    "lima": (-12.0464, -77.0428),
    "santiago": (-33.4489, -70.6693),
    "bogota": (4.7110, -74.0721),
    "amsterdam": (52.3676, 4.9041),
    "rome": (41.9028, 12.4964),
    "madrid": (40.4168, -3.7038),
    "lisbon": (38.7223, -9.1393),
    "stockholm": (59.3293, 18.0686),
    "oslo": (59.9139, 10.7522),
    "copenhagen": (55.6761, 12.5683),
    "vienna": (48.2082, 16.3738),
    "zurich": (47.3769, 8.5417),
    "warsaw": (52.2297, 21.0122),
    "istanbul": (41.0082, 28.9784),
    "athens": (37.9838, 23.7275),
    "tel aviv": (32.0853, 34.7818),
    "accra": (5.6037, -0.1870),
    "kinshasa": (-4.4419, 15.2663),
    "addis ababa": (9.0250, 38.7469),
    "dar es salaam": (-6.7924, 39.2083),
    "kampala": (0.3476, 32.5825),
    "kuala lumpur": (3.1390, 101.6869),
    "jakarta": (-6.2088, 106.8456),
    "manila": (14.5995, 120.9842),
    "hanoi": (21.0278, 105.8342),
    "kolkata": (22.5726, 88.3639),
    "delhi": (28.7041, 77.1025),
    "chennai": (13.0827, 80.2707),
    "karachi": (24.8607, 67.0011),
    "dhaka": (23.8103, 90.4125),
    "colombo": (6.9271, 79.8612),
    "kathmandu": (27.7172, 85.3240),
}


def _lookup_city_coordinates(city: str) -> tuple[float, float] | None:
    """Look up latitude/longitude for a city name.

    Returns None if the city is not in the lookup table.
    Case-insensitive matching.
    """
    return CITY_COORDINATES.get(city.lower().strip())


def approximate_ascendant(
    birth_date: date,
    birth_time: time,
    latitude: float,
    longitude: float,
) -> tuple[str, float]:
    """Approximate the Ascendant (Rising sign) for a given birth date/time/location.

    Uses a simplified calculation based on:
    1. Local Sidereal Time (LST) at the birth moment
    2. The obliquity of the ecliptic (~23.44 degrees)
    3. The geographic latitude

    The Ascendant is the degree of the ecliptic rising on the eastern horizon.

    Parameters
    ----------
    birth_date : date
        Date of birth.
    birth_time : time
        Time of birth (local time is assumed; for best accuracy, use UTC).
    latitude : float
        Geographic latitude in degrees (positive N, negative S).
    longitude : float
        Geographic longitude in degrees (positive E, negative W).

    Returns
    -------
    tuple[str, float]
        (rising_sign, rising_degree) where rising_degree is 0-360.
    """
    # Step 1: Approximate days since J2000.0
    ref = date(2000, 1, 1)
    days_since_j2000 = (birth_date - ref).days

    # Step 2: Calculate Greenwich Mean Sidereal Time (GMST) at 0h UT
    # Simplified formula (accurate to ~1 degree over decades)
    # T = Julian centuries since J2000.0
    t_centuries = days_since_j2000 / 36525.0
    # GMST at 0h UT in degrees
    gmst_0h = (
        280.46061837
        + 360.98564736629 * days_since_j2000
        + 0.000387933 * t_centuries**2
    ) % 360

    # Step 3: Add the birth time contribution
    # Convert birth time to fractional hours
    birth_hours = (
        birth_time.hour + birth_time.minute / 60.0 + birth_time.second / 3600.0
    )
    # Sidereal time advances ~1.00274 sidereal degrees per solar hour
    # (360 degrees in ~23h 56m 4s)
    gmst = (gmst_0h + birth_hours * 15.04107) % 360

    # Step 4: Convert to Local Sidereal Time
    lst = (gmst + longitude) % 360

    # Step 5: Calculate the Ascendant
    # Formula: tan(ASC) = -cos(LST) / (sin(epsilon) * tan(latitude) + cos(epsilon) * sin(LST))
    # where epsilon = obliquity of the ecliptic (~23.44 degrees)
    epsilon = 23.4393  # obliquity in degrees
    epsilon_rad = math.radians(epsilon)
    lst_rad = math.radians(lst)
    lat_rad = math.radians(latitude)

    numerator = -math.cos(lst_rad)
    denominator = (
        math.sin(epsilon_rad) * math.tan(lat_rad)
        + math.cos(epsilon_rad) * math.sin(lst_rad)
    )

    if abs(denominator) < 1e-10:
        # Near-zero denominator: Ascendant is near 90 or 270 degrees
        asc_degree = 90.0 if numerator > 0 else 270.0
    else:
        asc_rad = math.atan2(numerator, denominator)
        asc_degree = math.degrees(asc_rad) % 360

    asc_degree = round(asc_degree, 2)
    rising_sign = _degree_to_sign(asc_degree)
    return rising_sign, asc_degree


def calculate_house_cusps(
    ascendant_degree: float,
    house_system: HouseSystem = HouseSystem.PLACIDUS,
    latitude: float = 0.0,
    mc_degree: float | None = None,
) -> list[float]:
    """Calculate house cusp positions for a given house system.

    Parameters
    ----------
    ascendant_degree : float
        The Ascendant (1st house cusp) in ecliptic degrees.
    house_system : HouseSystem
        Which house system to use.
    latitude : float
        Geographic latitude (needed for Placidus/Koch).
    mc_degree : float | None
        Midheaven degree (10th house cusp). Estimated if not provided.

    Returns
    -------
    list[float]
        12 house cusp positions in ecliptic degrees (0-360).
        cusps[0] is the 1st house, cusps[1] is the 2nd house, etc.
    """
    if house_system == HouseSystem.WHOLE_SIGN:
        return _whole_sign_houses(ascendant_degree)
    elif house_system == HouseSystem.EQUAL:
        return _equal_houses(ascendant_degree)
    else:
        # Placidus and Koch both need MC; for our approximation, we use
        # the same simplified interpolation for both.
        if mc_degree is None:
            mc_degree = (ascendant_degree + 270.0) % 360
        return _quadrant_houses(ascendant_degree, mc_degree)


def _whole_sign_houses(ascendant_degree: float) -> list[float]:
    """Whole Sign houses: each house is exactly 30 degrees, starting
    at the beginning of the Ascendant's sign."""
    # Find the start of the Ascendant's sign (multiple of 30)
    sign_start = (ascendant_degree // 30) * 30
    return [round((sign_start + i * 30) % 360, 2) for i in range(12)]


def _equal_houses(ascendant_degree: float) -> list[float]:
    """Equal houses: each house is exactly 30 degrees from the Ascendant."""
    return [round((ascendant_degree + i * 30) % 360, 2) for i in range(12)]


def _quadrant_houses(ascendant_degree: float, mc_degree: float) -> list[float]:
    """Simplified quadrant house calculation (Placidus/Koch approximation).

    Divides each quadrant into three equal parts using the Ascendant and MC
    as anchoring cusps. This is a simplification of the full Placidus/Koch
    algorithms, which require iterative trigonometric solutions.
    """
    asc = ascendant_degree % 360
    mc = mc_degree % 360
    ic = (mc + 180) % 360
    dsc = (asc + 180) % 360

    # Four quadrants, each divided into 3 houses
    # Q1: ASC to IC (houses 1, 2, 3)
    # Q2: IC to DSC (houses 4, 5, 6)
    # Q3: DSC to MC (houses 7, 8, 9)
    # Q4: MC to ASC (houses 10, 11, 12)
    def _trisect(start: float, end: float) -> list[float]:
        """Divide an arc into 3 equal parts."""
        arc = (end - start) % 360
        return [
            round((start + arc * i / 3) % 360, 2) for i in range(3)
        ]

    cusps: list[float] = []
    cusps.extend(_trisect(asc, ic))    # Houses 1, 2, 3
    cusps.extend(_trisect(ic, dsc))    # Houses 4, 5, 6
    cusps.extend(_trisect(dsc, mc))    # Houses 7, 8, 9
    cusps.extend(_trisect(mc, asc))    # Houses 10, 11, 12
    return cusps


def _approximate_planetary_positions(birth_date: date) -> dict[str, float]:
    """Get approximate ecliptic longitudes for major planets at a birth date.

    Uses the mean orbital element approximations from the transits module.
    """
    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars",
               "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    positions: dict[str, float] = {}
    for planet in planets:
        positions[planet] = approximate_planet_longitude(planet, birth_date)
    return positions


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
    latitude: float | None = None,
    longitude: float | None = None,
    house_system: HouseSystem = HouseSystem.PLACIDUS,
    include_aspects: bool = True,
    include_minor_aspects: bool = False,
) -> dict[str, Any]:
    """Calculate a natal chart for the given birth data.

    Attempts to use pyswisseph for precise planetary positions.
    Falls back to approximations if not available.
    Rising sign, house cusps, and aspects are always calculated
    using the approximation engine when birth time/location are available.

    Parameters
    ----------
    birth_date : date
        Date of birth.
    birth_time : time | None
        Time of birth (enables Rising sign). Optional.
    birth_city : str | None
        City of birth (enables house system). Optional.
        Used for coordinate lookup if latitude/longitude not provided.
    latitude : float | None
        Geographic latitude. Overrides birth_city lookup if provided.
    longitude : float | None
        Geographic longitude. Overrides birth_city lookup if provided.
    house_system : HouseSystem
        House system to use (default Placidus).
    include_aspects : bool
        Whether to calculate natal aspects (default True).
    include_minor_aspects : bool
        Whether to include minor aspects (default False).

    Returns
    -------
    dict with keys matching AstrologyResponse fields.
    """
    # Resolve coordinates from city if not provided directly
    if latitude is None or longitude is None:
        if birth_city is not None:
            coords = _lookup_city_coordinates(birth_city)
            if coords is not None:
                latitude, longitude = coords

    # Step 1: Get core planetary positions (swisseph or approximate)
    try:
        base_result = _calculate_with_swisseph(birth_date, birth_time, birth_city)
    except ImportError:
        base_result = _calculate_base_approximate(birth_date, birth_time)

    # Step 2: Get full planetary positions for aspects (always approximate-based)
    planetary_positions = _approximate_planetary_positions(birth_date)
    # Override Sun and Moon with whatever the base calculation gave us
    planetary_positions["Sun"] = base_result["sun_degree"]
    planetary_positions["Moon"] = base_result["moon_degree"]
    base_result["planetary_positions"] = planetary_positions

    # Step 3: Rising sign / Ascendant (requires birth time + location)
    if birth_time is not None and latitude is not None and longitude is not None:
        rising_sign, rising_degree = approximate_ascendant(
            birth_date, birth_time, latitude, longitude
        )
        base_result["rising_sign"] = rising_sign
        base_result["rising_degree"] = rising_degree

        # Step 4: House cusps
        house_cusps = calculate_house_cusps(
            rising_degree,
            house_system=house_system,
            latitude=latitude,
        )
        base_result["house_system"] = house_system.value
        base_result["house_cusps"] = house_cusps
        base_result["house_placements"] = _assign_house_placements(
            planetary_positions, house_cusps
        )
    else:
        base_result.setdefault("house_system", None)
        base_result.setdefault("house_cusps", None)
        base_result.setdefault("house_placements", None)

    # Step 5: Aspects
    if include_aspects:
        aspects = calculate_aspects(
            planetary_positions,
            include_minor=include_minor_aspects,
        )
        base_result["aspects"] = [
            {
                "planet1": a.planet1,
                "planet2": a.planet2,
                "aspect": a.aspect_type.value,
                "exact_angle": a.exact_angle,
                "actual_angle": a.actual_angle,
                "orb": a.orb,
            }
            for a in aspects
        ]
    else:
        base_result["aspects"] = []

    # Add notes about missing data
    notes: list[str] = []
    if base_result.get("calculation_note"):
        notes.append(base_result["calculation_note"])
    if birth_time is not None and (latitude is None or longitude is None):
        notes.append("Rising sign requires birth location (city or lat/lon)")
    base_result["calculation_note"] = "; ".join(notes) if notes else None

    return base_result


def _calculate_base_approximate(
    birth_date: date,
    birth_time: time | None = None,
) -> dict[str, Any]:
    """Approximate core planetary positions without Swiss Ephemeris.

    Returns a base result dict with sun/moon data. Rising sign, aspects,
    and house cusps are computed by the main calculate_natal_chart function.
    """
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


def _assign_house_placements(
    positions: dict[str, float],
    cusps: list[float],
) -> dict[str, int]:
    """Assign each planet to its house based on house cusp positions.

    Parameters
    ----------
    positions : dict[str, float]
        Planet name -> ecliptic longitude.
    cusps : list[float]
        12 house cusp positions in ecliptic degrees.

    Returns
    -------
    dict[str, int]
        Planet name -> house number (1-12).
    """
    placements: dict[str, int] = {}
    for planet, degree in positions.items():
        placements[planet] = _find_house(degree, cusps)
    return placements


def _find_house(degree: float, cusps: list[float]) -> int:
    """Determine which house a given degree falls in.

    Parameters
    ----------
    degree : float
        Ecliptic longitude (0-360).
    cusps : list[float]
        12 house cusp positions.

    Returns
    -------
    int
        House number (1-12).
    """
    degree = degree % 360
    for i in range(12):
        cusp_start = cusps[i]
        cusp_end = cusps[(i + 1) % 12]

        if cusp_start < cusp_end:
            if cusp_start <= degree < cusp_end:
                return i + 1
        else:
            # Wraps around 360/0
            if degree >= cusp_start or degree < cusp_end:
                return i + 1

    return 12  # Fallback


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

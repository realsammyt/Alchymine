"""Transit overlay calculations.

Calculates current planetary positions and their aspects to natal chart positions.
Uses approximate ephemeris data for deterministic, reproducible results.

All calculations are deterministic — no LLM or randomness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from .aspects import (
    DEFAULT_ORBS,
    MAJOR_ASPECTS,
    Aspect,
    AspectType,
    find_aspect,
)

# ─── Approximate Planetary Periods and Reference Positions ──────────────
# Reference epoch: J2000.0 (January 1, 2000, 12:00 TT)
# These are simplified mean orbital elements for approximate position calculation.
# Accuracy: within ~1-2 degrees for inner planets, ~1 degree for outer planets
# over a span of a few decades from J2000.


@dataclass(frozen=True)
class OrbitalElements:
    """Simplified mean orbital elements for a planet at J2000.0.

    Attributes
    ----------
    mean_longitude_j2000 : float
        Mean ecliptic longitude at J2000.0 epoch (degrees).
    daily_motion : float
        Average daily motion in ecliptic longitude (degrees/day).
    name : str
        Planet name.
    """

    mean_longitude_j2000: float
    daily_motion: float
    name: str


# Approximate mean orbital elements at J2000.0
# Sources: Meeus "Astronomical Algorithms", simplified for approximation.
PLANET_ELEMENTS: dict[str, OrbitalElements] = {
    "Sun": OrbitalElements(
        mean_longitude_j2000=280.46,
        daily_motion=0.9856474,
        name="Sun",
    ),
    "Moon": OrbitalElements(
        mean_longitude_j2000=218.32,
        daily_motion=13.17639,
        name="Moon",
    ),
    "Mercury": OrbitalElements(
        mean_longitude_j2000=252.25,
        daily_motion=4.09233,
        name="Mercury",
    ),
    "Venus": OrbitalElements(
        mean_longitude_j2000=181.98,
        daily_motion=1.60213,
        name="Venus",
    ),
    "Mars": OrbitalElements(
        mean_longitude_j2000=355.45,
        daily_motion=0.5240,
        name="Mars",
    ),
    "Jupiter": OrbitalElements(
        mean_longitude_j2000=34.40,
        daily_motion=0.08309,
        name="Jupiter",
    ),
    "Saturn": OrbitalElements(
        mean_longitude_j2000=49.94,
        daily_motion=0.03346,
        name="Saturn",
    ),
    "Uranus": OrbitalElements(
        mean_longitude_j2000=313.23,
        daily_motion=0.01173,
        name="Uranus",
    ),
    "Neptune": OrbitalElements(
        mean_longitude_j2000=304.88,
        daily_motion=0.00598,
        name="Neptune",
    ),
    "Pluto": OrbitalElements(
        mean_longitude_j2000=238.93,
        daily_motion=0.00397,
        name="Pluto",
    ),
}

# J2000.0 reference date
_J2000_ORDINAL = date(2000, 1, 1).toordinal()


def _days_since_j2000(target_date: date) -> float:
    """Calculate the number of days between J2000.0 and the target date.

    J2000.0 is January 1, 2000 at 12:00 TT. We approximate by using
    midnight, which introduces at most ~0.5 day error — acceptable
    for our approximation-based approach.
    """
    return float(target_date.toordinal() - _J2000_ORDINAL)


def approximate_planet_longitude(
    planet: str,
    target_date: date,
) -> float:
    """Approximate a planet's ecliptic longitude for a given date.

    Uses mean orbital elements from J2000.0. This gives a rough position
    that is accurate to within a few degrees for most planets.

    Parameters
    ----------
    planet : str
        Planet name (must be a key in PLANET_ELEMENTS).
    target_date : date
        The date to calculate the position for.

    Returns
    -------
    float
        Ecliptic longitude in degrees (0-360).

    Raises
    ------
    ValueError
        If the planet name is not recognized.

    >>> 0 <= approximate_planet_longitude("Sun", date(2024, 6, 21)) < 360
    True
    """
    if planet not in PLANET_ELEMENTS:
        raise ValueError(
            f"Unknown planet: {planet!r}. Valid planets: {', '.join(PLANET_ELEMENTS.keys())}"
        )

    elements = PLANET_ELEMENTS[planet]
    days = _days_since_j2000(target_date)
    longitude = (elements.mean_longitude_j2000 + days * elements.daily_motion) % 360
    return round(longitude, 2)


def get_current_positions(
    target_date: date | None = None,
    planets: list[str] | None = None,
) -> dict[str, float]:
    """Get approximate ecliptic longitudes for all (or specified) planets.

    Parameters
    ----------
    target_date : date | None
        Date to calculate positions for. Defaults to today (UTC).
    planets : list[str] | None
        Which planets to include. Defaults to all.

    Returns
    -------
    dict[str, float]
        Mapping of planet name to ecliptic longitude (0-360).
    """
    if target_date is None:
        target_date = datetime.now(UTC).date()

    if planets is None:
        planets = list(PLANET_ELEMENTS.keys())

    positions: dict[str, float] = {}
    for planet in planets:
        positions[planet] = approximate_planet_longitude(planet, target_date)
    return positions


@dataclass(frozen=True)
class TransitAspect:
    """An aspect between a transiting planet and a natal planet.

    Attributes
    ----------
    transit_planet : str
        The transiting (current) planet.
    natal_planet : str
        The natal planet being aspected.
    transit_degree : float
        Current ecliptic longitude of the transiting planet.
    natal_degree : float
        Ecliptic longitude of the natal planet.
    aspect : Aspect
        The detected aspect details.
    """

    transit_planet: str
    natal_planet: str
    transit_degree: float
    natal_degree: float
    aspect: Aspect


def calculate_transit_aspects(
    natal_positions: dict[str, float],
    transit_date: date | None = None,
    transit_planets: list[str] | None = None,
    orbs: dict[AspectType, float] | None = None,
    include_minor: bool = False,
) -> list[TransitAspect]:
    """Calculate aspects between current transits and natal positions.

    Parameters
    ----------
    natal_positions : dict[str, float]
        Natal planet positions (planet name -> ecliptic longitude).
    transit_date : date | None
        Date for transit calculation. Defaults to today (UTC).
    transit_planets : list[str] | None
        Which transiting planets to consider. Defaults to all.
    orbs : dict | None
        Custom orb tolerances. Uses tighter transit orbs if None.
    include_minor : bool
        Whether to include minor aspects (default False for transits).

    Returns
    -------
    list[TransitAspect]
        All detected transit aspects, sorted by orb (tightest first).
    """
    if orbs is None:
        # Transit orbs are typically tighter than natal orbs
        orbs = _transit_orbs()

    aspect_types = frozenset(AspectType) if include_minor else MAJOR_ASPECTS

    current_positions = get_current_positions(
        target_date=transit_date,
        planets=transit_planets,
    )

    results: list[TransitAspect] = []

    for t_planet, t_degree in current_positions.items():
        for n_planet, n_degree in natal_positions.items():
            aspect = find_aspect(
                t_degree,
                n_degree,
                orbs=orbs,
                aspect_types=aspect_types,
            )
            if aspect is not None:
                transit_aspect = TransitAspect(
                    transit_planet=t_planet,
                    natal_planet=n_planet,
                    transit_degree=t_degree,
                    natal_degree=n_degree,
                    aspect=Aspect(
                        planet1=f"T.{t_planet}",
                        planet2=f"N.{n_planet}",
                        aspect_type=aspect.aspect_type,
                        exact_angle=aspect.exact_angle,
                        actual_angle=aspect.actual_angle,
                        orb=aspect.orb,
                    ),
                )
                results.append(transit_aspect)

    # Sort by tightness
    results.sort(key=lambda ta: ta.aspect.orb)
    return results


def _transit_orbs() -> dict[AspectType, float]:
    """Return tighter orb tolerances suitable for transit analysis.

    Transit orbs are typically about half the natal orbs.
    """
    return {aspect: orb * 0.625 for aspect, orb in DEFAULT_ORBS.items()}


def summarize_transits(
    transit_aspects: list[TransitAspect],
) -> dict[str, str]:
    """Produce a human-readable summary of active transits.

    Returns a dict suitable for the AstrologyProfile.current_transits field.

    Parameters
    ----------
    transit_aspects : list[TransitAspect]
        Transit aspects to summarize.

    Returns
    -------
    dict[str, str]
        Keys are like "T.Jupiter-N.Sun", values are like "trine (orb 2.5°)".
    """
    summary: dict[str, str] = {}
    for ta in transit_aspects:
        key = f"{ta.transit_planet} -> {ta.natal_planet}"
        value = f"{ta.aspect.aspect_type.value} (orb {ta.aspect.orb:.1f}\u00b0)"
        summary[key] = value
    return summary


def get_transit_overlay(
    natal_positions: dict[str, float],
    transit_date: date | None = None,
    include_minor: bool = False,
) -> dict[str, object]:
    """Full transit overlay: current positions + aspects to natal chart.

    This is the main entry point for transit analysis.

    Parameters
    ----------
    natal_positions : dict[str, float]
        Natal planet positions.
    transit_date : date | None
        Date for transit calculation.
    include_minor : bool
        Whether to include minor aspects.

    Returns
    -------
    dict with keys:
        - "transit_positions": dict of current planetary positions
        - "transit_aspects": list of TransitAspect objects
        - "summary": dict of human-readable transit descriptions
        - "transit_date": the date used for calculation
    """
    if transit_date is None:
        transit_date = datetime.now(UTC).date()

    current_positions = get_current_positions(target_date=transit_date)

    aspects = calculate_transit_aspects(
        natal_positions=natal_positions,
        transit_date=transit_date,
        include_minor=include_minor,
    )

    summary = summarize_transits(aspects)

    return {
        "transit_positions": current_positions,
        "transit_aspects": aspects,
        "summary": summary,
        "transit_date": transit_date,
    }

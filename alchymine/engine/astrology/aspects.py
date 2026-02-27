"""Aspect calculations between planetary positions.

Aspects are angular relationships between planets in a natal chart.
This module provides deterministic calculation of major and minor aspects
with configurable orb tolerances.

All calculations are deterministic — no LLM or randomness.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AspectType(str, Enum):
    """Aspect types with their exact angles."""

    # Major aspects
    CONJUNCTION = "conjunction"
    OPPOSITION = "opposition"
    TRINE = "trine"
    SQUARE = "square"
    SEXTILE = "sextile"

    # Minor aspects
    QUINCUNX = "quincunx"
    SEMI_SEXTILE = "semi-sextile"
    SEMI_SQUARE = "semi-square"
    SESQUIQUADRATE = "sesquiquadrate"


# Exact angles for each aspect type
ASPECT_ANGLES: dict[AspectType, float] = {
    AspectType.CONJUNCTION: 0.0,
    AspectType.OPPOSITION: 180.0,
    AspectType.TRINE: 120.0,
    AspectType.SQUARE: 90.0,
    AspectType.SEXTILE: 60.0,
    AspectType.QUINCUNX: 150.0,
    AspectType.SEMI_SEXTILE: 30.0,
    AspectType.SEMI_SQUARE: 45.0,
    AspectType.SESQUIQUADRATE: 135.0,
}

# Default orb tolerances (in degrees) for each aspect type.
# Major aspects get wider orbs; minor aspects get tighter orbs.
# These follow common astrological conventions.
DEFAULT_ORBS: dict[AspectType, float] = {
    # Major aspects
    AspectType.CONJUNCTION: 8.0,
    AspectType.OPPOSITION: 8.0,
    AspectType.TRINE: 8.0,
    AspectType.SQUARE: 7.0,
    AspectType.SEXTILE: 6.0,
    # Minor aspects
    AspectType.QUINCUNX: 3.0,
    AspectType.SEMI_SEXTILE: 2.0,
    AspectType.SEMI_SQUARE: 2.0,
    AspectType.SESQUIQUADRATE: 2.0,
}

# Classification of major vs minor aspects
MAJOR_ASPECTS: frozenset[AspectType] = frozenset(
    {
        AspectType.CONJUNCTION,
        AspectType.OPPOSITION,
        AspectType.TRINE,
        AspectType.SQUARE,
        AspectType.SEXTILE,
    }
)

MINOR_ASPECTS: frozenset[AspectType] = frozenset(
    {
        AspectType.QUINCUNX,
        AspectType.SEMI_SEXTILE,
        AspectType.SEMI_SQUARE,
        AspectType.SESQUIQUADRATE,
    }
)


@dataclass(frozen=True)
class Aspect:
    """A detected aspect between two planetary positions.

    Attributes
    ----------
    planet1 : str
        Name of the first planet/body.
    planet2 : str
        Name of the second planet/body.
    aspect_type : AspectType
        The type of aspect detected.
    exact_angle : float
        The exact angle for this aspect type.
    actual_angle : float
        The actual angular separation between the two bodies.
    orb : float
        The difference between actual_angle and exact_angle (always >= 0).
    is_applying : bool | None
        Whether the aspect is applying (True) or separating (False).
        None if speed data not available.
    """

    planet1: str
    planet2: str
    aspect_type: AspectType
    exact_angle: float
    actual_angle: float
    orb: float
    is_applying: bool | None = None


def normalize_angle(angle: float) -> float:
    """Normalize an angle to the range [0, 360).

    >>> normalize_angle(370.0)
    10.0
    >>> normalize_angle(-10.0)
    350.0
    >>> normalize_angle(0.0)
    0.0
    """
    angle = angle % 360
    if angle < 0:
        angle += 360
    return angle


def angular_separation(degree1: float, degree2: float) -> float:
    """Calculate the shortest angular separation between two ecliptic positions.

    The result is always in the range [0, 180].

    >>> angular_separation(10.0, 190.0)
    180.0
    >>> angular_separation(350.0, 10.0)
    20.0
    >>> angular_separation(0.0, 0.0)
    0.0
    """
    d1 = normalize_angle(degree1)
    d2 = normalize_angle(degree2)
    diff = abs(d1 - d2)
    if diff > 180:
        diff = 360 - diff
    return round(diff, 4)


def find_aspect(
    degree1: float,
    degree2: float,
    orbs: dict[AspectType, float] | None = None,
    aspect_types: frozenset[AspectType] | None = None,
) -> Aspect | None:
    """Find the closest aspect (if any) between two ecliptic longitudes.

    Parameters
    ----------
    degree1 : float
        Ecliptic longitude of the first body (0-360).
    degree2 : float
        Ecliptic longitude of the second body (0-360).
    orbs : dict | None
        Custom orb tolerances. Uses DEFAULT_ORBS if None.
    aspect_types : frozenset | None
        Which aspect types to check. Checks all if None.

    Returns
    -------
    Aspect | None
        The closest matching aspect within orb, or None if no aspect found.
    """
    if orbs is None:
        orbs = DEFAULT_ORBS

    if aspect_types is None:
        aspect_types = frozenset(AspectType)

    separation = angular_separation(degree1, degree2)

    best_aspect: Aspect | None = None
    best_orb = float("inf")

    for aspect_type in aspect_types:
        if aspect_type not in orbs:
            continue

        target_angle = ASPECT_ANGLES[aspect_type]
        max_orb = orbs[aspect_type]
        current_orb = abs(separation - target_angle)

        if current_orb <= max_orb and current_orb < best_orb:
            best_orb = current_orb
            best_aspect = Aspect(
                planet1="",  # Caller fills in planet names
                planet2="",
                aspect_type=aspect_type,
                exact_angle=target_angle,
                actual_angle=separation,
                orb=round(current_orb, 4),
            )

    return best_aspect


def calculate_aspects(
    positions: dict[str, float],
    orbs: dict[AspectType, float] | None = None,
    include_minor: bool = True,
) -> list[Aspect]:
    """Calculate all aspects between a set of planetary positions.

    Parameters
    ----------
    positions : dict[str, float]
        Mapping of planet name to ecliptic longitude (0-360).
        Example: {"Sun": 355.0, "Moon": 120.5, "Mercury": 340.0}
    orbs : dict | None
        Custom orb tolerances. Uses DEFAULT_ORBS if None.
    include_minor : bool
        Whether to include minor aspects (default True).

    Returns
    -------
    list[Aspect]
        All detected aspects, sorted by orb (tightest first).
    """
    if orbs is None:
        orbs = DEFAULT_ORBS

    aspect_types: frozenset[AspectType]
    if include_minor:
        aspect_types = frozenset(AspectType)
    else:
        aspect_types = MAJOR_ASPECTS

    planets = list(positions.keys())
    aspects: list[Aspect] = []

    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1 = planets[i]
            p2 = planets[j]
            d1 = positions[p1]
            d2 = positions[p2]

            result = find_aspect(d1, d2, orbs=orbs, aspect_types=aspect_types)
            if result is not None:
                # Fill in planet names
                aspect = Aspect(
                    planet1=p1,
                    planet2=p2,
                    aspect_type=result.aspect_type,
                    exact_angle=result.exact_angle,
                    actual_angle=result.actual_angle,
                    orb=result.orb,
                    is_applying=result.is_applying,
                )
                aspects.append(aspect)

    # Sort by tightness of orb (tightest first)
    aspects.sort(key=lambda a: a.orb)
    return aspects


def is_aspect_applying(
    degree1: float,
    degree2: float,
    speed1: float,
    speed2: float,
    aspect_angle: float,
) -> bool:
    """Determine if an aspect is applying (getting tighter) or separating.

    An aspect is applying when the angular separation is moving toward
    the exact aspect angle.

    Parameters
    ----------
    degree1, degree2 : float
        Current ecliptic longitudes.
    speed1, speed2 : float
        Daily motion in degrees (positive = direct, negative = retrograde).
    aspect_angle : float
        The exact angle of the aspect (e.g., 120 for trine).

    Returns
    -------
    bool
        True if applying, False if separating.
    """
    current_sep = angular_separation(degree1, degree2)

    # Project positions forward by a small amount (0.01 day)
    future1 = degree1 + speed1 * 0.01
    future2 = degree2 + speed2 * 0.01
    future_sep = angular_separation(future1, future2)

    # If the separation is moving toward the aspect angle, it's applying
    current_diff = abs(current_sep - aspect_angle)
    future_diff = abs(future_sep - aspect_angle)

    return future_diff < current_diff


def filter_aspects_by_type(
    aspects: list[Aspect],
    major_only: bool = False,
    minor_only: bool = False,
) -> list[Aspect]:
    """Filter a list of aspects by major/minor classification.

    Parameters
    ----------
    aspects : list[Aspect]
        The aspects to filter.
    major_only : bool
        If True, return only major aspects.
    minor_only : bool
        If True, return only minor aspects.

    Returns
    -------
    list[Aspect]
        Filtered list of aspects.
    """
    if major_only and minor_only:
        return []  # Contradictory — return nothing

    if major_only:
        return [a for a in aspects if a.aspect_type in MAJOR_ASPECTS]
    if minor_only:
        return [a for a in aspects if a.aspect_type in MINOR_ASPECTS]
    return list(aspects)


def aspect_strength(orb: float, max_orb: float) -> float:
    """Calculate the strength of an aspect based on its orb.

    Returns a value from 0.0 (at max orb) to 1.0 (exact aspect).

    Parameters
    ----------
    orb : float
        The actual orb in degrees.
    max_orb : float
        The maximum orb allowed for this aspect type.

    Returns
    -------
    float
        Strength from 0.0 to 1.0.

    >>> aspect_strength(0.0, 8.0)
    1.0
    >>> aspect_strength(4.0, 8.0)
    0.5
    >>> aspect_strength(8.0, 8.0)
    0.0
    """
    if max_orb <= 0:
        return 1.0 if orb == 0 else 0.0
    strength = max(0.0, 1.0 - (orb / max_orb))
    return round(strength, 4)

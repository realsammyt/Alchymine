"""Astrological chart engine — Swiss Ephemeris integration.

Public API:
    calculate_natal_chart       — Full natal chart calculation
    approximate_sun_sign        — Date-based sun sign approximation
    approximate_sun_degree      — Approximate ecliptic longitude
    approximate_ascendant       — Rising sign approximation
    calculate_house_cusps       — House cusp calculation
    HouseSystem                 — House system enum

    calculate_aspects           — Natal aspect calculation
    find_aspect                 — Single aspect detection
    angular_separation          — Angular distance between two positions
    AspectType                  — Aspect type enum
    Aspect                      — Aspect dataclass

    get_transit_overlay          — Full transit overlay
    calculate_transit_aspects    — Transit-to-natal aspects
    get_current_positions        — Current planetary positions
    approximate_planet_longitude — Single planet position
    TransitAspect                — Transit aspect dataclass
"""

from .aspects import (
    Aspect,
    AspectType,
    MAJOR_ASPECTS,
    MINOR_ASPECTS,
    angular_separation,
    aspect_strength,
    calculate_aspects,
    filter_aspects_by_type,
    find_aspect,
    normalize_angle,
)
from .chart import (
    HouseSystem,
    approximate_ascendant,
    approximate_sun_degree,
    approximate_sun_sign,
    calculate_house_cusps,
    calculate_natal_chart,
)
from .transits import (
    TransitAspect,
    approximate_planet_longitude,
    calculate_transit_aspects,
    get_current_positions,
    get_transit_overlay,
    summarize_transits,
)

__all__ = [
    # Chart
    "calculate_natal_chart",
    "approximate_sun_sign",
    "approximate_sun_degree",
    "approximate_ascendant",
    "calculate_house_cusps",
    "HouseSystem",
    # Aspects
    "calculate_aspects",
    "find_aspect",
    "angular_separation",
    "normalize_angle",
    "aspect_strength",
    "filter_aspects_by_type",
    "AspectType",
    "Aspect",
    "MAJOR_ASPECTS",
    "MINOR_ASPECTS",
    # Transits
    "get_transit_overlay",
    "calculate_transit_aspects",
    "get_current_positions",
    "approximate_planet_longitude",
    "summarize_transits",
    "TransitAspect",
]

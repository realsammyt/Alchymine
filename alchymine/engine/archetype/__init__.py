"""Jungian archetype mapping engine.

Public API:
    map_archetype          — Map inputs to an ArchetypeProfile
    get_archetype_scores   — Expose raw scores for debugging
    ArchetypeDefinition    — Dataclass for archetype metadata
    ARCHETYPE_DEFINITIONS  — Registry of all 12 definitions
"""

from .definitions import ARCHETYPE_DEFINITIONS, ArchetypeDefinition
from .mapper import get_archetype_scores, map_archetype

__all__ = [
    "ARCHETYPE_DEFINITIONS",
    "ArchetypeDefinition",
    "get_archetype_scores",
    "map_archetype",
]

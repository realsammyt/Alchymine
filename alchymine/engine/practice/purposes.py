"""The five purpose dimensions a practice can develop.

A purpose is a *capacity*, not a topic. The five map one-to-one onto the
five pillars, so a practice log row's purpose joins against
``outcome_metrics.system`` through :data:`PURPOSE_TO_SYSTEM` with a
lookup and no translation logic.

The mapping is validated by the schema itself rather than only by tests:
an external pack cannot rely on this repository's test suite.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# Purpose key -> pillar. Read-only at runtime so an importer cannot
# mutate the mapping the log rows are interpreted through.
PURPOSE_TO_SYSTEM: Final[MappingProxyType[str, str]] = MappingProxyType(
    {
        "self-knowledge": "intelligence",
        "steadiness": "healing",
        "stewardship": "wealth",
        "expression": "creative",
        "reframing": "perspective",
    }
)

# Human-readable definitions, surfaced next to purpose chips in the UI.
PURPOSE_DEFINITIONS: Final[MappingProxyType[str, str]] = MappingProxyType(
    {
        "self-knowledge": ("Noticing your own patterns while they are running, not afterwards."),
        "steadiness": ("Coming back to a workable baseline after something knocks you off it."),
        "stewardship": (
            "Acting well with limited resources across a longer horizon than the moment."
        ),
        "expression": ("Moving an inner impulse into an outward form somebody else could meet."),
        "reframing": (
            "Holding more than one account of the same situation without collapsing to one."
        ),
    }
)

VALID_PURPOSES: Final[frozenset[str]] = frozenset(PURPOSE_TO_SYSTEM)

# Fixed display and tie-break order. The recommender's round-robin reads
# this, so it has to be a sequence rather than the frozenset above.
PURPOSE_ORDER: Final[tuple[str, ...]] = tuple(PURPOSE_TO_SYSTEM)


def system_for_purpose(purpose: str) -> str:
    """Return the pillar a *purpose* belongs to.

    Raises
    ------
    KeyError
        If *purpose* is not one of the five. Callers hold validated
        practice data, so an unknown purpose is a programming error and
        should surface as one rather than resolving to a default pillar.
    """
    return PURPOSE_TO_SYSTEM[purpose]

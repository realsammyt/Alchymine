"""Cross-system bridge definitions (XS-01..XS-07).

Each :class:`Bridge` describes how an insight produced by one of the five
Alchymine pillars (intelligence, healing, wealth, creative, perspective)
informs a downstream pillar.  The seven bridges are static reference
data, declared as frozen dataclasses and exposed through a registry
mapping plus convenience filters.

System enum values must match the directory names under
``alchymine/engine/`` and the names used elsewhere in the codebase
(e.g. routers, frontend ``currentSystem`` props).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

# ─────────────────────────────────────────────────────────────────────────
# System enum
# ─────────────────────────────────────────────────────────────────────────

#: Canonical names of the five Alchymine systems.  Bridges may only
#: reference these as ``source_system`` or ``target_system``.
VALID_SYSTEMS: Final[frozenset[str]] = frozenset(
    {"intelligence", "healing", "wealth", "creative", "perspective"}
)

BridgeId: TypeAlias = Literal[
    "XS-01",
    "XS-02",
    "XS-03",
    "XS-04",
    "XS-05",
    "XS-06",
    "XS-07",
]


# ─────────────────────────────────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────────────────────────────────


class BridgeNotFoundError(Exception):
    """Raised when a bridge id is not present in :data:`BRIDGE_REGISTRY`."""


# ─────────────────────────────────────────────────────────────────────────
# Dataclass
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Bridge:
    """A single cross-system bridge.

    Attributes:
        id: Stable identifier in the form ``XS-NN``.
        name: Short human-readable title shown in UI cards.
        source_system: The pillar that produces the insight.
        target_system: The pillar that consumes / surfaces the insight.
        description: Long-form sentence describing what insight flows
            from ``source_system`` to ``target_system``.
        insight_keys: Tuple of field names on the source system's output
            that get surfaced in the target system.  These are stable
            keys that downstream consumers (other engines, the chat
            agent, the frontend bridge panel) can rely on.
    """

    id: str
    name: str
    source_system: str
    target_system: str
    description: str
    insight_keys: tuple[str, ...]


# ─────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────

# Bridge content is sourced from
# ``docs/superpowers/plans/2026-03-10-track-1-healing-skills-cross-system-ux.md``
# (Sprint 3, Task 3.1).  ``insight_keys`` are derived from each bridge's
# stated mechanism — they name the source-system fields that the target
# system pulls in to personalize its output.
BRIDGE_REGISTRY: Final[dict[BridgeId, Bridge]] = {
    "XS-01": Bridge(
        id="XS-01",
        name="Healing Primes Perspective",
        source_system="healing",
        target_system="perspective",
        description=(
            "Breathwork and somatic work soften rigid thinking patterns, "
            "making Kegan stage transitions more accessible."
        ),
        insight_keys=("regulation_state", "somatic_readiness"),
    ),
    "XS-02": Bridge(
        id="XS-02",
        name="Numerology Selects Modality",
        source_system="intelligence",
        target_system="healing",
        description=(
            "Your Life Path number has strong affinity with specific "
            "healing traditions. The engine pre-selects modalities "
            "aligned to your number."
        ),
        insight_keys=("life_path_number", "archetype_affinity"),
    ),
    "XS-03": Bridge(
        id="XS-03",
        name="Financial Stress Routes to Somatic Release",
        source_system="wealth",
        target_system="healing",
        description=(
            "Money anxiety activates the same stress circuits as physical "
            "threat. Somatic and breathwork practices directly address "
            "wealth-related cortisol."
        ),
        insight_keys=("financial_stress_score", "anxiety_indicators"),
    ),
    "XS-04": Bridge(
        id="XS-04",
        name="Creative Expression Heals",
        source_system="creative",
        target_system="healing",
        description=(
            "Expressive healing modalities use art, movement, and writing "
            "to access pre-verbal experience — the same materials your "
            "Creative system works with."
        ),
        insight_keys=("expression_modes", "creative_themes"),
    ),
    "XS-05": Bridge(
        id="XS-05",
        name="Kegan Stage Unlocks Money Mindset",
        source_system="perspective",
        target_system="wealth",
        description=(
            "Stage 4 development (self-authoring) is the psychological "
            "prerequisite for the generative wealth mindset. Perspective "
            "work directly enables wealth expansion."
        ),
        insight_keys=("kegan_stage", "self_authoring_score"),
    ),
    "XS-06": Bridge(
        id="XS-06",
        name="Healed Expression Flows",
        source_system="healing",
        target_system="creative",
        description=(
            "Clearing somatic blocks through healing practices removes "
            "the psychological censorship that suppresses creative output."
        ),
        insight_keys=("regulation_state", "inhibition_level"),
    ),
    "XS-07": Bridge(
        id="XS-07",
        name="Archetype Shapes Stage Pathway",
        source_system="intelligence",
        target_system="perspective",
        description=(
            "Your Jungian archetype has natural affinity with specific "
            "Kegan developmental stages. Intelligence data fast-tracks "
            "your perspective growth path."
        ),
        insight_keys=("archetype", "life_path_number"),
    ),
}


# ─────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────


def get_bridge(bridge_id: str) -> Bridge:
    """Return the bridge with the given id.

    Args:
        bridge_id: Bridge identifier (e.g. ``"XS-01"``).

    Returns:
        The matching :class:`Bridge`.

    Raises:
        BridgeNotFoundError: if ``bridge_id`` is not in the registry.
    """
    try:
        return BRIDGE_REGISTRY[bridge_id]  # type: ignore[index]
    except KeyError as exc:
        raise BridgeNotFoundError(f"Unknown bridge id: {bridge_id}") from exc


def list_bridges() -> tuple[Bridge, ...]:
    """Return all bridges in stable id order (XS-01 first, XS-07 last)."""
    return tuple(BRIDGE_REGISTRY[bid] for bid in sorted(BRIDGE_REGISTRY.keys()))


def list_bridges_from(source_system: str) -> tuple[Bridge, ...]:
    """Return all bridges whose ``source_system`` matches, in id order."""
    return tuple(b for b in list_bridges() if b.source_system == source_system)


def list_bridges_to(target_system: str) -> tuple[Bridge, ...]:
    """Return all bridges whose ``target_system`` matches, in id order."""
    return tuple(b for b in list_bridges() if b.target_system == target_system)

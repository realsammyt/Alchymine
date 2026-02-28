"""Crew registry — spoke layer of the hub-and-spoke architecture.

Provides 5 system crews with 28 total domain agents:
    - Intelligence (6 agents)
    - Healing (6 agents)
    - Wealth (6 agents)
    - Creative (5 agents)
    - Perspective (5 agents)

Public API:
    get_crew(system)       — Get a single crew by system name.
    get_all_crews()        — Get all 5 system crews.
    CREW_BUILDERS          — Registry of system name -> crew builder function.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import AgentRole, AgentTask, DomainAgent, SystemCrew
from .creative import build_creative_crew
from .healing import build_healing_crew
from .intelligence import build_intelligence_crew
from .perspective import build_perspective_crew
from .wealth import build_wealth_crew

# ─── Crew builder registry ─────────────────────────────────────────

CREW_BUILDERS: dict[str, Callable[[], SystemCrew]] = {
    "intelligence": build_intelligence_crew,
    "healing": build_healing_crew,
    "wealth": build_wealth_crew,
    "creative": build_creative_crew,
    "perspective": build_perspective_crew,
}

VALID_SYSTEMS = frozenset(CREW_BUILDERS.keys())


def get_crew(system: str) -> SystemCrew:
    """Get the crew for a given system.

    Parameters
    ----------
    system:
        The system name — "intelligence", "healing", "wealth",
        "creative", or "perspective".

    Returns
    -------
    SystemCrew
        The assembled crew with all agents and tasks.

    Raises
    ------
    ValueError
        If the system name is not recognised.
    """
    if system not in CREW_BUILDERS:
        raise ValueError(
            f"Unknown system '{system}'. Valid systems: {', '.join(sorted(VALID_SYSTEMS))}"
        )
    return CREW_BUILDERS[system]()


def get_all_crews() -> dict[str, SystemCrew]:
    """Get all system crews.

    Returns
    -------
    dict[str, SystemCrew]
        Mapping of system name to assembled SystemCrew.
    """
    return {system: builder() for system, builder in CREW_BUILDERS.items()}


__all__ = [
    # Base abstractions
    "AgentRole",
    "AgentTask",
    "DomainAgent",
    "SystemCrew",
    # Registry
    "CREW_BUILDERS",
    "VALID_SYSTEMS",
    "get_crew",
    "get_all_crews",
    # Crew builders
    "build_intelligence_crew",
    "build_healing_crew",
    "build_wealth_crew",
    "build_creative_crew",
    "build_perspective_crew",
]

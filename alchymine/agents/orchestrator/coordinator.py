"""System coordinators — one per Alchymine pillar.

Each coordinator wraps the corresponding engine module, invokes the
right calculations, runs quality gate validation, and returns a
uniform CoordinatorResult. Coordinators handle ImportError and
runtime exceptions gracefully so the orchestrator can continue with
the remaining systems when one is unavailable (degraded mode).

Since issue #27 the five concrete coordinators delegate their
``_execute`` logic to LangGraph StateGraphs defined in
``alchymine.agents.orchestrator.graphs``. The public ``process()``
contract (via ``BaseCoordinator``) is unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .graphs import (
    CoordinatorState,
    build_creative_graph,
    build_healing_graph,
    build_intelligence_graph,
    build_perspective_graph,
    build_wealth_graph,
)

logger = logging.getLogger(__name__)


# ─── Coordinator status ──────────────────────────────────────────────


class CoordinatorStatus(StrEnum):
    """Status of a coordinator's processing result."""

    SUCCESS = "success"
    ERROR = "error"
    DEGRADED = "degraded"


# ─── Coordinator result ──────────────────────────────────────────────


@dataclass
class CoordinatorResult:
    """Uniform result from any system coordinator.

    Attributes
    ----------
    system:
        Name of the system that produced this result.
    status:
        Processing status (success / error / degraded).
    data:
        The output data dictionary from the engine.
    errors:
        Error messages collected during processing.
    quality_passed:
        Whether the quality gate passed for this output.
    """

    system: str
    status: str  # CoordinatorStatus value
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    quality_passed: bool = True


# ─── Base coordinator ────────────────────────────────────────────────


class BaseCoordinator:
    """Abstract base for system coordinators.

    Subclasses must implement ``_execute`` to perform the actual
    engine calls. The public ``process`` method wraps ``_execute``
    in error handling and quality gate validation.
    """

    system_name: str = "base"

    async def process(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        """Process a request through this system's coordinator.

        Parameters
        ----------
        user_id:
            The user's profile identifier.
        request_data:
            Request-specific data to pass to the engine.

        Returns
        -------
        CoordinatorResult
            The result with status, data, errors, and quality flag.
        """
        try:
            result = await self._execute(user_id, request_data)

            # Run quality gate validation
            quality_result = self._run_quality_gate(result.data)
            result.quality_passed = quality_result

            if not quality_result:
                if result.status == CoordinatorStatus.SUCCESS.value:
                    result.status = CoordinatorStatus.DEGRADED.value
                result.errors.append(f"Quality gate validation failed for {self.system_name}")

            return result

        except Exception as exc:
            logger.exception(
                "Coordinator %s failed for user %s: %s",
                self.system_name,
                user_id,
                exc,
            )
            return CoordinatorResult(
                system=self.system_name,
                status=CoordinatorStatus.ERROR.value,
                data={},
                errors=[f"{self.system_name} coordinator error: {exc!s}"],
                quality_passed=False,
            )

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        """Execute the system-specific logic.

        Subclasses must override this method.

        Parameters
        ----------
        user_id:
            The user's profile identifier.
        request_data:
            Request-specific data.

        Returns
        -------
        CoordinatorResult
            The processing result before quality gate validation.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement _execute")

    def _run_quality_gate(self, output: dict) -> bool:
        """Run the quality gate for this system's output.

        Default implementation uses the quality gate dispatcher.
        Systems without a dedicated gate (e.g. intelligence) return True.

        Parameters
        ----------
        output:
            The output data dictionary to validate.

        Returns
        -------
        bool
            True if the quality gate passed, False otherwise.
        """
        try:
            from alchymine.agents.quality.validators import run_quality_gate

            gate_result = run_quality_gate(output, system=self.system_name)
            return gate_result.passed
        except ValueError:
            # No quality gate registered for this system — pass by default
            return True
        except Exception as exc:
            logger.warning("Quality gate error for %s: %s", self.system_name, exc)
            return True


# ─── Graph-based coordinator mixin ──────────────────────────────────


class _GraphCoordinatorMixin:
    """Shared helper for graph-backed coordinators.

    Builds a ``CoordinatorState`` from the public API arguments,
    invokes the compiled graph, and converts the final state back
    to a ``CoordinatorResult``.
    """

    _graph: Any  # CompiledStateGraph or _SequentialGraph

    def _invoke_graph(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        """Run the system graph and return a CoordinatorResult."""
        initial_state: CoordinatorState = {
            "user_id": user_id,
            "request_data": request_data,
            "results": {},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        final_state = self._graph.invoke(initial_state)
        return CoordinatorResult(
            system=getattr(self, "system_name", "unknown"),
            status=final_state.get("status", "success"),
            data=final_state.get("results", {}),
            errors=list(final_state.get("errors", [])),
            quality_passed=final_state.get("quality_passed", True),
        )


# ─── Intelligence coordinator ────────────────────────────────────────


class IntelligenceCoordinator(_GraphCoordinatorMixin, BaseCoordinator):
    """Coordinator for the Personalized Intelligence system.

    Handles numerology, astrology, archetype, and personality
    calculations. Delegates processing to an Intelligence StateGraph.
    """

    system_name = "intelligence"

    def __init__(self) -> None:
        self._graph = build_intelligence_graph(include_quality_gate=False)

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        return self._invoke_graph(user_id, request_data)


# ─── Healing coordinator ─────────────────────────────────────────────


class HealingCoordinator(_GraphCoordinatorMixin, BaseCoordinator):
    """Coordinator for the Ethical Healing system.

    Handles modality matching, breathwork patterns, and crisis
    detection. Delegates processing to a Healing StateGraph.

    Before invoking the graph, the coordinator pre-loads the user's
    IdentityProfile from the database and merges any available
    enrichment fields (archetype, big_five, life_path, etc.) into
    ``request_data``.  Existing keys are never overwritten, so callers
    that already supply enrichment data take precedence.
    """

    system_name = "healing"

    def __init__(self) -> None:
        self._graph = build_healing_graph(include_quality_gate=False)

    async def _load_identity_profile(self, user_id: str) -> Any:
        """Load the user's IdentityProfile from the database."""
        try:
            from alchymine.db import repository
            from alchymine.db.base import get_async_engine, get_async_session_factory

            engine = get_async_engine()
            factory = get_async_session_factory(engine)
            async with factory() as session:
                user = await repository.get_profile(session, user_id)
                return user.identity if user else None
        except Exception as exc:
            logger.warning(
                "Healing: failed to load identity profile for %s: %s",
                user_id,
                exc,
            )
            return None

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        identity = await self._load_identity_profile(user_id)
        if identity is not None:
            from alchymine.api.routers.profile import _extract_identity_enrichment

            enrichment = _extract_identity_enrichment(identity)
            for key, val in enrichment.items():
                if key not in request_data:
                    request_data[key] = val
        return self._invoke_graph(user_id, request_data)


# ─── Wealth coordinator ──────────────────────────────────────────────


class WealthCoordinator(_GraphCoordinatorMixin, BaseCoordinator):
    """Coordinator for the Generational Wealth system.

    Handles wealth archetype mapping, lever prioritisation, debt
    strategies, and activation plans. All calculations are
    deterministic. Delegates processing to a Wealth StateGraph.
    """

    system_name = "wealth"

    def __init__(self) -> None:
        self._graph = build_wealth_graph(include_quality_gate=False)

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        return self._invoke_graph(user_id, request_data)


# ─── Creative coordinator ────────────────────────────────────────────


class CreativeCoordinator(_GraphCoordinatorMixin, BaseCoordinator):
    """Coordinator for the Creative Development system.

    Handles Guilford assessment, Creative DNA, style analysis,
    and project suggestions. Delegates processing to a Creative
    StateGraph.
    """

    system_name = "creative"

    def __init__(self) -> None:
        self._graph = build_creative_graph(include_quality_gate=False)

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        return self._invoke_graph(user_id, request_data)


# ─── Perspective coordinator ─────────────────────────────────────────


class PerspectiveCoordinator(_GraphCoordinatorMixin, BaseCoordinator):
    """Coordinator for the Perspective Enhancement system.

    Handles decision frameworks, bias detection, Kegan stage
    assessment, and scenario modelling. Delegates processing to a
    Perspective StateGraph.
    """

    system_name = "perspective"

    def __init__(self) -> None:
        self._graph = build_perspective_graph(include_quality_gate=False)

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        return self._invoke_graph(user_id, request_data)

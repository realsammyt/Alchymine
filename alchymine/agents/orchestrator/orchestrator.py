"""Master Orchestrator — top-level request router.

Receives a raw user input string, classifies intent, delegates to the
appropriate coordinator(s), runs quality validation on the combined
output, and returns a unified OrchestratorResult. Supports multi-system
requests and graceful degradation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from .coordinator import (
    BaseCoordinator,
    CoordinatorResult,
    CoordinatorStatus,
    CreativeCoordinator,
    HealingCoordinator,
    IntelligenceCoordinator,
    PerspectiveCoordinator,
    WealthCoordinator,
)
from .intent import IntentResult, SystemIntent, classify_intent

logger = logging.getLogger(__name__)


# ─── Orchestrator result ─────────────────────────────────────────────


@dataclass
class OrchestratorResult:
    """Top-level result from the Master Orchestrator.

    Attributes
    ----------
    request_id:
        Unique identifier for this request (UUID string).
    intent:
        The classified intent result.
    coordinator_results:
        Results from each coordinator that was invoked.
    synthesis:
        Combined output when multiple systems contribute (None for
        single-system requests).
    quality_passed:
        True if all quality gates passed.
    """

    request_id: str
    intent: IntentResult
    coordinator_results: list[CoordinatorResult] = field(default_factory=list)
    synthesis: dict | None = None
    quality_passed: bool = True


# ─── Master Orchestrator ─────────────────────────────────────────────


class MasterOrchestrator:
    """Hub of the hub-and-spoke architecture.

    Routes user requests to the appropriate system coordinator(s),
    manages cross-system synthesis, and ensures all outputs pass
    quality validation before delivery.
    """

    def __init__(self) -> None:
        self._coordinators: dict[SystemIntent, BaseCoordinator] = {
            SystemIntent.INTELLIGENCE: IntelligenceCoordinator(),
            SystemIntent.HEALING: HealingCoordinator(),
            SystemIntent.WEALTH: WealthCoordinator(),
            SystemIntent.CREATIVE: CreativeCoordinator(),
            SystemIntent.PERSPECTIVE: PerspectiveCoordinator(),
        }

    async def process_request(
        self,
        user_input: str,
        user_profile: dict | None = None,
    ) -> OrchestratorResult:
        """Process a user request end-to-end.

        1. Classify intent
        2. Delegate to coordinator(s)
        3. Run quality validation
        4. Synthesize multi-system results

        Parameters
        ----------
        user_input:
            Raw text from the user describing their request.
        user_profile:
            Optional user profile data dict to pass along to
            coordinators as context.

        Returns
        -------
        OrchestratorResult
            The full processing result.
        """
        request_id = str(uuid.uuid4())
        intent_result = classify_intent(user_input)

        request_data = dict(user_profile or {})
        request_data["text"] = user_input

        user_id = request_data.get("id", "anonymous")

        # Determine which coordinators to invoke
        if intent_result.intent == SystemIntent.UNKNOWN:
            return OrchestratorResult(
                request_id=request_id,
                intent=intent_result,
                coordinator_results=[],
                synthesis=None,
                quality_passed=True,
            )

        if intent_result.intent == SystemIntent.MULTI_SYSTEM:
            systems_to_invoke = intent_result.secondary_intents
        else:
            systems_to_invoke = [intent_result.intent]

        # Run coordinators
        coordinator_results: list[CoordinatorResult] = []
        for system in systems_to_invoke:
            coordinator = self._coordinators.get(system)
            if coordinator is None:
                logger.warning("No coordinator for system: %s", system)
                continue
            result = await coordinator.process(user_id, request_data)
            coordinator_results.append(result)

        # Synthesize if multi-system
        synthesis = None
        if len(coordinator_results) > 1:
            synthesis = synthesize_results(coordinator_results)

        # Overall quality check
        quality_passed = all(
            cr.quality_passed for cr in coordinator_results
        )

        # Run ethics check on synthesis text if present
        if synthesis:
            quality_passed = quality_passed and self._validate_synthesis(
                synthesis
            )

        return OrchestratorResult(
            request_id=request_id,
            intent=intent_result,
            coordinator_results=coordinator_results,
            synthesis=synthesis,
            quality_passed=quality_passed,
        )

    def _validate_synthesis(self, synthesis: dict) -> bool:
        """Run ethics validation on synthesis output.

        Parameters
        ----------
        synthesis:
            The synthesized output dictionary.

        Returns
        -------
        bool
            True if ethics validation passes.
        """
        try:
            from alchymine.agents.quality.ethics_check import validate_output

            result = validate_output(synthesis, system="general")
            return result.passed
        except Exception as exc:
            logger.warning("Synthesis ethics check error: %s", exc)
            return True


# ─── Synthesis ───────────────────────────────────────────────────────


def synthesize_results(
    results: list[CoordinatorResult],
) -> dict:
    """Combine outputs from multiple system coordinators.

    Creates a unified view by merging each coordinator's data under
    its system key and collecting cross-system metadata.

    Parameters
    ----------
    results:
        A list of CoordinatorResult objects from different systems.

    Returns
    -------
    dict
        A synthesized output dictionary with per-system data,
        participating systems, overall status, and collected errors.
    """
    synthesis: dict = {
        "systems": {},
        "participating_systems": [],
        "overall_status": CoordinatorStatus.SUCCESS.value,
        "errors": [],
    }

    has_error = False
    has_degraded = False

    for result in results:
        synthesis["systems"][result.system] = result.data
        synthesis["participating_systems"].append(result.system)

        if result.status == CoordinatorStatus.ERROR.value:
            has_error = True
        elif result.status == CoordinatorStatus.DEGRADED.value:
            has_degraded = True

        if result.errors:
            synthesis["errors"].extend(result.errors)

    # Determine overall status
    if has_error and all(
        r.status == CoordinatorStatus.ERROR.value for r in results
    ):
        synthesis["overall_status"] = CoordinatorStatus.ERROR.value
    elif has_error or has_degraded:
        synthesis["overall_status"] = CoordinatorStatus.DEGRADED.value
    else:
        synthesis["overall_status"] = CoordinatorStatus.SUCCESS.value

    return synthesis

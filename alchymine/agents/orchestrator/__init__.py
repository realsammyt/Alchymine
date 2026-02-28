"""Master Orchestrator — hub-and-spoke routing for Alchymine's five systems.

Routes user requests to the appropriate system coordinator(s), manages
cross-system synthesis, and ensures all outputs pass quality validation.

Architecture:
    MasterOrchestrator
      -> classify_intent (keyword-based, deterministic)
      -> delegate to coordinator(s)
         - IntelligenceCoordinator (numerology, astrology, archetype, personality)
         - HealingCoordinator (breathwork, modalities, crisis)
         - WealthCoordinator (archetype, debt, levers, plan)
         - CreativeCoordinator (assessment, style, projects)
         - PerspectiveCoordinator (frameworks, biases, kegan, scenarios)
      -> quality gate validation
      -> synthesize (for multi-system requests)
"""

from .coordinator import (
    BaseCoordinator,
    CoordinatorResult,
    CreativeCoordinator,
    HealingCoordinator,
    IntelligenceCoordinator,
    PerspectiveCoordinator,
    WealthCoordinator,
)
from .intent import (
    IntentResult,
    SystemIntent,
    classify_intent,
)
from .orchestrator import (
    MasterOrchestrator,
    OrchestratorResult,
)
from .synthesis import (
    SynthesisResult,
    aggregate_evidence,
    detect_conflicts,
    synthesize_full_profile,
    synthesize_guided_session,
)

__all__ = [
    # Intent
    "SystemIntent",
    "IntentResult",
    "classify_intent",
    # Coordinators
    "CoordinatorResult",
    "BaseCoordinator",
    "IntelligenceCoordinator",
    "HealingCoordinator",
    "WealthCoordinator",
    "CreativeCoordinator",
    "PerspectiveCoordinator",
    # Orchestrator
    "MasterOrchestrator",
    "OrchestratorResult",
    # Synthesis
    "SynthesisResult",
    "synthesize_full_profile",
    "synthesize_guided_session",
    "detect_conflicts",
    "aggregate_evidence",
]

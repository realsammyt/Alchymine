"""Quality Swarm — ethics validation and quality gate pipeline.

All outputs pass through Quality Swarm validation before delivery.
This package provides:
    - Ethics checking (fatalistic language, diagnostic language, dark patterns, etc.)
    - Quality gate validators (healing, wealth, creative output validation)
"""

from .ethics_check import (
    EthicsCheckResult,
    EthicsViolation,
    check_prompt,
    check_text,
    validate_output,
)
from .validators import (
    QualityGateResult,
    run_quality_gate,
    validate_creative_output,
    validate_healing_output,
    validate_wealth_output,
)

__all__ = [
    "EthicsCheckResult",
    "EthicsViolation",
    "QualityGateResult",
    "check_prompt",
    "check_text",
    "run_quality_gate",
    "validate_creative_output",
    "validate_healing_output",
    "validate_output",
    "validate_wealth_output",
]

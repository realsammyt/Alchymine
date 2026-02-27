"""Quality gate validators for system outputs.

Each Alchymine system (healing, wealth, creative, perspective) has
a dedicated validator that enforces system-specific rules in addition
to the shared ethics checks. The run_quality_gate dispatcher routes
to the appropriate validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .ethics_check import EthicsCheckResult, check_text

# ─── Quality gate result ────────────────────────────────────────────


@dataclass
class QualityGateResult:
    """Result of a quality gate validation."""

    gate_name: str
    passed: bool
    details: list[str] = field(default_factory=list)
    ethics_result: EthicsCheckResult | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ─── Healing output validator ───────────────────────────────────────


def validate_healing_output(output: dict) -> QualityGateResult:
    """Validate healing system output.

    Ensures:
    - Output contains appropriate disclaimers
    - No diagnostic language
    - Crisis resources present if crisis_flag is set
    - Modality recommendations include difficulty levels

    Parameters
    ----------
    output:
        Healing system output dictionary.

    Returns
    -------
    QualityGateResult
        Validation result with details of any issues found.
    """
    details: list[str] = []
    passed = True

    # Run ethics check on text content
    text_parts: list[str] = []
    for key in ("text", "content", "description", "summary", "narrative"):
        if key in output and isinstance(output[key], str):
            text_parts.append(output[key])
    combined_text = " ".join(text_parts)

    ethics_result = check_text(combined_text, context="healing") if combined_text.strip() else None

    if ethics_result is not None and not ethics_result.passed:
        passed = False
        for v in ethics_result.violations:
            details.append(f"Ethics: [{v.severity}] {v.category} — {v.description}")

    # Check disclaimers presence
    disclaimers = output.get("disclaimers", [])
    if not disclaimers:
        passed = False
        details.append("Missing: healing output must include at least one disclaimer")
    else:
        # Verify disclaimer content mentions non-medical nature
        disclaimer_text = " ".join(str(d) for d in disclaimers).lower()
        medical_disclaimer_indicators = [
            "not medical advice",
            "not a substitute for professional",
            "consult a qualified",
            "not a substitute for professional help",
            "healthcare professional",
        ]
        has_medical_disclaimer = any(
            indicator in disclaimer_text for indicator in medical_disclaimer_indicators
        )
        if not has_medical_disclaimer:
            passed = False
            details.append(
                "Missing: disclaimers must state this is not medical advice "
                "or not a substitute for professional help"
            )

    # Check crisis resources if crisis flag is set
    if output.get("crisis_flag", False):
        crisis_response = output.get("crisis_response")
        if crisis_response is None:
            passed = False
            details.append("Missing: crisis_flag is True but no crisis_response provided")
        else:
            # Check resources exist
            resources = (
                getattr(crisis_response, "resources", None)
                or crisis_response.get("resources", None)
                if isinstance(crisis_response, dict)
                else getattr(crisis_response, "resources", None)
            )
            if not resources:
                passed = False
                details.append("Missing: crisis response must include crisis resources")

    # Check recommended modalities have difficulty levels
    modalities = output.get("recommended_modalities", [])
    for mod in modalities:
        difficulty = None
        if isinstance(mod, dict):
            difficulty = mod.get("difficulty_level")
        elif hasattr(mod, "difficulty_level"):
            difficulty = mod.difficulty_level
        if difficulty is None:
            passed = False
            details.append("Missing: modality recommendation missing difficulty_level")
            break

    if not details:
        details.append("All healing quality checks passed")

    return QualityGateResult(
        gate_name="healing_quality_gate",
        passed=passed,
        details=details,
        ethics_result=ethics_result,
    )


# ─── Wealth output validator ───────────────────────────────────────


def validate_wealth_output(output: dict) -> QualityGateResult:
    """Validate wealth system output.

    Ensures:
    - Financial outputs are deterministic (not LLM-generated)
    - Contains appropriate financial disclaimers
    - No guaranteed returns language
    - No specific investment advice

    Parameters
    ----------
    output:
        Wealth system output dictionary.

    Returns
    -------
    QualityGateResult
        Validation result.
    """
    details: list[str] = []
    passed = True

    # Run ethics check on text content
    text_parts: list[str] = []
    for key in ("text", "content", "description", "summary", "narrative", "recommendations"):
        val = output.get(key)
        if isinstance(val, str):
            text_parts.append(val)
        elif isinstance(val, list):
            text_parts.extend(str(item) for item in val if isinstance(item, str))
    combined_text = " ".join(text_parts)

    ethics_result = check_text(combined_text, context="wealth") if combined_text.strip() else None

    if ethics_result is not None and not ethics_result.passed:
        passed = False
        for v in ethics_result.violations:
            details.append(f"Ethics: [{v.severity}] {v.category} — {v.description}")

    # Check disclaimers presence
    disclaimers = output.get("disclaimers", [])
    if not disclaimers:
        passed = False
        details.append("Missing: wealth output must include financial disclaimers")
    else:
        disclaimer_text = " ".join(str(d) for d in disclaimers).lower()
        financial_disclaimer_indicators = [
            "not financial advice",
            "consult a qualified financial",
            "not a substitute for professional financial",
            "financial advisor",
            "for educational purposes",
            "for informational purposes",
        ]
        has_financial_disclaimer = any(
            indicator in disclaimer_text for indicator in financial_disclaimer_indicators
        )
        if not has_financial_disclaimer:
            passed = False
            details.append("Missing: disclaimers must state this is not financial advice")

    # Check determinism flag
    if "llm_generated" in output and output["llm_generated"] is True:
        passed = False
        details.append(
            "Violation: wealth calculations must be deterministic, "
            "not LLM-generated (ADR: financial data never sent to LLM)"
        )

    # Check calculations are present and numeric
    calculations = output.get("calculations", {})
    if isinstance(calculations, dict):
        for key, value in calculations.items():
            if not isinstance(value, (int, float)):
                passed = False
                details.append(
                    f"Violation: calculation '{key}' has non-numeric value — "
                    f"wealth calculations must be deterministic"
                )
                break

    if not details:
        details.append("All wealth quality checks passed")

    return QualityGateResult(
        gate_name="wealth_quality_gate",
        passed=passed,
        details=details,
        ethics_result=ethics_result,
    )


# ─── Creative output validator ─────────────────────────────────────


def validate_creative_output(output: dict) -> QualityGateResult:
    """Validate creative system output.

    Ensures:
    - Creative outputs have proper attribution for techniques/traditions
    - No cultural appropriation without attribution
    - Encourages rather than judges creative expression

    Parameters
    ----------
    output:
        Creative system output dictionary.

    Returns
    -------
    QualityGateResult
        Validation result.
    """
    details: list[str] = []
    passed = True

    # Run ethics check
    text_parts: list[str] = []
    for key in ("text", "content", "description", "summary", "narrative", "feedback"):
        val = output.get(key)
        if isinstance(val, str):
            text_parts.append(val)
        elif isinstance(val, list):
            text_parts.extend(str(item) for item in val if isinstance(item, str))
    combined_text = " ".join(text_parts)

    ethics_result = check_text(combined_text, context="creative") if combined_text.strip() else None

    if ethics_result is not None and not ethics_result.passed:
        passed = False
        for v in ethics_result.violations:
            details.append(f"Ethics: [{v.severity}] {v.category} — {v.description}")

    # Check for attribution when traditions/techniques are referenced
    traditions = output.get("traditions", [])
    techniques = output.get("techniques", [])
    attributions = output.get("attributions", [])

    if (traditions or techniques) and not attributions:
        # Check if attributions are embedded in text
        attribution_indicators = [
            "originated from",
            "tradition of",
            "developed by",
            "inspired by",
            "rooted in",
            "drawing from",
            "attribution",
            "credit",
        ]
        text_lower = combined_text.lower()
        has_attribution = any(ind in text_lower for ind in attribution_indicators)
        if not has_attribution and (traditions or techniques):
            passed = False
            details.append(
                "Missing: creative output references traditions/techniques "
                "without proper attribution"
            )

    # Check for judgmental language about creative expression
    judgmental_patterns = [
        r"\bthat'?s?\s+(?:terrible|awful|bad|wrong|stupid)\b",
        r"\byou\s+(?:can'?t|shouldn'?t)\s+(?:create|make|write|draw|compose)\b",
        r"\bno\s+talent\b",
        r"\bnot\s+creative\b",
    ]
    import re

    for pattern in judgmental_patterns:
        if re.search(pattern, combined_text, re.IGNORECASE):
            passed = False
            details.append(
                "Violation: creative feedback should encourage, not judge. "
                "Found potentially discouraging language"
            )
            break

    if not details:
        details.append("All creative quality checks passed")

    return QualityGateResult(
        gate_name="creative_quality_gate",
        passed=passed,
        details=details,
        ethics_result=ethics_result,
    )


# ─── Quality gate dispatcher ───────────────────────────────────────


def run_quality_gate(output: dict, system: str) -> QualityGateResult:
    """Dispatch to the appropriate quality gate validator.

    Parameters
    ----------
    output:
        The system output to validate.
    system:
        The system name — "healing", "wealth", "creative",
        or "perspective".

    Returns
    -------
    QualityGateResult
        Validation result from the appropriate gate.

    Raises
    ------
    ValueError
        If the system name is not recognised.
    """
    validators = {
        "healing": validate_healing_output,
        "wealth": validate_wealth_output,
        "creative": validate_creative_output,
    }

    if system not in validators:
        raise ValueError(
            f"Unknown system '{system}'. Expected one of: {', '.join(validators.keys())}"
        )

    return validators[system](output)

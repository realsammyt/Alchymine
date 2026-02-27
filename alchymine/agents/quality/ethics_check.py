"""Ethics validation pipeline for the Quality Swarm.

Scans text, prompts, and system outputs for ethics violations
including fatalistic language, diagnostic language, dark patterns,
cultural insensitivity, unqualified financial advice, and missing
disclaimers. Implements the "First, Do No Harm" principle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ─── Violation severity ─────────────────────────────────────────────


class ViolationSeverity(str, Enum):
    """Severity levels for ethics violations."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ─── Violation categories ───────────────────────────────────────────


class ViolationCategory(str, Enum):
    """Categories of ethics violations."""

    FATALISTIC_LANGUAGE = "fatalistic_language"
    DIAGNOSTIC_LANGUAGE = "diagnostic_language"
    DARK_PATTERNS = "dark_patterns"
    CULTURAL_INSENSITIVITY = "cultural_insensitivity"
    FINANCIAL_ADVICE = "financial_advice"
    MISSING_DISCLAIMER = "missing_disclaimer"


# ─── Dataclasses ────────────────────────────────────────────────────


@dataclass(frozen=True)
class EthicsViolation:
    """A single ethics violation detected in text."""

    category: str
    description: str
    severity: str  # "warning", "error", "critical"
    suggestion: str
    matched_text: str = ""


@dataclass
class EthicsCheckResult:
    """Result of an ethics check."""

    passed: bool
    violations: list[EthicsViolation] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Pattern definitions ────────────────────────────────────────────

# Each pattern group: list of (regex_pattern, description, severity, suggestion)

_FATALISTIC_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        r"\byou\s+will\s+(?:definitely|certainly|inevitably|always)\b",
        "Deterministic prediction about the user's future",
        ViolationSeverity.ERROR.value,
        "Use possibility language: 'you may', 'this could', 'one potential path'",
    ),
    (
        r"\bdestined\s+to\b",
        "Fatalistic language implying predetermined outcomes",
        ViolationSeverity.ERROR.value,
        "Replace with agency-affirming language: 'you have the potential to'",
    ),
    (
        r"\bfated\s+to\b",
        "Fatalistic language implying predetermined outcomes",
        ViolationSeverity.ERROR.value,
        "Replace with possibility language: 'you may find yourself drawn to'",
    ),
    (
        r"\byour\s+destiny\s+is\b",
        "Deterministic destiny claims",
        ViolationSeverity.ERROR.value,
        "Replace with 'your path may include' or 'one possibility is'",
    ),
    (
        r"\bthe\s+stars\s+(?:say|decree|demand|dictate|require)\b",
        "Attributing deterministic authority to astrological positions",
        ViolationSeverity.ERROR.value,
        "Use 'the astrological pattern suggests' or 'this transit may influence'",
    ),
    (
        r"\bwill\s+never\b",
        "Absolute negative prediction",
        ViolationSeverity.WARNING.value,
        "Avoid absolute predictions. Use 'may find it challenging' instead",
    ),
    (
        r"\bguaranteed\s+(?:to\s+)?(?:succeed|fail|happen)\b",
        "Guaranteed outcome language",
        ViolationSeverity.ERROR.value,
        "No outcomes are guaranteed. Use probabilistic language instead",
    ),
]

_DIAGNOSTIC_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        r"\byou\s+(?:have|suffer\s+from|are\s+diagnosed\s+with)\s+(?:a\s+)?(?:disorder|condition|syndrome|disease)\b",
        "Clinical diagnostic language",
        ViolationSeverity.CRITICAL.value,
        "Alchymine does not diagnose. Remove diagnostic language and suggest professional consultation",
    ),
    (
        r"\b(?:diagnos(?:e|ed|is|ing)|disorder|syndrome|patholog)\b",
        "Use of clinical terminology",
        ViolationSeverity.ERROR.value,
        "Replace clinical terms with descriptive language. Suggest professional consultation",
    ),
    (
        r"\bprescri(?:be|ption|bing)\b",
        "Prescription language",
        ViolationSeverity.CRITICAL.value,
        "Alchymine does not prescribe. Use 'suggest', 'recommend exploring', or 'consider'",
    ),
    (
        r"\btreatment\s+(?:plan|protocol|regimen)\b",
        "Clinical treatment language",
        ViolationSeverity.ERROR.value,
        "Use 'practice plan', 'wellness approach', or 'exploration path' instead",
    ),
    (
        r"\bcure(?:s|d)?\b",
        "Cure claims",
        ViolationSeverity.CRITICAL.value,
        "Alchymine does not cure. Use 'support', 'complement', or 'contribute to wellness'",
    ),
]

_DARK_PATTERN_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        r"\blimited\s+time\b",
        "Artificial urgency — limited time pressure",
        ViolationSeverity.CRITICAL.value,
        "Remove urgency language. Alchymine never uses time pressure tactics",
    ),
    (
        r"\bact\s+now\b",
        "Pressure tactics — act now",
        ViolationSeverity.CRITICAL.value,
        "Remove pressure language. Users should feel free to engage at their own pace",
    ),
    (
        r"\bdon'?t\s+miss\s+(?:out|this)\b",
        "FOMO manipulation — don't miss out",
        ViolationSeverity.CRITICAL.value,
        "Remove FOMO language. Information should be presented without manipulation",
    ),
    (
        r"\bonly\s+\d+\s+\w*\s*(?:left|remaining|available)\b",
        "Artificial scarcity",
        ViolationSeverity.CRITICAL.value,
        "Remove scarcity language. Alchymine does not use artificial scarcity",
    ),
    (
        r"\byou'?(?:ll|re)\s+(?:missing|losing)\s+out\b",
        "Loss aversion manipulation",
        ViolationSeverity.ERROR.value,
        "Remove loss aversion language. Present benefits without fear of missing out",
    ),
    (
        r"\bexclusive\s+offer\b",
        "Artificial exclusivity",
        ViolationSeverity.ERROR.value,
        "Remove artificial exclusivity. Present offerings transparently",
    ),
]

_CULTURAL_INSENSITIVITY_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        r"\bspirit\s+animal\b",
        "Appropriation of Indigenous spiritual concept without context",
        ViolationSeverity.ERROR.value,
        "Use 'archetype' or provide proper attribution to the specific Indigenous tradition",
    ),
    (
        r"\btribe\b(?!\s+(?:of\s+)?(?:judah|israel|benjamin))",
        "Casual use of 'tribe' appropriating Indigenous identity",
        ViolationSeverity.WARNING.value,
        "Use 'community', 'group', or 'circle' instead of 'tribe'",
    ),
    (
        r"\bshaman(?:ic|ism)?\b",
        "Use of 'shaman' without proper cultural attribution",
        ViolationSeverity.WARNING.value,
        "Specify the tradition (e.g., 'Siberian shamanic tradition') or use 'practitioner'",
    ),
    (
        r"\bguru\b(?!\s+(?:nanak|granth))",
        "Casual use of 'guru' outside its spiritual context",
        ViolationSeverity.WARNING.value,
        "Use 'teacher', 'mentor', or 'guide' unless referring to a specific tradition",
    ),
]

_FINANCIAL_ADVICE_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        r"\byou\s+should\s+invest\b",
        "Direct investment advice",
        ViolationSeverity.CRITICAL.value,
        "Alchymine does not give financial advice. Use 'consider exploring' or 'research options'",
    ),
    (
        r"\bguaranteed\s+returns?\b",
        "Guaranteed returns language",
        ViolationSeverity.CRITICAL.value,
        "No financial returns are guaranteed. Remove this language entirely",
    ),
    (
        r"\b(?:buy|sell|trade)\s+(?:stocks?|bonds?|crypto|bitcoin|ethereum)\b",
        "Specific investment direction",
        ViolationSeverity.CRITICAL.value,
        "Alchymine does not direct specific investments. Suggest consulting a financial advisor",
    ),
    (
        r"\brisk[- ]free\b",
        "Risk-free claims about financial products",
        ViolationSeverity.CRITICAL.value,
        "No investment is risk-free. Remove this language and include appropriate risk disclaimers",
    ),
    (
        r"\bget\s+rich\b",
        "Get-rich promises",
        ViolationSeverity.ERROR.value,
        "Remove get-rich language. Focus on sustainable wealth-building principles",
    ),
    (
        r"\bfinancial\s+freedom\s+(?:guaranteed|in\s+\d+)\b",
        "Unrealistic financial freedom promises",
        ViolationSeverity.ERROR.value,
        "Remove guaranteed financial outcome language. Focus on principles and education",
    ),
]


# ─── Scanning logic ─────────────────────────────────────────────────


def _scan_patterns(
    text: str,
    patterns: list[tuple[str, str, str, str]],
    category: str,
) -> list[EthicsViolation]:
    """Scan text against a list of regex patterns and return violations."""
    violations: list[EthicsViolation] = []
    for pattern, description, severity, suggestion in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            violations.append(
                EthicsViolation(
                    category=category,
                    description=description,
                    severity=severity,
                    suggestion=suggestion,
                    matched_text=match.group(0),
                )
            )
    return violations


def _check_missing_disclaimer(
    text: str,
    context: str,
) -> list[EthicsViolation]:
    """Check if required disclaimers are missing for specific contexts."""
    violations: list[EthicsViolation] = []

    healing_keywords = [
        "healing", "modality", "breathwork", "meditation",
        "somatic", "energy", "chakra", "wellness practice",
    ]
    financial_keywords = [
        "wealth", "investment", "financial", "portfolio",
        "savings", "retirement", "income", "lever",
    ]
    disclaimer_indicators = [
        "not a substitute", "not medical advice", "consult a",
        "professional", "disclaimer", "not financial advice",
        "for informational purposes", "for educational purposes",
    ]

    text_lower = text.lower()

    has_disclaimer = any(indicator in text_lower for indicator in disclaimer_indicators)

    if context in ("healing", "general"):
        has_healing_content = any(kw in text_lower for kw in healing_keywords)
        if has_healing_content and not has_disclaimer and len(text) > 100:
            violations.append(
                EthicsViolation(
                    category=ViolationCategory.MISSING_DISCLAIMER.value,
                    description="Healing content without appropriate disclaimer",
                    severity=ViolationSeverity.ERROR.value,
                    suggestion=(
                        "Add disclaimer: 'This is not medical advice. "
                        "Consult a qualified healthcare professional.'"
                    ),
                )
            )

    if context in ("wealth", "general"):
        has_financial_content = any(kw in text_lower for kw in financial_keywords)
        if has_financial_content and not has_disclaimer and len(text) > 100:
            violations.append(
                EthicsViolation(
                    category=ViolationCategory.MISSING_DISCLAIMER.value,
                    description="Financial content without appropriate disclaimer",
                    severity=ViolationSeverity.ERROR.value,
                    suggestion=(
                        "Add disclaimer: 'This is not financial advice. "
                        "Consult a qualified financial advisor.'"
                    ),
                )
            )

    return violations


# ─── Public API ─────────────────────────────────────────────────────


def check_text(text: str, context: str = "general") -> EthicsCheckResult:
    """Scan text for ethics violations.

    Parameters
    ----------
    text:
        The text to check.
    context:
        Context for the check — "general", "healing", "wealth",
        "creative", or "perspective". Affects which rules are applied.

    Returns
    -------
    EthicsCheckResult
        Result with passed=True if no violations, or passed=False
        with a list of violations.
    """
    if not text or not text.strip():
        return EthicsCheckResult(passed=True)

    violations: list[EthicsViolation] = []

    # Always check fatalistic language
    violations.extend(
        _scan_patterns(text, _FATALISTIC_PATTERNS, ViolationCategory.FATALISTIC_LANGUAGE.value)
    )

    # Always check diagnostic language
    violations.extend(
        _scan_patterns(text, _DIAGNOSTIC_PATTERNS, ViolationCategory.DIAGNOSTIC_LANGUAGE.value)
    )

    # Always check dark patterns
    violations.extend(
        _scan_patterns(text, _DARK_PATTERN_PATTERNS, ViolationCategory.DARK_PATTERNS.value)
    )

    # Always check cultural insensitivity
    violations.extend(
        _scan_patterns(
            text,
            _CULTURAL_INSENSITIVITY_PATTERNS,
            ViolationCategory.CULTURAL_INSENSITIVITY.value,
        )
    )

    # Always check financial advice
    violations.extend(
        _scan_patterns(text, _FINANCIAL_ADVICE_PATTERNS, ViolationCategory.FINANCIAL_ADVICE.value)
    )

    # Check missing disclaimers based on context
    violations.extend(_check_missing_disclaimer(text, context))

    return EthicsCheckResult(
        passed=len(violations) == 0,
        violations=violations,
    )


def check_prompt(prompt_text: str) -> EthicsCheckResult:
    """Validate a prompt template for ethics violations.

    Prompts are checked with strict rules since they shape all
    downstream outputs. Uses the "general" context to apply all checks.

    Parameters
    ----------
    prompt_text:
        The prompt template text to validate.

    Returns
    -------
    EthicsCheckResult
        Validation result.
    """
    return check_text(prompt_text, context="general")


def validate_output(output: dict, system: str) -> EthicsCheckResult:
    """Validate a system output dict for ethics violations.

    Extracts text content from the output dict and runs the
    appropriate ethics checks based on the system context.

    Parameters
    ----------
    output:
        The output dictionary to validate. Text is extracted from
        common keys: "text", "content", "description", "summary",
        "recommendations", "disclaimers".
    system:
        The system that produced the output — "healing", "wealth",
        "creative", "perspective", or "general".

    Returns
    -------
    EthicsCheckResult
        Validation result.
    """
    # Extract all text content from the output dict
    text_parts: list[str] = []
    text_keys = ["text", "content", "description", "summary", "recommendations", "narrative"]

    for key in text_keys:
        if key in output and isinstance(output[key], str):
            text_parts.append(output[key])
        elif key in output and isinstance(output[key], list):
            for item in output[key]:
                if isinstance(item, str):
                    text_parts.append(item)

    # Also check disclaimer content
    if "disclaimers" in output and isinstance(output["disclaimers"], list):
        for d in output["disclaimers"]:
            if isinstance(d, str):
                text_parts.append(d)

    combined_text = " ".join(text_parts)

    if not combined_text.strip():
        return EthicsCheckResult(passed=True)

    return check_text(combined_text, context=system)

"""Content filtering pipeline for all Alchymine system outputs.

Provides a unified safety layer that orchestrates:
- Crisis detection (from healing.crisis)
- Ethics validation (from agents.quality.ethics_check)
- System-specific quality gates (from agents.quality.validators)
- PII detection and redaction
- Output sanitization

Every system output should pass through filter_content() before
being returned to the user. This is the "First, Do No Harm" gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from alchymine.agents.quality.ethics_check import EthicsCheckResult, check_text
from alchymine.engine.healing.crisis import CrisisResponse, detect_crisis


class FilterAction(StrEnum):
    """Actions the content filter can take."""

    PASS = "pass"  # noqa: S105
    WARN = "warn"
    BLOCK = "block"
    ESCALATE = "escalate"


@dataclass
class PIIMatch:
    """A detected PII pattern in content."""

    pii_type: str
    matched_text: str
    start: int
    end: int


@dataclass
class ContentFilterResult:
    """Result of running content through the safety filter."""

    action: FilterAction
    original_text: str
    filtered_text: str
    crisis_response: CrisisResponse | None = None
    ethics_result: EthicsCheckResult | None = None
    pii_matches: list[PIIMatch] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked_reason: str | None = None


# ── PII detection patterns ─────────────────────────────────────────

_PII_PATTERNS: list[tuple[str, str]] = [
    # SSN
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
    # Credit card (basic Luhn-pattern-length matches)
    (r"\b(?:\d{4}[- ]?){3}\d{4}\b", "credit_card"),
    # Email addresses (only redact if they appear in output, not input)
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
    # Phone numbers (US format)
    (r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone"),
    # IP addresses
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "ip_address"),
]

# ── Harmful content patterns ───────────────────────────────────────

_HARMFUL_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:kill|murder|attack|harm)\s+(?:someone|people|them|others)\b", "violence_incitement"),
    (r"\b(?:illegal|illicit)\s+(?:drugs?|substances?|weapons?)\b", "illegal_activity"),
]


def _detect_pii(text: str) -> list[PIIMatch]:
    """Detect PII patterns in text."""
    matches: list[PIIMatch] = []
    for pattern, pii_type in _PII_PATTERNS:
        for match in re.finditer(pattern, text):
            matches.append(
                PIIMatch(
                    pii_type=pii_type,
                    matched_text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
            )
    return matches


def _redact_pii(text: str, pii_matches: list[PIIMatch]) -> str:
    """Replace detected PII with redaction markers."""
    if not pii_matches:
        return text

    # Sort by position descending to avoid offset issues
    sorted_matches = sorted(pii_matches, key=lambda m: m.start, reverse=True)
    result = text
    for match in sorted_matches:
        redacted = f"[REDACTED:{match.pii_type.upper()}]"
        result = result[: match.start] + redacted + result[match.end :]
    return result


def _check_harmful_content(text: str) -> list[str]:
    """Check for harmful content patterns."""
    warnings: list[str] = []
    text_lower = text.lower()
    for pattern, category in _HARMFUL_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            warnings.append(f"Harmful content detected: {category}")
    return warnings


# ── Public API ─────────────────────────────────────────────────────


def filter_content(
    text: str,
    context: str = "general",
    redact_pii: bool = True,
    check_crisis: bool = True,
) -> ContentFilterResult:
    """Run text through the full content safety pipeline.

    Parameters
    ----------
    text:
        The text content to filter.
    context:
        System context — "general", "healing", "wealth", "creative",
        or "perspective".
    redact_pii:
        Whether to detect and redact PII patterns.
    check_crisis:
        Whether to run crisis detection (for user-facing text).

    Returns
    -------
    ContentFilterResult
        Complete filter result with action, filtered text, and details.
    """
    if not text or not text.strip():
        return ContentFilterResult(
            action=FilterAction.PASS,
            original_text=text,
            filtered_text=text,
        )

    warnings: list[str] = []
    crisis_response: CrisisResponse | None = None
    action = FilterAction.PASS
    blocked_reason: str | None = None

    # 1. Crisis detection (highest priority)
    if check_crisis:
        crisis_response = detect_crisis(text)
        if crisis_response is not None:
            from alchymine.engine.healing.crisis import CrisisSeverity

            if crisis_response.severity == CrisisSeverity.EMERGENCY:
                action = FilterAction.ESCALATE
                warnings.append(
                    "EMERGENCY: Crisis keywords detected — immediate resources required"
                )
            elif crisis_response.severity == CrisisSeverity.HIGH:
                action = FilterAction.ESCALATE
                warnings.append("HIGH: Serious safety concern detected — resources attached")
            else:
                action = FilterAction.WARN
                warnings.append("MEDIUM: Distress indicators detected — resources available")

    # 2. Ethics check
    ethics_result = check_text(text, context=context)
    if not ethics_result.passed:
        critical_violations = [v for v in ethics_result.violations if v.severity == "critical"]
        if critical_violations:
            action = FilterAction.BLOCK
            blocked_reason = "; ".join(v.description for v in critical_violations)
            warnings.append(f"Blocked: {len(critical_violations)} critical ethics violation(s)")
        elif action != FilterAction.ESCALATE:
            action = FilterAction.WARN
            warnings.extend(
                f"Ethics [{v.severity}]: {v.description}" for v in ethics_result.violations
            )

    # 3. Harmful content check
    harmful_warnings = _check_harmful_content(text)
    if harmful_warnings:
        action = FilterAction.BLOCK
        blocked_reason = "; ".join(harmful_warnings)
        warnings.extend(harmful_warnings)

    # 4. PII detection and redaction
    pii_matches: list[PIIMatch] = []
    filtered_text = text
    if redact_pii:
        pii_matches = _detect_pii(text)
        if pii_matches:
            filtered_text = _redact_pii(text, pii_matches)
            warnings.append(f"PII detected and redacted: {len(pii_matches)} instance(s)")

    return ContentFilterResult(
        action=action,
        original_text=text,
        filtered_text=filtered_text,
        crisis_response=crisis_response,
        ethics_result=ethics_result,
        pii_matches=pii_matches,
        warnings=warnings,
        blocked_reason=blocked_reason,
    )

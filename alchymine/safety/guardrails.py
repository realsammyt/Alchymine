"""Safety guardrails — rate limiting for sensitive operations and output caps.

Provides system-specific guardrails that enforce safety boundaries beyond
basic rate limiting. Examples:
- Healing system: limit reframing suggestions per session to prevent dependency
- Wealth system: cap financial projection timeframes to prevent overconfidence
- Perspective system: limit cognitive reframe suggestions per session
- Cross-system: limit bridge notifications per session (max 1 per PRD)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum


class GuardrailAction(StrEnum):
    """Actions a guardrail can enforce."""

    ALLOW = "allow"
    THROTTLE = "throttle"
    DENY = "deny"


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""

    action: GuardrailAction
    guardrail_name: str
    message: str
    remaining: int | None = None
    retry_after_seconds: float | None = None


# ── Session-scoped counters ────────────────────────────────────────

# session_id -> operation -> list of timestamps
_session_counters: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

# Operation limits per session (operation_name -> max_count, window_seconds)
_OPERATION_LIMITS: dict[str, tuple[int, float]] = {
    "healing_reframe": (5, 3600.0),  # max 5 reframes per hour
    "perspective_reframe": (5, 3600.0),  # max 5 cognitive reframes per hour
    "crisis_resource_view": (10, 3600.0),  # max 10 crisis resource lookups per hour
    "cross_system_bridge": (1, 3600.0),  # max 1 bridge notification per hour (PRD)
    "report_generation": (3, 3600.0),  # max 3 report generations per hour
    "wealth_projection": (10, 3600.0),  # max 10 projection calculations per hour
    "financial_data_export": (5, 3600.0),  # max 5 data exports per hour
}


def _clean_expired(timestamps: list[float], window: float) -> list[float]:
    """Remove timestamps outside the sliding window."""
    cutoff = time.monotonic() - window
    return [t for t in timestamps if t > cutoff]


def check_guardrail(
    session_id: str,
    operation: str,
) -> GuardrailResult:
    """Check whether an operation is allowed within session guardrails.

    Parameters
    ----------
    session_id:
        The user's session identifier.
    operation:
        The operation name to check (e.g., "healing_reframe").

    Returns
    -------
    GuardrailResult
        Whether the operation is allowed, throttled, or denied.
    """
    if operation not in _OPERATION_LIMITS:
        return GuardrailResult(
            action=GuardrailAction.ALLOW,
            guardrail_name=operation,
            message="No guardrail configured for this operation",
        )

    max_count, window_seconds = _OPERATION_LIMITS[operation]
    now = time.monotonic()

    # Clean expired entries
    _session_counters[session_id][operation] = _clean_expired(
        _session_counters[session_id][operation], window_seconds
    )

    current_count = len(_session_counters[session_id][operation])
    remaining = max_count - current_count

    if current_count >= max_count:
        # Calculate retry time from oldest entry
        oldest = _session_counters[session_id][operation][0]
        retry_after = window_seconds - (now - oldest)

        return GuardrailResult(
            action=GuardrailAction.DENY,
            guardrail_name=operation,
            message=f"Rate limit reached: {max_count} {operation} per {int(window_seconds / 60)} minutes",
            remaining=0,
            retry_after_seconds=max(0, retry_after),
        )

    # Allow and record
    _session_counters[session_id][operation].append(now)

    # Warn when approaching limit
    if remaining <= 1:
        return GuardrailResult(
            action=GuardrailAction.THROTTLE,
            guardrail_name=operation,
            message=f"Approaching limit: {remaining} {operation} remaining this hour",
            remaining=remaining - 1,
        )

    return GuardrailResult(
        action=GuardrailAction.ALLOW,
        guardrail_name=operation,
        message=f"{operation} allowed",
        remaining=remaining - 1,
    )


def reset_session(session_id: str) -> None:
    """Reset all counters for a session. Used in testing."""
    if session_id in _session_counters:
        del _session_counters[session_id]


def get_session_usage(session_id: str) -> dict[str, dict[str, int | float]]:
    """Get current usage stats for a session.

    Returns
    -------
    dict
        Usage per operation: count, limit, remaining, window_seconds.
    """
    usage: dict[str, dict[str, int | float]] = {}
    now = time.monotonic()

    for operation, (max_count, window_seconds) in _OPERATION_LIMITS.items():
        timestamps = _session_counters.get(session_id, {}).get(operation, [])
        active = [t for t in timestamps if t > now - window_seconds]
        usage[operation] = {
            "count": len(active),
            "limit": max_count,
            "remaining": max(0, max_count - len(active)),
            "window_seconds": window_seconds,
        }

    return usage

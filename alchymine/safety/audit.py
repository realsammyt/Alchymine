"""Audit logging for safety-sensitive operations.

Records all safety-relevant events (crisis detections, ethics violations,
PII redactions, blocked content) to an append-only log with timestamps
and contextual metadata. Designed for accountability and incident review.

In production, this should write to a persistent store (database or
append-only file). The current implementation uses an in-memory ring
buffer suitable for development and testing.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AuditEventType(StrEnum):
    """Types of auditable safety events."""

    CRISIS_DETECTED = "crisis_detected"
    ETHICS_VIOLATION = "ethics_violation"
    CONTENT_BLOCKED = "content_blocked"
    CONTENT_ESCALATED = "content_escalated"
    PII_REDACTED = "pii_redacted"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT_HIT = "rate_limit_hit"
    FINANCIAL_DATA_ACCESS = "financial_data_access"


@dataclass(frozen=True)
class AuditEntry:
    """A single audit log entry."""

    event_type: AuditEventType
    timestamp: datetime
    user_id: str | None
    system: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Audit log store ────────────────────────────────────────────────

_MAX_ENTRIES = 10_000
_audit_log: deque[AuditEntry] = deque(maxlen=_MAX_ENTRIES)
_lock = threading.Lock()


def log_event(
    event_type: AuditEventType,
    system: str,
    summary: str,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEntry:
    """Record a safety-relevant event to the audit log.

    Parameters
    ----------
    event_type:
        The type of auditable event.
    system:
        Which system produced the event (e.g., "healing", "wealth").
    summary:
        Human-readable summary of the event.
    user_id:
        Optional user identifier (never include PII here).
    metadata:
        Optional structured metadata for the event.

    Returns
    -------
    AuditEntry
        The recorded audit entry.
    """
    entry = AuditEntry(
        event_type=event_type,
        timestamp=datetime.now(UTC),
        user_id=user_id,
        system=system,
        summary=summary,
        metadata=metadata or {},
    )
    with _lock:
        _audit_log.append(entry)
    return entry


def get_audit_log(
    limit: int = 100,
    event_type: AuditEventType | None = None,
    user_id: str | None = None,
    system: str | None = None,
) -> list[AuditEntry]:
    """Retrieve audit log entries with optional filtering.

    Parameters
    ----------
    limit:
        Maximum number of entries to return (most recent first).
    event_type:
        Filter by event type.
    user_id:
        Filter by user ID.
    system:
        Filter by system name.

    Returns
    -------
    list[AuditEntry]
        Matching audit entries, most recent first.
    """
    with _lock:
        entries = list(_audit_log)

    # Apply filters
    if event_type is not None:
        entries = [e for e in entries if e.event_type == event_type]
    if user_id is not None:
        entries = [e for e in entries if e.user_id == user_id]
    if system is not None:
        entries = [e for e in entries if e.system == system]

    # Most recent first, limited
    entries.reverse()
    return entries[:limit]


def get_audit_stats() -> dict[str, Any]:
    """Get aggregate statistics from the audit log.

    Returns
    -------
    dict
        Statistics including counts by event type, most active systems,
        and recent activity summary.
    """
    with _lock:
        entries = list(_audit_log)

    if not entries:
        return {
            "total_events": 0,
            "events_by_type": {},
            "events_by_system": {},
            "critical_events_24h": 0,
        }

    # Count by type
    by_type: dict[str, int] = {}
    for e in entries:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

    # Count by system
    by_system: dict[str, int] = {}
    for e in entries:
        by_system[e.system] = by_system.get(e.system, 0) + 1

    # Critical events in last 24h
    now = datetime.now(UTC)
    critical_types = {
        AuditEventType.CRISIS_DETECTED,
        AuditEventType.CONTENT_BLOCKED,
        AuditEventType.CONTENT_ESCALATED,
    }
    critical_24h = sum(
        1
        for e in entries
        if e.event_type in critical_types and (now - e.timestamp).total_seconds() < 86400
    )

    return {
        "total_events": len(entries),
        "events_by_type": by_type,
        "events_by_system": by_system,
        "critical_events_24h": critical_24h,
    }


def clear_audit_log() -> int:
    """Clear the audit log. Returns the number of entries cleared.

    WARNING: This is destructive. In production, audit logs should
    be append-only and never cleared. This exists for testing only.
    """
    with _lock:
        count = len(_audit_log)
        _audit_log.clear()
    return count

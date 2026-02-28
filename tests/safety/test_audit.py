"""Tests for the safety audit logging system."""

from __future__ import annotations

import pytest

from alchymine.safety.audit import (
    AuditEventType,
    clear_audit_log,
    get_audit_log,
    get_audit_stats,
    log_event,
)


@pytest.fixture(autouse=True)
def _clean_audit_log():
    """Clear audit log before and after each test."""
    clear_audit_log()
    yield
    clear_audit_log()


class TestAuditLogging:
    """Tests for audit event logging."""

    def test_log_event_returns_entry(self) -> None:
        entry = log_event(
            event_type=AuditEventType.CRISIS_DETECTED,
            system="healing",
            summary="Crisis keywords detected in user input",
        )
        assert entry.event_type == AuditEventType.CRISIS_DETECTED
        assert entry.system == "healing"
        assert entry.summary == "Crisis keywords detected in user input"

    def test_log_event_with_user_id(self) -> None:
        entry = log_event(
            event_type=AuditEventType.PII_REDACTED,
            system="general",
            summary="SSN redacted from output",
            user_id="user-123",
        )
        assert entry.user_id == "user-123"

    def test_log_event_with_metadata(self) -> None:
        entry = log_event(
            event_type=AuditEventType.CONTENT_BLOCKED,
            system="wealth",
            summary="Guaranteed returns language blocked",
            metadata={"violation_count": 2, "category": "financial_advice"},
        )
        assert entry.metadata["violation_count"] == 2
        assert entry.metadata["category"] == "financial_advice"

    def test_timestamp_set_automatically(self) -> None:
        entry = log_event(
            event_type=AuditEventType.ETHICS_VIOLATION,
            system="creative",
            summary="Missing attribution",
        )
        assert entry.timestamp is not None


class TestAuditLogRetrieval:
    """Tests for retrieving audit log entries."""

    def test_get_empty_log(self) -> None:
        entries = get_audit_log()
        assert entries == []

    def test_get_log_returns_recent_first(self) -> None:
        log_event(AuditEventType.CRISIS_DETECTED, "healing", "First")
        log_event(AuditEventType.ETHICS_VIOLATION, "wealth", "Second")
        log_event(AuditEventType.PII_REDACTED, "general", "Third")

        entries = get_audit_log()
        assert len(entries) == 3
        assert entries[0].summary == "Third"
        assert entries[2].summary == "First"

    def test_get_log_with_limit(self) -> None:
        for i in range(10):
            log_event(AuditEventType.RATE_LIMIT_HIT, "api", f"Event {i}")

        entries = get_audit_log(limit=3)
        assert len(entries) == 3

    def test_filter_by_event_type(self) -> None:
        log_event(AuditEventType.CRISIS_DETECTED, "healing", "Crisis")
        log_event(AuditEventType.PII_REDACTED, "general", "PII")
        log_event(AuditEventType.CRISIS_DETECTED, "perspective", "Crisis 2")

        entries = get_audit_log(event_type=AuditEventType.CRISIS_DETECTED)
        assert len(entries) == 2
        assert all(e.event_type == AuditEventType.CRISIS_DETECTED for e in entries)

    def test_filter_by_user_id(self) -> None:
        log_event(AuditEventType.PII_REDACTED, "general", "User A", user_id="a")
        log_event(AuditEventType.PII_REDACTED, "general", "User B", user_id="b")
        log_event(AuditEventType.PII_REDACTED, "general", "User A again", user_id="a")

        entries = get_audit_log(user_id="a")
        assert len(entries) == 2

    def test_filter_by_system(self) -> None:
        log_event(AuditEventType.ETHICS_VIOLATION, "healing", "Healing issue")
        log_event(AuditEventType.ETHICS_VIOLATION, "wealth", "Wealth issue")
        log_event(AuditEventType.ETHICS_VIOLATION, "healing", "Another healing")

        entries = get_audit_log(system="healing")
        assert len(entries) == 2


class TestAuditStats:
    """Tests for audit statistics."""

    def test_empty_stats(self) -> None:
        stats = get_audit_stats()
        assert stats["total_events"] == 0
        assert stats["events_by_type"] == {}

    def test_stats_count_by_type(self) -> None:
        log_event(AuditEventType.CRISIS_DETECTED, "healing", "c1")
        log_event(AuditEventType.CRISIS_DETECTED, "healing", "c2")
        log_event(AuditEventType.PII_REDACTED, "general", "p1")

        stats = get_audit_stats()
        assert stats["total_events"] == 3
        assert stats["events_by_type"][AuditEventType.CRISIS_DETECTED] == 2
        assert stats["events_by_type"][AuditEventType.PII_REDACTED] == 1

    def test_stats_count_by_system(self) -> None:
        log_event(AuditEventType.ETHICS_VIOLATION, "healing", "h1")
        log_event(AuditEventType.ETHICS_VIOLATION, "wealth", "w1")
        log_event(AuditEventType.ETHICS_VIOLATION, "healing", "h2")

        stats = get_audit_stats()
        assert stats["events_by_system"]["healing"] == 2
        assert stats["events_by_system"]["wealth"] == 1

    def test_critical_events_24h(self) -> None:
        log_event(AuditEventType.CRISIS_DETECTED, "healing", "Critical 1")
        log_event(AuditEventType.CONTENT_BLOCKED, "wealth", "Critical 2")
        log_event(AuditEventType.PII_REDACTED, "general", "Not critical")

        stats = get_audit_stats()
        assert stats["critical_events_24h"] == 2


class TestClearAuditLog:
    """Tests for clearing the audit log."""

    def test_clear_returns_count(self) -> None:
        log_event(AuditEventType.PII_REDACTED, "general", "Entry 1")
        log_event(AuditEventType.PII_REDACTED, "general", "Entry 2")

        count = clear_audit_log()
        assert count == 2

    def test_clear_empties_log(self) -> None:
        log_event(AuditEventType.PII_REDACTED, "general", "Entry")
        clear_audit_log()

        entries = get_audit_log()
        assert len(entries) == 0

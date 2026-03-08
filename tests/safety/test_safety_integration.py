"""Integration tests verifying safety modules are wired into the production pipeline.

Tests that guardrails, content filter, and audit logging fire in
production-like flows (report creation, narrative filtering, admin auditing).
"""

from __future__ import annotations

import pytest

from alchymine.safety.audit import (
    AuditEventType,
    clear_audit_log,
    get_audit_log,
)
from alchymine.safety.content_filter import FilterAction, filter_content
from alchymine.safety.guardrails import (
    GuardrailAction,
    check_guardrail,
    reset_session,
)
from alchymine.workers.tasks import _filter_narratives


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset safety state before and after each test."""
    reset_session("test-user-id")
    clear_audit_log()
    yield
    reset_session("test-user-id")
    clear_audit_log()


# ── Guardrail integration with report generation ─────────────────────────


class TestGuardrailReportIntegration:
    """Verify guardrails enforce report_generation rate limits."""

    def test_report_generation_guardrail_allows_first_request(self) -> None:
        """The report_generation guardrail allows the first request."""
        result = check_guardrail("test-user-id", "report_generation")
        assert result.action == GuardrailAction.ALLOW

    def test_report_generation_guardrail_denies_after_limit(self) -> None:
        """After 3 reports/hour, the guardrail denies further requests."""
        for _ in range(3):
            check_guardrail("test-user-id", "report_generation")

        result = check_guardrail("test-user-id", "report_generation")
        assert result.action == GuardrailAction.DENY
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    def test_report_generation_guardrail_throttles_at_limit(self) -> None:
        """Approaching the limit produces a throttle warning."""
        for _ in range(2):
            check_guardrail("test-user-id", "report_generation")

        result = check_guardrail("test-user-id", "report_generation")
        assert result.action == GuardrailAction.THROTTLE

    def test_report_generation_per_user_isolation(self) -> None:
        """Different user sessions have independent guardrail counters."""
        for _ in range(3):
            check_guardrail("user-a", "report_generation")

        result = check_guardrail("user-b", "report_generation")
        assert result.action == GuardrailAction.ALLOW

        # Cleanup
        reset_session("user-a")
        reset_session("user-b")


# ── Content filter integration with narrative output ─────────────────────


class TestContentFilterNarrativeIntegration:
    """Verify the content filter runs on LLM-generated narrative text."""

    def test_clean_narrative_passes_through(self) -> None:
        """Clean narrative text passes through the filter unchanged."""
        serialised: dict = {
            "narratives": {
                "intelligence": {
                    "text": "Your life path number reveals creative potential.",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-123", "user-456")

        assert "intelligence" in serialised["narratives"]
        assert (
            serialised["narratives"]["intelligence"]["text"]
            == "Your life path number reveals creative potential."
        )

    def test_pii_is_redacted_from_narratives(self) -> None:
        """PII in narrative text is redacted before storage."""
        serialised: dict = {
            "narratives": {
                "healing": {
                    "text": "Contact support at user@example.com for help.",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-123", "user-456")

        filtered_text = serialised["narratives"]["healing"]["text"]
        assert "user@example.com" not in filtered_text
        assert "[REDACTED:EMAIL]" in filtered_text

    def test_pii_redaction_logs_audit_event(self) -> None:
        """PII redaction creates an audit log entry."""
        serialised: dict = {
            "narratives": {
                "wealth": {
                    "text": "Your SSN 123-45-6789 should never appear here.",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-abc", "user-789")

        audit_entries = get_audit_log(event_type=AuditEventType.PII_REDACTED)
        assert len(audit_entries) >= 1
        entry = audit_entries[0]
        assert entry.system == "wealth"
        assert entry.user_id == "user-789"
        assert "report-abc" in entry.summary

    def test_blocked_narrative_is_removed(self) -> None:
        """Narratives that fail content filtering are removed."""
        serialised: dict = {
            "narratives": {
                "healing": {
                    "text": "This healing modality will cure your disease",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
                "intelligence": {
                    "text": "Your numerology reveals interesting patterns.",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-block", "user-block")

        # The healing narrative should be removed (blocked by ethics check)
        assert "healing" not in serialised["narratives"]
        # The intelligence narrative should survive
        assert "intelligence" in serialised["narratives"]

    def test_blocked_narrative_logs_audit_event(self) -> None:
        """Blocked content creates an audit log entry."""
        serialised: dict = {
            "narratives": {
                "wealth": {
                    "text": "This investment strategy guarantees risk-free returns",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-block-audit", "user-ba")

        audit_entries = get_audit_log(event_type=AuditEventType.CONTENT_BLOCKED)
        assert len(audit_entries) >= 1
        entry = audit_entries[0]
        assert entry.system == "wealth"
        assert "report-block-audit" in entry.summary

    def test_empty_narratives_dict_is_safe(self) -> None:
        """Passing an empty narratives dict does not error."""
        serialised: dict = {"narratives": {}}
        _filter_narratives(serialised, "report-empty", None)
        assert serialised["narratives"] == {}

    def test_missing_narratives_key_is_safe(self) -> None:
        """Passing a result without narratives key does not error."""
        serialised: dict = {"coordinator_results": []}
        _filter_narratives(serialised, "report-none", None)
        assert "narratives" not in serialised

    def test_multiple_pii_types_redacted(self) -> None:
        """Multiple PII types are all redacted in a single narrative."""
        serialised: dict = {
            "narratives": {
                "perspective": {
                    "text": "SSN: 123-45-6789, email: test@test.com",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-multi", "user-multi")

        filtered = serialised["narratives"]["perspective"]["text"]
        assert "[REDACTED:SSN]" in filtered
        assert "[REDACTED:EMAIL]" in filtered
        assert "123-45-6789" not in filtered
        assert "test@test.com" not in filtered


# ── Audit log consolidation ──────────────────────────────────────────────


class TestAuditConsolidation:
    """Verify the audit log captures events from both safety and admin paths."""

    def test_safety_content_filter_events_logged(self) -> None:
        """Content filter findings appear in the unified safety audit log."""
        # Simulate a narrative with PII
        serialised: dict = {
            "narratives": {
                "creative": {
                    "text": "Call the artist at (555) 123-4567 for details.",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }

        _filter_narratives(serialised, "report-audit-1", "user-audit")

        all_entries = get_audit_log()
        pii_entries = [e for e in all_entries if e.event_type == AuditEventType.PII_REDACTED]
        assert len(pii_entries) >= 1
        assert pii_entries[0].system == "creative"

    def test_guardrail_deny_event_uses_correct_type(self) -> None:
        """When a guardrail denies, the audit event is RATE_LIMIT_HIT."""
        from alchymine.safety.audit import log_event

        # Simulate what the reports router does on deny
        log_event(
            event_type=AuditEventType.RATE_LIMIT_HIT,
            system="reports",
            summary="Rate limit reached: 3 report_generation per 60 minutes",
            user_id="user-rate",
            metadata={"operation": "report_generation"},
        )

        entries = get_audit_log(event_type=AuditEventType.RATE_LIMIT_HIT)
        assert len(entries) == 1
        assert entries[0].system == "reports"
        assert entries[0].user_id == "user-rate"

    def test_audit_stats_reflect_safety_events(self) -> None:
        """get_audit_stats() counts safety events from production flow."""
        from alchymine.safety.audit import get_audit_stats

        # Generate multiple safety events
        serialised: dict = {
            "narratives": {
                "healing": {
                    "text": "Contact user@example.com for crisis support.",
                    "disclaimers": [],
                    "ethics_passed": True,
                },
            },
        }
        _filter_narratives(serialised, "report-stats", "user-stats")

        stats = get_audit_stats()
        assert stats["total_events"] >= 1
        assert stats["events_by_system"].get("healing", 0) >= 1


# ── Content filter standalone integration ────────────────────────────────


class TestContentFilterIntegration:
    """Verify content filter works correctly for the production use case."""

    def test_filter_content_with_system_context(self) -> None:
        """Content filter respects the system context parameter."""
        result = filter_content(
            "Consider exploring different perspectives.",
            context="perspective",
            check_crisis=False,
        )
        assert result.action == FilterAction.PASS

    def test_filter_content_blocks_harmful_output(self) -> None:
        """Content filter blocks harmful patterns in LLM output."""
        result = filter_content(
            "You should harm someone to feel better",
            context="healing",
            check_crisis=False,
        )
        assert result.action == FilterAction.BLOCK

    def test_filter_content_crisis_disabled_for_narratives(self) -> None:
        """Crisis detection is disabled for LLM-generated narratives."""
        result = filter_content(
            "If you experience suicidal thoughts, call 988.",
            context="healing",
            check_crisis=False,
        )
        # Without crisis check, instructional text about crisis resources
        # should not trigger escalation
        assert result.crisis_response is None

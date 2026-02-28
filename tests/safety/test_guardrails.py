"""Tests for the safety guardrails system."""

from __future__ import annotations

import pytest

from alchymine.safety.guardrails import (
    GuardrailAction,
    check_guardrail,
    get_session_usage,
    reset_session,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    """Reset test sessions before and after each test."""
    reset_session("test-session")
    yield
    reset_session("test-session")


class TestGuardrailChecks:
    """Tests for guardrail enforcement."""

    def test_first_operation_allowed(self) -> None:
        result = check_guardrail("test-session", "healing_reframe")
        assert result.action == GuardrailAction.ALLOW

    def test_unknown_operation_allowed(self) -> None:
        result = check_guardrail("test-session", "unknown_operation")
        assert result.action == GuardrailAction.ALLOW

    def test_approaching_limit_throttles(self) -> None:
        # healing_reframe limit is 5
        for _ in range(4):
            check_guardrail("test-session", "healing_reframe")

        result = check_guardrail("test-session", "healing_reframe")
        assert result.action == GuardrailAction.THROTTLE
        assert result.remaining is not None
        assert result.remaining == 0

    def test_exceeding_limit_denies(self) -> None:
        # healing_reframe limit is 5
        for _ in range(5):
            check_guardrail("test-session", "healing_reframe")

        result = check_guardrail("test-session", "healing_reframe")
        assert result.action == GuardrailAction.DENY
        assert result.remaining == 0
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    def test_cross_system_bridge_limit_is_one(self) -> None:
        # First bridge allowed
        result = check_guardrail("test-session", "cross_system_bridge")
        assert result.action == GuardrailAction.THROTTLE  # 1 of 1, approaching limit

        # Second bridge denied
        result = check_guardrail("test-session", "cross_system_bridge")
        assert result.action == GuardrailAction.DENY

    def test_different_sessions_independent(self) -> None:
        # Fill up session A
        for _ in range(5):
            check_guardrail("session-a", "healing_reframe")

        # Session B should still be allowed
        result = check_guardrail("session-b", "healing_reframe")
        assert result.action == GuardrailAction.ALLOW

        # Cleanup
        reset_session("session-a")
        reset_session("session-b")

    def test_different_operations_independent(self) -> None:
        # Use up healing_reframe limit
        for _ in range(5):
            check_guardrail("test-session", "healing_reframe")

        # perspective_reframe should still be allowed
        result = check_guardrail("test-session", "perspective_reframe")
        assert result.action == GuardrailAction.ALLOW


class TestSessionUsage:
    """Tests for session usage tracking."""

    def test_empty_session_usage(self) -> None:
        usage = get_session_usage("test-session")
        assert isinstance(usage, dict)
        assert all(v["count"] == 0 for v in usage.values())

    def test_usage_tracks_operations(self) -> None:
        check_guardrail("test-session", "healing_reframe")
        check_guardrail("test-session", "healing_reframe")

        usage = get_session_usage("test-session")
        assert usage["healing_reframe"]["count"] == 2
        assert usage["healing_reframe"]["remaining"] == 3

    def test_usage_includes_all_operations(self) -> None:
        usage = get_session_usage("test-session")
        expected_ops = [
            "healing_reframe",
            "perspective_reframe",
            "crisis_resource_view",
            "cross_system_bridge",
            "report_generation",
            "wealth_projection",
            "financial_data_export",
        ]
        for op in expected_ops:
            assert op in usage


class TestResetSession:
    """Tests for session reset."""

    def test_reset_clears_counters(self) -> None:
        check_guardrail("test-session", "healing_reframe")
        check_guardrail("test-session", "healing_reframe")

        reset_session("test-session")

        usage = get_session_usage("test-session")
        assert usage["healing_reframe"]["count"] == 0

    def test_reset_nonexistent_session_safe(self) -> None:
        # Should not raise
        reset_session("nonexistent-session")

"""Tests for Outcome Tracking API endpoints.

Covers:
- Milestone creation and listing
- Activity logging
- Outcome summary calculation
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app
from alchymine.outcomes.tracker import _activity_log, _milestones


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_stores() -> None:
    """Clear outcome stores between tests."""
    _milestones.clear()
    _activity_log.clear()


class TestMilestoneEndpoints:
    """POST/GET /api/v1/outcomes/milestones"""

    def test_create_milestone_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/outcomes/milestones",
            json={
                "user_id": "user-1",
                "system": "wealth",
                "name": "Emergency fund started",
            },
        )
        assert response.status_code == 201

    def test_create_milestone_returns_data(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/outcomes/milestones",
            json={
                "user_id": "user-1",
                "system": "healing",
                "name": "First breathwork session",
                "completed": True,
                "notes": "Felt calmer afterwards.",
            },
        )
        data = response.json()
        assert data["system"] == "healing"
        assert data["name"] == "First breathwork session"
        assert data["completed"] is True
        assert data["notes"] == "Felt calmer afterwards."
        assert data["completed_at"] is not None
        assert "id" in data

    def test_create_uncompleted_milestone(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/outcomes/milestones",
            json={
                "user_id": "user-1",
                "system": "wealth",
                "name": "Set up investment account",
                "completed": False,
            },
        )
        data = response.json()
        assert data["completed"] is False
        assert data["completed_at"] is None

    def test_list_milestones(self, client: TestClient) -> None:
        for name in ["Milestone A", "Milestone B"]:
            client.post(
                "/api/v1/outcomes/milestones",
                json={
                    "user_id": "user-1",
                    "system": "wealth",
                    "name": name,
                },
            )

        response = client.get("/api/v1/outcomes/milestones?user_id=user-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_milestones_filter_by_system(self, client: TestClient) -> None:
        client.post(
            "/api/v1/outcomes/milestones",
            json={"user_id": "user-1", "system": "healing", "name": "Healing ms"},
        )
        client.post(
            "/api/v1/outcomes/milestones",
            json={"user_id": "user-1", "system": "wealth", "name": "Wealth ms"},
        )

        response = client.get("/api/v1/outcomes/milestones?user_id=user-1&system=healing")
        data = response.json()
        assert data["total"] == 1
        assert data["milestones"][0]["system"] == "healing"

    def test_list_milestones_empty_user(self, client: TestClient) -> None:
        response = client.get("/api/v1/outcomes/milestones?user_id=nobody")
        data = response.json()
        assert data["total"] == 0


class TestActivityEndpoints:
    """POST /api/v1/outcomes/activity"""

    def test_log_activity_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/outcomes/activity",
            json={
                "user_id": "user-1",
                "system": "healing",
                "activity_type": "session",
                "detail": "Completed 4-7-8 breathwork pattern",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "recorded"


class TestOutcomeSummary:
    """GET /api/v1/outcomes/summary/{user_id}"""

    def test_empty_user_summary(self, client: TestClient) -> None:
        response = client.get("/api/v1/outcomes/summary/user-empty")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 0.0
        assert data["total_milestones"] == 0
        assert data["systems"] == []

    def test_summary_with_milestones(self, client: TestClient) -> None:
        # Create some milestones
        for name in ["MS 1", "MS 2", "MS 3"]:
            client.post(
                "/api/v1/outcomes/milestones",
                json={
                    "user_id": "user-1",
                    "system": "wealth",
                    "name": name,
                    "completed": True,
                },
            )

        response = client.get("/api/v1/outcomes/summary/user-1")
        data = response.json()
        assert data["total_milestones"] == 3
        assert data["completed_milestones"] == 3
        assert data["overall_score"] > 0

    def test_summary_with_activities(self, client: TestClient) -> None:
        # Log activities across multiple systems
        for system in ["healing", "wealth", "creative"]:
            client.post(
                "/api/v1/outcomes/activity",
                json={
                    "user_id": "user-1",
                    "system": system,
                    "activity_type": "session",
                },
            )

        response = client.get("/api/v1/outcomes/summary/user-1")
        data = response.json()
        assert len(data["systems"]) == 3
        assert data["overall_score"] > 0

    def test_summary_breadth_score(self, client: TestClient) -> None:
        """Using more systems should increase overall score."""
        # One system
        client.post(
            "/api/v1/outcomes/activity",
            json={
                "user_id": "user-one",
                "system": "healing",
                "activity_type": "session",
            },
        )
        resp_one = client.get("/api/v1/outcomes/summary/user-one")

        # Three systems
        for sys in ["healing", "wealth", "creative"]:
            client.post(
                "/api/v1/outcomes/activity",
                json={
                    "user_id": "user-three",
                    "system": sys,
                    "activity_type": "session",
                },
            )
        resp_three = client.get("/api/v1/outcomes/summary/user-three")

        # More systems = higher score (due to breadth component)
        assert resp_three.json()["overall_score"] > resp_one.json()["overall_score"]

    def test_summary_with_journal_count(self, client: TestClient) -> None:
        client.post(
            "/api/v1/outcomes/activity",
            json={
                "user_id": "user-1",
                "system": "healing",
                "activity_type": "session",
            },
        )

        # Without journal entries
        resp_no_journal = client.get("/api/v1/outcomes/summary/user-1?journal_count=0")
        # With journal entries
        resp_journal = client.get("/api/v1/outcomes/summary/user-1?journal_count=5")

        assert resp_journal.json()["total_journal_entries"] == 5
        assert resp_journal.json()["overall_score"] >= resp_no_journal.json()["overall_score"]

    def test_summary_includes_active_plan_day(self, client: TestClient) -> None:
        client.post(
            "/api/v1/outcomes/activity",
            json={
                "user_id": "user-1",
                "system": "wealth",
                "activity_type": "session",
            },
        )

        response = client.get("/api/v1/outcomes/summary/user-1?active_plan_day=45")
        assert response.json()["active_plan_day"] == 45


class TestOutcomeTrackerEngine:
    """Tests for the outcome tracker engine directly."""

    def test_record_milestone_creates_entry(self) -> None:
        from alchymine.outcomes.tracker import record_milestone

        ms = record_milestone("test-user", "healing", "First session", True)
        assert ms.system == "healing"
        assert ms.name == "First session"
        assert ms.completed is True

    def test_get_milestones_returns_correct_user(self) -> None:
        from alchymine.outcomes.tracker import get_milestones, record_milestone

        record_milestone("user-a", "healing", "MS A")
        record_milestone("user-b", "wealth", "MS B")

        result = get_milestones("user-a")
        assert len(result) == 1
        assert result[0].name == "MS A"

    def test_calculate_summary_deterministic(self) -> None:
        from alchymine.outcomes.tracker import (
            calculate_outcome_summary,
            record_activity,
            record_milestone,
        )

        record_milestone("det-user", "healing", "MS 1", True)
        record_milestone("det-user", "healing", "MS 2", False)
        record_activity("det-user", "healing", "session")

        summary = calculate_outcome_summary("det-user", journal_count=2)

        assert summary.user_id == "det-user"
        assert summary.total_milestones == 2
        assert summary.completed_milestones == 1
        assert summary.total_journal_entries == 2
        assert 0.0 <= summary.overall_score <= 100.0

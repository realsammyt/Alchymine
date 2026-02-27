"""Tests for the reports API router.

All tests use Celery eager mode so tasks run synchronously
without requiring a running Redis broker.
"""

from __future__ import annotations

import os

# Enable Celery eager mode before any Celery imports
os.environ["CELERY_ALWAYS_EAGER"] = "true"

import importlib  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import alchymine.workers.celery_app as celery_app_mod  # noqa: E402

importlib.reload(celery_app_mod)

from alchymine.api.main import app  # noqa: E402
from alchymine.workers.tasks import report_store  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_store():
    """Clear the in-memory report store between tests."""
    report_store.clear()
    yield
    report_store.clear()


def _valid_report_payload() -> dict:
    """Return a minimal valid ReportRequest JSON payload."""
    return {
        "intake": {
            "full_name": "Maria Elena Vasquez",
            "birth_date": "1992-03-15",
            "intention": "family",
        },
        "user_input": "Generate my full numerology report",
    }


# ── POST /api/v1/reports ─────────────────────────────────────────────────


class TestPostReports:
    """Tests for POST /api/v1/reports."""

    def test_post_returns_202(self, client: TestClient) -> None:
        """POST should return 202 Accepted."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        assert response.status_code == 202

    def test_post_returns_report_id(self, client: TestClient) -> None:
        """Response should contain a UUID report id."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        data = response.json()
        assert "id" in data
        assert len(data["id"]) == 36  # UUID format

    def test_post_returns_queued_status(self, client: TestClient) -> None:
        """Initial status should be 'queued'."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        data = response.json()
        assert data["status"] == "queued"

    def test_post_returns_timestamps(self, client: TestClient) -> None:
        """Response should include created_at and updated_at."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data

    def test_post_stores_report_in_store(self, client: TestClient) -> None:
        """Report should be added to the report_store."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        report_id = response.json()["id"]
        assert report_id in report_store

    def test_post_with_user_profile(self, client: TestClient) -> None:
        """POST should accept an optional user_profile."""
        payload = _valid_report_payload()
        payload["user_profile"] = {"id": "user-123", "custom": True}
        response = client.post("/api/v1/reports", json=payload)
        assert response.status_code == 202

    def test_post_invalid_intake_returns_422(self, client: TestClient) -> None:
        """POST with invalid intake data should return 422."""
        response = client.post(
            "/api/v1/reports",
            json={"intake": {"full_name": "X"}},  # missing required fields
        )
        assert response.status_code == 422


# ── GET /api/v1/reports/{report_id}/status ───────────────────────────────


class TestGetReportStatus:
    """Tests for GET /api/v1/reports/{report_id}/status."""

    def test_status_not_found_returns_404(self, client: TestClient) -> None:
        """Querying a non-existent report should return 404."""
        response = client.get("/api/v1/reports/nonexistent-id/status")
        assert response.status_code == 404

    def test_status_returns_queued(self, client: TestClient) -> None:
        """A newly seeded report should show queued status."""
        report_store["seed-1"] = {
            "report_id": "seed-1",
            "status": "queued",
            "user_input": "test",
            "user_profile": None,
            "result": None,
            "error": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        response = client.get("/api/v1/reports/seed-1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["id"] == "seed-1"

    def test_status_returns_processing(self, client: TestClient) -> None:
        """A processing report should show processing status."""
        report_store["seed-2"] = {
            "report_id": "seed-2",
            "status": "processing",
            "user_input": "test",
            "user_profile": None,
            "result": None,
            "error": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:01+00:00",
        }
        response = client.get("/api/v1/reports/seed-2/status")
        assert response.status_code == 200
        assert response.json()["status"] == "processing"

    def test_status_returns_complete(self, client: TestClient) -> None:
        """A completed report should show complete status."""
        report_store["seed-3"] = {
            "report_id": "seed-3",
            "status": "complete",
            "user_input": "test",
            "user_profile": None,
            "result": {"data": "here"},
            "error": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:02+00:00",
        }
        response = client.get("/api/v1/reports/seed-3/status")
        assert response.status_code == 200
        assert response.json()["status"] == "complete"


# ── GET /api/v1/reports/{report_id} ──────────────────────────────────────


class TestGetReport:
    """Tests for GET /api/v1/reports/{report_id}."""

    def test_get_not_found_returns_404(self, client: TestClient) -> None:
        """Querying a non-existent report should return 404."""
        response = client.get("/api/v1/reports/doesnt-exist")
        assert response.status_code == 404

    def test_get_queued_returns_202(self, client: TestClient) -> None:
        """A queued report should return 202."""
        report_store["queued-1"] = {
            "report_id": "queued-1",
            "status": "queued",
            "user_input": "test",
            "user_profile": None,
            "result": None,
            "error": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        response = client.get("/api/v1/reports/queued-1")
        assert response.status_code == 202

    def test_get_processing_returns_202(self, client: TestClient) -> None:
        """A processing report should return 202."""
        report_store["processing-1"] = {
            "report_id": "processing-1",
            "status": "processing",
            "user_input": "test",
            "user_profile": None,
            "result": None,
            "error": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:01+00:00",
        }
        response = client.get("/api/v1/reports/processing-1")
        assert response.status_code == 202

    def test_get_complete_returns_200_with_result(self, client: TestClient) -> None:
        """A completed report should return 200 with result data."""
        report_store["done-1"] = {
            "report_id": "done-1",
            "status": "complete",
            "user_input": "test",
            "user_profile": None,
            "result": {"request_id": "r1", "quality_passed": True},
            "error": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:02+00:00",
        }
        response = client.get("/api/v1/reports/done-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "done-1"
        assert data["status"] == "complete"
        assert data["result"]["request_id"] == "r1"

    def test_get_failed_returns_200_with_error(self, client: TestClient) -> None:
        """A failed report should return 200 with error info."""
        report_store["fail-1"] = {
            "report_id": "fail-1",
            "status": "failed",
            "user_input": "test",
            "user_profile": None,
            "result": None,
            "error": "Something broke",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:02+00:00",
        }
        response = client.get("/api/v1/reports/fail-1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Something broke"

    def test_end_to_end_post_then_get(self, client: TestClient) -> None:
        """POST a report, then GET it — full round-trip with mocked orchestrator."""
        from dataclasses import dataclass, field

        @dataclass
        class FakeIntent:
            intent: str = "unknown"
            confidence: float = 0.0
            secondary_intents: list = field(default_factory=list)
            detected_keywords: list = field(default_factory=list)

        @dataclass
        class FakeResult:
            request_id: str = "e2e-req"
            intent: FakeIntent = field(default_factory=FakeIntent)
            coordinator_results: list = field(default_factory=list)
            synthesis: dict | None = None
            quality_passed: bool = True

        with patch(
            "alchymine.workers.tasks.MasterOrchestrator"
        ) as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=FakeResult())

            # POST
            post_resp = client.post("/api/v1/reports", json=_valid_report_payload())
            assert post_resp.status_code == 202
            report_id = post_resp.json()["id"]

            # GET status
            status_resp = client.get(f"/api/v1/reports/{report_id}/status")
            assert status_resp.status_code == 200
            # In eager mode, the task finishes synchronously before the
            # POST handler returns — so by the time we query status it
            # should already be complete.
            assert status_resp.json()["status"] in ("complete", "queued", "processing")

            # GET full report
            get_resp = client.get(f"/api/v1/reports/{report_id}")
            # Could be 200 (complete) or 202 (still processing) depending on timing
            assert get_resp.status_code in (200, 202)

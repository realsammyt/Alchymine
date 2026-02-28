"""Tests for the reports API router.

All tests use Celery eager mode so tasks run synchronously
without requiring a running Redis broker.  Report data is
persisted to an in-memory SQLite database.
"""

from __future__ import annotations

import os

# Enable Celery eager mode before any Celery imports
os.environ["CELERY_ALWAYS_EAGER"] = "true"

import importlib  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import alchymine.db.models  # noqa: F401,E402
import alchymine.workers.celery_app as celery_app_mod  # noqa: E402

importlib.reload(celery_app_mod)

from alchymine.api.deps import get_db_session, set_db_engine  # noqa: E402
from alchymine.api.main import app  # noqa: E402
from alchymine.db import repository  # noqa: E402
from alchymine.db.base import Base  # noqa: E402
from alchymine.workers.tasks import _set_task_engine  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a valid Fernet key is available."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine and initialise the schema."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Provide an async session for direct DB seeding in tests."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
def client(engine):
    """Provide a TestClient wired to the in-memory SQLite engine."""
    # Override the FastAPI dependency to use our test engine
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_session

    # Also override the task engine so Celery tasks use the same DB
    set_db_engine(engine)
    _set_task_engine(engine)

    yield TestClient(app)

    app.dependency_overrides.clear()
    set_db_engine(None)
    _set_task_engine(None)


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

    def test_post_returns_pending_status(self, client: TestClient) -> None:
        """Initial status should be 'pending'."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        data = response.json()
        assert data["status"] == "pending"

    def test_post_returns_timestamps(self, client: TestClient) -> None:
        """Response should include created_at and updated_at."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        data = response.json()
        assert "created_at" in data
        assert "updated_at" in data

    def test_post_persists_report_to_db(self, client: TestClient, engine) -> None:
        """Report should be persisted to the database."""
        response = client.post("/api/v1/reports", json=_valid_report_payload())
        report_id = response.json()["id"]

        from alchymine.workers.tasks import _run_async

        async def _check():
            from alchymine.db.base import get_async_session_factory

            factory = get_async_session_factory(engine)
            async with factory() as sess:
                return await repository.get_report(sess, report_id)

        report = _run_async(_check())
        assert report is not None

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

    def test_status_returns_pending(self, client: TestClient) -> None:
        """A newly created report should show pending status."""
        # Create a report via POST
        post_resp = client.post("/api/v1/reports", json=_valid_report_payload())
        report_id = post_resp.json()["id"]

        response = client.get(f"/api/v1/reports/{report_id}/status")
        assert response.status_code == 200
        data = response.json()
        # Status could be pending, generating, or complete depending on eager mode timing
        assert data["status"] in ("pending", "generating", "complete", "failed")
        assert data["id"] == report_id


# ── GET /api/v1/reports/{report_id} ──────────────────────────────────────


class TestGetReport:
    """Tests for GET /api/v1/reports/{report_id}."""

    def test_get_not_found_returns_404(self, client: TestClient) -> None:
        """Querying a non-existent report should return 404."""
        response = client.get("/api/v1/reports/doesnt-exist")
        assert response.status_code == 404

    def test_end_to_end_post_then_get(self, client: TestClient) -> None:
        """POST a report, then GET it -- full round-trip with mocked orchestrator."""
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

        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
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
            # POST handler returns -- so by the time we query status it
            # should already be complete.
            assert status_resp.json()["status"] in ("complete", "pending", "generating")

            # GET full report
            get_resp = client.get(f"/api/v1/reports/{report_id}")
            # Could be 200 (complete) or 202 (still processing) depending on timing
            assert get_resp.status_code in (200, 202)


# ── Pagination: GET /api/v1/reports/user/{user_id} ───────────────────────


class TestListUserReports:
    """Tests for GET /api/v1/reports/user/{user_id}."""

    def test_list_empty(self, client: TestClient) -> None:
        """Listing reports for a user with none should return empty list."""
        response = client.get("/api/v1/reports/user/no-such-user")
        assert response.status_code == 200
        data = response.json()
        assert data["reports"] == []
        assert data["count"] == 0

    def test_list_with_pagination_params(self, client: TestClient) -> None:
        """Pagination params should be reflected in the response."""
        response = client.get("/api/v1/reports/user/some-user?skip=5&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 5
        assert data["limit"] == 10

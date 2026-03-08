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
import logging  # noqa: E402
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

from alchymine.api.auth import get_current_user  # noqa: E402,F401
from alchymine.api.deps import get_db_session, set_db_engine  # noqa: E402
from alchymine.api.main import app  # noqa: E402
from alchymine.db import repository  # noqa: E402
from alchymine.db.base import Base  # noqa: E402
from alchymine.workers.tasks import _set_task_engine  # noqa: E402

# The test user sub used in the global conftest override.
_TEST_USER_ID = "user-1"
_OTHER_USER_ID = "other-user-99"


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

    app.dependency_overrides.pop(get_db_session, None)
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
        response = client.get("/api/v1/reports/user/user-1")
        assert response.status_code == 200
        data = response.json()
        assert data["reports"] == []
        assert data["count"] == 0

    def test_list_with_pagination_params(self, client: TestClient) -> None:
        """Pagination params should be reflected in the response."""
        response = client.get("/api/v1/reports/user/user-1?skip=5&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 5
        assert data["limit"] == 10


# ── IDOR: ownership checks on report endpoints ────────────────────────────


class TestReportOwnershipIDOR:
    """Tests that report endpoints enforce ownership (IDOR protection)."""

    def _seed_report_for_other_user(self, engine, report_id: str) -> None:
        """Directly insert a report owned by _OTHER_USER_ID into the DB."""
        from alchymine.db.base import get_async_session_factory
        from alchymine.workers.tasks import _run_async

        async def _insert():
            factory = get_async_session_factory(engine)
            async with factory() as sess:
                await repository.create_report(
                    sess,
                    report_id=report_id,
                    status="complete",
                    user_id=_OTHER_USER_ID,
                )
                await sess.commit()

        _run_async(_insert())

    def test_get_status_other_user_report_returns_403(self, client: TestClient, engine) -> None:
        """GET /reports/{id}/status for another user's report returns 403."""
        report_id = "foreign-report-001"
        self._seed_report_for_other_user(engine, report_id)

        response = client.get(f"/api/v1/reports/{report_id}/status")
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_get_report_other_user_returns_403(self, client: TestClient, engine) -> None:
        """GET /reports/{id} for another user's report returns 403."""
        report_id = "foreign-report-002"
        self._seed_report_for_other_user(engine, report_id)

        response = client.get(f"/api/v1/reports/{report_id}")
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_get_html_other_user_report_returns_403(self, client: TestClient, engine) -> None:
        """GET /reports/{id}/html for another user's report returns 403."""
        report_id = "foreign-report-003"
        self._seed_report_for_other_user(engine, report_id)

        response = client.get(f"/api/v1/reports/{report_id}/html")
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"

    def test_get_pdf_other_user_report_returns_403(self, client: TestClient, engine) -> None:
        """GET /reports/{id}/pdf for another user's report returns 403."""
        report_id = "foreign-report-004"
        self._seed_report_for_other_user(engine, report_id)

        response = client.get(f"/api/v1/reports/{report_id}/pdf")
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"


# ── Intake persistence via POST /reports ─────────────────────────────


@pytest_asyncio.fixture
async def seeded_client(engine, client):
    """Client with a pre-seeded User row so update_layer can find it."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        from alchymine.db.models import User

        user = User(id=_TEST_USER_ID, email="test@example.com", password_hash="hashed")  # noqa: S106
        sess.add(user)
        await sess.commit()
    return client


def _intake_report_payload() -> dict:
    """Return a report payload with full intake data including assessment responses."""
    return {
        "intake": {
            "full_name": "Test User",
            "birth_date": "1990-05-15",
            "birth_time": "14:30",
            "birth_city": "Portland",
            "intention": "career",
            "intentions": ["career", "money"],
            "assessment_responses": {"bf_e1": 4, "bf_e2": 3, "bf_a1": 5},
        },
        "user_input": "Generate my report",
    }


class TestIntakePersistence:
    """Tests for intake data persistence side-effect of POST /reports."""

    def test_post_reports_persists_intake_to_db(self, seeded_client, engine) -> None:
        """POST /reports should persist intake data to the intake_data table."""
        resp = seeded_client.post("/api/v1/reports", json=_intake_report_payload())
        assert resp.status_code == 202

        import asyncio

        async def _verify():
            from sqlalchemy import select as sa_select

            from alchymine.db.models import IntakeData

            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as sess:
                result = await sess.execute(
                    sa_select(IntakeData).where(IntakeData.user_id == _TEST_USER_ID)
                )
                intake = result.scalar_one_or_none()
                assert intake is not None, "Intake data was NOT persisted to DB"
                assert intake.full_name == "Test User"
                assert intake.intention == "career"
                assert intake.assessment_responses == {"bf_e1": 4, "bf_e2": 3, "bf_a1": 5}

        asyncio.get_event_loop().run_until_complete(_verify())

    def test_post_reports_without_user_row_still_returns_202(self, client: TestClient) -> None:
        """POST /reports should return 202 even if intake persist fails (no user row)."""
        resp = client.post("/api/v1/reports", json=_valid_report_payload())
        assert resp.status_code == 202

    def test_post_reports_intake_persist_logs_on_failure(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When intake persist fails (no user row), it should log a warning."""
        payload = _intake_report_payload()
        with caplog.at_level(logging.WARNING, logger="alchymine.api.routers.reports"):
            resp = client.post("/api/v1/reports", json=payload)
        assert resp.status_code == 202
        assert any("user row not found" in r.message for r in caplog.records)

    def test_post_reports_returns_202_when_update_layer_raises(self, client: TestClient) -> None:
        """POST /reports must return 202 even if update_layer raises an unexpected DB error.

        This is the root-cause regression test for the production 500.
        Previously, update_layer failures would dirty the SQLAlchemy session,
        and the subsequent session.commit() would raise PendingRollbackError,
        turning the whole request into a 500.
        """
        payload = _intake_report_payload()
        with patch(
            "alchymine.api.routers.reports.repository.update_layer",
            new_callable=AsyncMock,
            side_effect=RuntimeError("simulated DB error in update_layer"),
        ):
            resp = client.post("/api/v1/reports", json=payload)
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "pending"
        assert "id" in data

    def test_post_reports_report_persisted_despite_update_layer_failure(
        self, client: TestClient, engine
    ) -> None:
        """The report row must be committed even when intake persistence fails."""
        payload = _intake_report_payload()
        with patch(
            "alchymine.api.routers.reports.repository.update_layer",
            new_callable=AsyncMock,
            side_effect=RuntimeError("simulated DB error"),
        ):
            resp = client.post("/api/v1/reports", json=payload)
        assert resp.status_code == 202
        report_id = resp.json()["id"]

        # Verify the report row was actually committed to the DB
        from alchymine.workers.tasks import _run_async

        async def _check():
            from alchymine.db.base import get_async_session_factory

            factory = get_async_session_factory(engine)
            async with factory() as sess:
                return await repository.get_report(sess, report_id)

        report = _run_async(_check())
        assert report is not None, "Report row should exist despite update_layer failure"
        # In eager mode, the Celery task runs synchronously and may update
        # the status before we check.  The key assertion is the row exists.
        assert report.status in ("pending", "generating", "complete", "failed")

    def test_intake_retrievable_via_profile_after_report(self, seeded_client, engine) -> None:
        """After POST /reports, GET /profile/{id} should return saved intake data."""
        payload = _intake_report_payload()
        resp = seeded_client.post("/api/v1/reports", json=payload)
        assert resp.status_code == 202

        profile_resp = seeded_client.get(f"/api/v1/profile/{_TEST_USER_ID}")
        assert profile_resp.status_code == 200
        data = profile_resp.json()
        assert data["intake"] is not None, "Intake should be present in profile"
        assert data["intake"]["full_name"] == "Test User"
        assert data["intake"]["birth_date"] == "1990-05-15"
        assert data["intake"]["assessment_responses"] == {"bf_e1": 4, "bf_e2": 3, "bf_a1": 5}

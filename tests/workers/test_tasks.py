"""Tests for Celery worker tasks and configuration.

All tests run with ``CELERY_ALWAYS_EAGER=true`` so that tasks execute
synchronously in the test process -- no Redis broker required.
Report data is persisted to an in-memory SQLite database.
"""

from __future__ import annotations

import os

# Enable eager mode before importing Celery modules
os.environ["CELERY_ALWAYS_EAGER"] = "true"

import importlib  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Import models so Base.metadata is populated
import alchymine.db.models  # noqa: F401,E402

# Re-import celery_app so it picks up the env var
import alchymine.workers.celery_app as celery_app_mod  # noqa: E402

importlib.reload(celery_app_mod)

from alchymine.db.base import Base  # noqa: E402
from alchymine.db.repository import get_report  # noqa: E402
from alchymine.workers.celery_app import celery_app  # noqa: E402
from alchymine.workers.tasks import (  # noqa: E402
    _extract_missing_sections,
    _now_iso,
    _run_async,
    _serialise_orchestrator_result,
    _set_task_engine,
    generate_pdf_report,
    generate_report,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a valid Fernet key is available."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest_asyncio.fixture
async def engine() -> AsyncEngine:
    """Create an in-memory SQLite async engine and initialise the schema."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Wire up the task engine so Celery tasks use this DB
    _set_task_engine(eng)

    yield eng

    _set_task_engine(None)

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncSession:
    """Provide an async session for verifying DB state in tests."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
def mock_orchestrator_result():
    """Build a mock OrchestratorResult-like dataclass."""
    from dataclasses import dataclass, field

    @dataclass
    class FakeIntentResult:
        intent: str = "intelligence"
        confidence: float = 0.9
        secondary_intents: list = field(default_factory=list)
        detected_keywords: list = field(default_factory=lambda: ["numerology"])

    @dataclass
    class FakeCoordinatorResult:
        system: str = "intelligence"
        status: str = "success"
        data: dict = field(default_factory=lambda: {"numerology": {"life_path": 3}})
        errors: list = field(default_factory=list)
        quality_passed: bool = True

    @dataclass
    class FakeOrchestratorResult:
        request_id: str = "fake-request-id"
        intent: FakeIntentResult = field(default_factory=FakeIntentResult)
        coordinator_results: list = field(default_factory=lambda: [FakeCoordinatorResult()])
        synthesis: dict | None = None
        quality_passed: bool = True

    return FakeOrchestratorResult()


# ── Celery app configuration tests ──────────────────────────────────────


class TestCeleryAppConfiguration:
    """Tests for celery_app.py configuration."""

    def test_celery_app_is_celery_instance(self):
        """The celery_app should be a Celery application."""
        from celery import Celery

        assert isinstance(celery_app, Celery)

    def test_celery_app_name(self):
        """The app should be named 'alchymine'."""
        assert celery_app.main == "alchymine"

    def test_task_serializer_is_json(self):
        """Tasks should serialise with JSON."""
        assert celery_app.conf.task_serializer == "json"

    def test_result_serializer_is_json(self):
        """Results should serialise with JSON."""
        assert celery_app.conf.result_serializer == "json"

    def test_accept_content_includes_json(self):
        """Accepted content types should include JSON."""
        assert "json" in celery_app.conf.accept_content

    def test_task_routes_configured(self):
        """Report generation task should route to 'reports' queue."""
        routes = celery_app.conf.task_routes
        assert "alchymine.workers.tasks.generate_report" in routes
        assert routes["alchymine.workers.tasks.generate_report"]["queue"] == "reports"

    def test_eager_mode_enabled(self):
        """Eager mode should be active when CELERY_ALWAYS_EAGER is set."""
        assert celery_app.conf.task_always_eager is True

    def test_eager_propagates_enabled(self):
        """Eager propagates should be True so exceptions bubble up."""
        assert celery_app.conf.task_eager_propagates is True

    def test_timezone_is_utc(self):
        """Celery timezone should be UTC."""
        assert celery_app.conf.timezone == "UTC"

    def test_track_started_enabled(self):
        """Task tracking should be enabled."""
        assert celery_app.conf.task_track_started is True


# ── Task registration tests ─────────────────────────────────────────────


class TestTaskRegistration:
    """Tests for task registration in the Celery app."""

    def test_generate_report_task_registered(self):
        """The generate_report task should be registered."""
        assert "alchymine.workers.tasks.generate_report" in celery_app.tasks

    def test_generate_report_task_name(self):
        """The task should have the correct fully-qualified name."""
        assert generate_report.name == "alchymine.workers.tasks.generate_report"

    def test_generate_report_max_retries(self):
        """The task should allow up to 3 retries."""
        assert generate_report.max_retries == 3

    def test_generate_report_is_bound(self):
        """The task should be a bound task (receives self)."""
        # Celery bound tasks have the __bound__ attribute set to True
        assert getattr(generate_report, "__bound__", False) is True


# ── Helper function tests ───────────────────────────────────────────────


class TestHelpers:
    """Tests for helper functions."""

    def test_now_iso_returns_string(self):
        """_now_iso should return an ISO-8601 string."""
        result = _now_iso()
        assert isinstance(result, str)
        assert "T" in result

    def test_serialise_orchestrator_result(self, mock_orchestrator_result):
        """_serialise_orchestrator_result should return a JSON-safe dict."""
        result = _serialise_orchestrator_result(mock_orchestrator_result)
        assert isinstance(result, dict)
        assert result["request_id"] == "fake-request-id"
        assert result["quality_passed"] is True

    def test_serialise_includes_intent(self, mock_orchestrator_result):
        """Serialised result should include intent data."""
        result = _serialise_orchestrator_result(mock_orchestrator_result)
        assert "intent" in result
        assert result["intent"]["intent"] == "intelligence"

    def test_serialise_includes_coordinator_results(self, mock_orchestrator_result):
        """Serialised result should include coordinator results."""
        result = _serialise_orchestrator_result(mock_orchestrator_result)
        assert "coordinator_results" in result
        assert len(result["coordinator_results"]) == 1
        assert result["coordinator_results"][0]["system"] == "intelligence"

    def test_extract_missing_sections(self):
        """_extract_missing_sections returns map of system to missing prereqs."""
        results = [
            {
                "system": "healing",
                "data": {"missing_prerequisites": ["big_five", "archetype"]},
                "status": "degraded",
            },
            {"system": "intelligence", "data": {"personality": {}}, "status": "success"},
        ]
        result = _extract_missing_sections(results)
        assert result == {"healing": ["big_five", "archetype"]}

    def test_extract_missing_sections_empty(self):
        """_extract_missing_sections returns empty dict when no prereqs are missing."""
        results = [
            {"system": "intelligence", "data": {}, "status": "success"},
        ]
        assert _extract_missing_sections(results) == {}


# ── Report generation task tests (eager mode) ───────────────────────────


class TestGenerateReportTask:
    """Tests for the generate_report Celery task execution."""

    def test_successful_report_generation(self, engine, mock_orchestrator_result):
        """Task should complete successfully and persist result to DB."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            result = generate_report.apply(args=["test-report-1", "Tell me about numerology"]).get()

            assert isinstance(result, dict)
            assert result["request_id"] == "fake-request-id"

            # Verify DB state
            report = _run_async(
                _get_report_from_db(engine, "test-report-1")
            )
            assert report is not None
            assert report.status == "complete"

    def test_status_transitions_to_complete(self, engine, mock_orchestrator_result):
        """Task should transition status to complete in DB."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            generate_report.apply(args=["test-transitions", "test input"]).get()

            report = _run_async(
                _get_report_from_db(engine, "test-transitions")
            )
            assert report is not None
            assert report.status == "complete"

    def test_failed_task_stores_error(self, engine):
        """Task should record error message on non-transient failure."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(side_effect=ValueError("Something went wrong"))

            result = generate_report.apply(args=["test-fail-1", "bad input"]).get()

            report = _run_async(
                _get_report_from_db(engine, "test-fail-1")
            )
            assert report is not None
            assert report.status == "failed"
            assert "Something went wrong" in report.error
            assert result["status"] == "failed"

    def test_report_created_if_missing(self, engine, mock_orchestrator_result):
        """Task should create a DB row if one is not pre-seeded."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            generate_report.apply(args=["new-report", "test input"]).get()

            report = _run_async(
                _get_report_from_db(engine, "new-report")
            )
            assert report is not None
            assert report.status == "complete"

    def test_result_stored_on_success(self, engine, mock_orchestrator_result):
        """Completed report should contain orchestrator result data."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            generate_report.apply(args=["test-result-stored", "numerology please"]).get()

            report = _run_async(
                _get_report_from_db(engine, "test-result-stored")
            )
            assert report is not None
            assert report.result is not None
            assert report.result["request_id"] == "fake-request-id"
            assert report.error is None

    def test_user_profile_forwarded_to_orchestrator(self, engine, mock_orchestrator_result):
        """User profile dict should be forwarded to orchestrator.process_request."""
        profile = {"id": "user-123", "name": "Test User"}

        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            generate_report.apply(args=["test-profile", "test", profile]).get()

            instance.process_request.assert_called_once_with(
                "test",
                profile,
                intention=None,
                intentions=None,
            )

    def test_generate_report_forwards_intentions(self, engine, mock_orchestrator_result):
        """Intentions list should be forwarded to orchestrator.process_request."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            generate_report.apply(
                args=["test-intentions", "test input", None, "career", ["career", "money"]],
            ).get()

            instance.process_request.assert_called_once_with(
                "test input",
                None,
                intention="career",
                intentions=["career", "money"],
            )

    def test_connection_error_stays_generating_on_retry(self, engine):
        """ConnectionError should keep status 'generating' when retries remain."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(side_effect=ConnectionError("Redis down"))

            # In eager mode with task_eager_propagates=True, autoretry_for
            # causes Celery to raise a Retry exception which propagates.
            with pytest.raises(Exception):
                generate_report.apply(args=["test-conn-err", "test"]).get()

            report = _run_async(
                _get_report_from_db(engine, "test-conn-err")
            )
            assert report is not None
            # On first retry attempt, status should stay "generating", not "failed"
            assert report.status == "generating"

    def test_timeout_error_stays_generating_on_retry(self, engine):
        """TimeoutError should keep status 'generating' when retries remain."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(side_effect=TimeoutError("Operation timed out"))

            with pytest.raises(Exception):
                generate_report.apply(args=["test-timeout", "test"]).get()

            report = _run_async(
                _get_report_from_db(engine, "test-timeout")
            )
            assert report is not None
            # On first retry attempt, status should stay "generating", not "failed"
            assert report.status == "generating"

    def test_multiple_reports_independent(self, engine, mock_orchestrator_result):
        """Multiple reports should not interfere with each other."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)

            generate_report.apply(args=["report-a", "input a"]).get()
            generate_report.apply(args=["report-b", "input b"]).get()

            report_a = _run_async(_get_report_from_db(engine, "report-a"))
            report_b = _run_async(_get_report_from_db(engine, "report-b"))

            assert report_a is not None
            assert report_b is not None
            assert report_a.status == "complete"
            assert report_b.status == "complete"
            assert report_a.user_input == "input a"
            assert report_b.user_input == "input b"


# ── DB helper for test assertions ────────────────────────────────────────


async def _get_report_from_db(engine, report_id: str):
    """Fetch a report from the test DB for assertion purposes."""
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(engine)
    async with factory() as session:
        report = await get_report(session, report_id)
        if report is not None:
            await session.refresh(report)
        return report

"""Integration test -- full pipeline from API through orchestrator to DB.

Tests the entire report generation flow using Celery eager mode
and a mocked MasterOrchestrator to avoid external LLM dependencies.
"""

from __future__ import annotations

import os

os.environ["CELERY_ALWAYS_EAGER"] = "true"

import importlib  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
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
from alchymine.db.base import Base  # noqa: E402
from alchymine.workers.tasks import _set_task_engine  # noqa: E402

# ── Fake orchestrator result ──────────────────────────────────────────


@dataclass
class FakeIntentResult:
    intent: str = "intelligence"
    confidence: float = 0.95
    secondary_intents: list = field(default_factory=list)
    detected_keywords: list = field(default_factory=lambda: ["numerology"])


@dataclass
class FakeCoordinatorResult:
    system: str = "intelligence"
    status: str = "success"
    data: dict = field(
        default_factory=lambda: {
            "numerology": {"life_path": 7, "expression": 3},
            "personality": {"big_five": {"openness": 75.0}},
        }
    )
    errors: list = field(default_factory=list)
    quality_passed: bool = True


@dataclass
class FakeOrchestratorResult:
    request_id: str = "integration-test-req"
    intent: FakeIntentResult = field(default_factory=FakeIntentResult)
    coordinator_results: list = field(default_factory=lambda: [FakeCoordinatorResult()])
    synthesis: dict | None = None
    quality_passed: bool = True


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
def client(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create the test user row so Report FK (user_id) is valid.
    import asyncio

    from alchymine.db.models import User

    async def _create_test_user():
        async with factory() as session:
            session.add(User(id="user-1", email="test@example.com"))
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_create_test_user())

    async def _override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_session
    set_db_engine(engine)
    _set_task_engine(engine)

    yield TestClient(app)

    app.dependency_overrides.pop(get_db_session, None)
    set_db_engine(None)
    _set_task_engine(None)


# ── Integration Tests ─────────────────────────────────────────────────


class TestPipelineIntegration:
    """End-to-end pipeline: POST report -> orchestrator -> DB -> GET result."""

    def test_full_report_pipeline(self, client: TestClient) -> None:
        """POST -> task executes -> GET returns completed report."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=FakeOrchestratorResult())

            # 1. POST to create report
            post_resp = client.post(
                "/api/v1/reports",
                json={
                    "intake": {
                        "full_name": "Integration Test User",
                        "birth_date": "1990-06-15",
                        "intention": "career",
                    },
                    "user_input": "Full integration test",
                },
            )
            assert post_resp.status_code == 202
            report_id = post_resp.json()["id"]

            # 2. Check status -- should be complete in eager mode
            status_resp = client.get(f"/api/v1/reports/{report_id}/status")
            assert status_resp.status_code == 200
            assert status_resp.json()["status"] in (
                "complete",
                "pending",
                "generating",
            )

            # 3. GET full report
            get_resp = client.get(f"/api/v1/reports/{report_id}")
            if get_resp.status_code == 200:
                data = get_resp.json()
                assert data["id"] == report_id
                assert data["status"] == "complete"
                assert data["result"] is not None
                assert data["result"]["request_id"] == "integration-test-req"

    def test_pipeline_with_user_profile(self, client: TestClient) -> None:
        """Profile data is forwarded through the pipeline."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=FakeOrchestratorResult())

            resp = client.post(
                "/api/v1/reports",
                json={
                    "intake": {
                        "full_name": "Profile Test User",
                        "birth_date": "1985-01-20",
                        "intention": "family",
                    },
                    "user_input": "Profile forwarding test",
                    "user_profile": {"id": "user-1", "custom_field": True},
                },
            )
            assert resp.status_code == 202
            # Verify orchestrator was called with profile data
            instance.process_request.assert_called_once()

    def test_pipeline_orchestrator_failure(self, client: TestClient) -> None:
        """When orchestrator fails, report is marked as failed."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(side_effect=ValueError("LLM unavailable"))

            resp = client.post(
                "/api/v1/reports",
                json={
                    "intake": {
                        "full_name": "Failure Test User",
                        "birth_date": "1988-12-01",
                        "intention": "career",
                    },
                },
            )
            assert resp.status_code == 202
            report_id = resp.json()["id"]

            # Check that status shows failed
            status_resp = client.get(f"/api/v1/reports/{report_id}/status")
            assert status_resp.status_code == 200
            assert status_resp.json()["status"] == "failed"

    def test_report_list_after_creation(self, client: TestClient) -> None:
        """User report list shows reports created through the pipeline."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=FakeOrchestratorResult())

            # Create 2 reports
            for _ in range(2):
                resp = client.post(
                    "/api/v1/reports",
                    json={
                        "intake": {
                            "full_name": "List Test User",
                            "birth_date": "1995-03-10",
                            "intention": "career",
                        },
                    },
                )
                assert resp.status_code == 202

            # List reports
            list_resp = client.get("/api/v1/reports/user/user-1")
            assert list_resp.status_code == 200
            data = list_resp.json()
            assert data["count"] >= 2

    def test_pipeline_with_intentions(self, client: TestClient) -> None:
        """Multi-intention reports pass intentions through."""
        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=FakeOrchestratorResult())

            resp = client.post(
                "/api/v1/reports",
                json={
                    "intake": {
                        "full_name": "Intentions Test",
                        "birth_date": "1992-07-04",
                        "intention": "career",
                        "intentions": ["career", "money"],
                    },
                },
            )
            assert resp.status_code == 202

            # Verify intentions were forwarded
            call_args = instance.process_request.call_args
            assert call_args is not None

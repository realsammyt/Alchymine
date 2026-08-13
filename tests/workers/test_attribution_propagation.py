"""Attribution must survive the Celery bridge.

``_run_async`` has two paths. Path A (``asyncio.run``, no loop running)
propagates ContextVars for free. Path B runs the coroutine in a worker
thread, and a fresh thread starts with an empty context, so every
ContextVar reads its default unless the context is copied across
explicitly.

Path B is the ``CELERY_ALWAYS_EAGER`` path, which is how the whole test
suite runs. Without the copy, attribution would silently be lost exactly
where the test suite cannot see it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.db.base import Base
from alchymine.llm.attribution import current_attribution, set_attribution
from alchymine.workers.tasks import _run_async, _set_task_engine, generate_report


@pytest.fixture
def mock_orchestrator_result():  # noqa: ANN201
    """A minimal OrchestratorResult stand-in, as in tests/workers/test_tasks.py."""
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


@pytest_asyncio.fixture
async def engine() -> AsyncEngine:
    eng = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _set_task_engine(eng)
    yield eng
    _set_task_engine(None)
    await eng.dispose()


async def _read_attribution() -> tuple[str | None, str | None, str | None]:
    return current_attribution()


class TestRunAsyncPropagation:
    @pytest.mark.asyncio
    async def test_path_b_carries_attribution_into_the_worker_thread(self) -> None:
        """A running loop forces the ThreadPoolExecutor path."""
        set_attribution(user_id="u-eager", surface="report_narrative")
        assert _run_async(_read_attribution()) == ("u-eager", "report_narrative", None)

    def test_path_a_carries_attribution_too(self) -> None:
        """No running loop: asyncio.run stays in the calling context."""
        set_attribution(user_id="u-worker", surface="report_narrative", request_id=None)
        assert _run_async(_read_attribution()) == ("u-worker", "report_narrative", None)


class TestGenerateReportAttribution:
    def test_narratives_are_attributed_to_the_report_owner(
        self, engine, mock_orchestrator_result
    ) -> None:
        seen: list[tuple[str | None, str | None, str | None]] = []

        class _FakeGenerator:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def generate_all(self, systems: list[str], engine_data: dict) -> dict:
                seen.append(current_attribution())
                return {}

        _run_async(_seed_report(engine, "report-attr", "user-owner"))

        with patch("alchymine.workers.tasks.MasterOrchestrator") as MockOrch:
            instance = MockOrch.return_value
            instance.process_request = AsyncMock(return_value=mock_orchestrator_result)
            with patch("alchymine.llm.narrative.NarrativeGenerator", _FakeGenerator):
                generate_report.apply(args=["report-attr", "tell me about numerology"]).get()

        assert seen == [("user-owner", "report_narrative", None)]


async def _seed_report(engine: AsyncEngine, report_id: str, user_id: str) -> None:
    from alchymine.db.models import User
    from alchymine.db.repository import create_report

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.com"))
        await session.commit()
        await create_report(session, report_id=report_id, user_id=user_id, user_input="hi")
        await session.commit()

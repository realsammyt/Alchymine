"""A real Celery task, through the thread bridge, into a real ledger row.

Every link in this chain is pinned somewhere else: attribution survives
``_run_async``'s worker thread (``test_attribution_propagation``), the
Claude chokepoint writes a priced row (``test_ledger_chokepoints``), the
report fan-out shares one user id. What none of those show is that the
links compose.

They meet at three boundaries, and each one could swallow a write while
every unit test still passed:

1. ``_run_async`` path B runs the coroutine in a worker thread with its own
   event loop, so the row is written from a context that was copied rather
   than inherited.
2. The ledger write is a detached task under ``asyncio.shield``, so it has
   to finish before ``asyncio.run`` tears that loop down.
3. The row lands through a session factory built from the module-level
   engine singleton, which the worker thread has to be able to reach.

So this starts where production starts: ``generate_report.apply()``, called
from inside a running loop so ``_run_async`` takes path B, with only the
orchestrator and the Anthropic SDK faked. The ledger, the meters, the
attribution and the thread bridge are all the real thing.

Asked for by the slice 2 review.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.deps import set_db_engine
from alchymine.config import get_settings
from alchymine.db.base import Base
from alchymine.db.models import UsageRecord, User
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_SPEND_MICROS_DAILY,
    METER_SPEND_MICROS_MONTHLY,
    clear_ledger_degraded,
    get_count,
    current_month_key,
)
from alchymine.llm.budget import reset_budget_alerts
from alchymine.workers.tasks import _set_task_engine, generate_report

OWNER_ID = "user-report-owner"
REPORT_ID = "report-e2e"
SONNET = "claude-sonnet-4-6"

# One narrative call, priced from the table: 3 micros per input token,
# 15 per output token.
INPUT_TOKENS = 1_200
OUTPUT_TOKENS = 400
EXPECTED_MICROS = INPUT_TOKENS * 3 + OUTPUT_TOKENS * 15


@dataclass
class _FakeIntentResult:
    intent: str = "intelligence"
    confidence: float = 0.9
    secondary_intents: list = field(default_factory=list)
    detected_keywords: list = field(default_factory=lambda: ["numerology"])


@dataclass
class _FakeCoordinatorResult:
    system: str = "intelligence"
    status: str = "success"
    data: dict = field(default_factory=lambda: {"numerology": {"life_path": 3}})
    errors: list = field(default_factory=list)
    quality_passed: bool = True


@dataclass
class _FakeOrchestratorResult:
    request_id: str = "fake-request-id"
    intent: _FakeIntentResult = field(default_factory=_FakeIntentResult)
    coordinator_results: list = field(default_factory=lambda: [_FakeCoordinatorResult()])
    synthesis: dict | None = None
    quality_passed: bool = True


@dataclass
class _Usage:
    input_tokens: int = INPUT_TOKENS
    output_tokens: int = OUTPUT_TOKENS
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """One database for the task, the ledger and the meters alike.

    The worker thread reads the engine back through the ``api.deps``
    singleton, which is why ``set_db_engine`` matters here as much as
    ``_set_task_engine``: without it the ledger write would go looking for
    a Postgres that is not there and the row would be lost to a log line.
    """
    eng = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(eng, expire_on_commit=False)
    async with factory() as session:
        session.add(User(id=OWNER_ID, email="owner@example.com"))
        await session.commit()

    _set_task_engine(eng)
    set_db_engine(eng)
    clear_ledger_degraded()
    reset_budget_alerts()
    try:
        yield eng
    finally:
        _set_task_engine(None)
        set_db_engine(None)
        clear_ledger_degraded()
        reset_budget_alerts()
        await eng.dispose()


async def _seed_report(eng: AsyncEngine) -> None:
    from alchymine.db.repository import create_report

    factory = async_sessionmaker(eng, expire_on_commit=False)
    async with factory() as session:
        await create_report(
            session, report_id=REPORT_ID, user_id=OWNER_ID, user_input="tell me about numerology"
        )
        await session.commit()


async def _rows(eng: AsyncEngine) -> list[UsageRecord]:
    factory = async_sessionmaker(eng, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(select(UsageRecord).order_by(UsageRecord.id))
        return list(result.scalars().all())


def _run_the_task() -> None:
    """Run generate_report exactly as eager Celery does.

    Called from an async test on purpose. A running loop is what pushes
    ``_run_async`` onto path B, the thread bridge, which is the boundary
    this module exists to test.
    """
    response = MagicMock()
    response.content = [MagicMock(text="a gentle narrative about the number three")]
    response.usage = _Usage()
    fake_sdk = MagicMock()
    fake_sdk.messages.create = AsyncMock(return_value=response)

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        get_settings.cache_clear()
        try:
            with patch("alchymine.workers.tasks.MasterOrchestrator") as orchestrator:
                orchestrator.return_value.process_request = AsyncMock(
                    return_value=_FakeOrchestratorResult()
                )
                with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
                    generate_report.apply(
                        args=[REPORT_ID, "tell me about numerology"]
                    ).get()
        finally:
            get_settings.cache_clear()


class TestTheWholeChain:
    async def test_a_report_task_lands_one_priced_ledger_row(self, engine) -> None:
        await _seed_report(engine)

        _run_the_task()

        rows = await _rows(engine)
        assert len(rows) == 1, "the narrative call must reach the ledger, not just the log"
        assert rows[0].cost_micros == EXPECTED_MICROS
        assert rows[0].model == SONNET
        assert rows[0].provider == "anthropic"
        assert rows[0].input_tokens == INPUT_TOKENS
        assert rows[0].estimated is False

    async def test_the_row_names_the_report_owner(self, engine) -> None:
        """The whole point of copying the context across the thread."""
        await _seed_report(engine)

        _run_the_task()

        row = (await _rows(engine))[0]
        assert row.user_id == OWNER_ID
        assert row.scope == OWNER_ID
        assert row.surface == "report_narrative"

    async def test_both_spend_meters_move(self, engine) -> None:
        """Written from the worker thread's loop, read back from this one."""
        await _seed_report(engine)

        _run_the_task()

        assert (
            await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)
        ) == EXPECTED_MICROS
        assert (
            await get_count(
                scope=OWNER_ID,
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=current_month_key(),
            )
        ) == EXPECTED_MICROS

    async def test_an_orphan_report_records_the_spend_as_unattributed(self, engine) -> None:
        """reports.py creates rows with no user; that spend is still ours."""
        from alchymine.db.repository import create_report

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            await create_report(
                session, report_id=REPORT_ID, user_id=None, user_input="orphan"
            )
            await session.commit()

        _run_the_task()

        row = (await _rows(engine))[0]
        assert row.user_id is None
        assert row.scope == "unattributed"
        # Nameless, but not free: the global meter still holds it.
        assert (
            await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)
        ) == EXPECTED_MICROS

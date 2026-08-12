"""Tests for the atomic usage-counter primitive backing every cost ceiling.

These cover the properties the cost meters depend on: increments are
atomic (no lost updates under concurrency), counts are scoped per
(scope, meter, UTC day), ceilings raise instead of returning a boolean
the caller could forget to check, and a broken database blocks the call
rather than letting it through unmetered.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.db.base import Base
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    CostCeilingExceeded,
    consume,
    current_period_key,
    get_count,
    increment_and_get,
    next_period_start,
)


@pytest_asyncio.fixture
async def counter_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Point the counter module's engine at a fresh in-memory SQLite DB."""
    from alchymine.api.deps import set_db_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_db_engine(engine)
    yield engine
    set_db_engine(None)
    await engine.dispose()


class TestPeriodKeys:
    def test_period_key_is_the_utc_date(self) -> None:
        moment = datetime(2026, 8, 12, 23, 59, 59, tzinfo=UTC)
        assert current_period_key(moment) == "2026-08-12"

    def test_period_key_rolls_over_at_utc_midnight(self) -> None:
        before = datetime(2026, 8, 12, 23, 59, 59, tzinfo=UTC)
        after = datetime(2026, 8, 13, 0, 0, 0, tzinfo=UTC)
        assert current_period_key(before) != current_period_key(after)

    def test_next_period_start_is_next_utc_midnight(self) -> None:
        moment = datetime(2026, 8, 12, 14, 30, tzinfo=UTC)
        assert next_period_start(moment) == datetime(2026, 8, 13, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
class TestIncrementAndGet:
    async def test_first_increment_returns_one(self, counter_engine: AsyncEngine) -> None:
        count = await increment_and_get(scope=GLOBAL_SCOPE, meter="llm_calls")
        assert count == 1

    async def test_increments_accumulate(self, counter_engine: AsyncEngine) -> None:
        for expected in (1, 2, 3):
            assert await increment_and_get(scope=GLOBAL_SCOPE, meter="llm_calls") == expected

    async def test_concurrent_increments_do_not_lose_counts(
        self, counter_engine: AsyncEngine
    ) -> None:
        results = await asyncio.gather(
            *(increment_and_get(scope=GLOBAL_SCOPE, meter="llm_calls") for _ in range(20))
        )
        # Every caller must see a distinct value, and the final count must
        # equal the number of increments — a read-modify-write race would
        # produce duplicates and a total below 20.
        assert sorted(results) == list(range(1, 21))
        assert await get_count(scope=GLOBAL_SCOPE, meter="llm_calls") == 20

    async def test_scopes_are_isolated(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope="user-a", meter="art_generations")
        await increment_and_get(scope="user-a", meter="art_generations")
        await increment_and_get(scope="user-b", meter="art_generations")
        assert await get_count(scope="user-a", meter="art_generations") == 2
        assert await get_count(scope="user-b", meter="art_generations") == 1

    async def test_meters_are_isolated(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope=GLOBAL_SCOPE, meter="llm_calls")
        assert await get_count(scope=GLOBAL_SCOPE, meter="art_generations") == 0

    async def test_periods_are_isolated(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope=GLOBAL_SCOPE, meter="llm_calls", period_key="2026-08-12")
        await increment_and_get(scope=GLOBAL_SCOPE, meter="llm_calls", period_key="2026-08-12")
        assert (
            await get_count(scope=GLOBAL_SCOPE, meter="llm_calls", period_key="2026-08-13")
        ) == 0

    async def test_unknown_counter_reads_as_zero(self, counter_engine: AsyncEngine) -> None:
        assert await get_count(scope=GLOBAL_SCOPE, meter="never_used") == 0


@pytest.mark.asyncio
class TestConsume:
    async def test_allows_calls_up_to_the_ceiling(self, counter_engine: AsyncEngine) -> None:
        for _ in range(3):
            await consume(scope="user-a", meter="art_generations", ceiling=3)
        assert await get_count(scope="user-a", meter="art_generations") == 3

    async def test_blocks_the_call_past_the_ceiling(self, counter_engine: AsyncEngine) -> None:
        for _ in range(3):
            await consume(scope="user-a", meter="art_generations", ceiling=3)
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await consume(scope="user-a", meter="art_generations", ceiling=3)
        assert excinfo.value.meter == "art_generations"
        assert excinfo.value.scope == "user-a"

    async def test_exhausted_ceiling_reports_when_to_retry(
        self, counter_engine: AsyncEngine
    ) -> None:
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await consume(scope="user-a", meter="art_generations", ceiling=0)
        retry_at = excinfo.value.retry_at
        assert retry_at.tzinfo is not None
        assert retry_at > datetime.now(UTC)

    async def test_ceiling_resets_on_the_next_utc_day(self, counter_engine: AsyncEngine) -> None:
        for _ in range(3):
            await consume(
                scope="user-a", meter="art_generations", ceiling=3, period_key="2026-08-12"
            )
        with pytest.raises(CostCeilingExceeded):
            await consume(
                scope="user-a", meter="art_generations", ceiling=3, period_key="2026-08-12"
            )
        # A new UTC day starts from zero.
        await consume(scope="user-a", meter="art_generations", ceiling=3, period_key="2026-08-13")

    async def test_fails_closed_when_the_database_is_unreachable(
        self, counter_engine: AsyncEngine
    ) -> None:
        """A broken meter must block the call, never fall through to unlimited."""
        from alchymine.api.deps import set_db_engine

        broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/nothing")
        set_db_engine(broken)
        try:
            with pytest.raises(CostCeilingExceeded) as excinfo:
                await consume(scope=GLOBAL_SCOPE, meter="llm_calls", ceiling=1_000_000)
            assert excinfo.value.reason == "meter_unavailable"
        finally:
            set_db_engine(counter_engine)
            await broken.dispose()

"""Tests for the atomic usage-counter primitive backing every cost ceiling.

These cover the properties the cost meters depend on: increments are
atomic (no lost updates under concurrency), counts are scoped per
(scope, meter, UTC day), ceilings raise instead of returning a boolean
the caller could forget to check, and a broken database blocks the call
rather than letting it through unmetered.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.db.base import Base
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    CostCeilingExceeded,
    check_ceiling,
    clear_ledger_degraded,
    consume,
    current_month_key,
    current_period_key,
    get_count,
    increment_and_get,
    ledger_is_degraded,
    mark_ledger_degraded,
    next_month_start,
    next_period_start,
    refund,
)


@pytest.fixture(autouse=True)
def _clean_ledger_flag() -> Iterator[None]:
    """The degraded flag is process-local; never carry it between tests."""
    clear_ledger_degraded()
    yield
    clear_ledger_degraded()


@pytest_asyncio.fixture
async def counter_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Point the counter module's engine at an empty usage_counters table.

    Defaults to in-memory SQLite. Set ``TEST_COUNTER_DATABASE_URL`` to an
    asyncpg URL to run this same file against a real PostgreSQL instance
    that has already had ``alembic upgrade head`` applied. That is what
    proves ``increment_and_get``'s ``pg_insert`` branch actually infers
    its conflict target from migration 0016's unique constraint. SQLite
    exercises a different dialect's ON CONFLICT and cannot show that.
    """
    from alchymine.api.deps import set_db_engine

    pg_url = os.environ.get("TEST_COUNTER_DATABASE_URL")
    if pg_url:
        engine = create_async_engine(pg_url)
        # Schema comes from the migration, deliberately not create_all:
        # the point is to test against the shape production will have.
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM usage_counters"))
    else:
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


@pytest.mark.asyncio
class TestRefund:
    """Giving back usage that was charged but delivered nothing."""

    async def test_refund_gives_the_unit_back(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope="user-a", meter="art_generations")
        await increment_and_get(scope="user-a", meter="art_generations")

        await refund(scope="user-a", meter="art_generations")

        assert await get_count(scope="user-a", meter="art_generations") == 1

    async def test_refund_restores_a_blocked_allowance(self, counter_engine: AsyncEngine) -> None:
        """A refunded slot is usable again, not merely cosmetic."""
        for _ in range(3):
            await consume(scope="user-a", meter="art_generations", ceiling=3)
        await refund(scope="user-a", meter="art_generations")

        # The slot came back, so this must not raise.
        await consume(scope="user-a", meter="art_generations", ceiling=3)

    async def test_refund_never_goes_negative(self, counter_engine: AsyncEngine) -> None:
        """A double refund must not mint free allowance."""
        await increment_and_get(scope="user-a", meter="art_generations")

        await refund(scope="user-a", meter="art_generations")
        await refund(scope="user-a", meter="art_generations")

        assert await get_count(scope="user-a", meter="art_generations") == 0

    async def test_refund_of_an_unknown_counter_is_a_no_op(
        self, counter_engine: AsyncEngine
    ) -> None:
        await refund(scope="user-nobody", meter="art_generations")
        assert await get_count(scope="user-nobody", meter="art_generations") == 0

    async def test_refund_touches_only_its_own_counter(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope="user-a", meter="art_generations")
        await increment_and_get(scope="user-b", meter="art_generations")

        await refund(scope="user-a", meter="art_generations")

        assert await get_count(scope="user-b", meter="art_generations") == 1


class TestMonthKeys:
    """Monthly meters key on ``YYYY-MM``; the ledger denormalizes the same key."""

    def test_month_key_is_the_utc_month(self) -> None:
        moment = datetime(2026, 8, 13, 14, 22, 5, tzinfo=UTC)
        assert current_month_key(moment) == "2026-08"

    def test_month_key_rolls_over_at_the_utc_month_boundary(self) -> None:
        before = datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC)
        after = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
        assert current_month_key(before) == "2026-08"
        assert current_month_key(after) == "2026-09"

    def test_next_month_start_is_the_first_of_next_month(self) -> None:
        moment = datetime(2026, 8, 13, 14, 30, tzinfo=UTC)
        assert next_month_start(moment) == datetime(2026, 9, 1, 0, 0, tzinfo=UTC)

    def test_next_month_start_rolls_the_year_over(self) -> None:
        moment = datetime(2026, 12, 31, 23, 59, tzinfo=UTC)
        assert next_month_start(moment) == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
class TestCheckCeiling:
    """Read-only gate for spend meters: check, call, then record what it cost."""

    async def test_returns_the_current_count(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope=GLOBAL_SCOPE, meter="spend_micros_daily", amount=4200)
        count = await check_ceiling(
            scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=15_000_000
        )
        assert count == 4200

    async def test_never_increments(self, counter_engine: AsyncEngine) -> None:
        """A ledger that counts money we did not spend is simply wrong."""
        await increment_and_get(scope=GLOBAL_SCOPE, meter="spend_micros_daily", amount=100)
        for _ in range(3):
            await check_ceiling(scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=10_000)
        assert await get_count(scope=GLOBAL_SCOPE, meter="spend_micros_daily") == 100

    async def test_raises_at_the_ceiling(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope=GLOBAL_SCOPE, meter="spend_micros_daily", amount=500)
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await check_ceiling(scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=500)
        assert excinfo.value.reason == "ceiling_reached"
        assert excinfo.value.meter == "spend_micros_daily"

    async def test_raises_past_the_ceiling(self, counter_engine: AsyncEngine) -> None:
        await increment_and_get(scope=GLOBAL_SCOPE, meter="spend_micros_daily", amount=501)
        with pytest.raises(CostCeilingExceeded):
            await check_ceiling(scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=500)

    async def test_an_empty_counter_passes(self, counter_engine: AsyncEngine) -> None:
        assert await check_ceiling(scope="user-a", meter="spend_micros_monthly", ceiling=1) == 0

    async def test_retry_at_is_next_utc_midnight_for_a_daily_key(
        self, counter_engine: AsyncEngine
    ) -> None:
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await check_ceiling(
                scope=GLOBAL_SCOPE,
                meter="spend_micros_daily",
                ceiling=0,
                period_key=current_period_key(),
            )
        assert excinfo.value.retry_at == next_period_start()

    async def test_retry_at_is_the_next_month_for_a_month_key(
        self, counter_engine: AsyncEngine
    ) -> None:
        """A monthly meter that says "try again tomorrow" is a lie."""
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await check_ceiling(
                scope="user-a",
                meter="spend_micros_monthly",
                ceiling=0,
                period_key=current_month_key(),
            )
        assert excinfo.value.retry_at == next_month_start()

    async def test_fails_closed_when_the_counter_cannot_be_read(
        self, counter_engine: AsyncEngine
    ) -> None:
        from alchymine.api.deps import set_db_engine

        broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/nothing")
        set_db_engine(broken)
        try:
            with pytest.raises(CostCeilingExceeded) as excinfo:
                await check_ceiling(
                    scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=1_000_000
                )
            assert excinfo.value.reason == "meter_unavailable"
        finally:
            set_db_engine(counter_engine)
            await broken.dispose()


@pytest.mark.asyncio
class TestLedgerDegradedFlag:
    """A ledger write that failed must block the *next* cost-bearing call."""

    async def test_starts_clear(self, counter_engine: AsyncEngine) -> None:
        assert ledger_is_degraded() is False

    async def test_a_degraded_ledger_blocks_the_next_check(
        self, counter_engine: AsyncEngine
    ) -> None:
        mark_ledger_degraded("insert failed")
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await check_ceiling(scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=1_000_000)
        assert excinfo.value.reason == "meter_unavailable"

    async def test_clearing_the_flag_reopens_the_gate(self, counter_engine: AsyncEngine) -> None:
        mark_ledger_degraded("insert failed")
        clear_ledger_degraded()
        assert ledger_is_degraded() is False
        assert await check_ceiling(scope=GLOBAL_SCOPE, meter="spend_micros_daily", ceiling=10) == 0

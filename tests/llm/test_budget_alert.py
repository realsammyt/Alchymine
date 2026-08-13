"""The 80% monthly budget alert, and the kill switch that does not exist.

Design section 7.1 is explicit: crossing 80% of the monthly budget logs at
ERROR and stops nothing. An automatic monthly cutoff would convert an
overspend into an outage of unknown length, potentially weeks, and the
person who should make that call is a human looking at the number.

So what is tested here is a log line and the *absence* of enforcement.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from alchymine.config import get_settings
from alchymine.db.models import UsageRecord
from alchymine.db.usage_counters import current_month_key
from alchymine.llm.budget import (
    MONTHLY_ALERT_FRACTION,
    check_monthly_budget,
    reset_budget_alerts,
)

# asyncio_mode="auto" handles the async tests; a module-level mark would
# only warn on the sync one.


@contextmanager
def _env(**overrides: object) -> Iterator[None]:
    values = {key.upper(): str(value) for key, value in overrides.items()}
    with patch.dict(os.environ, values, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _fresh_alert_state() -> Iterator[None]:
    """The alert latch is process-local, so it leaks between tests."""
    reset_budget_alerts()
    yield
    reset_budget_alerts()


async def _spend(engine, micros: int) -> None:
    """Put *micros* of month-to-date spend in the ledger."""
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(engine)
    async with factory() as session:
        session.add(
            UsageRecord(
                user_id=None,
                scope="unattributed",
                surface="chat",
                meter="llm_calls",
                provider="anthropic",
                model="claude-sonnet-4-6",
                cost_micros=micros,
                period_key="2026-08-13",
                month_key=current_month_key(),
            )
        )
        await session.commit()


class TestTheThresholdItself:
    def test_the_fraction_is_eighty_percent(self) -> None:
        assert MONTHLY_ALERT_FRACTION == 0.8

    async def test_below_the_threshold_says_nothing(
        self, cost_meter_db, caplog: pytest.LogCaptureFixture
    ) -> None:
        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 799_999)  # 79.99% of 1_000_000

            with caplog.at_level(logging.ERROR, logger="alchymine.llm.budget"):
                await check_monthly_budget()

        assert caplog.records == []

    async def test_crossing_the_threshold_logs_at_error(
        self, cost_meter_db, caplog: pytest.LogCaptureFixture
    ) -> None:
        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 800_000)

            with caplog.at_level(logging.ERROR, logger="alchymine.llm.budget"):
                await check_monthly_budget()

        assert len(caplog.records) == 1
        message = caplog.records[0].getMessage()
        assert "COST_BUDGET_ALERT" in message
        assert "80%" in message
        assert current_month_key() in message

    async def test_it_says_out_loud_that_nothing_was_stopped(
        self, cost_meter_db, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An operator reading the line must not assume spending halted."""
        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 900_000)

            with caplog.at_level(logging.ERROR, logger="alchymine.llm.budget"):
                await check_monthly_budget()

        assert "Nothing has been stopped" in caplog.records[0].getMessage()

    async def test_the_same_threshold_does_not_log_twice(
        self, cost_meter_db, caplog: pytest.LogCaptureFixture
    ) -> None:
        """One line per crossing, not one per paid call for the rest of the month."""
        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 850_000)

            with caplog.at_level(logging.ERROR, logger="alchymine.llm.budget"):
                await check_monthly_budget()
                await check_monthly_budget(force=True)
                await check_monthly_budget(force=True)

        assert len(caplog.records) == 1

    async def test_going_over_budget_logs_a_second_time(
        self, cost_meter_db, caplog: pytest.LogCaptureFixture
    ) -> None:
        """80% and 100% are different news."""
        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 850_000)
            with caplog.at_level(logging.ERROR, logger="alchymine.llm.budget"):
                await check_monthly_budget()
                await _spend(cost_meter_db, 200_000)  # now 1_050_000, over budget
                await check_monthly_budget(force=True)

        messages = [record.getMessage() for record in caplog.records]
        assert len(messages) == 2
        assert "80%" in messages[0]
        assert "100%" in messages[1]


class TestItStopsNothing:
    async def test_being_over_budget_does_not_block_a_paid_call(self, cost_meter_db) -> None:
        """There is no automatic monthly kill switch, by design."""
        from alchymine.llm.cost_guard import charge_paid_call

        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 10_000_000)  # ten times the budget
            await check_monthly_budget()

            # The daily ceiling is what can block, and it is untouched here.
            await charge_paid_call()


class TestItIsCheapEnoughToLiveOnTheWritePath:
    async def test_repeat_calls_are_throttled_rather_than_re_querying(
        self, cost_meter_db
    ) -> None:
        """One aggregate per paid call would be a real cost; this is not that."""
        with _env(monthly_llm_spend_budget_usd=1.0):
            await _spend(cost_meter_db, 100)

            with patch("alchymine.llm.budget._month_to_date_micros") as read:
                read.return_value = 0
                await check_monthly_budget()
                await check_monthly_budget()
                await check_monthly_budget()

        assert read.call_count == 1

    async def test_a_broken_read_never_reaches_the_caller(self, cost_meter_db) -> None:
        """This runs on the ledger write path; it must not break a reply."""
        with patch(
            "alchymine.llm.budget._month_to_date_micros",
            side_effect=RuntimeError("database is on fire"),
        ):
            await check_monthly_budget()  # must not raise

    async def test_a_zero_budget_is_not_a_division_by_zero(self, cost_meter_db) -> None:
        with _env(monthly_llm_spend_budget_usd=0.0):
            await _spend(cost_meter_db, 1_000)

            await check_monthly_budget()  # must not raise

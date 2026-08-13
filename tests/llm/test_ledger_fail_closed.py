"""What a failed ledger write does to the next paid call.

The rail: a cost-bearing call whose usage record cannot be written must not
proceed silently. Applied to a call already in flight that would mean
raising after the user has read the reply, which does not unspend the money.
So the rule is loud now, block the *next* one — and the block lives in
``charge_paid_call``, the one function all three egress sites already call.

Two properties keep that from turning a bookkeeping fault into a permanent
outage: a degraded ledger stops blocking once a write succeeds, and it stops
blocking on its own after a cooldown so one transient failure cannot brick
every paid surface in the process until someone restarts it.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from alchymine.config import get_settings
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_LLM_CALLS,
    CostCeilingExceeded,
    clear_ledger_degraded,
    get_count,
    ledger_is_degraded,
    mark_ledger_degraded,
)
from alchymine.llm.cost_guard import charge_paid_call
from alchymine.llm.ledger import record_usage

HAIKU = "claude-haiku-4-5-20251001"


@pytest.fixture(autouse=True)
def _clean_flag() -> Iterator[None]:
    clear_ledger_degraded()
    yield
    clear_ledger_degraded()


class TestDegradedLedgerBlocksTheNextCall:
    async def test_charge_paid_call_raises_while_degraded(self, cost_meter_db) -> None:
        mark_ledger_degraded("insert failed")
        with pytest.raises(CostCeilingExceeded) as excinfo:
            await charge_paid_call()
        assert excinfo.value.reason == "meter_unavailable"
        assert excinfo.value.meter == METER_LLM_CALLS
        assert excinfo.value.scope == GLOBAL_SCOPE

    async def test_the_blocked_call_never_reaches_the_counter(self, cost_meter_db) -> None:
        """Blocked means not attempted, so it must not move the call meter."""
        mark_ledger_degraded("insert failed")
        with pytest.raises(CostCeilingExceeded):
            await charge_paid_call()
        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) == 0

    async def test_a_healthy_ledger_does_not_block(self, cost_meter_db) -> None:
        await charge_paid_call()
        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) == 1

    async def test_a_successful_write_reopens_the_gate(self, cost_meter_db) -> None:
        mark_ledger_degraded("insert failed")
        await record_usage(
            meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
        )
        assert ledger_is_degraded() is False
        await charge_paid_call()  # must not raise


class TestDegradedLedgerRecoversOnItsOwn:
    """One failed INSERT must not brick every paid surface until a restart.

    The block is what makes the ledger fail closed, but a hard block has no
    way out: no call proceeds, so no write happens, so nothing ever clears
    the flag. After a cooldown the breaker goes half-open and lets one call
    through; if its write lands the ledger is healthy again, and if it fails
    the cooldown restarts.
    """

    async def test_the_flag_expires_after_the_cooldown(self, cost_meter_db) -> None:
        mark_ledger_degraded("insert failed")
        assert ledger_is_degraded() is True

        with patch("alchymine.db.usage_counters.LEDGER_DEGRADED_RETRY_SECONDS", 0.0):
            assert ledger_is_degraded() is False
            await charge_paid_call()  # the half-open probe goes through

    async def test_a_failure_during_the_probe_restarts_the_cooldown(self, cost_meter_db) -> None:
        with patch("alchymine.db.usage_counters.LEDGER_DEGRADED_RETRY_SECONDS", 0.0):
            mark_ledger_degraded("insert failed")
            assert ledger_is_degraded() is False
        mark_ledger_degraded("insert failed again")
        assert ledger_is_degraded() is True


class TestTheKillSwitchIsAnEscapeHatch:
    """Disabling the ledger must not leave the degraded flag holding the door.

    An operator who turns the ledger off to stop a write storm is deciding to
    fly without spend accounting for a while. Blocking every paid call on a
    flag the disabled ledger can no longer clear would make that switch the
    opposite of an escape hatch.
    """

    async def test_a_disabled_ledger_does_not_block_paid_calls(
        self, cost_meter_db, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mark_ledger_degraded("insert failed")
        monkeypatch.setenv("USAGE_LEDGER_ENABLED", "false")
        get_settings.cache_clear()
        try:
            await charge_paid_call()
        finally:
            get_settings.cache_clear()

    async def test_a_disabled_ledger_clears_the_flag(
        self, cost_meter_db, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mark_ledger_degraded("insert failed")
        monkeypatch.setenv("USAGE_LEDGER_ENABLED", "false")
        get_settings.cache_clear()
        try:
            await record_usage(meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU)
        finally:
            get_settings.cache_clear()
        assert ledger_is_degraded() is False


class TestRecoveryIsNotDeclaredEarly:
    """The row and both meters have to land before the ledger is healthy."""

    async def test_a_failed_meter_increment_keeps_the_ledger_degraded(
        self, cost_meter_db
    ) -> None:
        with patch(
            "alchymine.llm.ledger.increment_and_get",
            AsyncMock(side_effect=RuntimeError("counter table is gone")),
        ):
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
        assert ledger_is_degraded() is True

    async def test_the_row_still_lands_when_the_meters_fail(self, cost_meter_db) -> None:
        """Losing the counter must not also lose the history."""
        from sqlalchemy import func, select

        from alchymine.db.base import get_async_session_factory
        from alchymine.db.models import UsageRecord

        with patch(
            "alchymine.llm.ledger.increment_and_get",
            AsyncMock(side_effect=RuntimeError("counter table is gone")),
        ):
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )

        factory = get_async_session_factory(cost_meter_db)
        async with factory() as session:
            result = await session.execute(select(func.count()).select_from(UsageRecord))
            assert int(result.scalar_one()) == 1

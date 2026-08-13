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
    claim_ledger_admission,
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

    async def test_exactly_one_call_is_admitted_when_the_cooldown_lapses(
        self, cost_meter_db
    ) -> None:
        """One probe, not an open door.

        A purely time-based lapse admits every caller until somebody's write
        fails and re-arms it. Under a sustained database failure with steady
        traffic that is a whole cooldown's worth of unrecorded spend per
        cycle — and the report path alone fires five paid calls at once.
        """
        import asyncio

        mark_ledger_degraded("insert failed")

        with patch("alchymine.db.usage_counters._degraded_retry_seconds", return_value=0.0):
            results = await asyncio.gather(
                *[charge_paid_call() for _ in range(5)], return_exceptions=True
            )

        admitted = [r for r in results if not isinstance(r, BaseException)]
        blocked = [r for r in results if isinstance(r, CostCeilingExceeded)]
        assert len(admitted) == 1, "the half-open window admits one probe, not everyone"
        assert len(blocked) == 4

    async def test_the_probe_holds_the_gate_until_its_write_resolves(
        self, cost_meter_db
    ) -> None:
        mark_ledger_degraded("insert failed")

        with patch("alchymine.db.usage_counters._degraded_retry_seconds", return_value=0.0):
            await charge_paid_call()  # claims the probe
            # The probe has not written anything yet, so the gate stays shut
            # even though the cooldown has long since lapsed.
            with pytest.raises(CostCeilingExceeded):
                await charge_paid_call()

    async def test_a_successful_probe_write_reopens_the_gate(self, cost_meter_db) -> None:
        mark_ledger_degraded("insert failed")

        with patch("alchymine.db.usage_counters._degraded_retry_seconds", return_value=0.0):
            await charge_paid_call()
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
            assert ledger_is_degraded() is False
            await charge_paid_call()
            await charge_paid_call()

    async def test_a_failed_probe_re_arms_the_cooldown(self, cost_meter_db) -> None:
        with patch("alchymine.db.usage_counters._degraded_retry_seconds", return_value=0.0):
            mark_ledger_degraded("insert failed")
            await charge_paid_call()  # the probe

        mark_ledger_degraded("insert failed again")  # the probe's write failed
        with pytest.raises(CostCeilingExceeded):
            await charge_paid_call()

    async def test_an_abandoned_probe_does_not_wedge_the_gate(self, cost_meter_db) -> None:
        """A probe whose call dies before it writes must not block forever.

        Otherwise the fix for the deadlock introduces a second one: the
        probe is claimed, nothing resolves it, and every later call is
        refused for the life of the process.
        """
        mark_ledger_degraded("insert failed")

        with patch("alchymine.db.usage_counters._degraded_retry_seconds", return_value=0.0):
            await charge_paid_call()  # claims the probe, then vanishes
            with pytest.raises(CostCeilingExceeded):
                await charge_paid_call()

            with patch("alchymine.db.usage_counters.LEDGER_PROBE_TIMEOUT_SECONDS", 0.0):
                await charge_paid_call()  # a fresh probe replaces the abandoned one

    def test_the_claim_is_atomic_across_threads(self) -> None:
        """Celery runs the async work in a worker thread, so asyncio's
        single-threaded guarantee is not enough on its own."""
        import threading

        mark_ledger_degraded("insert failed")
        results: list[bool] = []
        results_lock = threading.Lock()

        with patch("alchymine.db.usage_counters._degraded_retry_seconds", return_value=0.0):
            barrier = threading.Barrier(16)

            def worker() -> None:
                barrier.wait()
                admitted = claim_ledger_admission()
                with results_lock:
                    results.append(admitted)

            threads = [threading.Thread(target=worker) for _ in range(16)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        assert results.count(True) == 1, f"exactly one probe may be claimed, got {results}"


class TestTheCooldownIsConfigurable:
    """A wrong cooldown under real traffic should be a restart, not a patch."""

    def test_the_default_is_sixty_seconds(self) -> None:
        assert get_settings().ledger_degraded_retry_seconds == 60.0

    def test_the_env_var_reaches_the_gate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """End to end: env var, Settings field, the value the breaker reads."""
        from alchymine.db.usage_counters import _degraded_retry_seconds

        monkeypatch.setenv("LEDGER_DEGRADED_RETRY_SECONDS", "0")
        get_settings.cache_clear()
        try:
            assert _degraded_retry_seconds() == 0.0
            mark_ledger_degraded("insert failed")
            # A zero cooldown means the very next call is the probe.
            assert claim_ledger_admission() is True
            assert claim_ledger_admission() is False
        finally:
            get_settings.cache_clear()


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

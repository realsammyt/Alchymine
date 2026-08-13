"""The revenue-linked global spend budget (design section 7).

The breaker PR #214 shipped counts *calls*. This one counts *dollars*.
They live in the same chokepoint, in that order, and neither replaces the
other: at $15/day and roughly a cent a call, spend binds first for typical
traffic, while the 2000-call backstop binds first for unusually cheap
calls, which is exactly the case a dollar ceiling would miss.

The independence is tested in both directions on purpose. A spend ceiling
wired in a way that also disabled the count breaker would look identical
to a correct one in every "does the ceiling trip" test.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.config import Settings, get_settings
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_LLM_CALLS,
    METER_SPEND_MICROS_DAILY,
    CostCeilingExceeded,
    get_count,
    increment_and_get,
)
from alchymine.llm.client import LLMClient
from alchymine.llm.cost_guard import charge_paid_call
from alchymine.llm.gemini import GeminiClient

# No module-level asyncio mark: pytest runs in asyncio_mode="auto" and this
# module mixes sync arithmetic tests with async chokepoint ones.


@contextmanager
def _env(**overrides: object) -> Iterator[None]:
    """Run a block with settings rebuilt from *overrides*.

    ``get_settings`` is ``lru_cache``d, so the cache has to be dropped on
    both sides: once so the block sees the override, once so the rest of
    the session does not inherit it.
    """
    values = {key.upper(): str(value) for key, value in overrides.items()}
    with patch.dict(os.environ, values, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()


def _claude_client() -> LLMClient:
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        get_settings.cache_clear()
        client = LLMClient()
    get_settings.cache_clear()
    return client


def _gemini_client() -> GeminiClient:
    client = GeminiClient(api_key="test-key", model="gemini-test")
    assert client.is_available, "fixture error: patch _genai before constructing"
    client._client = MagicMock()
    return client


# ── The formula ──────────────────────────────────────────────────────────


class TestCeilingArithmetic:
    """``monthly / 30 x headroom``, in micro-dollars, integer at the end."""

    def test_the_provisional_defaults_give_fifteen_dollars_a_day(self) -> None:
        settings = Settings()

        assert settings.monthly_llm_spend_budget_usd == 300.0
        assert settings.daily_spend_headroom_factor == 1.5
        # $300/month is $10/day flat; 1.5x headroom is $15/day, and a
        # dollar is 1,000,000 micro-dollars.
        assert settings.daily_global_spend_ceiling_micros() == 15_000_000

    def test_the_monthly_budget_is_exposed_in_micros_too(self) -> None:
        assert Settings().monthly_llm_spend_budget_micros() == 300_000_000

    def test_headroom_of_one_is_the_flat_monthly_thirtieth(self) -> None:
        settings = Settings(monthly_llm_spend_budget_usd=300.0, daily_spend_headroom_factor=1.0)

        assert settings.daily_global_spend_ceiling_micros() == 10_000_000

    def test_the_budget_scales_the_ceiling_linearly(self) -> None:
        settings = Settings(monthly_llm_spend_budget_usd=200.0, daily_spend_headroom_factor=1.5)

        assert settings.daily_global_spend_ceiling_micros() == 10_000_000

    def test_a_fractional_result_truncates_rather_than_rounding_up(self) -> None:
        # 1 / 30 * 1.5 = 50_000.000...x micros. Truncating keeps the ceiling
        # at or below the budget the operator actually set.
        settings = Settings(monthly_llm_spend_budget_usd=1.0, daily_spend_headroom_factor=1.5)

        assert settings.daily_global_spend_ceiling_micros() == 50_000

    def test_a_zero_budget_blocks_everything(self) -> None:
        """Fail closed. A budget of nothing must not read as "no ceiling"."""
        settings = Settings(monthly_llm_spend_budget_usd=0.0)

        assert settings.daily_global_spend_ceiling_micros() == 0

    def test_a_negative_budget_clamps_to_zero_rather_than_wrapping(self) -> None:
        settings = Settings(monthly_llm_spend_budget_usd=-50.0)

        assert settings.daily_global_spend_ceiling_micros() == 0
        assert settings.monthly_llm_spend_budget_micros() == 0


# ── Enforcement at the chokepoint ────────────────────────────────────────


class TestSpendCeilingAtTheChokepoint:
    async def test_a_spent_day_blocks_the_next_paid_call(self, cost_meter_db) -> None:
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            ceiling = get_settings().daily_global_spend_ceiling_micros()
            assert ceiling == 1_000
            await increment_and_get(
                scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY, amount=ceiling
            )

            with pytest.raises(CostCeilingExceeded) as caught:
                await charge_paid_call()

        assert caught.value.meter == METER_SPEND_MICROS_DAILY
        assert caught.value.scope == GLOBAL_SCOPE
        assert caught.value.reason == "ceiling_reached"

    async def test_a_day_under_the_ceiling_still_passes(self, cost_meter_db) -> None:
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            await increment_and_get(
                scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY, amount=999
            )

            await charge_paid_call()  # must not raise

    async def test_a_blocked_call_still_counts_as_an_attempt(self, cost_meter_db) -> None:
        """The count meter measures pressure, so a refusal is still a try.

        ``consume`` runs before the spend read, so the ordering is what
        keeps the abuse signal (issue #220) intact for calls the dollar
        ceiling turns away.
        """
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            await increment_and_get(
                scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY, amount=1_000
            )
            with pytest.raises(CostCeilingExceeded):
                await charge_paid_call()

        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) == 1

    async def test_an_unreadable_spend_meter_fails_closed(self, cost_meter_db) -> None:
        """Same rail as the count meter: no reading means no spending."""
        with patch(
            "alchymine.llm.cost_guard.check_ceiling",
            AsyncMock(
                side_effect=CostCeilingExceeded(
                    meter=METER_SPEND_MICROS_DAILY,
                    scope=GLOBAL_SCOPE,
                    retry_at=datetime.now(UTC) + timedelta(hours=1),
                    reason="meter_unavailable",
                )
            ),
        ):
            with pytest.raises(CostCeilingExceeded) as caught:
                await charge_paid_call()

        assert caught.value.reason == "meter_unavailable"

    async def test_the_ceiling_comes_from_config_not_a_call_site(self, cost_meter_db) -> None:
        """Raising the budget in env must raise the ceiling, with no redeploy."""
        checked: list[int] = []

        async def _capture(**kwargs: object) -> int:
            if kwargs.get("meter") == METER_SPEND_MICROS_DAILY:
                checked.append(int(kwargs["ceiling"]))  # type: ignore[arg-type]
            return 0

        with _env(monthly_llm_spend_budget_usd=600.0, daily_spend_headroom_factor=2.0):
            with patch("alchymine.llm.cost_guard.check_ceiling", _capture):
                await charge_paid_call()

        assert checked == [40_000_000]


# ── The two breakers are independent ─────────────────────────────────────


class TestTheTwoBreakersAreIndependent:
    async def test_the_count_backstop_still_trips_when_spend_is_empty(
        self, cost_meter_db
    ) -> None:
        """Cheap calls are exactly what a dollar ceiling misses."""
        with _env(global_daily_llm_call_ceiling=5):
            await increment_and_get(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS, amount=5)

            with pytest.raises(CostCeilingExceeded) as caught:
                await charge_paid_call()

        assert caught.value.meter == METER_LLM_CALLS
        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY) == 0

    async def test_the_count_backstop_survives_a_stubbed_out_spend_check(
        self, cost_meter_db
    ) -> None:
        """Wiring the spend gate must not have disarmed the older one."""
        with _env(global_daily_llm_call_ceiling=2):
            await increment_and_get(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS, amount=2)

            with patch("alchymine.llm.cost_guard.check_ceiling", AsyncMock(return_value=0)):
                with pytest.raises(CostCeilingExceeded) as caught:
                    await charge_paid_call()

        assert caught.value.meter == METER_LLM_CALLS

    async def test_the_spend_ceiling_trips_while_the_count_is_nearly_untouched(
        self, cost_meter_db
    ) -> None:
        """The case the call count cannot see: few calls, expensive ones."""
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            await increment_and_get(
                scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY, amount=5_000
            )

            with pytest.raises(CostCeilingExceeded) as caught:
                await charge_paid_call()

        assert caught.value.meter == METER_SPEND_MICROS_DAILY
        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) < 10


# ── All three egress paths inherit it ────────────────────────────────────


class TestEveryEgressPathIsGated:
    """One gate, three call sites — slice 4 adds no new ones."""

    async def _spend_the_day(self) -> None:
        await increment_and_get(
            scope=GLOBAL_SCOPE,
            meter=METER_SPEND_MICROS_DAILY,
            amount=get_settings().daily_global_spend_ceiling_micros(),
        )

    async def test_claude_generate_is_blocked(self, cost_meter_db) -> None:
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            client = _claude_client()
            await self._spend_the_day()
            fake_sdk = MagicMock()
            fake_sdk.messages.create = AsyncMock()

            with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
                with pytest.raises(CostCeilingExceeded) as caught:
                    await client._generate_claude("system", "user", 100, 0.5)

            assert fake_sdk.messages.create.await_count == 0

        assert caught.value.meter == METER_SPEND_MICROS_DAILY

    async def test_claude_stream_is_blocked(self, cost_meter_db) -> None:
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            client = _claude_client()
            await self._spend_the_day()
            fake_sdk = MagicMock()
            fake_sdk.messages.stream = MagicMock()

            with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
                with pytest.raises(CostCeilingExceeded) as caught:
                    async for _ in client._stream_claude("prompt", "system", 100, 0.5):
                        pass

            assert fake_sdk.messages.stream.call_count == 0

        assert caught.value.meter == METER_SPEND_MICROS_DAILY

    async def test_gemini_image_generation_is_blocked(self, cost_meter_db) -> None:
        with _env(monthly_llm_spend_budget_usd=0.03, daily_spend_headroom_factor=1.0):
            with patch("alchymine.llm.gemini._genai", MagicMock()):
                client = _gemini_client()
                client._client.aio.models.generate_content = AsyncMock()
                await self._spend_the_day()

                with pytest.raises(CostCeilingExceeded) as caught:
                    await client.generate_image("a serene forest")

                assert client._client.aio.models.generate_content.await_count == 0

        assert caught.value.meter == METER_SPEND_MICROS_DAILY

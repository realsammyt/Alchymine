"""Tests for the dollar-denominated cost ledger.

Two halves:

- :func:`cost_micros` — pure integer arithmetic over the four Anthropic
  usage fields. Prices come from config and never from a call site, and an
  unknown model is priced at the most expensive rate in the table rather
  than at zero.
- :func:`record_usage` — one ``usage_records`` row per delivered call, plus
  the two spend meters. It must never raise into the caller (the reply has
  already been delivered), but a failed write must be loud and must block
  the *next* cost-bearing call.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from sqlalchemy import func, select

from alchymine.config import get_settings
from alchymine.db.models import UsageRecord
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_ART_GENERATIONS,
    METER_LLM_CALLS,
    METER_SPEND_MICROS_DAILY,
    METER_SPEND_MICROS_MONTHLY,
    clear_ledger_degraded,
    current_month_key,
    get_count,
    ledger_is_degraded,
)
from alchymine.llm.attribution import attributed, set_attribution
from alchymine.llm.ledger import cost_micros, record_usage

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"


@pytest.fixture(autouse=True)
def _clean_ledger_flag() -> Iterator[None]:
    clear_ledger_degraded()
    yield
    clear_ledger_degraded()


async def _rows(engine) -> list[UsageRecord]:
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(engine)
    async with factory() as session:
        result = await session.execute(select(UsageRecord).order_by(UsageRecord.id))
        return list(result.scalars().all())


async def _row_count(engine) -> int:
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(engine)
    async with factory() as session:
        result = await session.execute(select(func.count()).select_from(UsageRecord))
        return int(result.scalar_one())


class TestCostFormula:
    """Exact micro-dollars for known token counts. No floats anywhere."""

    def test_sonnet_input_and_output(self) -> None:
        # 1,000 x 3 + 500 x 15
        assert cost_micros(model=SONNET, input_tokens=1000, output_tokens=500) == 10_500

    def test_haiku_is_a_third_of_sonnet_on_the_same_turn(self) -> None:
        # The design's 10-turn chat turn: 3,100 in / 400 out.
        assert cost_micros(model=SONNET, input_tokens=3100, output_tokens=400) == 15_300
        assert cost_micros(model=HAIKU, input_tokens=3100, output_tokens=400) == 5_100

    def test_cache_reads_are_a_tenth_of_the_input_price(self) -> None:
        assert cost_micros(model=SONNET, cache_read_input_tokens=1000) == 300

    def test_cache_writes_are_one_and_a_quarter_input_price(self) -> None:
        assert cost_micros(model=SONNET, cache_creation_input_tokens=1000) == 3_750

    def test_all_four_fields_are_priced(self) -> None:
        """Pricing only input+output would under-count every cached call."""
        assert (
            cost_micros(
                model=SONNET,
                input_tokens=1000,
                output_tokens=500,
                cache_read_input_tokens=1000,
                cache_creation_input_tokens=1000,
            )
            == 10_500 + 300 + 3_750
        )

    def test_cache_read_truncates_down_rather_than_up(self) -> None:
        # 1 x 1 // 10 == 0 on Haiku: under one micro-dollar, floored.
        assert cost_micros(model=HAIKU, cache_read_input_tokens=1) == 0

    def test_multiplies_before_dividing(self) -> None:
        """(3 x 3 x 5) // 4 == 11. Dividing first would give 10."""
        assert cost_micros(model=SONNET, cache_creation_input_tokens=3) == 11

    def test_zero_tokens_cost_zero(self) -> None:
        assert cost_micros(model=SONNET) == 0

    def test_negative_token_counts_clamp_to_zero(self) -> None:
        """A garbage usage field must not mint negative spend."""
        assert cost_micros(model=SONNET, input_tokens=-1000, output_tokens=500) == 7_500


class TestUnknownModelPricing:
    """A model we forgot to add to the table must look expensive, not free."""

    def test_priced_at_the_most_expensive_rate_in_the_table(self) -> None:
        unknown = cost_micros(model="claude-something-new", input_tokens=1000, output_tokens=1000)
        priciest = cost_micros(model=SONNET, input_tokens=1000, output_tokens=1000)
        assert unknown == priciest

    def test_never_prices_an_unknown_model_at_zero(self) -> None:
        assert cost_micros(model="not-a-model", input_tokens=1, output_tokens=1) > 0

    def test_logs_at_error(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.ERROR):
            cost_micros(model="not-a-model", input_tokens=1)
        assert any("not-a-model" in r.getMessage() for r in caplog.records)

    def test_an_empty_price_table_still_prices_above_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_PRICE_TABLE", "")
        get_settings.cache_clear()
        try:
            assert cost_micros(model=SONNET, input_tokens=1000, output_tokens=1000) > 0
        finally:
            get_settings.cache_clear()


class TestPriceTableConfig:
    def test_parses_the_default_table(self) -> None:
        prices = get_settings().get_llm_prices()
        assert prices[SONNET] == (3, 15)
        assert prices[HAIKU] == (1, 5)

    def test_skips_malformed_entries_without_raising(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("LLM_PRICE_TABLE", f"{SONNET}:3:15,broken-entry,{HAIKU}:x:5")
        get_settings.cache_clear()
        try:
            with caplog.at_level(logging.ERROR):
                prices = get_settings().get_llm_prices()
            assert prices == {SONNET: (3, 15)}
        finally:
            get_settings.cache_clear()


class TestRecordUsage:
    async def test_writes_one_attributed_row(self, cost_meter_db) -> None:
        set_attribution(user_id="user-1", surface="chat", request_id="req-1")
        await record_usage(
            meter=METER_LLM_CALLS,
            provider="anthropic",
            model=HAIKU,
            input_tokens=3100,
            output_tokens=400,
        )

        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        row = rows[0]
        assert row.user_id == "user-1"
        assert row.scope == "user-1"
        assert row.surface == "chat"
        assert row.request_id == "req-1"
        assert row.provider == "anthropic"
        assert row.model == HAIKU
        assert row.input_tokens == 3100
        assert row.output_tokens == 400
        assert row.cost_micros == 5_100
        assert row.estimated is False

    async def test_denormalizes_the_period_and_month_keys(self, cost_meter_db) -> None:
        from alchymine.db.usage_counters import current_period_key

        set_attribution(user_id="user-1", surface="chat")
        await record_usage(meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU)

        row = (await _rows(cost_meter_db))[0]
        assert row.period_key == current_period_key()
        assert row.month_key == current_month_key()

    async def test_increments_the_global_daily_spend_meter(self, cost_meter_db) -> None:
        set_attribution(user_id="user-1", surface="chat")
        await record_usage(
            meter=METER_LLM_CALLS,
            provider="anthropic",
            model=HAIKU,
            input_tokens=3100,
            output_tokens=400,
        )
        assert (
            await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)
        ) == 5_100

    async def test_increments_the_per_user_monthly_spend_meter(self, cost_meter_db) -> None:
        set_attribution(user_id="user-1", surface="chat")
        await record_usage(
            meter=METER_LLM_CALLS,
            provider="anthropic",
            model=HAIKU,
            input_tokens=3100,
            output_tokens=400,
        )
        assert (
            await get_count(
                scope="user-1",
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=current_month_key(),
            )
        ) == 5_100

    async def test_meters_accumulate_across_calls(self, cost_meter_db) -> None:
        set_attribution(user_id="user-1", surface="chat")
        for _ in range(3):
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
        assert (await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)) == 3_000

    async def test_an_explicit_surface_beats_the_context_var(self, cost_meter_db) -> None:
        set_attribution(user_id="user-1", surface="chat")
        await record_usage(
            meter=METER_ART_GENERATIONS,
            provider="google",
            model="gemini-test",
            images=1,
            cost_micros_override=67_000,
            surface="art",
        )
        row = (await _rows(cost_meter_db))[0]
        assert row.surface == "art"
        assert row.images == 1
        assert row.cost_micros == 67_000

    async def test_the_kill_switch_writes_nothing(
        self, cost_meter_db, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("USAGE_LEDGER_ENABLED", "false")
        get_settings.cache_clear()
        try:
            set_attribution(user_id="user-1", surface="chat")
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
        finally:
            get_settings.cache_clear()

        assert await _row_count(cost_meter_db) == 0
        assert (await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)) == 0


class TestUnattributedSpend:
    """A missing ContextVar is a wiring defect, not a reason to block."""

    async def test_writes_the_row_with_a_null_user_id(self, cost_meter_db) -> None:
        await record_usage(
            meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
        )
        row = (await _rows(cost_meter_db))[0]
        assert row.user_id is None
        assert row.scope == "unattributed"
        assert row.surface == "unknown"

    async def test_still_charges_the_global_meter(self, cost_meter_db) -> None:
        """An unattributed call must not escape the global budget."""
        await record_usage(
            meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
        )
        assert (await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)) == 1_000

    async def test_writes_no_per_user_meter(self, cost_meter_db) -> None:
        await record_usage(
            meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
        )
        assert (
            await get_count(
                scope="unattributed",
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=current_month_key(),
            )
        ) == 0

    async def test_warns_loudly(self, cost_meter_db, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
        assert any(r.levelno >= logging.WARNING for r in caplog.records)


class TestFailClosedOnLedgerWriteFailure:
    """Loud, and it fails the NEXT call — not the one already delivered."""

    async def test_a_failed_insert_does_not_raise_into_the_caller(self, cost_meter_db) -> None:
        from alchymine.api.deps import set_db_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/nothing")
        set_db_engine(broken)
        try:
            # Must not raise: the user has already read the reply.
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
        finally:
            set_db_engine(cost_meter_db)
            await broken.dispose()

    async def test_a_failed_insert_marks_the_ledger_degraded(self, cost_meter_db) -> None:
        from alchymine.api.deps import set_db_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/nothing")
        set_db_engine(broken)
        try:
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
            assert ledger_is_degraded() is True
        finally:
            set_db_engine(cost_meter_db)
            await broken.dispose()

    async def test_a_failed_insert_logs_the_row_as_structured_json(
        self, cost_meter_db, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The spend has to be reconstructible from logs."""
        import json

        from alchymine.api.deps import set_db_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/nothing")
        set_db_engine(broken)
        try:
            with caplog.at_level(logging.ERROR):
                set_attribution(user_id="user-1", surface="chat")
                await record_usage(
                    meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
                )
        finally:
            set_db_engine(cost_meter_db)
            await broken.dispose()

        payloads = [
            message[message.index("row={") + len("row=") :]
            for message in (record.getMessage() for record in caplog.records)
            if "row={" in message
        ]
        assert payloads, f"no structured row logged; saw {[r.getMessage() for r in caplog.records]}"
        parsed = json.loads(payloads[-1])
        assert parsed["model"] == HAIKU
        assert parsed["cost_micros"] == 1_000
        assert parsed["user_id"] == "user-1"

    async def test_a_later_successful_write_clears_the_flag(self, cost_meter_db) -> None:
        from alchymine.api.deps import set_db_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/nothing")
        set_db_engine(broken)
        try:
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )
        finally:
            set_db_engine(cost_meter_db)
            await broken.dispose()

        assert ledger_is_degraded() is True

        with attributed(user_id="user-1", surface="chat"):
            await record_usage(
                meter=METER_LLM_CALLS, provider="anthropic", model=HAIKU, input_tokens=1000
            )

        assert ledger_is_degraded() is False

"""Tests for the global daily LLM spend circuit breaker.

The breaker sits at the three paid-egress chokepoints — Claude generate,
Claude stream, and Gemini image generation — and shares one global daily
counter across all of them. Once it trips, no paid call may be attempted
and the failure must reach the caller as a distinct, structured error
rather than being swallowed into a fallback or a silent ``None``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_LLM_CALLS,
    CostCeilingExceeded,
    get_count,
    increment_and_get,
)
from alchymine.llm.client import LLMClient
from alchymine.llm.gemini import GeminiClient

pytestmark = pytest.mark.asyncio


async def _spend_the_day(ceiling: int) -> None:
    """Put the global counter exactly at its ceiling, in one bump."""
    await increment_and_get(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS, amount=ceiling)


def _claude_client() -> LLMClient:
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        from alchymine.config import get_settings

        get_settings.cache_clear()
        client = LLMClient()
    get_settings.cache_clear()
    return client


class TestClaudeGenerateChokepoint:
    async def test_charges_the_global_counter_on_a_paid_call(self, cost_meter_db) -> None:
        client = _claude_client()
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="hello")]
        fake_response.usage = MagicMock(input_tokens=1, output_tokens=1)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=fake_response)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            await client._generate_claude("system", "user", 100, 0.5)

        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) == 1

    async def test_blocks_the_call_once_the_ceiling_is_spent(self, cost_meter_db) -> None:
        from alchymine.config import get_settings

        ceiling = get_settings().global_daily_llm_call_ceiling
        await _spend_the_day(ceiling)

        client = _claude_client()
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock()

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with pytest.raises(CostCeilingExceeded):
                await client._generate_claude("system", "user", 100, 0.5)

        # The whole point: the paid call is never attempted.
        fake_sdk.messages.create.assert_not_called()

    async def test_generate_surfaces_the_breaker_instead_of_canned_fallback_text(
        self, cost_meter_db
    ) -> None:
        """A tripped breaker must not degrade into a fake answer."""
        from alchymine.config import get_settings

        await _spend_the_day(get_settings().global_daily_llm_call_ceiling)
        client = _claude_client()

        with patch("anthropic.AsyncAnthropic", return_value=MagicMock()):
            with pytest.raises(CostCeilingExceeded):
                await client.generate("system", "user")


class TestClaudeStreamChokepoint:
    async def test_blocks_the_stream_once_the_ceiling_is_spent(self, cost_meter_db) -> None:
        from alchymine.config import get_settings

        await _spend_the_day(get_settings().global_daily_llm_call_ceiling)
        client = _claude_client()
        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock()

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with pytest.raises(CostCeilingExceeded):
                async for _ in client._stream_claude("prompt", "system", 100, 0.5):
                    pass

        fake_sdk.messages.stream.assert_not_called()

    async def test_stream_generate_surfaces_the_breaker(self, cost_meter_db) -> None:
        from alchymine.config import get_settings

        await _spend_the_day(get_settings().global_daily_llm_call_ceiling)
        client = _claude_client()

        with patch("anthropic.AsyncAnthropic", return_value=MagicMock()):
            with pytest.raises(CostCeilingExceeded):
                async for _ in client.stream_generate("prompt"):
                    pass


class TestGeminiChokepoint:
    def _available_client(self) -> GeminiClient:
        client = GeminiClient(api_key="test-key", model="gemini-test")
        return client

    async def test_charges_the_global_counter_on_a_paid_call(self, cost_meter_db) -> None:
        client = self._available_client()
        fake_response = MagicMock(candidates=[])
        client._client = MagicMock()
        client._client.aio.models.generate_content = AsyncMock(return_value=fake_response)

        with patch("alchymine.llm.gemini._genai", MagicMock()):
            await client.generate_image("a serene forest")

        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) == 1

    async def test_tripped_breaker_raises_instead_of_returning_none(self, cost_meter_db) -> None:
        """The silent-None path must not swallow a tripped breaker.

        generate_image returns None for "no image available" — if the
        breaker collapsed into that, the art route would render its
        placeholder and nobody would learn that spending is capped.
        """
        from alchymine.config import get_settings

        await _spend_the_day(get_settings().global_daily_llm_call_ceiling)

        client = self._available_client()
        client._client = MagicMock()
        client._client.aio.models.generate_content = AsyncMock()

        with patch("alchymine.llm.gemini._genai", MagicMock()):
            with pytest.raises(CostCeilingExceeded):
                await client.generate_image("a serene forest")

        client._client.aio.models.generate_content.assert_not_called()


class TestModelFallbackChain:
    """The 529-overload fallback chain must never escalate to a pricier model."""

    async def test_chain_holds_no_opus_model(self) -> None:
        assert not any("opus" in model for model in LLMClient.CLAUDE_MODELS)

    async def test_chain_is_sonnet_then_haiku(self) -> None:
        assert LLMClient.CLAUDE_MODELS == [
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ]


class TestBreakerScope:
    async def test_claude_and_gemini_share_one_global_budget(self, cost_meter_db) -> None:
        """One breaker, not one per vendor — the bill is a single number."""
        client = _claude_client()
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="hi")]
        fake_response.usage = MagicMock(input_tokens=1, output_tokens=1)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=fake_response)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            await client._generate_claude("system", "user", 100, 0.5)

        gemini = GeminiClient(api_key="test-key", model="gemini-test")
        gemini._client = MagicMock()
        gemini._client.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(candidates=[])
        )
        with patch("alchymine.llm.gemini._genai", MagicMock()):
            await gemini.generate_image("a forest")

        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS) == 2

    async def test_budget_resets_on_the_next_utc_day(self, cost_meter_db) -> None:
        from alchymine.config import get_settings

        ceiling = get_settings().global_daily_llm_call_ceiling
        await _spend_the_day(ceiling)
        client = _claude_client()

        with patch("anthropic.AsyncAnthropic", return_value=MagicMock()):
            with pytest.raises(CostCeilingExceeded):
                await client._generate_claude("system", "user", 100, 0.5)

        # Tomorrow's counter starts empty, so the same call goes through.
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="hello")]
        fake_response.usage = MagicMock(input_tokens=1, output_tokens=1)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=fake_response)

        tomorrow = "2099-01-01"
        with patch("alchymine.db.usage_counters.current_period_key", return_value=tomorrow):
            with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
                await client._generate_claude("system", "user", 100, 0.5)

        assert await get_count(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS, period_key=tomorrow) == 1

"""Chat on Haiku, and the prompt-cache breakpoint that rides along with it.

Two independent changes, verified through the slice-2 ledger because the
ledger is the only thing that can say what a call actually cost:

- **Routing.** The chat path names its own model, which becomes the head
  of the existing fallback chain. Report narratives pass nothing and keep
  the Sonnet-first chain. Whichever model actually served is what gets
  priced, including the one direction the chain can go uphill: a 529 on
  Haiku escalates to Sonnet, and the ledger has to say Sonnet.

- **Caching.** The chat system prompt becomes a single text block with one
  ``cache_control`` breakpoint on it. The prefix is far below Haiku's
  4,096-token minimum today, so this produces no cache hits yet; what the
  tests here pin is the request shape and that cache tokens, when they do
  arrive, are priced at 0.1x input rather than dropped.

See docs/plans/2026-08-13-unit-economics.md sections 8.1 to 8.3.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import select

from alchymine.config import get_settings
from alchymine.db.models import UsageRecord
from alchymine.db.usage_counters import clear_ledger_degraded
from alchymine.llm.attribution import attributed
from alchymine.llm.client import LLMClient

pytestmark = pytest.mark.asyncio

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"


# ── Fakes ────────────────────────────────────────────────────────────────


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _FinalMessage:
    usage: _Usage


class _FakeStream:
    def __init__(self, chunks: list[str], final: _FinalMessage | None) -> None:
        self._chunks = chunks
        self._final = final

    @property
    def text_stream(self):  # noqa: ANN202
        async def _iter():  # noqa: ANN202
            for chunk in self._chunks:
                yield chunk

        return _iter()

    async def get_final_message(self) -> _FinalMessage:
        if self._final is None:
            raise RuntimeError("no final message")
        return self._final


class _FakeStreamManager:
    def __init__(self, stream: _FakeStream) -> None:
        self._stream = stream

    async def __aenter__(self) -> _FakeStream:
        return self._stream

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


@contextmanager
def _configured(**env: str) -> Iterator[None]:
    """Run with these env vars in force and the settings cache cleared.

    ``get_settings`` is lru_cached, which is exactly why flipping either
    flag in production needs a restart; here it means the cache has to be
    cleared on both sides of the block.
    """
    env.setdefault("ANTHROPIC_API_KEY", "test-key")
    with patch.dict("os.environ", env, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()


def _ok_stream(**usage: int) -> MagicMock:
    """A fake SDK whose stream succeeds and reports *usage*."""
    stream = _FakeStream(["hello"], _FinalMessage(usage=_Usage(**usage)))
    sdk = MagicMock()
    sdk.messages.stream = MagicMock(return_value=_FakeStreamManager(stream))
    return sdk


def _overloaded() -> Exception:
    import anthropic

    return anthropic.APIStatusError(
        "overloaded",
        response=httpx.Response(529, request=httpx.Request("POST", "https://api")),
        body=None,
    )


async def _rows(engine) -> list[UsageRecord]:  # noqa: ANN001
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(engine)
    async with factory() as session:
        result = await session.execute(select(UsageRecord).order_by(UsageRecord.id))
        return list(result.scalars().all())


def _models_tried(sdk: MagicMock) -> list[str]:
    return [call.kwargs["model"] for call in sdk.messages.stream.call_args_list]


@pytest.fixture(autouse=True)
def _clean_flag() -> Iterator[None]:
    clear_ledger_degraded()
    yield
    clear_ledger_degraded()


# ── Routing ──────────────────────────────────────────────────────────────


class TestChatRouting:
    async def test_a_chat_turn_is_served_and_priced_at_the_chat_model(self, cost_meter_db) -> None:
        """The whole point of the slice: the same turn, at a fifth the price."""
        sdk = _ok_stream(input_tokens=3100, output_tokens=400)

        with _configured(LLM_CHAT_MODEL=HAIKU):
            client = LLMClient()
            chat_model = get_settings().llm_chat_model
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                with attributed(user_id="user-1", surface="chat"):
                    chunks = [
                        c
                        async for c in client.stream_generate(
                            prompt="prompt", system_prompt="system", model=chat_model
                        )
                    ]

        assert chunks == ["hello"]
        assert _models_tried(sdk) == [HAIKU]
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].model == HAIKU
        assert rows[0].surface == "chat"
        # Haiku is 1 in / 5 out; the same turn on Sonnet costs 15,300.
        assert rows[0].cost_micros == 3100 * 1 + 400 * 5

    async def test_an_empty_chat_model_leaves_the_default_chain_alone(self, cost_meter_db) -> None:
        """LLM_CHAT_MODEL="" is the documented off switch, not a model id."""
        sdk = _ok_stream(input_tokens=1100, output_tokens=400)

        with _configured(LLM_CHAT_MODEL=""):
            client = LLMClient()
            assert get_settings().llm_chat_model == ""
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                async for _ in client.stream_generate(
                    prompt="prompt",
                    system_prompt="system",
                    model=get_settings().llm_chat_model,
                ):
                    pass

        assert _models_tried(sdk) == [SONNET]
        rows = await _rows(cost_meter_db)
        assert rows[0].model == SONNET
        assert rows[0].cost_micros == 1100 * 3 + 400 * 15

    async def test_a_report_narrative_still_runs_and_prices_on_sonnet(self, cost_meter_db) -> None:
        """Non-chat callers pass no model, so nothing about them moves."""
        from unittest.mock import AsyncMock

        response = MagicMock()
        response.content = [MagicMock(text="a gentle narrative")]
        response.usage = _Usage(input_tokens=1000, output_tokens=500)
        sdk = MagicMock()
        sdk.messages.create = AsyncMock(return_value=response)

        with _configured(LLM_CHAT_MODEL=HAIKU):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                with attributed(user_id="user-1", surface="report_narrative"):
                    await client.generate("system", "user")

        assert sdk.messages.create.call_args.kwargs["model"] == SONNET
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].model == SONNET
        assert rows[0].cost_micros == 1000 * 3 + 500 * 15

    async def test_a_529_on_haiku_falls_back_to_sonnet_at_sonnet_prices(
        self, cost_meter_db
    ) -> None:
        """The one place the chain runs uphill in price, and it is intended.

        A 529 is rare, and the alternative to escalating is telling the
        user the coach is unavailable. The cost has to follow whichever
        server actually answered, so the row says Sonnet and costs Sonnet.
        """
        good = _FakeStream(
            ["ok"], _FinalMessage(usage=_Usage(input_tokens=3100, output_tokens=400))
        )

        def _stream(**kwargs: object):  # noqa: ANN202
            if kwargs.get("model") == HAIKU:
                raise _overloaded()
            return _FakeStreamManager(good)

        sdk = MagicMock()
        sdk.messages.stream = MagicMock(side_effect=_stream)

        with _configured(LLM_CHAT_MODEL=HAIKU):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                with attributed(user_id="user-1", surface="chat"):
                    chunks = [
                        c
                        async for c in client.stream_generate(
                            prompt="prompt", system_prompt="system", model=HAIKU
                        )
                    ]

        assert chunks == ["ok"]
        assert _models_tried(sdk) == [HAIKU, SONNET]
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1, "one delivered answer is one ledger row"
        assert rows[0].model == SONNET
        assert rows[0].cost_micros == 3100 * 3 + 400 * 15

    async def test_a_chat_model_already_in_the_chain_is_not_tried_twice(
        self, cost_meter_db
    ) -> None:
        """Haiku heads the chain and must not also reappear as its own fallback."""
        sdk = MagicMock()
        sdk.messages.stream = MagicMock(
            side_effect=lambda **kwargs: (_ for _ in ()).throw(_overloaded())
        )

        with _configured(LLM_CHAT_MODEL=HAIKU):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                with pytest.raises(Exception):
                    async for _ in client._stream_claude("prompt", "system", 100, 0.5, model=HAIKU):
                        pass

        assert _models_tried(sdk) == [HAIKU, SONNET]

    async def test_an_off_chain_chat_model_keeps_both_defaults_as_fallbacks(
        self, cost_meter_db
    ) -> None:
        sdk = MagicMock()
        sdk.messages.stream = MagicMock(
            side_effect=lambda **kwargs: (_ for _ in ()).throw(_overloaded())
        )

        with _configured():
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                with pytest.raises(Exception):
                    async for _ in client._stream_claude(
                        "prompt", "system", 100, 0.5, model="claude-something-else"
                    ):
                        pass

        assert _models_tried(sdk) == ["claude-something-else", SONNET, HAIKU]


# ── Prompt caching ───────────────────────────────────────────────────────


class TestPromptCacheBreakpoint:
    async def test_the_flag_on_sends_one_breakpoint_on_the_stable_prefix(
        self, cost_meter_db
    ) -> None:
        sdk = _ok_stream(input_tokens=10, output_tokens=2)

        with _configured(LLM_PROMPT_CACHE_ENABLED="true"):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                async for _ in client._stream_claude("prompt", "the system prompt", 100, 0.5):
                    pass

        system = sdk.messages.stream.call_args.kwargs["system"]
        assert isinstance(system, list)
        assert len(system) == 1
        assert system[0]["type"] == "text"
        assert system[0]["text"] == "the system prompt"
        assert system[0]["cache_control"] == {"type": "ephemeral"}
        breakpoints = [block for block in system if "cache_control" in block]
        assert len(breakpoints) == 1, "exactly one breakpoint, on the stable block"

    async def test_the_flag_off_sends_the_plain_string_it_always_sent(self, cost_meter_db) -> None:
        """The non-caching path stays byte-identical to today's request."""
        sdk = _ok_stream(input_tokens=10, output_tokens=2)

        with _configured(LLM_PROMPT_CACHE_ENABLED="false"):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                async for _ in client._stream_claude("prompt", "the system prompt", 100, 0.5):
                    pass

        assert sdk.messages.stream.call_args.kwargs["system"] == "the system prompt"

    async def test_an_empty_system_prompt_is_never_wrapped(self, cost_meter_db) -> None:
        """An empty text block is not a valid request; send the empty string."""
        sdk = _ok_stream(input_tokens=10, output_tokens=2)

        with _configured(LLM_PROMPT_CACHE_ENABLED="true"):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                async for _ in client._stream_claude("prompt", "", 100, 0.5):
                    pass

        assert sdk.messages.stream.call_args.kwargs["system"] == ""

    async def test_report_narratives_are_never_wrapped(self, cost_meter_db) -> None:
        """Their prompts interleave stable and per-user text; out of scope."""
        from unittest.mock import AsyncMock

        response = MagicMock()
        response.content = [MagicMock(text="narrative")]
        response.usage = _Usage(input_tokens=10, output_tokens=2)
        sdk = MagicMock()
        sdk.messages.create = AsyncMock(return_value=response)

        with _configured(LLM_PROMPT_CACHE_ENABLED="true"):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                await client._generate_claude("the system prompt", "user", 100, 0.5)

        assert sdk.messages.create.call_args.kwargs["system"] == "the system prompt"

    async def test_cache_reads_reach_the_ledger_at_a_tenth_of_input(self, cost_meter_db) -> None:
        """Nothing to observe today, but the pipe has to work when it fills."""
        sdk = _ok_stream(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=3000,
            cache_creation_input_tokens=800,
        )

        with _configured(LLM_CHAT_MODEL=HAIKU):
            client = LLMClient()
            with patch("anthropic.AsyncAnthropic", return_value=sdk):
                with attributed(user_id="user-1", surface="chat"):
                    async for _ in client.stream_generate(
                        prompt="prompt", system_prompt="system", model=HAIKU
                    ):
                        pass

        row = (await _rows(cost_meter_db))[0]
        assert row.cache_read_input_tokens == 3000
        assert row.cache_creation_input_tokens == 800
        # Haiku input is 1 micro/token: reads at 0.1x, writes at 1.25x.
        assert row.cost_micros == 100 * 1 + 50 * 5 + (3000 * 1) // 10 + (800 * 1 * 5) // 4

"""The ledger at the three paid-egress chokepoints.

Claude non-streaming, Claude streaming, Gemini image generation. Each one
must leave exactly one ``usage_records`` row per delivered call, priced
from the model that actually served the request.

The streaming path carries the interesting guarantees: exactly one row on
normal completion (the ``finally`` is the only recording site, so it can
neither double-record nor miss), and an ``estimated=True`` row when the
browser disappears mid-stream and the exact usage can no longer be read.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select

from alchymine.config import get_settings
from alchymine.db.models import UsageRecord
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_ART_GENERATIONS,
    METER_LLM_CALLS,
    METER_SPEND_MICROS_DAILY,
    clear_ledger_degraded,
    get_count,
)
from alchymine.llm.attribution import attributed
from alchymine.llm.client import LLMClient
from alchymine.llm.gemini import GeminiClient
from alchymine.llm.ledger import flush_pending_writes

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
    model: str = SONNET


class _FakeStream:
    """Stands in for ``anthropic``'s ``MessageStream``."""

    def __init__(self, chunks: list[str], final: _FinalMessage | None) -> None:
        self._chunks = chunks
        self._final = final
        self.get_final_message_calls = 0

    @property
    def text_stream(self):  # noqa: ANN202
        async def _iter():  # noqa: ANN202
            for chunk in self._chunks:
                yield chunk

        return _iter()

    async def get_final_message(self) -> _FinalMessage:
        self.get_final_message_calls += 1
        if self._final is None:
            raise RuntimeError("stream was torn down before the final message arrived")
        return self._final


class _FakeStreamManager:
    def __init__(self, stream: _FakeStream) -> None:
        self._stream = stream

    async def __aenter__(self) -> _FakeStream:
        return self._stream

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


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


async def _rows(engine) -> list[UsageRecord]:
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(engine)
    async with factory() as session:
        result = await session.execute(select(UsageRecord).order_by(UsageRecord.id))
        return list(result.scalars().all())


@pytest.fixture(autouse=True)
def _clean_flag():  # noqa: ANN202
    clear_ledger_degraded()
    yield
    clear_ledger_degraded()


# ── Claude, non-streaming ────────────────────────────────────────────────


class TestGenerateChokepoint:
    async def test_writes_one_priced_row(self, cost_meter_db) -> None:
        client = _claude_client()
        response = MagicMock()
        response.content = [MagicMock(text="hello")]
        response.usage = _Usage(input_tokens=1000, output_tokens=500)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=response)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with attributed(user_id="user-1", surface="report_narrative"):
                await client._generate_claude("system", "user", 100, 0.5)

        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].model == SONNET
        assert rows[0].meter == METER_LLM_CALLS
        assert rows[0].provider == "anthropic"
        assert rows[0].user_id == "user-1"
        assert rows[0].surface == "report_narrative"
        assert rows[0].cost_micros == 1000 * 3 + 500 * 15
        assert rows[0].estimated is False

    async def test_records_the_two_cache_fields(self, cost_meter_db) -> None:
        """Slice 5 turns caching on; pricing only in/out would under-count."""
        client = _claude_client()
        response = MagicMock()
        response.content = [MagicMock(text="hello")]
        response.usage = _Usage(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=2000,
            cache_creation_input_tokens=400,
        )
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=response)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            await client._generate_claude("system", "user", 100, 0.5)

        row = (await _rows(cost_meter_db))[0]
        assert row.cache_read_input_tokens == 2000
        assert row.cache_creation_input_tokens == 400
        assert row.cost_micros == 100 * 3 + 50 * 15 + (2000 * 3) // 10 + (400 * 3 * 5) // 4

    async def test_records_the_model_that_actually_served(self, cost_meter_db) -> None:
        """The 529 walk changes the model; the price must follow it."""
        import anthropic

        client = _claude_client()
        overloaded = anthropic.APIStatusError(
            "overloaded",
            response=httpx.Response(529, request=httpx.Request("POST", "https://api")),
            body=None,
        )
        ok = MagicMock()
        ok.content = [MagicMock(text="hello")]
        ok.usage = _Usage(input_tokens=1000, output_tokens=1000)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(side_effect=[overloaded, ok])

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            await client._generate_claude("system", "user", 100, 0.5)

        rows = await _rows(cost_meter_db)
        assert len(rows) == 1, "one delivered answer is one ledger row"
        assert rows[0].model == HAIKU
        assert rows[0].cost_micros == 1000 * 1 + 1000 * 5

    async def test_charges_the_global_daily_spend_meter(self, cost_meter_db) -> None:
        client = _claude_client()
        response = MagicMock()
        response.content = [MagicMock(text="hello")]
        response.usage = _Usage(input_tokens=1000, output_tokens=500)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=response)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            await client._generate_claude("system", "user", 100, 0.5)

        assert (
            await get_count(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY)
        ) == 1000 * 3 + 500 * 15


# ── Claude, streaming ────────────────────────────────────────────────────


class TestStreamChokepoint:
    async def test_normal_completion_writes_exactly_one_exact_row(self, cost_meter_db) -> None:
        client = _claude_client()
        stream = _FakeStream(
            ["hello ", "world"],
            _FinalMessage(usage=_Usage(input_tokens=1100, output_tokens=400)),
        )
        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock(return_value=_FakeStreamManager(stream))

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with attributed(user_id="user-1", surface="chat"):
                chunks = [c async for c in client._stream_claude("prompt", "system", 100, 0.5)]

        assert chunks == ["hello ", "world"]
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1, "the finally block is the only recording site"
        assert rows[0].estimated is False
        assert rows[0].input_tokens == 1100
        assert rows[0].output_tokens == 400
        assert rows[0].cost_micros == 1100 * 3 + 400 * 15
        assert rows[0].surface == "chat"

    async def test_a_mid_stream_disconnect_still_records_an_estimate(self, cost_meter_db) -> None:
        """The browser goes away; the call was still paid for."""
        client = _claude_client()
        stream = _FakeStream(["hello ", "world"], final=None)
        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock(return_value=_FakeStreamManager(stream))

        system_prompt = "s" * 40
        prompt = "p" * 60

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with attributed(user_id="user-1", surface="chat"):
                generator = client._stream_claude(prompt, system_prompt, 100, 0.5)
                first = await generator.__anext__()
                await generator.aclose()

        assert first == "hello "
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].estimated is True
        # Estimated from what was actually sent and delivered: chars // 4.
        assert rows[0].input_tokens == (len(system_prompt) + len(prompt)) // 4
        assert rows[0].output_tokens == len("hello ") // 4
        assert rows[0].cost_micros > 0

    async def test_a_hung_final_message_falls_back_to_the_estimate(self, cost_meter_db) -> None:
        """get_final_message is bounded: a torn-down stream must not hang."""
        client = _claude_client()

        class _HangingStream(_FakeStream):
            async def get_final_message(self) -> _FinalMessage:
                import asyncio

                await asyncio.sleep(30)
                raise AssertionError("should have timed out")

        stream = _HangingStream(["hello"], final=None)
        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock(return_value=_FakeStreamManager(stream))

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with patch("alchymine.llm.client._FINAL_MESSAGE_TIMEOUT_SECONDS", 0.01):
                chunks = [c async for c in client._stream_claude("prompt", "system", 100, 0.5)]

        assert chunks == ["hello"]
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].estimated is True

    async def test_a_broken_ledger_does_not_truncate_the_stream(self, cost_meter_db) -> None:
        """A logging failure must never cost the user their reply."""
        from alchymine.api.deps import set_db_engine
        from sqlalchemy.ext.asyncio import create_async_engine

        client = _claude_client()
        stream = _FakeStream(
            ["a", "b", "c"], _FinalMessage(usage=_Usage(input_tokens=10, output_tokens=5))
        )
        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock(return_value=_FakeStreamManager(stream))

        chunks: list[str] = []
        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            async for chunk in client._stream_claude("prompt", "system", 100, 0.5):
                chunks.append(chunk)
                if len(chunks) == 1:
                    # Break the ledger mid-stream, after the call is charged.
                    broken = create_async_engine("postgresql+asyncpg://nobody@127.0.0.1:1/x")
                    set_db_engine(broken)

        set_db_engine(cost_meter_db)
        await broken.dispose()
        assert chunks == ["a", "b", "c"]

    async def test_cancellation_inside_the_recording_path_still_leaves_a_row(
        self, cost_meter_db
    ) -> None:
        """uvicorn cancels the request task; the cancel lands mid-capture.

        CancelledError is a BaseException, so it walks straight past every
        ``except Exception`` net. Cancel the task while the recording code
        is waiting on ``get_final_message()`` and, without explicit
        handling, the estimate is never written and a call we were billed
        for in full disappears from the ledger.
        """
        import asyncio

        client = _claude_client()
        reached_capture = asyncio.Event()

        class _HangingFinalStream(_FakeStream):
            async def get_final_message(self) -> _FinalMessage:
                reached_capture.set()
                await asyncio.sleep(3600)
                raise AssertionError("unreachable")

        stream = _HangingFinalStream(["hello "], final=None)
        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock(return_value=_FakeStreamManager(stream))

        async def consume() -> None:
            with attributed(user_id="user-gone", surface="chat"):
                async for _ in client._stream_claude("prompt", "system", 100, 0.5):
                    pass

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            task = asyncio.create_task(consume())
            await reached_capture.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await flush_pending_writes()

        rows = await _rows(cost_meter_db)
        assert len(rows) == 1, "a cancelled stream must still be recorded"
        assert rows[0].estimated is True
        assert rows[0].user_id == "user-gone"
        assert rows[0].output_tokens == len("hello ") // 4

    async def test_the_stream_records_once_per_model_that_delivered(self, cost_meter_db) -> None:
        """A 529 before any text is delivered leaves no ledger row behind."""
        import anthropic

        client = _claude_client()
        overloaded = anthropic.APIStatusError(
            "overloaded",
            response=httpx.Response(529, request=httpx.Request("POST", "https://api")),
            body=None,
        )
        good = _FakeStream(
            ["ok"], _FinalMessage(usage=_Usage(input_tokens=10, output_tokens=2), model=HAIKU)
        )

        def _stream(**kwargs: object):  # noqa: ANN202
            if kwargs.get("model") == SONNET:
                raise overloaded
            return _FakeStreamManager(good)

        fake_sdk = MagicMock()
        fake_sdk.messages.stream = MagicMock(side_effect=_stream)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            chunks = [c async for c in client._stream_claude("prompt", "system", 100, 0.5)]

        assert chunks == ["ok"]
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].model == HAIKU


# ── Gemini ───────────────────────────────────────────────────────────────


class TestGeminiChokepoint:
    async def test_writes_one_flat_priced_row_per_image(self, cost_meter_db) -> None:
        inline = MagicMock(data=b"\x89PNG", mime_type="image/png")
        part = MagicMock(inline_data=inline)
        candidate = MagicMock(content=MagicMock(parts=[part]))

        with patch("alchymine.llm.gemini._genai", MagicMock()):
            client = _gemini_client()
            client._client.aio.models.generate_content = AsyncMock(
                return_value=MagicMock(candidates=[candidate])
            )
            with attributed(user_id="user-1", surface="art"):
                result = await client.generate_image("a serene forest")

        assert result is not None
        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].provider == "google"
        assert rows[0].meter == METER_ART_GENERATIONS
        assert rows[0].images == 1
        assert rows[0].model == "gemini-test"
        assert rows[0].surface == "art"
        assert rows[0].cost_micros == get_settings().gemini_image_cost_micros

    async def test_an_undecodable_image_is_still_recorded(self, cost_meter_db) -> None:
        """Google billed for the image it produced; the ledger must see it.

        A payload we cannot decode is our problem, not evidence that the
        generation never happened. Returning None without a row would hide
        real spend behind a client-side parse failure.
        """
        inline = MagicMock(data="not base64 !!!", mime_type="image/png")
        part = MagicMock(inline_data=inline)
        candidate = MagicMock(content=MagicMock(parts=[part]))

        with patch("alchymine.llm.gemini._genai", MagicMock()):
            client = _gemini_client()
            client._client.aio.models.generate_content = AsyncMock(
                return_value=MagicMock(candidates=[candidate])
            )
            assert await client.generate_image("a serene forest") is None

        rows = await _rows(cost_meter_db)
        assert len(rows) == 1
        assert rows[0].images == 1
        assert rows[0].estimated is True
        assert rows[0].cost_micros == get_settings().gemini_image_cost_micros

    async def test_a_generation_that_produced_no_image_writes_no_row(self, cost_meter_db) -> None:
        with patch("alchymine.llm.gemini._genai", MagicMock()):
            client = _gemini_client()
            client._client.aio.models.generate_content = AsyncMock(
                return_value=MagicMock(candidates=[])
            )
            assert await client.generate_image("a serene forest") is None

        assert await _rows(cost_meter_db) == []


# ── The report fan-out ───────────────────────────────────────────────────


class TestNarrativeFanOut:
    async def test_five_concurrent_narratives_share_one_user_id(self, cost_meter_db) -> None:
        """narrative.py gathers five paid calls; Task creation copies context."""
        from alchymine.llm.narrative import NarrativeGenerator

        client = _claude_client()
        response = MagicMock()
        response.content = [MagicMock(text="a gentle narrative")]
        response.usage = _Usage(input_tokens=100, output_tokens=50)
        fake_sdk = MagicMock()
        fake_sdk.messages.create = AsyncMock(return_value=response)

        systems = ["intelligence", "healing", "wealth", "creative", "perspective"]
        generator = NarrativeGenerator(client=client)

        with patch("anthropic.AsyncAnthropic", return_value=fake_sdk):
            with attributed(user_id="user-report", surface="report_narrative"):
                await generator.generate_all(systems, {s: {} for s in systems})

        rows = await _rows(cost_meter_db)
        assert len(rows) == 5
        assert {row.user_id for row in rows} == {"user-report"}
        assert {row.surface for row in rows} == {"report_narrative"}

"""What survives a client that walks away mid-reply (issue #297).

Both chat generators persisted the assistant half of the turn *after*
their streaming block, outside any ``try``.  That placement has two
consequences and neither of them is visible from a passing request:

- A browser closing the tab mid-reply throws ``GeneratorExit`` at the
  suspended ``yield``.  ``GeneratorExit`` is a ``BaseException``, so it
  walks straight past ``except Exception`` and out of the generator, and
  the write below never runs.  The user message was committed up front
  and survives; the reply the reader watched arrive does not.  The
  transcript ends up with a question and no answer.
- A database failure in that same write escaped the generator after
  content had already streamed, which is a 500 with a 200 already on the
  wire.

The tests here drive the generators directly rather than through
``TestClient``.  A disconnect is exactly ``aclose()`` on a suspended
async generator, and the test client has no way to express one: it
consumes every response whole.

The crisis path carries the same guarantee and one more.  Its frames
went out as raw ``data: {part}`` lines, which is correct only while the
copy holds no newlines -- an invariant nothing enforced, on the
highest-stakes content in the app.  It now shares ``_sse_data_frame``
with the model path, so a newline that ever does appear survives instead
of truncating a hotline number.  The copy itself is unchanged, and that
is asserted here rather than assumed.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import alchymine.db.models  # noqa: F401 (registers models with metadata)
from alchymine.api.deps import set_db_engine
from alchymine.api.routers import chat as chat_router
from alchymine.api.routers.chat import flush_pending_reply_writes
from alchymine.db.base import Base
from alchymine.db.models import ChatMessage
from alchymine.engine.healing.crisis import (
    CrisisResource,
    CrisisResponse,
    CrisisSeverity,
    detect_crisis,
)

from .conftest import TEST_USER_ID

pytestmark = pytest.mark.asyncio


# On topic for the general coach and clear of every blocked pattern.
MESSAGE = "How can I steady my morning routine?"

# Short on purpose.  The ethics checker has a 100-character floor, so a
# reply this size cannot trip a category or ask for a disclaimer, and the
# tests below stay about persistence rather than about the gates.
CHUNKS = ["A steady ", "start helps."]
REPLY = "".join(CHUNKS)

EMERGENCY_MESSAGE = "I keep thinking about suicide and I cannot shake it"


# ─── A spec-correct SSE parser, written for the test ───────────────────
#
# Deliberately not imported from the router: a test that reuses the code
# under test cannot tell correct framing from matching bugs.  Same parser
# as ``test_chat_sse_framing``, kept local for the same reason.


def parse_sse(body: str) -> list[tuple[str | None, str]]:
    """Return ``(event name, data)`` per event, the way a client reads it."""
    events: list[tuple[str | None, str]] = []
    name: str | None = None
    data: list[str] = []

    for raw_line in body.split("\n"):
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line

        if line == "":
            if data or name is not None:
                events.append((name, "\n".join(data)))
            name = None
            data = []
            continue

        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            value = line[5:]
            data.append(value[1:] if value.startswith(" ") else value)

    return events


def streamed_text(body: str) -> str:
    """The reply a client assembles: every unnamed event, concatenated."""
    return "".join(data for name, data in parse_sse(body) if name is None)


# ─── Fixtures ──────────────────────────────────────────────────────────


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class _ScriptedClient:
    """Stands in for ``LLMClient`` and emits exactly the chunks set on it."""

    chunks: list[str] = []

    def __init__(self) -> None:
        pass

    async def stream_generate(self, **kwargs: object) -> AsyncGenerator[str, None]:
        for chunk in _ScriptedClient.chunks:
            yield chunk


@pytest.fixture(autouse=True)
def scripted_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_ScriptedClient]]:
    _ScriptedClient.chunks = list(CHUNKS)
    monkeypatch.setattr(chat_router, "LLMClient", _ScriptedClient)
    yield _ScriptedClient
    _ScriptedClient.chunks = []


@pytest.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    await _create_tables(engine)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    # The retry on the disconnect path opens a session of its own from the
    # engine singleton, exactly as production does where the request
    # session and the singleton are the same database.  Without this the
    # fallback would write to the counters-only engine the shared fixture
    # installs, and miss the table it is looking for.
    set_db_engine(engine)
    try:
        yield factory
    finally:
        await flush_pending_reply_writes()
        set_db_engine(None)
        await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as db_session:
        yield db_session


async def _messages(factory: async_sessionmaker[AsyncSession]) -> list[ChatMessage]:
    async with factory() as read_session:
        result = await read_session.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == TEST_USER_ID)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        return list(result.scalars().all())


def _chat_stream(session: AsyncSession, **overrides: object) -> AsyncGenerator[str, None]:
    kwargs: dict = {
        "user_id": TEST_USER_ID,
        "message": MESSAGE,
        "system_key": None,
        "session": session,
    }
    kwargs.update(overrides)
    return chat_router._chat_event_stream(**kwargs)


# ─── The model path: a browser that goes away ──────────────────────────


class TestChatDisconnectPersistence:
    async def test_a_mid_stream_disconnect_still_persists_the_delivered_reply(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """The reader saw it; the transcript has to have it too.

        ``aclose()`` on a suspended generator is what a closed tab does to
        this code.  Before the fix the assistant row was simply absent.
        """
        stream = _chat_stream(session)
        first = await stream.__anext__()
        await stream.aclose()

        assert streamed_text(first) == CHUNKS[0]

        rows = await _messages(session_factory)
        assert [row.role for row in rows] == ["user", "assistant"]
        assert rows[1].content == CHUNKS[0]

    async def test_a_disconnect_before_any_content_writes_no_assistant_row(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Nothing was delivered, so there is no reply to keep.

        The faithful shape of this one is a cancellation while the
        generator is still waiting on the model's first chunk, which is
        where a reader who changes their mind lands most often.
        Persisting anyway would seed every abandoned turn with a blank
        assistant bubble that renders as a reply the coach never gave.
        """

        class _HangingClient:
            async def stream_generate(self, **kwargs: object) -> AsyncGenerator[str, None]:
                await asyncio.sleep(3600)
                yield "unreachable"

        monkeypatch.setattr(chat_router, "LLMClient", _HangingClient)

        async def consume() -> None:
            async for _ in _chat_stream(session):
                pass

        task = asyncio.create_task(consume())
        # Long enough for the user message to commit and the generator to
        # reach the model call it will never get an answer from.
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        rows = await _messages(session_factory)
        assert [row.role for row in rows] == ["user"]

    async def test_a_completed_stream_persists_exactly_one_reply(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Moving the write into a ``finally`` must not double-write it."""
        body = "".join([frame async for frame in _chat_stream(session)])

        assert streamed_text(body) == REPLY

        rows = await _messages(session_factory)
        assert [row.role for row in rows] == ["user", "assistant"]
        assert rows[1].content == REPLY

    async def test_an_empty_reply_that_completed_is_still_persisted(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """A model that said nothing is different from a reader who left.

        The first is a turn that happened and read as empty; the second
        never finished.  Only the second is skipped.
        """
        _ScriptedClient.chunks = []

        body = "".join([frame async for frame in _chat_stream(session)])

        assert body.endswith("event: done\ndata: \n\n")

        rows = await _messages(session_factory)
        assert [row.role for row in rows] == ["user", "assistant"]
        assert rows[1].content == ""

    async def test_an_ephemeral_disconnect_persists_nothing(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Ephemeral means ephemeral on every exit path, disconnect included."""
        stream = _chat_stream(session, ephemeral=True)
        await stream.__anext__()
        await stream.aclose()

        assert await _messages(session_factory) == []

    async def test_cancellation_mid_stream_persists_and_re_raises(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """uvicorn cancels the request task when the socket drops.

        ``CancelledError`` is a ``BaseException`` too, and swallowing it
        would break the shutdown of whoever asked for the cancel.  The
        write is attempted first, then the cancellation continues on its
        way.
        """
        started = asyncio.Event()

        async def consume() -> None:
            # Owned and closed by the consumer, which is the shape
            # Starlette's task group has around a streaming response body.
            # The close therefore runs while this task is already
            # unwinding, and the write inside it has to survive that.
            stream = _chat_stream(session)
            try:
                async for _ in stream:
                    started.set()
                    await asyncio.sleep(3600)
            finally:
                await stream.aclose()

        task = asyncio.create_task(consume())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # The write outlived the caller that started it, which is the
        # whole point; it still has to land.
        await flush_pending_reply_writes()

        rows = await _messages(session_factory)
        assert [row.role for row in rows] == ["user", "assistant"]
        assert rows[1].content == CHUNKS[0]


def _failing_assistant_write(calls: list[str]):
    """A ``save_chat_message`` whose assistant write always fails.

    The user write still succeeds and still returns a row, because the
    generator reads ``id`` off it to attribute the ledger.
    """

    async def _write(session: AsyncSession, **kwargs: object) -> ChatMessage:
        role = str(kwargs.get("role"))
        calls.append(role)
        if role == "assistant":
            raise RuntimeError("chat_messages is unreachable")
        row = ChatMessage(
            user_id=str(kwargs["user_id"]),
            role=role,
            content=str(kwargs["content"]),
            system_key=kwargs.get("system_key"),  # type: ignore[arg-type]
        )
        session.add(row)
        await session.flush()
        return row

    return _write


class TestChatPersistenceFailure:
    async def test_a_failed_write_does_not_truncate_the_delivered_reply(
        self,
        session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A broken transcript must not cost the user their answer."""

        monkeypatch.setattr(
            chat_router.repository, "save_chat_message", _failing_assistant_write([])
        )

        body = "".join([frame async for frame in _chat_stream(session)])

        assert streamed_text(body) == REPLY
        assert body.endswith("event: done\ndata: \n\n")

    async def test_a_failed_write_is_logged_without_the_message_text(
        self,
        session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Loud about the failure, silent about the content.

        Chat text is user data.  A log line that quotes the reply turns a
        transcript outage into a disclosure.
        """
        calls: list[str] = []

        monkeypatch.setattr(
            chat_router.repository, "save_chat_message", _failing_assistant_write(calls)
        )

        with caplog.at_level(logging.ERROR, logger=chat_router.logger.name):
            [frame async for frame in _chat_stream(session)]

        assert "assistant" in calls
        assert caplog.records, "a dropped reply has to be loud in the logs"
        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert REPLY not in logged
        assert MESSAGE not in logged


# ─── The crisis path ───────────────────────────────────────────────────


def _crisis() -> CrisisResponse:
    crisis = detect_crisis(EMERGENCY_MESSAGE)
    assert crisis is not None
    return crisis


def _crisis_stream(session: AsyncSession, **overrides: object) -> AsyncGenerator[str, None]:
    kwargs: dict = {
        "user_id": TEST_USER_ID,
        "message": EMERGENCY_MESSAGE,
        "system_key": None,
        "crisis": _crisis(),
        "session": session,
    }
    kwargs.update(overrides)
    return chat_router._crisis_event_stream(**kwargs)


class TestCrisisDisconnectPersistence:
    async def test_a_crisis_disconnect_still_persists_the_whole_turn(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """The docstring promised the turn is persisted.  Only half was.

        The reply here is ours and is complete before the first frame
        leaves, so a reader who closes the tab loses nothing that has to
        be reconstructed.  Dropping it would leave the hardest thing a
        user has typed sitting in the transcript with no answer under it.
        """
        stream = _crisis_stream(session)
        await stream.__anext__()
        await stream.aclose()

        rows = await _messages(session_factory)
        assert [row.role for row in rows] == ["user", "assistant"]
        assert "988" in rows[1].content

    async def test_an_ephemeral_crisis_disconnect_persists_nothing(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        stream = _crisis_stream(session, ephemeral=True)
        await stream.__anext__()
        await stream.aclose()

        assert await _messages(session_factory) == []


class TestCrisisFraming:
    async def test_a_newline_in_crisis_copy_survives_the_wire(
        self, session: AsyncSession
    ) -> None:
        """The invariant nobody enforced, now enforced by the framing.

        Raw ``data: {part}`` truncates at the first newline.  On this path
        that would cut a hotline number in half, so the framing is shared
        with the model path rather than trusted to stay single-line.
        """
        crisis = CrisisResponse(
            severity=CrisisSeverity.EMERGENCY,
            matched_keywords=("suicide",),
            resources=(
                CrisisResource(
                    name="988 Suicide & Crisis Lifeline",
                    contact="Call or text 988",
                    description="Free and confidential.\nAvailable 24/7.",
                ),
            ),
            disclaimers=("This is not a substitute for professional help.",),
        )

        body = "".join([frame async for frame in _crisis_stream(session, crisis=crisis)])

        assert "Free and confidential.\nAvailable 24/7." in streamed_text(body)

    async def test_the_streamed_crisis_text_equals_what_is_persisted(
        self,
        session: AsyncSession,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """A transcript that disagrees with the stream is a second bug.

        The old framing appended a space to every frame, so the stream
        carried one more character than the row did.
        """
        body = "".join([frame async for frame in _crisis_stream(session)])

        rows = await _messages(session_factory)
        assert streamed_text(body) == rows[1].content

    async def test_the_crisis_copy_is_unchanged(self, session: AsyncSession) -> None:
        """Framing moved.  Wording did not."""
        body = "".join([frame async for frame in _crisis_stream(session)])
        text = streamed_text(body)

        assert text == " ".join(chat_router._crisis_frames(_crisis(), None))
        assert "988" in text
        assert "Before anything else:" in text
        assert "not a substitute for professional help" in text

    async def test_the_practice_opening_still_rides_the_practice_scope(
        self, session: AsyncSession
    ) -> None:
        body = "".join(
            [frame async for frame in _crisis_stream(session, system_key="practice")]
        )

        assert "Before anything about practice" in streamed_text(body)

    async def test_the_stream_still_ends_with_the_done_sentinel(
        self, session: AsyncSession
    ) -> None:
        body = "".join([frame async for frame in _crisis_stream(session)])

        assert body.endswith("event: done\ndata: \n\n")

"""SSE framing on ``POST /api/v1/chat``: newlines survive the wire.

Issue #278. A ``data:`` field ends at the first newline, so a model
chunk carrying newlines cannot go out as one ``data:`` line: everything
after the first newline stops being part of the field and the client
drops it. Paragraph breaks are the common case, so the loss is silent
and routine.

The properties pinned here:

- Text handed to the stream comes back byte-for-byte after a spec-correct
  parse, newlines and blank lines included.
- Single-line chunks frame exactly the way they always have, so nothing
  about the common case moved.
- Every scope shares the one framing site, so the guarantee is the same
  on all six.
- What is persisted equals what was streamed. A reply that reads whole in
  the transcript and truncated in the live stream is the failure this
  test exists to catch.

The parser below is deliberately written from the SSE spec rather than
imported from the router: a test that reuses the code under test cannot
tell correct framing from matching bugs.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import alchymine.db.models  # noqa: F401 (registers models with metadata)
from alchymine.api.deps import get_db_session, set_db_engine
from alchymine.api.main import app
from alchymine.api.routers import chat as chat_router
from alchymine.db.base import Base
from alchymine.db.models import ChatMessage

from .conftest import TEST_USER_ID

# On-topic for all six scopes and clear of every blocked pattern.
MESSAGE = "How can I steady my morning routine?"

# The shape that breaks today: a hard line break, a blank line between
# paragraphs, and a trailing newline.
MULTILINE_CHUNK = "First line\nSecond line\n\nThird paragraph"

SCOPES = ["intelligence", "healing", "wealth", "creative", "perspective", "practice"]


# ─── A spec-correct SSE parser, written for the test ───────────────────


class SseEvent:
    """One parsed event: its name (``None`` when unnamed) and its data."""

    def __init__(self, name: str | None, data: str) -> None:
        self.name = name
        self.data = data


def parse_sse(body: str) -> list[SseEvent]:
    """Parse an event stream the way a spec-following client does.

    Data lines accumulate until the blank line that ends the event, then
    join with a newline. A single leading space after the colon is part
    of the framing, not the payload.
    """
    events: list[SseEvent] = []
    name: str | None = None
    data: list[str] = []

    for raw_line in body.split("\n"):
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line

        if line == "":
            if data or name is not None:
                events.append(SseEvent(name, "\n".join(data)))
            name = None
            data = []
            continue

        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            value = line[5:]
            data.append(value[1:] if value.startswith(" ") else value)
        # Anything else (a comment line, say) is ignored per the spec.

    return events


def streamed_text(body: str) -> str:
    """The reply a client assembles: every unnamed event, concatenated."""
    return "".join(event.data for event in parse_sse(body) if event.name is None)


# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class _Env:
    """A TestClient plus a way to read back what was persisted."""

    def __init__(
        self,
        client: TestClient,
        factory: async_sessionmaker[AsyncSession],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.client = client
        self.factory = factory
        self.loop = loop

    def assistant_replies(self) -> list[str]:
        async def _read() -> list[str]:
            async with self.factory() as session:
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.user_id == TEST_USER_ID)
                    .where(ChatMessage.role == "assistant")
                    .order_by(ChatMessage.created_at.asc())
                )
                return [row.content for row in result.scalars().all()]

        return self.loop.run_until_complete(_read())

    def post(self, system_key: str | None = None) -> str:
        body: dict = {"message": MESSAGE, "system_key": system_key}
        response = self.client.post("/api/v1/chat", json=body)
        assert response.status_code == 200, response.text
        return response.text


@pytest.fixture
def env() -> Iterator[_Env]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_create_tables(engine))

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_session
    set_db_engine(engine)
    try:
        yield _Env(TestClient(app), factory, loop)
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        set_db_engine(None)
        loop.run_until_complete(engine.dispose())
        loop.close()


class _ScriptedClient:
    """Stands in for ``LLMClient`` and emits exactly the chunks set on it.

    The bundled ``none`` backend splits on whitespace, so it structurally
    cannot produce a chunk with a newline in it. This one can, which is
    the only reason the bug was invisible to the suite.
    """

    chunks: list[str] = []

    def __init__(self) -> None:
        pass

    async def stream_generate(self, **kwargs: object) -> AsyncGenerator[str, None]:
        for chunk in _ScriptedClient.chunks:
            yield chunk


@pytest.fixture(autouse=True)
def scripted_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_ScriptedClient]]:
    _ScriptedClient.chunks = [MULTILINE_CHUNK]
    monkeypatch.setattr(chat_router, "LLMClient", _ScriptedClient)
    yield _ScriptedClient
    _ScriptedClient.chunks = []


# ─── Round-trip ────────────────────────────────────────────────────────


class TestNewlineRoundTrip:
    def test_multiline_chunk_arrives_whole(self, env: _Env) -> None:
        body = env.post()

        assert streamed_text(body) == MULTILINE_CHUNK

    def test_blank_line_between_paragraphs_survives(self, env: _Env) -> None:
        """The empty segment between two newlines is content, not padding."""
        _ScriptedClient.chunks = ["Paragraph one.\n\nParagraph two."]

        assert streamed_text(env.post()) == "Paragraph one.\n\nParagraph two."

    def test_trailing_newline_survives(self, env: _Env) -> None:
        _ScriptedClient.chunks = ["Ends with a break\n"]

        assert streamed_text(env.post()) == "Ends with a break\n"

    def test_leading_newline_survives(self, env: _Env) -> None:
        _ScriptedClient.chunks = ["\nStarts with a break"]

        assert streamed_text(env.post()) == "\nStarts with a break"

    def test_bare_newline_chunk_survives(self, env: _Env) -> None:
        _ScriptedClient.chunks = ["one", "\n", "two"]

        assert streamed_text(env.post()) == "one\ntwo"

    def test_many_chunks_concatenate_exactly(self, env: _Env) -> None:
        """Chunk boundaries are not separators. The join adds nothing."""
        chunks = ["Try this:\n\n", "1. Sit down\n", "2. Breathe\n", "\nThat is the whole of it."]
        _ScriptedClient.chunks = list(chunks)

        assert streamed_text(env.post()) == "".join(chunks)


# ─── The common case does not move ─────────────────────────────────────


class TestSingleLineFramingUnchanged:
    def test_single_line_chunks_frame_one_data_line_each(self, env: _Env) -> None:
        _ScriptedClient.chunks = ["A steady ", "reply."]

        body = env.post()

        assert "data: A steady \n\n" in body
        assert "data: reply.\n\n" in body

    def test_single_line_reply_reassembles(self, env: _Env) -> None:
        _ScriptedClient.chunks = ["A steady ", "reply."]

        assert streamed_text(env.post()) == "A steady reply."

    def test_stream_still_ends_with_the_done_sentinel(self, env: _Env) -> None:
        body = env.post()

        assert body.endswith("event: done\ndata: \n\n")
        assert [event.name for event in parse_sse(body)][-1] == "done"


# ─── One framing site, six scopes ──────────────────────────────────────


class TestEveryScope:
    @pytest.mark.parametrize("system_key", SCOPES)
    def test_scope_carries_newlines_whole(self, env: _Env, system_key: str) -> None:
        assert streamed_text(env.post(system_key)) == MULTILINE_CHUNK

    def test_default_scope_carries_newlines_whole(self, env: _Env) -> None:
        """No ``system_key`` at all routes to the general coach."""
        assert streamed_text(env.post(None)) == MULTILINE_CHUNK


# ─── Transcript and stream agree ───────────────────────────────────────


class TestPersistenceMatchesTheStream:
    def test_persisted_reply_equals_the_streamed_text(self, env: _Env) -> None:
        body = env.post()

        assert env.assistant_replies() == [streamed_text(body)]

    def test_persisted_reply_keeps_its_newlines(self, env: _Env) -> None:
        env.post()

        assert env.assistant_replies() == [MULTILINE_CHUNK]

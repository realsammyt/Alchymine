"""The crisis and ethics gates on every chat scope (issues #263, #279).

Slice 5 of epic #251 wired ``detect_crisis`` and ``check_text`` to the
``practice`` scope alone and left the other five with the local regex
they had always had.  This is the rollout.  The six scopes share one
code path, so widening the two scope guards in
``alchymine/api/routers/chat.py`` is the whole of the structural change;
these tests pin what that widening is supposed to mean.

The properties worth naming:

- A crisis disclosure gets resources on every scope, and on no scope
  does it cost an LLM call, a ledger row or a plan check.  The ordering
  slice 1 established (crisis before ``require_chat.enforce``) is
  structural, so it holds for the widened gate without further work;
  these tests are what stops it silently un-holding.
- The five harm categories block exactly as they did on practice.
  Nothing about which categories block moved.
- A missing disclaimer never blocks and never interrupts.  It is
  appended to the reply as extra frames before ``event: done``, which is
  what #279 asks for and what the old code deferred.
- ``check_text`` runs under the context that matches the scope rather
  than under ``"healing"`` for everything.  ``creative`` and
  ``perspective`` have no disclaimer rule at all in the checker, so the
  visible consequence of getting the context wrong is a disclaimer
  appearing on a scope that never asked for one.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager

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

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.agents.growth.system_prompts import SYSTEM_PROMPTS
from alchymine.agents.quality.ethics_check import (
    FINANCIAL_DISCLAIMER,
    HEALING_DISCLAIMER,
    ViolationCategory,
    check_text,
)
from alchymine.api.auth import get_current_account
from alchymine.api.deps import get_db_session, set_db_engine
from alchymine.api.main import app
from alchymine.api.routers import chat as chat_router
from alchymine.db.base import Base
from alchymine.db.models import ChatMessage, UsageRecord

from .conftest import TEST_USER_ID
from .conftest import test_account as build_account

# Every scope the endpoint accepts, plus the unscoped default.  ``None``
# is the general coach the chat bubble reaches when no system is
# selected, and a gate that covered the six named scopes but not the
# default would leave the most reachable surface of all uncovered.
SCOPES: list[str] = sorted(SYSTEM_PROMPTS)
SCOPES_AND_DEFAULT: list[str | None] = [*SCOPES, None]

EMERGENCY_MESSAGE = "I keep thinking about suicide and I cannot shake it"
HIGH_MESSAGE = "my partner has been abusing me and I do not know what to do"
MEDIUM_MESSAGE = "I had a panic attack this morning"

# Long enough to clear the checker's 100-character floor, carrying
# healing vocabulary ("meditation", "breathwork", "somatic") and no
# disclaimer indicator.
HEALING_REPLY_CHUNKS = [
    "Your breathwork and meditation rhythm has held steady this week. ",
    "Two somatic sessions and one long reflection is a real pattern, ",
    "not a fluke, and it is worth naming that out loud.",
]

# Same shape on the financial side ("income", "savings", "portfolio").
WEALTH_REPLY_CHUNKS = [
    "Your income has been steadier than it was, and the savings buffer ",
    "you started in spring is doing the job you built it for. ",
    "The portfolio question can wait until that buffer feels boring.",
]

# Healing vocabulary with a disclaimer already in it, so the checker has
# nothing to ask for.
HEALING_REPLY_WITH_DISCLAIMER = [
    "Your breathwork and meditation rhythm has held steady this week, ",
    "and two somatic sessions is a real pattern rather than a fluke. ",
    "This is not medical advice. Consult a qualified healthcare professional.",
]

# Trips FATALISTIC_LANGUAGE at ERROR severity, which is one of the five
# blocking categories.
BLOCKING_CHUNK = "You are destined to master this."


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class _Env:
    """A TestClient plus the pieces a test inspects afterwards."""

    def __init__(
        self,
        client: TestClient,
        factory: async_sessionmaker[AsyncSession],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.client = client
        self.factory = factory
        self.loop = loop

    def run(self, coro):  # type: ignore[no-untyped-def]
        return self.loop.run_until_complete(coro)

    def chat_messages(self) -> list[ChatMessage]:
        async def _read() -> list[ChatMessage]:
            async with self.factory() as session:
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.user_id == TEST_USER_ID)
                    .order_by(ChatMessage.created_at.asc())
                )
                return list(result.scalars().all())

        return self.run(_read())

    def usage_records(self) -> list[UsageRecord]:
        async def _read() -> list[UsageRecord]:
            async with self.factory() as session:
                result = await session.execute(select(UsageRecord))
                return list(result.scalars().all())

        return self.run(_read())


@pytest.fixture
def env() -> Iterator[_Env]:
    """One in-memory database serving both the app and the ledger."""
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


class _RecordingClient:
    """Stands in for ``LLMClient`` and remembers what it was asked for."""

    calls: list[dict] = []
    chunks: list[str] = ["A steady ", "reply."]

    def __init__(self) -> None:
        pass

    async def stream_generate(self, **kwargs: object) -> AsyncGenerator[str, None]:
        _RecordingClient.calls.append(dict(kwargs))
        for chunk in _RecordingClient.chunks:
            yield chunk


@pytest.fixture(autouse=True)
def recording_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_RecordingClient]]:
    _RecordingClient.calls = []
    _RecordingClient.chunks = ["A steady ", "reply."]
    monkeypatch.setattr(chat_router, "LLMClient", _RecordingClient)
    yield _RecordingClient
    _RecordingClient.calls = []


def _post(env: _Env, message: str, system_key: str | None, **params: object):
    body: dict = {"message": message}
    if system_key is not None:
        body["system_key"] = system_key
    response = env.client.post("/api/v1/chat", json=body, params=params)
    _ = response.text  # drain the stream so after-stream persistence runs
    return response


@contextmanager
def _as_plan(plan: str) -> Iterator[None]:
    """Call the endpoint as the test user on *plan*."""
    previous = app.dependency_overrides.get(get_current_account)
    app.dependency_overrides[get_current_account] = lambda: build_account(TEST_USER_ID, plan)
    try:
        yield
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_account, None)
        else:
            app.dependency_overrides[get_current_account] = previous


def _streamed_text(response_text: str) -> str:
    """Join the ``data:`` payloads of every unnamed event, SSE-style.

    Written from the spec rather than reusing the router's framing
    helper: a test that shares the code under test cannot tell correct
    framing from a matching bug.
    """
    text: list[str] = []
    for block in response_text.split("\n\n"):
        lines = block.split("\n")
        if any(line.startswith("event:") for line in lines):
            continue
        data = [line[len("data:") :].lstrip(" ") for line in lines if line.startswith("data:")]
        if data:
            text.append("\n".join(data))
    return "".join(text)


# ─── Inbound: the crisis gate, everywhere ───────────────────────────────


class TestCrisisGateOnEveryScope:
    """``detect_crisis`` no longer stops at the practice scope.

    The gate used to read ``PRACTICE_SYSTEM_KEY`` and return ``None`` for
    everything else, which meant the five live coaching scopes answered
    "I keep thinking about suicide" with a coaching reply.  That was the
    deliberate limit of slice 5 and the whole of issue #263.
    """

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    @pytest.mark.parametrize("message", [EMERGENCY_MESSAGE, HIGH_MESSAGE])
    def test_crisis_message_streams_resources(
        self, env: _Env, system_key: str | None, message: str
    ) -> None:
        response = _post(env, message, system_key)

        assert response.status_code == 200
        assert "988" in response.text
        assert "event: done" in response.text

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_crisis_message_makes_no_llm_call(self, env: _Env, system_key: str | None) -> None:
        _post(env, EMERGENCY_MESSAGE, system_key)

        assert _RecordingClient.calls == []

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_crisis_message_writes_no_ledger_row(self, env: _Env, system_key: str | None) -> None:
        """Ungated does not mean free inference. The path stays deterministic."""
        _post(env, EMERGENCY_MESSAGE, system_key)

        assert env.usage_records() == []

    @pytest.mark.parametrize("system_key", ["healing", "wealth", "creative", None])
    def test_a_free_plan_crisis_message_is_not_refused(
        self, env: _Env, system_key: str | None
    ) -> None:
        """Slice 1 put the crisis check above the plan gate for exactly this.

        The ordering is structural, so widening the gate inherits it. This
        is the test that says so out loud for the scopes that were never
        covered before.
        """
        with _as_plan("free"):
            response = _post(env, EMERGENCY_MESSAGE, system_key)

        assert response.status_code == 200
        assert "988" in response.text
        assert _RecordingClient.calls == []

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_medium_severity_still_reaches_the_coach(
        self, env: _Env, system_key: str | None
    ) -> None:
        """The gate fires at high and emergency only, on every scope.

        Handing somebody who mentioned a panic attack a hotline list
        instead of a conversation would be the wrong kind of careful, and
        the tier boundary is unchanged by the rollout.
        """
        _post(env, MEDIUM_MESSAGE, system_key)

        assert len(_RecordingClient.calls) == 1

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_the_crisis_turn_is_persisted(self, env: _Env, system_key: str | None) -> None:
        _post(env, EMERGENCY_MESSAGE, system_key)

        messages = env.chat_messages()
        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[0].content == EMERGENCY_MESSAGE
        assert "988" in messages[1].content

    def test_the_practice_opening_line_stays_on_the_practice_scope(self, env: _Env) -> None:
        """Reviewed copy, reused verbatim where it still fits.

        "Before anything about practice" is true on the practice scope and
        false on wealth, so the wealth reader gets a scope-neutral opener
        instead. Both carry the same resources and the same disclaimer.
        """
        practice = _post(env, EMERGENCY_MESSAGE, "practice").text
        wealth = _post(env, EMERGENCY_MESSAGE, "wealth").text

        assert "Before anything about practice" in practice
        assert "Before anything about practice" not in wealth
        assert "988" in wealth
        assert "not a substitute for professional help" in wealth


# ─── Outbound: the blocking categories, everywhere ──────────────────────


class TestBlockingCategoriesOnEveryScope:
    """The five harm categories block on every scope, and only those five."""

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_a_violating_reply_is_blocked_at_end_of_stream(
        self, env: _Env, system_key: str | None
    ) -> None:
        _RecordingClient.chunks = [BLOCKING_CHUNK]

        response = _post(env, "How am I doing?", system_key)

        assert "event: error" in response.text

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_a_violating_reply_is_truncated_at_the_cadence(
        self, env: _Env, system_key: str | None
    ) -> None:
        """Eight chunks in, the accumulation is checked and the rest dropped."""
        _RecordingClient.chunks = [
            *[f"word{n} " for n in range(7)],
            "you are destined to master this. ",
            *[f"tail{n} " for n in range(8)],
        ]

        response = _post(env, "How am I doing?", system_key)

        assert "event: error" in response.text
        assert "tail7" not in response.text

    @pytest.mark.parametrize("system_key", SCOPES_AND_DEFAULT)
    def test_a_violating_reply_is_not_persisted(self, env: _Env, system_key: str | None) -> None:
        _RecordingClient.chunks = [BLOCKING_CHUNK]

        _post(env, "How am I doing?", system_key)

        assistant = [m for m in env.chat_messages() if m.role == "assistant"]
        assert assistant[0].content == "[response blocked by safety filter]"

    def test_the_blocking_categories_are_the_same_five(self) -> None:
        """The rollout widens who is checked, not what blocks."""
        assert chat_router._BLOCKING_CATEGORIES == frozenset(
            {
                ViolationCategory.FATALISTIC_LANGUAGE.value,
                ViolationCategory.DIAGNOSTIC_LANGUAGE.value,
                ViolationCategory.DARK_PATTERNS.value,
                ViolationCategory.CULTURAL_INSENSITIVITY.value,
                ViolationCategory.FINANCIAL_ADVICE.value,
            }
        )
        assert ViolationCategory.MISSING_DISCLAIMER.value not in chat_router._BLOCKING_CATEGORIES


# ─── Outbound: append the disclaimer, never block on it ─────────────────


class TestDisclaimerIsAppendedNotBlocked:
    """Issue #279, chat half.

    A reply that talks about meditation without saying "professional" is
    not harmful, it is incomplete, and truncating it mid-sentence to
    punish the omission refuses more good replies than bad ones. The fix
    is to finish the reply and add what is missing.
    """

    def test_the_reply_streams_whole(self, env: _Env) -> None:
        _RecordingClient.chunks = list(HEALING_REPLY_CHUNKS)

        response = _post(env, "How is my week going?", "healing")

        assert "event: error" not in response.text
        assert "worth naming that out loud" in response.text

    def test_the_healing_disclaimer_is_appended(self, env: _Env) -> None:
        _RecordingClient.chunks = list(HEALING_REPLY_CHUNKS)

        response = _post(env, "How is my week going?", "healing")

        assert HEALING_DISCLAIMER in _streamed_text(response.text)

    def test_the_disclaimer_is_appended_exactly_once(self, env: _Env) -> None:
        _RecordingClient.chunks = list(HEALING_REPLY_CHUNKS)

        response = _post(env, "How is my week going?", "healing")

        assert _streamed_text(response.text).count(HEALING_DISCLAIMER) == 1

    def test_the_disclaimer_arrives_before_the_done_sentinel(self, env: _Env) -> None:
        """A client that stops reading at ``done`` must still have seen it."""
        _RecordingClient.chunks = list(HEALING_REPLY_CHUNKS)

        response = _post(env, "How is my week going?", "healing")

        assert response.text.index(HEALING_DISCLAIMER) < response.text.index("event: done")

    def test_the_wealth_disclaimer_is_appended_on_the_wealth_scope(self, env: _Env) -> None:
        _RecordingClient.chunks = list(WEALTH_REPLY_CHUNKS)

        response = _post(env, "How is my money doing?", "wealth")

        streamed = _streamed_text(response.text)
        assert FINANCIAL_DISCLAIMER in streamed
        assert HEALING_DISCLAIMER not in streamed

    def test_a_reply_that_already_disclaims_gets_nothing_added(self, env: _Env) -> None:
        _RecordingClient.chunks = list(HEALING_REPLY_WITH_DISCLAIMER)

        response = _post(env, "How is my week going?", "healing")

        assert _streamed_text(response.text).count(HEALING_DISCLAIMER) == 1

    def test_a_short_reply_gets_nothing_added(self, env: _Env) -> None:
        """The checker's 100-character floor still applies, unchanged."""
        _RecordingClient.chunks = ["Meditation helps."]

        response = _post(env, "How is my week going?", "healing")

        assert HEALING_DISCLAIMER not in _streamed_text(response.text)

    def test_the_cadence_check_never_interrupts_for_a_missing_disclaimer(self, env: _Env) -> None:
        """Mid-stream, "no disclaimer yet" is true of every unfinished reply.

        Sixteen chunks means the cadence check runs twice before the end,
        on an accumulation that is long enough to trip the rule and has no
        disclaimer in it. Neither may cut the stream.
        """
        _RecordingClient.chunks = [f"meditation and breathwork note {n}. " for n in range(16)]

        response = _post(env, "How is my week going?", "healing")

        assert "event: error" not in response.text
        assert "note 15" in response.text

    def test_what_is_persisted_equals_what_was_streamed(self, env: _Env) -> None:
        """The transcript must not disagree with the live reply."""
        _RecordingClient.chunks = list(HEALING_REPLY_CHUNKS)

        response = _post(env, "How is my week going?", "healing")

        assistant = [m for m in env.chat_messages() if m.role == "assistant"]
        assert assistant[0].content == _streamed_text(response.text)
        assert HEALING_DISCLAIMER in assistant[0].content

    def test_the_appended_text_satisfies_the_checker(self) -> None:
        """The gate has to converge, or it would ask forever.

        Running the checker over the reply plus what was appended must
        leave no missing-disclaimer violation, and must not introduce a
        blocking one either.
        """
        reply = "".join(HEALING_REPLY_CHUNKS)
        appended = chat_router.missing_disclaimers("healing", reply)
        assert appended == [HEALING_DISCLAIMER]

        result = check_text(reply + "\n\n" + "\n\n".join(appended), context="healing")
        categories = {v.category for v in result.violations}
        assert ViolationCategory.MISSING_DISCLAIMER.value not in categories
        assert categories & chat_router._BLOCKING_CATEGORIES == set()

    def test_a_blocked_reply_gets_no_disclaimer(self, env: _Env) -> None:
        """Blocking wins. There is nothing left to disclaim."""
        _RecordingClient.chunks = [*HEALING_REPLY_CHUNKS, BLOCKING_CHUNK]

        response = _post(env, "How is my week going?", "healing")

        assert "event: error" in response.text
        assert HEALING_DISCLAIMER not in _streamed_text(response.text)


# ─── The scope-to-context map ───────────────────────────────────────────


class TestEthicsContextPerScope:
    """``check_text`` runs under the scope's own context, not ``"healing"``.

    Slice 5 reused ``context="healing"`` for the practice scope and left a
    note that per-scope contexts belonged to the rollout. This is that.
    The contexts the checker knows are "general", "healing", "wealth",
    "creative" and "perspective"; ``intelligence`` maps to "general"
    because it has no branch of its own, and "general" runs both the
    healing and the financial disclaimer rules.
    """

    def test_every_scope_has_a_context(self) -> None:
        assert set(chat_router._ETHICS_CONTEXTS) == set(SYSTEM_PROMPTS)

    def test_the_map_is_the_one_shipped(self) -> None:
        assert chat_router._ETHICS_CONTEXTS == {
            "intelligence": "general",
            "healing": "healing",
            "wealth": "wealth",
            "creative": "creative",
            "perspective": "perspective",
            "practice": "healing",
        }

    def test_the_unscoped_default_is_general(self) -> None:
        assert chat_router._ethics_context(None) == "general"

    @pytest.mark.parametrize("system_key", ["creative", "perspective"])
    def test_scopes_with_no_disclaimer_rule_get_no_disclaimer(
        self, env: _Env, system_key: str
    ) -> None:
        """The visible consequence of the map being right.

        The checker has no disclaimer branch for "creative" or
        "perspective", so healing vocabulary on those scopes is just
        vocabulary. Under the old flat ``context="healing"`` this same
        reply would have collected a medical disclaimer it never needed.
        """
        _RecordingClient.chunks = list(HEALING_REPLY_CHUNKS)

        response = _post(env, "How is my week going?", system_key)

        assert HEALING_DISCLAIMER not in _streamed_text(response.text)
        assert "event: error" not in response.text

    def test_the_general_context_covers_both_rules(self, env: _Env) -> None:
        """``intelligence`` and the unscoped default run healing and wealth."""
        _RecordingClient.chunks = list(WEALTH_REPLY_CHUNKS)

        response = _post(env, "How am I doing?", "intelligence")

        assert FINANCIAL_DISCLAIMER in _streamed_text(response.text)

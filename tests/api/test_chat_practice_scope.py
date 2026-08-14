"""The ``practice`` coach scope on ``POST /api/v1/chat``.

Slice 5 of epic #251. This is the live chat endpoint, so most of these
tests are about the five other scopes *not* changing, and about the two
new gates costing nothing when they fire.

The properties worth naming:

- The router's key set and the prompt table cannot drift apart. They are
  two literals in two files today, guarded by a comment; a mismatch
  would 422 a scope whose prompt exists, or route a scope with no prompt
  to the general coach.
- A crisis disclosure on the practice scope returns resources, not an
  HTTP 400 and not an LLM reply. Zero model calls, zero ledger rows.
- The practice context rides on the user message, never the system
  prompt. The system prompt is the cacheable stable prefix, and a block
  that changes daily would invalidate it daily.
- Only what the user typed is persisted. The assembled prompt is not.
- The ledger row for a chat turn names the user message that caused it.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime

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
from alchymine.api.auth import get_current_account
from alchymine.api.deps import get_db_session, set_db_engine
from alchymine.api.entitlements import CODE_ALLOWANCE_REACHED, CODE_UPGRADE_REQUIRED
from alchymine.api.main import app
from alchymine.api.routers import chat as chat_router
from alchymine.db.base import Base
from alchymine.db.models import ChatMessage, UsageRecord, User
from alchymine.db.usage_counters import (
    METER_LLM_CALLS,
    METER_SPEND_MICROS_MONTHLY,
    current_month_key,
    increment_and_get,
)
from alchymine.llm.attribution import current_attribution
from alchymine.llm.ledger import record_usage

# Aliased on import: pytest collects any module-level ``test_*`` name as
# a test case, and the conftest helper is a factory, not one.
from .conftest import TEST_USER_ID
from .conftest import test_account as build_account

BUNDLED_PACK_ID = "alchymine-foundations"

# One message per severity tier the gate acts on, plus one it must not.
EMERGENCY_MESSAGE = "I keep thinking about suicide and I did my practice anyway"
HIGH_MESSAGE = "my partner has been abusing me and practice is the only quiet I get"
MEDIUM_MESSAGE = "I had a panic attack before my morning practice"


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class _Env:
    """A TestClient plus the pieces a test needs to inspect afterwards."""

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
    """One in-memory database serving both the app and the ledger.

    The ledger writes through the ``deps`` engine singleton rather than
    the request session, so pointing both at the same engine is what
    lets a test join a usage row back to the chat message that caused
    it — which is the whole point of the attribution change.
    """
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
        _RecordingClient.calls.append(
            {**kwargs, "attribution": current_attribution()},
        )
        for chunk in _RecordingClient.chunks:
            yield chunk


@pytest.fixture(autouse=True)
def recording_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_RecordingClient]]:
    _RecordingClient.calls = []
    _RecordingClient.chunks = ["A steady ", "reply."]
    monkeypatch.setattr(chat_router, "LLMClient", _RecordingClient)
    yield _RecordingClient
    _RecordingClient.calls = []


def _post(env: _Env, message: str, system_key: str | None = "practice", **params: object):
    body: dict = {"message": message}
    if system_key is not None:
        body["system_key"] = system_key
    response = env.client.post("/api/v1/chat", json=body, params=params)
    _ = response.text  # drain the stream so after-stream persistence runs
    return response


# ─── The sync pin ───────────────────────────────────────────────────────


class TestScopeRegistration:
    def test_valid_system_keys_match_the_prompt_table(self) -> None:
        """Two literals in two files. Nothing but this test keeps them equal."""
        assert chat_router._VALID_SYSTEM_KEYS == set(SYSTEM_PROMPTS)

    def test_practice_is_one_of_the_six_scopes(self) -> None:
        assert "practice" in chat_router._VALID_SYSTEM_KEYS
        assert "practice" in SYSTEM_PROMPTS

    def test_practice_scope_is_accepted(self, env: _Env) -> None:
        assert _post(env, "What should I do with today's protocol?").status_code == 200

    def test_practice_history_filter_is_accepted(self, env: _Env) -> None:
        assert env.client.get("/api/v1/chat/history?system_key=practice").status_code == 200


# ─── Inbound: the crisis gate ───────────────────────────────────────────


class TestCrisisGate:
    @pytest.mark.parametrize("message", [EMERGENCY_MESSAGE, HIGH_MESSAGE])
    def test_crisis_message_streams_resources(self, env: _Env, message: str) -> None:
        response = _post(env, message)

        assert response.status_code == 200
        assert "988" in response.text
        assert "event: done" in response.text

    @pytest.mark.parametrize("message", [EMERGENCY_MESSAGE, HIGH_MESSAGE])
    def test_crisis_message_makes_no_llm_call(self, env: _Env, message: str) -> None:
        _post(env, message)

        assert _RecordingClient.calls == []

    def test_crisis_message_writes_no_ledger_row(self, env: _Env) -> None:
        _post(env, EMERGENCY_MESSAGE)

        assert env.usage_records() == []

    def test_crisis_message_is_not_a_client_error(self, env: _Env) -> None:
        """A 400 reads as 'you did something wrong' at the worst moment."""
        response = _post(env, EMERGENCY_MESSAGE)

        assert response.status_code == 200

    def test_medium_severity_still_reaches_the_coach(self, env: _Env) -> None:
        """The gate fires at high and emergency only."""
        _post(env, MEDIUM_MESSAGE)

        assert len(_RecordingClient.calls) == 1

    def test_ordinary_practice_message_reaches_the_coach(self, env: _Env) -> None:
        _post(env, "Which of today's practices should I start with?")

        assert len(_RecordingClient.calls) == 1

    def test_crisis_turn_is_persisted(self, env: _Env) -> None:
        """The conversation must not look like it swallowed the message."""
        _post(env, EMERGENCY_MESSAGE)

        messages = env.chat_messages()
        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[0].content == EMERGENCY_MESSAGE
        assert "988" in messages[1].content

    def test_ephemeral_crisis_turn_persists_nothing(self, env: _Env) -> None:
        _post(env, EMERGENCY_MESSAGE, ephemeral=True)

        assert env.chat_messages() == []


class TestCrisisGateIsPracticeOnly:
    """The rollback property: the other five scopes are untouched."""

    @pytest.mark.parametrize("system_key", ["healing", "wealth", None])
    def test_other_scopes_have_no_crisis_gate(self, env: _Env, system_key: str | None) -> None:
        # "abuse" is a high-severity keyword, so this would short-circuit
        # if the gate were global. On healing it reaches the coach exactly
        # as it did before slice 5.
        _post(env, HIGH_MESSAGE, system_key=system_key)

        assert len(_RecordingClient.calls) == 1

    def test_other_scopes_get_an_unchanged_system_prompt(self, env: _Env) -> None:
        _post(env, "How do I ground myself?", system_key="healing")

        assert _RecordingClient.calls[0]["system_prompt"] == SYSTEM_PROMPTS["healing"]

    def test_other_scopes_send_the_raw_message(self, env: _Env) -> None:
        _post(env, "How do I ground myself?", system_key="healing")

        assert _RecordingClient.calls[0]["prompt"] == "How do I ground myself?"


# ─── Outbound: the ethics gate ──────────────────────────────────────────


class TestEthicsGate:
    def test_violating_output_truncates_the_stream(self, env: _Env) -> None:
        """The gate runs on a cadence, so the violation is caught within
        eight chunks of arriving and the rest is never sent."""
        _RecordingClient.chunks = [
            *[f"word{n} " for n in range(7)],
            "you are destined to master this. ",
            *[f"tail{n} " for n in range(8)],
        ]

        response = _post(env, "How is my practice going?")

        assert "event: error" in response.text
        assert "tail7" not in response.text

    def test_violating_output_is_not_persisted(self, env: _Env) -> None:
        _RecordingClient.chunks = ["You are destined to master this."]

        _post(env, "How is my practice going?")

        assistant = [m for m in env.chat_messages() if m.role == "assistant"]
        assert assistant[0].content == "[response blocked by safety filter]"

    def test_a_missing_disclaimer_does_not_block_the_reply(self, env: _Env) -> None:
        """A partial reply has not reached its disclaimer yet, so blocking
        on one guarantees it never arrives."""
        _RecordingClient.chunks = [
            "Your breathwork and meditation practice looks steady this week. ",
            "Two somatic sessions and one reflection, which is a real rhythm ",
            "for someone who told me they were finding mornings hard.",
        ]

        response = _post(env, "How is my practice going?")

        assert "event: error" not in response.text
        assert "real rhythm" in response.text

    def test_other_scopes_are_not_ethics_checked(self, env: _Env) -> None:
        """The rollback property, outbound half."""
        _RecordingClient.chunks = ["You are destined to master this."]

        response = _post(env, "How am I doing?", system_key="healing")

        assert "event: error" not in response.text


# ─── The practice context block ─────────────────────────────────────────


class TestPracticeContext:
    def _seed(self, env: _Env) -> None:
        async def _write() -> None:
            async with env.factory() as session:
                existing = await session.get(User, TEST_USER_ID)
                if existing is None:
                    session.add(User(id=TEST_USER_ID))
                    await session.flush()
                from alchymine.db import repository

                await repository.create_practice_log_entry(
                    session,
                    user_id=TEST_USER_ID,
                    pack_id=BUNDLED_PACK_ID,
                    practice_slug="find-the-floor",
                    primary_purpose="steadiness",
                    purposes=["steadiness"],
                    category="somatic",
                    status="completed",
                    occurred_at=datetime.now(UTC),
                    day_key=datetime.now(UTC).date().isoformat(),
                    reflection="I thought about quitting my job the whole time",
                )
                await session.commit()

        env.run(_write())

    def test_context_rides_on_the_user_message(self, env: _Env) -> None:
        self._seed(env)

        _post(env, "What should I notice today?")

        call = _RecordingClient.calls[0]
        assert "Find the Floor" in call["prompt"]
        assert call["prompt"].endswith("What should I notice today?")

    def test_the_system_prompt_is_byte_identical_with_and_without_context(
        self, env: _Env
    ) -> None:
        """The system prompt is the cacheable prefix. Nothing per-user or
        per-day may enter it."""
        _post(env, "What should I notice today?")
        without = _RecordingClient.calls[0]["system_prompt"]

        _RecordingClient.calls = []
        self._seed(env)
        _post(env, "What should I notice today?")
        with_context = _RecordingClient.calls[0]["system_prompt"]

        assert with_context == without
        assert with_context == SYSTEM_PROMPTS["practice"]

    def test_only_the_typed_message_is_persisted(self, env: _Env) -> None:
        self._seed(env)

        _post(env, "What should I notice today?")

        user_rows = [m for m in env.chat_messages() if m.role == "user"]
        assert user_rows[-1].content == "What should I notice today?"

    def test_reflection_text_never_reaches_the_prompt(self, env: _Env) -> None:
        """The data rail, asserted at the egress boundary itself."""
        self._seed(env)

        _post(env, "What should I notice today?")

        call = _RecordingClient.calls[0]
        emitted = f"{call['system_prompt']}\n{call['prompt']}"
        assert "quitting my job" not in emitted

    def test_other_scopes_get_no_practice_context(self, env: _Env) -> None:
        self._seed(env)

        _post(env, "What should I notice today?", system_key="healing")

        assert _RecordingClient.calls[0]["prompt"] == "What should I notice today?"


# ─── Metering ───────────────────────────────────────────────────────────


class TestMetering:
    def test_free_plan_is_refused_with_402(self, env: _Env) -> None:
        app.dependency_overrides[get_current_account] = lambda: build_account(
            TEST_USER_ID, "free"
        )
        try:
            response = env.client.post(
                "/api/v1/chat",
                json={"message": "What should I practice?", "system_key": "practice"},
            )
        finally:
            app.dependency_overrides.pop(get_current_account, None)

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == CODE_UPGRADE_REQUIRED
        assert _RecordingClient.calls == []

    def test_exhausted_allowance_is_refused_with_429(self, env: _Env) -> None:
        async def _exhaust() -> None:
            await increment_and_get(
                scope=TEST_USER_ID,
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=current_month_key(),
                amount=10_000_000_000,
            )

        env.run(_exhaust())

        response = env.client.post(
            "/api/v1/chat",
            json={"message": "What should I practice?", "system_key": "practice"},
        )

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == CODE_ALLOWANCE_REACHED
        assert _RecordingClient.calls == []

    def test_the_surface_stays_chat(self, env: _Env) -> None:
        """No new ledger surface string for the sixth scope."""
        _post(env, "What should I practice?")

        _user_id, surface, _request_id = _RecordingClient.calls[0]["attribution"]
        assert surface == "chat"


# ─── Cost attribution ───────────────────────────────────────────────────


class TestAttribution:
    def test_request_id_is_the_persisted_user_message_id(self, env: _Env) -> None:
        _post(env, "What should I practice?")

        _user_id, _surface, request_id = _RecordingClient.calls[0]["attribution"]
        user_rows = [m for m in env.chat_messages() if m.role == "user"]
        assert request_id == user_rows[0].id

    def test_attribution_applies_to_every_scope(self, env: _Env) -> None:
        _post(env, "How do I ground myself?", system_key="healing")

        _user_id, _surface, request_id = _RecordingClient.calls[0]["attribution"]
        user_rows = [m for m in env.chat_messages() if m.role == "user"]
        assert request_id == user_rows[0].id

    def test_ephemeral_turns_carry_no_request_id(self, env: _Env) -> None:
        """Nothing was persisted, so there is no row to point at."""
        _post(env, "What should I practice?", ephemeral=True)

        _user_id, _surface, request_id = _RecordingClient.calls[0]["attribution"]
        assert request_id is None

    def test_the_user_id_still_names_the_caller(self, env: _Env) -> None:
        _post(env, "What should I practice?")

        user_id, _surface, _request_id = _RecordingClient.calls[0]["attribution"]
        assert user_id == TEST_USER_ID

    def test_the_ledger_row_joins_back_to_the_chat_message(
        self, env: _Env, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The measurement the whole change exists for.

        A real ledger row is written from inside the stream, in the same
        context the Claude egress site runs in, and its ``request_id``
        has to be the id of the message that caused it — that is what
        makes per-scope cost a join rather than a guess.
        """

        async def _spending_stream(self, **kwargs: object) -> AsyncGenerator[str, None]:
            _RecordingClient.calls.append({**kwargs, "attribution": current_attribution()})
            await record_usage(
                meter=METER_LLM_CALLS,
                provider="anthropic",
                model="claude-haiku-4-5-20251001",
                input_tokens=100,
                output_tokens=20,
            )
            yield "A steady reply."

        monkeypatch.setattr(_RecordingClient, "stream_generate", _spending_stream)

        _post(env, "What should I practice?")

        rows = env.usage_records()
        user_rows = [m for m in env.chat_messages() if m.role == "user"]
        assert len(rows) == 1
        assert rows[0].request_id == user_rows[0].id
        assert rows[0].surface == "chat"

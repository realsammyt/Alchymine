"""The ``practice`` coach scope on ``POST /api/v1/chat``.

Slice 5 of epic #251. This is the live chat endpoint, so most of these
tests are about the five other scopes *not* changing, and about the two
new gates costing nothing when they fire.

The two gates have since rolled out to every scope (#263), so the
"practice only" half of that no longer holds and the tests that pinned
it say so where they sit. What this file still owns is the practice
scope itself: its context block, its kill switch, and its metering.
``tests/api/test_chat_safety_gates_all_scopes.py`` owns the rest.

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
from contextlib import contextmanager
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
from alchymine.engine.healing.crisis import detect_crisis
from alchymine.db.usage_counters import (
    METER_LLM_CALLS,
    METER_SPEND_MICROS_MONTHLY,
    current_month_key,
    increment_and_get,
)
from alchymine.llm.attribution import current_attribution, set_attribution
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


@contextmanager
def _as_plan(plan: str) -> Iterator[None]:
    """Call the endpoint as the test user on *plan*.

    Restores whatever override was in place rather than popping, so the
    conftest account override survives the block and the rest of the
    test still runs as an entitled caller.
    """
    previous = app.dependency_overrides.get(get_current_account)
    app.dependency_overrides[get_current_account] = lambda: build_account(TEST_USER_ID, plan)
    try:
        yield
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_account, None)
        else:
            app.dependency_overrides[get_current_account] = previous


def _exhaust_allowance(env: _Env) -> None:
    """Spend past any plan's monthly ceiling, so the meter refuses."""

    async def _spend() -> None:
        await increment_and_get(
            scope=TEST_USER_ID,
            meter=METER_SPEND_MICROS_MONTHLY,
            period_key=current_month_key(),
            amount=10_000_000_000,
        )

    env.run(_spend())


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

    def test_the_whole_turn_survives_a_disconnect(self, env: _Env) -> None:
        """The turn is committed before the first frame, not after the last.

        Somebody who closes the tab a second after typing this is the
        likeliest reader of all, and deferring the commit to the end of
        the stream would roll their message back precisely then.

        The assistant half used to be the casualty instead: its write sat
        after the frame loop, outside any ``try``, so the ``GeneratorExit``
        below walked straight past it and the transcript kept the
        disclosure with no resources under it.  Both halves survive now
        (issue #297); the write moved into a ``finally``.
        """

        async def _abandon_after_first_frame() -> None:
            async with env.factory() as session:
                session.add(User(id=TEST_USER_ID))
                await session.flush()
                await session.commit()

                crisis = detect_crisis(EMERGENCY_MESSAGE)
                assert crisis is not None
                stream = chat_router._crisis_event_stream(
                    user_id=TEST_USER_ID,
                    message=EMERGENCY_MESSAGE,
                    system_key="practice",
                    crisis=crisis,
                    session=session,
                )
                first = await stream.__anext__()
                assert first.startswith("data: ")
                # The client goes away: GeneratorExit at the suspended
                # yield. Only the generator's ``finally`` runs after this.
                await stream.aclose()

        env.run(_abandon_after_first_frame())

        messages = env.chat_messages()
        assert [m.role for m in messages] == ["user", "assistant"]
        assert messages[0].content == EMERGENCY_MESSAGE
        assert "988" in messages[1].content


class TestKillSwitch:
    """What removing ``"practice"`` from ``_VALID_SYSTEM_KEYS`` actually kills.

    The design's rollback note said "the scope 422s". That is true of
    the LLM call and the context builder, and it is deliberately not
    true of the crisis gate: ``crisis_for`` runs before the validity
    check.

    An operator disabling a feature must not turn a crisis disclosure
    into a schema error, and the resource stream costs nothing to serve.
    This is the test that keeps the exception honest, in both directions.
    """

    @pytest.fixture
    def killed(self) -> Iterator[None]:
        original = set(chat_router._VALID_SYSTEM_KEYS)
        chat_router._VALID_SYSTEM_KEYS.discard("practice")
        try:
            yield
        finally:
            chat_router._VALID_SYSTEM_KEYS.clear()
            chat_router._VALID_SYSTEM_KEYS.update(original)

    def test_an_ordinary_practice_message_422s(self, env: _Env, killed: None) -> None:
        response = env.client.post(
            "/api/v1/chat",
            json={"message": "What should I practice today?", "system_key": "practice"},
        )

        assert response.status_code == 422
        assert _RecordingClient.calls == []

    def test_a_crisis_message_still_gets_resources(self, env: _Env, killed: None) -> None:
        response = _post(env, EMERGENCY_MESSAGE)

        assert response.status_code == 200
        assert "988" in response.text
        assert "event: done" in response.text
        assert _RecordingClient.calls == []

    def test_the_other_five_scopes_are_untouched(self, env: _Env, killed: None) -> None:
        response = _post(env, "How do I ground myself?", system_key="healing")

        assert response.status_code == 200
        assert len(_RecordingClient.calls) == 1

    def test_a_free_plan_crisis_message_survives_both(self, env: _Env, killed: None) -> None:
        """Killed scope and unpaid plan at once, which is the worst case.

        Neither refusal is one a person in crisis should meet, and the
        two are enforced at different layers, so the ordering has to hold
        against both together rather than each on its own.
        """
        with _as_plan("free"):
            response = _post(env, EMERGENCY_MESSAGE)

        assert response.status_code == 200
        assert "988" in response.text
        assert _RecordingClient.calls == []


class TestCrisisEscapesThePlanGate:
    """Issue #284. Crisis resources sit behind no paywall, anywhere.

    The plan gate used to be a route dependency, and FastAPI resolves
    dependencies before the handler body runs. So a free account writing
    the hardest sentence it can write was answered with a 402 upsell
    before ``crisis_for`` ever saw the message. The gate now runs inside
    the handler, after the crisis check, and refuses exactly the same
    ordinary traffic it always did.

    These are ordering tests, not copy tests. When the crisis gate widens
    beyond the practice scope, the property they pin is what has to hold.
    """

    @pytest.mark.parametrize("message", [EMERGENCY_MESSAGE, HIGH_MESSAGE])
    def test_a_free_plan_crisis_message_gets_resources(self, env: _Env, message: str) -> None:
        with _as_plan("free"):
            response = _post(env, message)

        assert response.status_code == 200
        assert "988" in response.text
        assert "event: done" in response.text

    def test_a_free_plan_crisis_message_makes_no_llm_call(self, env: _Env) -> None:
        """Ungated does not mean free inference. The path stays deterministic."""
        with _as_plan("free"):
            _post(env, EMERGENCY_MESSAGE)

        assert _RecordingClient.calls == []

    def test_a_free_plan_crisis_message_writes_no_ledger_row(self, env: _Env) -> None:
        with _as_plan("free"):
            _post(env, EMERGENCY_MESSAGE)

        assert env.usage_records() == []

    def test_an_ordinary_free_plan_message_is_still_refused(self, env: _Env) -> None:
        """The exemption is crisis-shaped, not a hole in the gate."""
        with _as_plan("free"):
            response = env.client.post(
                "/api/v1/chat",
                json={"message": "What should I practice?", "system_key": "practice"},
            )

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == CODE_UPGRADE_REQUIRED
        assert _RecordingClient.calls == []

    def test_a_medium_severity_message_is_still_gated(self, env: _Env) -> None:
        """Medium severity is coaching material, so it is ordinary traffic."""
        with _as_plan("free"):
            response = _post(env, MEDIUM_MESSAGE)

        assert response.status_code == 402
        assert _RecordingClient.calls == []

    def test_an_exhausted_allowance_still_serves_crisis(self, env: _Env) -> None:
        """The 429 half of the gate. A spent meter is not a reason either."""
        _exhaust_allowance(env)

        response = _post(env, EMERGENCY_MESSAGE)

        assert response.status_code == 200
        assert "988" in response.text
        assert _RecordingClient.calls == []

    def test_an_exhausted_allowance_still_refuses_ordinary_traffic(self, env: _Env) -> None:
        _exhaust_allowance(env)

        response = env.client.post(
            "/api/v1/chat",
            json={"message": "What should I practice?", "system_key": "practice"},
        )

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == CODE_ALLOWANCE_REACHED

    def test_a_free_plan_crisis_turn_is_persisted(self, env: _Env) -> None:
        with _as_plan("free"):
            _post(env, EMERGENCY_MESSAGE)

        messages = env.chat_messages()
        assert [m.role for m in messages] == ["user", "assistant"]
        assert "988" in messages[1].content


class TestWhatIsStillPracticeOnly:
    """What the gate rollout (#263) did and did not take with it.

    Slice 5 shipped the crisis and ethics gates on the practice scope
    alone, and this class used to pin that as a rollback property. The
    rollout removed the scope guards on both gates deliberately, so the
    crisis half of that property is gone on purpose: a high-severity
    disclosure now receives resources on every scope, which is the whole
    of issue #263. ``tests/api/test_chat_safety_gates_all_scopes.py``
    owns the widened behaviour.

    What is still practice-only is the practice-context block. It is a
    feature of the scope rather than a safety gate, and nothing about the
    rollout touched it.
    """

    @pytest.mark.parametrize("system_key", ["healing", "wealth", None])
    def test_other_scopes_now_have_the_crisis_gate_too(
        self, env: _Env, system_key: str | None
    ) -> None:
        # "abusing" is a high-severity keyword. Before the rollout this
        # reached the coach on every scope but practice; now it reaches
        # the coach on none of them.
        _post(env, HIGH_MESSAGE, system_key=system_key)

        assert _RecordingClient.calls == []

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
        on one guarantees it never arrives.

        Since #279 the finished reply also collects the disclaimer it was
        missing, appended after the last model chunk. That half is pinned
        in ``test_chat_safety_gates_all_scopes.py``; what matters here is
        that nothing was refused."""
        _RecordingClient.chunks = [
            "Your breathwork and meditation practice looks steady this week. ",
            "Two somatic sessions and one reflection, which is a real rhythm ",
            "for someone who told me they were finding mornings hard.",
        ]

        response = _post(env, "How is my practice going?")

        assert "event: error" not in response.text
        assert "real rhythm" in response.text

    def test_other_scopes_are_ethics_checked_too(self, env: _Env) -> None:
        """The outbound half of the rollout (#263).

        This asserted the opposite while the gate was practice-only. The
        five harm categories now block on every scope, and the widened
        behaviour is pinned in full in
        ``tests/api/test_chat_safety_gates_all_scopes.py``.
        """
        _RecordingClient.chunks = ["You are destined to master this."]

        response = _post(env, "How am I doing?", system_key="healing")

        assert "event: error" in response.text


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

    def test_the_system_prompt_is_byte_identical_with_and_without_context(self, env: _Env) -> None:
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
        app.dependency_overrides[get_current_account] = lambda: build_account(TEST_USER_ID, "free")
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

    def test_ephemeral_turns_keep_the_http_request_id(self, env: _Env) -> None:
        """Nothing was persisted, so there is no message row to point at.

        The HTTP request id ``RequestIdMiddleware`` minted stays where it
        is rather than being cleared: it is the only handle anybody has
        on an ephemeral turn in the logs, and trading it for ``None``
        would swap one form of attribution for none at all.

        Driven at the generator rather than through the route, because
        the shared ``get_current_account`` override in ``conftest`` sets
        ``request_id=None`` and there is no HTTP id to preserve behind
        it. The generator is where the decision actually lives.
        """

        async def _drive_ephemeral() -> None:
            async with env.factory() as session:
                set_attribution(user_id=TEST_USER_ID, surface="chat", request_id="http-request-id")
                stream = chat_router._chat_event_stream(
                    user_id=TEST_USER_ID,
                    message="What should I practice?",
                    system_key="practice",
                    session=session,
                    ephemeral=True,
                )
                async for _frame in stream:
                    pass

        env.run(_drive_ephemeral())

        _user_id, _surface, request_id = _RecordingClient.calls[0]["attribution"]
        assert request_id == "http-request-id"

    def test_a_persisted_turn_replaces_the_http_request_id(self, env: _Env) -> None:
        """The other half: when there is a row, it wins."""

        async def _drive_persisted() -> None:
            async with env.factory() as session:
                session.add(User(id=TEST_USER_ID))
                await session.flush()
                await session.commit()
                set_attribution(user_id=TEST_USER_ID, surface="chat", request_id="http-request-id")
                stream = chat_router._chat_event_stream(
                    user_id=TEST_USER_ID,
                    message="What should I practice?",
                    system_key="practice",
                    session=session,
                    ephemeral=False,
                )
                async for _frame in stream:
                    pass

        env.run(_drive_persisted())

        _user_id, _surface, request_id = _RecordingClient.calls[0]["attribution"]
        user_rows = [m for m in env.chat_messages() if m.role == "user"]
        assert request_id != "http-request-id"
        assert request_id == user_rows[0].id

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

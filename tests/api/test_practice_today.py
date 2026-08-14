"""Tests for ``GET /practice/today`` and ``GET /practice/summary``.

Both are auth-required, owner-scoped and not plan-gated (decision 27:
nothing here costs money, and gating the retention loop defeats the
loop). Neither makes an LLM call.

The algorithm itself is pinned in ``tests/engine/practice/test_ecology.py``.
What this module covers is the wiring: the owner comes from the token,
``ecology_state`` is created and advanced, the stable-day rule survives a
round trip through Postgres-shaped JSON, and ``today`` is the caller's
day rather than the server's.
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

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.api.main import app
from alchymine.db.base import Base
from alchymine.db.models import EcologyState
from alchymine.engine.practice import PURPOSE_ORDER

from .conftest import TEST_USER_ID

BUNDLED_PACK_ID = "alchymine-foundations"
OTHER_USER_ID = "user-2"
TODAY = "2026-08-14"


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def session_factory() -> Iterator[async_sessionmaker[AsyncSession]]:
    """An in-memory engine plus the factory the route override shares."""
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, echo=False
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
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        loop.run_until_complete(engine.dispose())
        loop.close()


@pytest.fixture
def client(session_factory: async_sessionmaker[AsyncSession]) -> Iterator[TestClient]:
    yield TestClient(app)


@pytest.fixture
def anonymous_client(client: TestClient) -> Iterator[TestClient]:
    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        yield client
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


@pytest.fixture
def as_other_user() -> Iterator[None]:
    original = app.dependency_overrides.get(get_current_user)

    async def _other() -> dict:
        return {"sub": OTHER_USER_ID, "email": "other@example.com"}

    app.dependency_overrides[get_current_user] = _other
    try:
        yield
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


def get_today(client: TestClient, **params: object):
    query = {"today": TODAY, **params}
    return client.get("/api/v1/practice/today", params=query)


def log_practice(client: TestClient, slug: str, **overrides: object):
    body: dict = {"pack_id": BUNDLED_PACK_ID, "practice_slug": slug, "day_key": TODAY}
    body.update(overrides)
    return client.post("/api/v1/practice/log", json=body)


def read_state(
    factory: async_sessionmaker[AsyncSession], user_id: str = TEST_USER_ID
) -> EcologyState | None:
    async def _read() -> EcologyState | None:
        async with factory() as session:
            result = await session.execute(
                select(EcologyState).where(EcologyState.user_id == user_id)
            )
            return result.scalar_one_or_none()

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_read())
    finally:
        loop.close()


# ─── Auth ───────────────────────────────────────────────────────────────


class TestAuth:
    def test_today_requires_auth(self, anonymous_client: TestClient) -> None:
        assert get_today(anonymous_client).status_code == 401

    def test_summary_requires_auth(self, anonymous_client: TestClient) -> None:
        response = anonymous_client.get("/api/v1/practice/summary", params={"today": TODAY})
        assert response.status_code == 401


# ─── The today query parameter ──────────────────────────────────────────


class TestTodayParameter:
    def test_today_is_required(self, client: TestClient) -> None:
        """The server must not guess the caller's local day."""
        assert client.get("/api/v1/practice/today").status_code == 422
        assert client.get("/api/v1/practice/summary").status_code == 422

    @pytest.mark.parametrize(
        "value",
        ["2026-13-01", "2026-02-30", "14-08-2026", "2026-W33-5", "not-a-date", "٢٠٢٦-٠٨-١٤"],
        ids=["month-13", "feb-30", "wrong-order", "iso-week", "words", "arabic-indic-digits"],
    )
    def test_an_unusable_today_is_rejected(self, client: TestClient, value: str) -> None:
        assert get_today(client, today=value).status_code == 422
        assert (
            client.get("/api/v1/practice/summary", params={"today": value}).status_code == 422
        )

    def test_the_response_echoes_the_day_it_was_computed_for(
        self, client: TestClient
    ) -> None:
        assert get_today(client, today="2027-01-31").json()["day_key"] == "2027-01-31"


# ─── GET /practice/today ────────────────────────────────────────────────


class TestToday:
    def test_returns_a_cold_start_protocol(self, client: TestClient) -> None:
        body = get_today(client).json()

        assert body["protocol_size"] == 5
        assert len(body["items"]) == 5
        assert len({item["purpose"] for item in body["items"]}) == 5

    def test_every_item_carries_a_reason_and_its_template_id(
        self, client: TestClient
    ) -> None:
        for item in get_today(client).json()["items"]:
            assert item["reason"]
            assert item["reason_template"]

    def test_slots_mirror_the_items_with_that_slot_prompt(self, client: TestClient) -> None:
        body = get_today(client).json()
        keys = [(item["pack_id"], item["slug"]) for item in body["items"]]

        assert set(body["slots"]) == {"morning", "day", "evening"}
        for entries in body["slots"].values():
            assert [(e["pack_id"], e["slug"]) for e in entries] == keys
            assert all(e["prompt"] for e in entries)

    def test_a_completed_practice_leaves_the_protocol_on_refresh(
        self, client: TestClient
    ) -> None:
        first = get_today(client).json()
        completed = first["items"][0]

        assert log_practice(client, completed["slug"]).status_code == 201

        refreshed = get_today(client, refresh=True).json()
        assert completed["slug"] not in {item["slug"] for item in refreshed["items"]}

    def test_the_same_day_replays_without_refresh(self, client: TestClient) -> None:
        """Completing one practice must not reshuffle the rest under the user."""
        first = get_today(client).json()
        log_practice(client, first["items"][0]["slug"])

        assert get_today(client).json() == first

    def test_a_new_day_recomputes(self, client: TestClient) -> None:
        first = get_today(client).json()

        second = get_today(client, today="2026-08-15").json()

        assert second["day_key"] == "2026-08-15"
        assert second["generated_at"] != first["generated_at"]

    def test_refresh_recomputes_within_the_same_day(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        get_today(client)
        before = read_state(session_factory)
        assert before is not None

        get_today(client, refresh=True)

        after = read_state(session_factory)
        assert after is not None
        assert after.rotation_cursor != before.rotation_cursor

    def test_another_users_completion_does_not_shape_this_protocol(
        self, client: TestClient
    ) -> None:
        """The log the recommender reads is scoped to the caller."""
        completed = get_today(client).json()["items"][0]["slug"]
        log_practice(client, completed)
        mine = get_today(client, refresh=True).json()

        async def _other() -> dict:
            return {"sub": OTHER_USER_ID, "email": "other@example.com"}

        app.dependency_overrides[get_current_user] = _other
        theirs = get_today(client).json()

        assert completed not in {item["slug"] for item in mine["items"]}
        assert completed in {item["slug"] for item in theirs["items"]}

    def test_no_score_reaches_the_client(self, client: TestClient) -> None:
        assert "score" not in get_today(client).text


# ─── ecology_state writes ───────────────────────────────────────────────


class TestEcologyState:
    def test_the_row_is_created_with_defaults_on_first_use(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        assert read_state(session_factory) is None

        get_today(client)

        state = read_state(session_factory)
        assert state is not None
        assert state.protocol_size == 5
        assert state.active_pack_ids is None

    def test_a_recomputation_stores_the_envelope_and_the_timestamp(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        body = get_today(client).json()

        state = read_state(session_factory)
        assert state is not None
        assert state.last_recommended_at is not None
        assert state.last_recommendation is not None
        assert state.last_recommendation["day_key"] == TODAY
        assert state.last_recommendation["pack_fingerprint"]
        assert state.last_recommendation["payload"] == body

    def test_the_cursor_advances_on_a_recomputation_and_not_on_a_replay(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        get_today(client)
        after_first = read_state(session_factory)
        assert after_first is not None

        get_today(client)

        after_replay = read_state(session_factory)
        assert after_replay is not None
        assert after_replay.rotation_cursor == after_first.rotation_cursor

    def test_a_summary_call_does_not_create_state(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The summary is a read. It has no business writing recommender state."""
        client.get("/api/v1/practice/summary", params={"today": TODAY})

        assert read_state(session_factory) is None

    def test_an_unreadable_stored_payload_recomputes_rather_than_500s(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A row written by an older build must not strand a user on an error."""
        get_today(client)

        async def _corrupt() -> None:
            async with session_factory() as session:
                state = (
                    await session.execute(
                        select(EcologyState).where(EcologyState.user_id == TEST_USER_ID)
                    )
                ).scalar_one()
                stored = dict(state.last_recommendation)
                stored["payload"] = {"day_key": TODAY, "unexpected": True}
                state.last_recommendation = stored
                await session.commit()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_corrupt())
        finally:
            loop.close()

        response = get_today(client)

        assert response.status_code == 200
        assert len(response.json()["items"]) == 5


# ─── GET /practice/summary ──────────────────────────────────────────────


class TestSummary:
    def test_an_empty_log_is_all_zeroes_and_still_the_full_shape(
        self, client: TestClient
    ) -> None:
        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body == {
            "day_key": TODAY,
            "days_practiced_last_7": 0,
            "last_7": [False] * 7,
            "by_purpose": dict.fromkeys(PURPOSE_ORDER, 0),
            "total_completed": 0,
        }

    def test_a_completion_today_lands_on_the_last_marker(self, client: TestClient) -> None:
        log_practice(client, "find-the-floor")

        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body["last_7"] == [False, False, False, False, False, False, True]
        assert body["days_practiced_last_7"] == 1
        assert body["by_purpose"]["steadiness"] == 1
        assert body["total_completed"] == 1

    def test_markers_are_oldest_first(self, client: TestClient) -> None:
        log_practice(client, "find-the-floor", day_key="2026-08-11")

        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body["last_7"] == [False, False, False, True, False, False, False]

    def test_two_completions_on_one_day_count_once(self, client: TestClient) -> None:
        log_practice(client, "find-the-floor")
        log_practice(client, "name-the-pattern")

        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body["days_practiced_last_7"] == 1
        assert body["total_completed"] == 2

    def test_a_skip_is_not_a_smaller_success(self, client: TestClient) -> None:
        log_practice(client, "find-the-floor", status="skipped")

        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body["days_practiced_last_7"] == 0
        assert body["total_completed"] == 0

    def test_an_older_completion_counts_in_the_total_but_not_the_week(
        self, client: TestClient
    ) -> None:
        log_practice(client, "find-the-floor", day_key="2026-06-01")

        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body["last_7"] == [False] * 7
        assert body["total_completed"] == 1
        assert body["by_purpose"]["steadiness"] == 1

    def test_another_users_practice_is_not_counted(
        self, client: TestClient, as_other_user: None
    ) -> None:
        log_practice(client, "find-the-floor")

        app.dependency_overrides.pop(get_current_user, None)

        async def _as_test_user() -> dict:
            return {"sub": TEST_USER_ID, "email": "test@example.com"}

        app.dependency_overrides[get_current_user] = _as_test_user
        body = client.get("/api/v1/practice/summary", params={"today": TODAY}).json()

        assert body["total_completed"] == 0


# ─── Route registration ─────────────────────────────────────────────────


class TestRouteResolution:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/practices",
            "/api/v1/practices/packs",
            f"/api/v1/practices/{BUNDLED_PACK_ID}/name-the-pattern",
            "/api/v1/practice/log",
        ],
    )
    def test_the_slice_one_and_two_routes_still_resolve(
        self, client: TestClient, path: str
    ) -> None:
        assert client.get(path).status_code == 200

    def test_the_new_literal_routes_are_not_shadowed(self, client: TestClient) -> None:
        assert get_today(client).status_code == 200
        assert (
            client.get("/api/v1/practice/summary", params={"today": TODAY}).status_code == 200
        )

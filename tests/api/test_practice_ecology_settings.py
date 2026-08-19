"""Tests for ``GET`` and ``PATCH /practice/ecology``.

Two columns on ``ecology_state`` shape every protocol the recommender
emits, and until now nothing could write them. These are the routes that
can, so what this module covers is the contract around that write: the
bounds are refused rather than clamped, an unmounted pack id is refused
rather than silently dropped, an omitted field is left alone, and the
stored protocol is cleared exactly when the settings actually moved.

That last one is the load-bearing case. ``protocol_size`` is not part of
the stable-day fingerprint, so a size change that left the stored
envelope in place would replay yesterday's protocol at yesterday's size
and the setting would look broken for a day.

Owner-scoped like the rest of the practice layer: the subject comes from
the token, and there is no shape of request that writes somebody else's
row.
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

import alchymine.db.models  # noqa: F401 (registers the models with metadata)
from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.api.main import app
from alchymine.db.base import Base
from alchymine.db.models import EcologyState

from .conftest import TEST_USER_ID

BUNDLED_PACK_ID = "alchymine-foundations"
OTHER_USER_ID = "user-2"
TODAY = "2026-08-14"
ECOLOGY_PATH = "/api/v1/practice/ecology"


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


def act_as(user_id: str) -> None:
    async def _subject() -> dict:
        return {"sub": user_id, "email": f"{user_id}@example.com"}

    app.dependency_overrides[get_current_user] = _subject


def patch_settings(client: TestClient, **body: object):
    return client.patch(ECOLOGY_PATH, json=body)


def patch_raw(client: TestClient, body: object):
    return client.patch(ECOLOGY_PATH, json=body)


def get_today(client: TestClient, **params: object):
    return client.get("/api/v1/practice/today", params={"today": TODAY, **params})


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
    def test_reading_the_settings_requires_auth(self, anonymous_client: TestClient) -> None:
        assert anonymous_client.get(ECOLOGY_PATH).status_code == 401

    def test_writing_the_settings_requires_auth(self, anonymous_client: TestClient) -> None:
        assert anonymous_client.patch(ECOLOGY_PATH, json={"protocol_size": 3}).status_code == 401


# ─── GET ────────────────────────────────────────────────────────────────


class TestRead:
    def test_a_first_read_answers_the_defaults(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The settings page reads before it writes, so this cannot 404."""
        assert read_state(session_factory) is None

        response = client.get(ECOLOGY_PATH)

        assert response.status_code == 200
        assert response.json() == {"protocol_size": 5, "active_pack_ids": None}

    def test_a_first_read_creates_the_row(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        assert client.get(ECOLOGY_PATH).status_code == 200

        state = read_state(session_factory)
        assert state is not None
        assert state.protocol_size == 5
        assert state.active_pack_ids is None

    def test_a_read_answers_what_the_last_write_stored(self, client: TestClient) -> None:
        patch_settings(client, protocol_size=6, active_pack_ids=[BUNDLED_PACK_ID])

        assert client.get(ECOLOGY_PATH).json() == {
            "protocol_size": 6,
            "active_pack_ids": [BUNDLED_PACK_ID],
        }


# ─── protocol_size ──────────────────────────────────────────────────────


class TestProtocolSize:
    @pytest.mark.parametrize("size", [3, 7])
    def test_the_bounds_themselves_are_accepted(self, client: TestClient, size: int) -> None:
        response = patch_settings(client, protocol_size=size)

        assert response.status_code == 200
        assert response.json()["protocol_size"] == size

    @pytest.mark.parametrize("size", [2, 8, 0, -1])
    def test_a_size_outside_the_bounds_is_refused_rather_than_clamped(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession], size: int
    ) -> None:
        """Silently storing 7 for a request of 99 would be a lie about what saved."""
        response = patch_settings(client, protocol_size=size)

        assert response.status_code == 422
        assert read_state(session_factory) is None

    def test_a_size_that_is_not_a_whole_number_is_refused(self, client: TestClient) -> None:
        assert patch_settings(client, protocol_size=4.5).status_code == 422

    def test_an_explicit_null_size_is_refused(self, client: TestClient) -> None:
        """Omitting the field means "leave it alone". Null means nothing at all."""
        assert patch_settings(client, protocol_size=None).status_code == 422


# ─── active_pack_ids ────────────────────────────────────────────────────


class TestActivePackIds:
    def test_a_mounted_pack_is_accepted(self, client: TestClient) -> None:
        response = patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID])

        assert response.status_code == 200
        assert response.json()["active_pack_ids"] == [BUNDLED_PACK_ID]

    def test_null_means_every_mounted_pack(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID])

        response = patch_settings(client, active_pack_ids=None)

        assert response.status_code == 200
        assert response.json()["active_pack_ids"] is None
        state = read_state(session_factory)
        assert state is not None
        assert state.active_pack_ids is None

    def test_an_unmounted_pack_id_is_refused(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        response = patch_settings(client, active_pack_ids=["not-a-mounted-pack"])

        assert response.status_code == 422
        assert "not-a-mounted-pack" in response.json()["detail"]
        assert read_state(session_factory) is None

    def test_the_refusal_names_only_the_ids_it_could_not_find(self, client: TestClient) -> None:
        """Echoing the whole request back tells the caller nothing extra."""
        response = patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID, "not-a-mounted-pack"])

        detail = response.json()["detail"]
        assert response.status_code == 422
        assert "not-a-mounted-pack" in detail
        assert BUNDLED_PACK_ID not in detail

    def test_an_empty_list_is_refused(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A protocol needs something to draw from. Null is how you say "all"."""
        response = patch_settings(client, active_pack_ids=[])

        assert response.status_code == 422
        assert read_state(session_factory) is None

    def test_a_repeated_id_is_stored_once(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        response = patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID, BUNDLED_PACK_ID])

        assert response.status_code == 200
        assert response.json()["active_pack_ids"] == [BUNDLED_PACK_ID]
        state = read_state(session_factory)
        assert state is not None
        assert state.active_pack_ids == [BUNDLED_PACK_ID]

    def test_an_id_that_is_not_a_string_is_refused(self, client: TestClient) -> None:
        assert patch_raw(client, {"active_pack_ids": [7]}).status_code == 422


# ─── Partial updates ────────────────────────────────────────────────────


class TestPartialUpdate:
    def test_an_omitted_pack_list_is_left_alone(self, client: TestClient) -> None:
        patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID])

        response = patch_settings(client, protocol_size=4)

        assert response.json() == {"protocol_size": 4, "active_pack_ids": [BUNDLED_PACK_ID]}

    def test_an_omitted_size_is_left_alone(self, client: TestClient) -> None:
        patch_settings(client, protocol_size=6)

        response = patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID])

        assert response.json() == {"protocol_size": 6, "active_pack_ids": [BUNDLED_PACK_ID]}

    def test_an_empty_body_is_refused(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        response = patch_raw(client, {})

        assert response.status_code == 422
        assert read_state(session_factory) is None

    def test_an_unknown_field_is_refused(self, client: TestClient) -> None:
        """A typo'd field name that saved nothing would look like a save."""
        assert patch_raw(client, {"protocolSize": 3}).status_code == 422


# ─── The stored protocol ────────────────────────────────────────────────


class TestStoredProtocolIsCleared:
    """``protocol_size`` is not in the stable-day fingerprint.

    Nothing downstream would notice a size change on its own, so the
    write has to clear the stored envelope itself or the user waits until
    tomorrow to see the setting they just changed.
    """

    def test_a_size_change_clears_the_stored_protocol(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        assert get_today(client).status_code == 200
        before = read_state(session_factory)
        assert before is not None and before.last_recommendation is not None

        patch_settings(client, protocol_size=3)

        after = read_state(session_factory)
        assert after is not None
        assert after.last_recommendation is None
        assert after.last_recommended_at is None

    def test_a_pack_change_clears_the_stored_protocol(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        get_today(client)

        patch_settings(client, active_pack_ids=[BUNDLED_PACK_ID])

        after = read_state(session_factory)
        assert after is not None
        assert after.last_recommendation is None

    def test_a_write_that_changes_nothing_keeps_the_stored_protocol(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Opening the settings page and saving it unchanged is not a reshuffle."""
        first = patch_settings(client, protocol_size=5, active_pack_ids=[BUNDLED_PACK_ID])
        assert first.status_code == 200
        stored = get_today(client).json()
        before = read_state(session_factory)
        assert before is not None and before.last_recommendation is not None

        again = patch_settings(client, protocol_size=5, active_pack_ids=[BUNDLED_PACK_ID])
        assert again.status_code == 200

        after = read_state(session_factory)
        assert after is not None
        assert after.last_recommendation == before.last_recommendation
        assert after.last_recommended_at is not None
        assert get_today(client).json() == stored

    def test_the_next_protocol_is_computed_at_the_new_size(self, client: TestClient) -> None:
        """The point of the whole endpoint: the setting has to reach the protocol."""
        assert len(get_today(client).json()["items"]) == 5

        assert patch_settings(client, protocol_size=3).status_code == 200

        body = get_today(client).json()
        assert body["protocol_size"] == 3
        assert len(body["items"]) == 3

    def test_a_refused_write_leaves_the_stored_protocol_alone(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        get_today(client)
        before = read_state(session_factory)
        assert before is not None and before.last_recommendation is not None

        assert patch_settings(client, protocol_size=99).status_code == 422

        after = read_state(session_factory)
        assert after is not None
        assert after.last_recommendation == before.last_recommendation
        assert after.protocol_size == 5


# ─── Ownership ──────────────────────────────────────────────────────────


class TestOwnership:
    def test_a_write_lands_on_the_caller_and_nobody_else(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        act_as(OTHER_USER_ID)
        assert patch_settings(client, protocol_size=7).status_code == 200

        act_as(TEST_USER_ID)
        assert patch_settings(client, protocol_size=3).status_code == 200

        mine = read_state(session_factory, TEST_USER_ID)
        theirs = read_state(session_factory, OTHER_USER_ID)
        assert mine is not None and mine.protocol_size == 3
        assert theirs is not None and theirs.protocol_size == 7

    def test_a_user_id_in_the_body_is_refused_rather_than_honoured(
        self, client: TestClient, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The subject comes from the token. There is no second way in."""
        response = patch_raw(client, {"protocol_size": 3, "user_id": OTHER_USER_ID})

        assert response.status_code == 422
        assert read_state(session_factory, OTHER_USER_ID) is None


# ─── Route registration ─────────────────────────────────────────────────


class TestRouteResolution:
    def test_the_literal_route_is_not_shadowed(self, client: TestClient) -> None:
        assert client.get(ECOLOGY_PATH).status_code == 200
        assert client.get("/api/v1/practices/packs").status_code == 200
        assert get_today(client).status_code == 200

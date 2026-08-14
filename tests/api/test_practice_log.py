"""Tests for the practice-log endpoints.

Two routes: ``POST /api/v1/practice/log`` and ``GET /api/v1/practice/log``.
Both are auth-required and owner-scoped, and neither is plan-gated
(decision 27: nothing here costs money).

The properties worth naming, because each of them is a bug somebody
would otherwise ship:

- The owner comes from the token, never from the body. A client that
  sends ``user_id`` gets its own row back, not somebody else's.
- ``primary_purpose``, ``purposes`` and ``category`` are read off the
  registry definition. A client cannot log a somatic practice as
  reflection, so the recommender's inputs stay trustworthy.
- ``day_key`` is stored exactly as the client sent it. It is the user's
  *local* day; recomputing it server-side from UTC would put an evening
  practice in Auckland on the wrong day, every day.
- An unknown pack or slug is rejected. A log row naming a practice that
  does not exist is unreadable later, and the registry is the only place
  that knows.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
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

from .conftest import TEST_USER_ID

BUNDLED_PACK_ID = "alchymine-foundations"
OTHER_USER_ID = "user-2"


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid Fernet key, so the encrypted columns can be written."""
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient wired to an in-memory SQLite engine."""
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
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        loop.run_until_complete(engine.dispose())
        loop.close()


@pytest.fixture
def as_other_user() -> Iterator[None]:
    """Switch the authenticated identity for the duration of a test."""
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


@pytest.fixture
def anonymous_client(client: TestClient) -> Iterator[TestClient]:
    """A client with the test auth override removed."""
    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        yield client
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


def _payload(**overrides: object) -> dict:
    body: dict = {
        "pack_id": BUNDLED_PACK_ID,
        "practice_slug": "find-the-floor",
        "day_key": "2026-08-14",
    }
    body.update(overrides)
    return body


def _log(client: TestClient, **overrides: object):
    return client.post("/api/v1/practice/log", json=_payload(**overrides))


# ─── Auth ───────────────────────────────────────────────────────────────


class TestAuth:
    def test_post_requires_auth(self, anonymous_client: TestClient) -> None:
        response = anonymous_client.post("/api/v1/practice/log", json=_payload())
        assert response.status_code == 401

    def test_get_requires_auth(self, anonymous_client: TestClient) -> None:
        assert anonymous_client.get("/api/v1/practice/log").status_code == 401


# ─── Route registration ─────────────────────────────────────────────────


class TestRouteResolution:
    def test_practice_log_is_not_shadowed_by_the_practice_detail_route(
        self, client: TestClient
    ) -> None:
        """``/practice/log`` must reach the log handler, not a pack lookup."""
        response = client.get("/api/v1/practice/log")
        assert response.status_code == 200
        assert "entries" in response.json()

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/practices",
            "/api/v1/practices/packs",
            f"/api/v1/practices/{BUNDLED_PACK_ID}/name-the-pattern",
        ],
    )
    def test_slice_one_routes_still_resolve(self, client: TestClient, path: str) -> None:
        assert client.get(path).status_code == 200


# ─── POST /practice/log ─────────────────────────────────────────────────


class TestCreate:
    def test_returns_201_and_echoes_the_row(self, client: TestClient) -> None:
        response = _log(client)
        assert response.status_code == 201

        body = response.json()
        assert body["id"]
        assert body["pack_id"] == BUNDLED_PACK_ID
        assert body["practice_slug"] == "find-the-floor"
        assert body["status"] == "completed"

    def test_derives_purpose_and_category_from_the_registry(self, client: TestClient) -> None:
        """The client never gets to say what a practice develops."""
        body = _log(client).json()

        assert body["primary_purpose"] == "steadiness"
        assert body["purposes"] == ["steadiness"]
        assert body["category"] == "somatic"

    def test_client_supplied_purpose_and_category_are_ignored(self, client: TestClient) -> None:
        body = _log(
            client,
            primary_purpose="stewardship",
            purposes=["stewardship", "expression"],
            category="reflection",
        ).json()

        assert body["primary_purpose"] == "steadiness"
        assert body["purposes"] == ["steadiness"]
        assert body["category"] == "somatic"

    def test_owner_comes_from_the_token_not_the_body(self, client: TestClient) -> None:
        """PR #210 ownership pattern: the authed sub is the only owner."""
        body = _log(client, user_id=OTHER_USER_ID).json()
        assert body["user_id"] == TEST_USER_ID

    def test_day_key_is_stored_exactly_as_sent(self, client: TestClient) -> None:
        """It is the user's local day. Recomputing it in UTC loses the day."""
        body = _log(client, day_key="2026-01-01").json()
        assert body["day_key"] == "2026-01-01"

        listed = client.get("/api/v1/practice/log").json()["entries"]
        assert listed[0]["day_key"] == "2026-01-01"

    def test_occurred_at_defaults_to_now_when_absent(self, client: TestClient) -> None:
        body = _log(client).json()
        assert body["occurred_at"]

    def test_occurred_at_is_kept_when_supplied(self, client: TestClient) -> None:
        body = _log(client, occurred_at="2026-08-14T21:30:00+00:00").json()
        assert body["occurred_at"].startswith("2026-08-14T21:30:00")

    def test_reflection_and_self_check_round_trip_to_the_owner(self, client: TestClient) -> None:
        body = _log(
            client,
            reflection="Both feet on the floor helped.",
            self_check_response="It changed what I did next.",
        ).json()

        assert body["reflection"] == "Both feet on the floor helped."
        assert body["self_check_response"] == "It changed what I did next."

    def test_optional_text_is_null_when_omitted(self, client: TestClient) -> None:
        body = _log(client).json()
        assert body["reflection"] is None
        assert body["self_check_response"] is None


class TestValidation:
    def test_unknown_pack_is_rejected_with_a_clear_message(self, client: TestClient) -> None:
        response = _log(client, pack_id="not-a-pack")
        assert response.status_code == 400

        detail = response.json()["detail"]
        assert "not-a-pack" in detail
        assert "mounted" in detail.lower() or "not found" in detail.lower()

    def test_unknown_slug_is_rejected_with_a_clear_message(self, client: TestClient) -> None:
        response = _log(client, practice_slug="not-a-practice")
        assert response.status_code == 400
        assert "not-a-practice" in response.json()["detail"]

    def test_nothing_is_written_when_the_practice_is_unknown(self, client: TestClient) -> None:
        _log(client, practice_slug="not-a-practice")
        assert client.get("/api/v1/practice/log").json()["total"] == 0

    def test_missing_day_key_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/practice/log",
            json={"pack_id": BUNDLED_PACK_ID, "practice_slug": "find-the-floor"},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("day_key", ["14-08-2026", "2026-8-14", "not-a-date", "2026-13-01"])
    def test_malformed_day_key_is_rejected(self, client: TestClient, day_key: str) -> None:
        assert _log(client, day_key=day_key).status_code == 422

    @pytest.mark.parametrize("status", ["completed", "skipped", "started"])
    def test_accepted_statuses(self, client: TestClient, status: str) -> None:
        response = _log(client, status=status)
        assert response.status_code == 201
        assert response.json()["status"] == status

    @pytest.mark.parametrize("status", ["done", "COMPLETED", "abandoned", ""])
    def test_rejected_statuses(self, client: TestClient, status: str) -> None:
        assert _log(client, status=status).status_code == 422

    @pytest.mark.parametrize("slot", ["morning", "day", "evening", "unscheduled"])
    def test_accepted_protocol_slots(self, client: TestClient, slot: str) -> None:
        response = _log(client, protocol_slot=slot)
        assert response.status_code == 201
        assert response.json()["protocol_slot"] == slot

    def test_protocol_slot_may_be_null(self, client: TestClient) -> None:
        response = _log(client, protocol_slot=None)
        assert response.status_code == 201
        assert response.json()["protocol_slot"] is None

    @pytest.mark.parametrize("slot", ["afternoon", "Morning", "night"])
    def test_rejected_protocol_slots(self, client: TestClient, slot: str) -> None:
        assert _log(client, protocol_slot=slot).status_code == 422

    @pytest.mark.parametrize("minutes", [-1, 1441])
    def test_out_of_range_duration_is_rejected(self, client: TestClient, minutes: int) -> None:
        assert _log(client, duration_minutes=minutes).status_code == 422

    def test_over_long_reflection_is_rejected(self, client: TestClient) -> None:
        assert _log(client, reflection="x" * 5001).status_code == 422


# ─── GET /practice/log ──────────────────────────────────────────────────


class TestList:
    def test_empty_log_returns_an_empty_page(self, client: TestClient) -> None:
        body = client.get("/api/v1/practice/log").json()
        assert body == {"entries": [], "total": 0, "page": 1, "per_page": 20}

    def test_returns_the_users_own_rows_newest_first(self, client: TestClient) -> None:
        for day, slug in [("2026-08-12", "find-the-floor"), ("2026-08-14", "name-the-pattern")]:
            _log(client, day_key=day, practice_slug=slug)

        entries = client.get("/api/v1/practice/log").json()["entries"]
        assert [e["day_key"] for e in entries] == ["2026-08-14", "2026-08-12"]

    def test_from_and_to_filter_on_day_key(self, client: TestClient) -> None:
        for day in ("2026-08-10", "2026-08-12", "2026-08-14", "2026-08-16"):
            _log(client, day_key=day)

        body = client.get(
            "/api/v1/practice/log", params={"from": "2026-08-12", "to": "2026-08-14"}
        ).json()

        assert body["total"] == 2
        assert {e["day_key"] for e in body["entries"]} == {"2026-08-12", "2026-08-14"}

    def test_the_range_is_inclusive_at_both_ends(self, client: TestClient) -> None:
        _log(client, day_key="2026-08-12")

        body = client.get(
            "/api/v1/practice/log", params={"from": "2026-08-12", "to": "2026-08-12"}
        ).json()
        assert body["total"] == 1

    def test_from_alone_is_an_open_ended_range(self, client: TestClient) -> None:
        _log(client, day_key="2026-08-10")
        _log(client, day_key="2026-08-14")

        body = client.get("/api/v1/practice/log", params={"from": "2026-08-12"}).json()
        assert body["total"] == 1
        assert body["entries"][0]["day_key"] == "2026-08-14"

    def test_malformed_range_bound_is_rejected(self, client: TestClient) -> None:
        assert (
            client.get("/api/v1/practice/log", params={"from": "last-tuesday"}).status_code == 422
        )

    def test_pagination(self, client: TestClient) -> None:
        for day in range(10, 15):
            _log(client, day_key=f"2026-08-{day}")

        page_one = client.get("/api/v1/practice/log", params={"per_page": 2}).json()
        page_two = client.get("/api/v1/practice/log", params={"per_page": 2, "page": 2}).json()

        assert page_one["total"] == 5
        assert page_one["page"] == 1
        assert len(page_one["entries"]) == 2
        assert len(page_two["entries"]) == 2

        ids = {e["id"] for e in page_one["entries"]}
        assert ids.isdisjoint({e["id"] for e in page_two["entries"]})

    def test_reflection_is_readable_by_its_owner(self, client: TestClient) -> None:
        _log(client, reflection="Both feet on the floor helped.")

        entries = client.get("/api/v1/practice/log").json()["entries"]
        assert entries[0]["reflection"] == "Both feet on the floor helped."


# ─── Ownership ──────────────────────────────────────────────────────────


class TestOwnership:
    def test_user_a_cannot_read_user_bs_log(self, client: TestClient, as_other_user) -> None:
        """The list is scoped by the token, with no user_id parameter at all."""
        _log(client, reflection="Private to user-2.")

        app.dependency_overrides.pop(get_current_user, None)

        async def _back_to_test_user() -> dict:
            return {"sub": TEST_USER_ID, "email": "test@example.com"}

        app.dependency_overrides[get_current_user] = _back_to_test_user

        body = client.get("/api/v1/practice/log").json()
        assert body["total"] == 0
        assert body["entries"] == []

    def test_a_user_id_query_parameter_does_not_widen_the_scope(self, client: TestClient) -> None:
        """An ignored parameter is the point: there is no way to ask for another user."""
        _log(client)

        body = client.get("/api/v1/practice/log", params={"user_id": OTHER_USER_ID}).json()
        assert body["total"] == 1
        assert body["entries"][0]["user_id"] == TEST_USER_ID

    def test_user_a_cannot_write_a_row_owned_by_user_b(
        self, client: TestClient, as_other_user
    ) -> None:
        created = _log(client, user_id=TEST_USER_ID).json()
        assert created["user_id"] == OTHER_USER_ID

"""Tests for ``POST /api/v1/practice/integration``.

The route closes the loop: an intention, an experience and a reflection
become one link row, plus exactly one derived ``outcome_metrics`` row so
the change shows up where the user already looks.

The properties worth naming, because each is a bug somebody would
otherwise ship:

- Every id in the body is checked against the caller. Another user's
  ``practice_log_id`` or journal id is a 404, not a 403: a 403 confirms
  the row exists, which is an existence oracle on somebody else's data.
- ``purpose`` is read off the practice_log row, never the body. A client
  that could pick the purpose could file its practice under whichever
  pillar it liked and skew the dashboard.
- Exactly one outcome row is written per integration entry. Not zero
  (the loop would be invisible), not two (every count downstream doubles).
- ``note`` is encrypted at rest and unreadable in the raw column.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import text
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
from alchymine.db import repository
from alchymine.db.base import Base

from .conftest import TEST_USER_ID

BUNDLED_PACK_ID = "alchymine-foundations"
OTHER_USER_ID = "user-2"

# find-the-floor is a steadiness practice, and steadiness maps to the
# healing pillar. Both facts are asserted rather than assumed below.
STEADINESS_SLUG = "find-the-floor"
SELF_KNOWLEDGE_SLUG = "name-the-pattern"


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid Fernet key, so the encrypted column can be written."""
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@dataclass
class Env:
    """A client plus a way to read the database it wrote to."""

    client: TestClient
    _loop: asyncio.AbstractEventLoop
    _factory: async_sessionmaker[AsyncSession]

    def run(self, fn: Any) -> Any:
        """Run an async callable against a fresh session, then commit."""

        async def _run() -> Any:
            async with self._factory() as session:
                result = await fn(session)
                await session.commit()
                return result

        return self._loop.run_until_complete(_run())

    def query(self, sql: str, **params: Any) -> list[tuple]:
        async def _run() -> list[tuple]:
            async with self._factory() as session:
                result = await session.execute(text(sql), params)
                return [tuple(row) for row in result.all()]

        return self._loop.run_until_complete(_run())


@pytest.fixture
def env() -> Iterator[Env]:
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
        yield Env(client=TestClient(app), _loop=loop, _factory=factory)
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        loop.run_until_complete(engine.dispose())
        loop.close()


@pytest.fixture
def client(env: Env) -> TestClient:
    return env.client


@contextmanager
def as_other_user() -> Iterator[None]:
    """Switch the authenticated identity for the duration of a block."""
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
    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        yield client
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


# ─── Helpers ────────────────────────────────────────────────────────────


def _log_practice(client: TestClient, slug: str = STEADINESS_SLUG) -> str:
    response = client.post(
        "/api/v1/practice/log",
        json={
            "pack_id": BUNDLED_PACK_ID,
            "practice_slug": slug,
            "day_key": "2026-08-14",
            "status": "completed",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _journal(client: TestClient, entry_type: str = "intention") -> str:
    response = client.post(
        "/api/v1/journal",
        json={
            "title": "Before the conversation",
            "content": "What I want to be able to do afterwards.",
            "system": "healing",
            "entry_type": entry_type,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _integrate(client: TestClient, **body: Any):
    return client.post("/api/v1/practice/integration", json=body)


# ─── Auth ───────────────────────────────────────────────────────────────


class TestAuth:
    def test_requires_auth(self, anonymous_client: TestClient) -> None:
        response = anonymous_client.post(
            "/api/v1/practice/integration", json={"practice_log_id": "whatever"}
        )
        assert response.status_code == 401


# ─── Ownership ──────────────────────────────────────────────────────────


class TestOwnership:
    def test_unknown_practice_log_id_is_404(self, client: TestClient) -> None:
        response = _integrate(client, practice_log_id="does-not-exist")
        assert response.status_code == 404

    def test_another_users_practice_log_id_is_404_not_403(self, env: Env) -> None:
        """A 403 would confirm the row exists. 404 tells the caller nothing."""
        with as_other_user():
            foreign_log_id = _log_practice(env.client)

        response = _integrate(env.client, practice_log_id=foreign_log_id)
        assert response.status_code == 404

    def test_another_users_intention_entry_is_404(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with as_other_user():
            foreign_entry = _journal(env.client)

        response = _integrate(env.client, practice_log_id=log_id, intention_entry_id=foreign_entry)
        assert response.status_code == 404

    def test_another_users_reflection_entry_is_404(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with as_other_user():
            foreign_entry = _journal(env.client)

        response = _integrate(env.client, practice_log_id=log_id, reflection_entry_id=foreign_entry)
        assert response.status_code == 404

    def test_unknown_journal_entry_id_is_404(self, client: TestClient) -> None:
        log_id = _log_practice(client)
        response = _integrate(client, practice_log_id=log_id, intention_entry_id="nope")
        assert response.status_code == 404

    def test_nothing_is_written_when_ownership_fails(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, intention_entry_id="nope")

        assert env.query("SELECT count(*) FROM integration_entries")[0][0] == 0
        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 0


# ─── Creation ───────────────────────────────────────────────────────────


class TestCreate:
    def test_returns_201_and_the_created_row(self, client: TestClient) -> None:
        log_id = _log_practice(client)
        response = _integrate(client, practice_log_id=log_id)

        assert response.status_code == 201
        body = response.json()
        assert body["id"]
        assert body["practice_log_id"] == log_id
        assert body["user_id"] == TEST_USER_ID

    def test_purpose_comes_from_the_log_row_not_the_client(self, client: TestClient) -> None:
        """A client that picks the purpose picks which pillar it credits."""
        log_id = _log_practice(client, STEADINESS_SLUG)
        body = _integrate(client, practice_log_id=log_id, purpose="stewardship").json()

        assert body["purpose"] == "steadiness"

    def test_links_both_journal_entries(self, client: TestClient) -> None:
        log_id = _log_practice(client)
        intention = _journal(client, "intention")
        reflection = _journal(client, "integration")

        body = _integrate(
            client,
            practice_log_id=log_id,
            intention_entry_id=intention,
            reflection_entry_id=reflection,
        ).json()

        assert body["intention_entry_id"] == intention
        assert body["reflection_entry_id"] == reflection

    def test_capacity_delta_outside_the_range_is_rejected(self, client: TestClient) -> None:
        log_id = _log_practice(client)
        assert _integrate(client, practice_log_id=log_id, capacity_delta=3).status_code == 422
        assert _integrate(client, practice_log_id=log_id, capacity_delta=-3).status_code == 422

    def test_practice_log_id_is_required(self, client: TestClient) -> None:
        assert _integrate(client, capacity_delta=1).status_code == 422


# ─── The derived outcome row ────────────────────────────────────────────


class TestDerivedOutcome:
    def test_writes_exactly_one_outcome_row(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, capacity_delta=1)

        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 1

    def test_two_integrations_write_two_rows_not_four(self, env: Env) -> None:
        first = _log_practice(env.client, STEADINESS_SLUG)
        second = _log_practice(env.client, SELF_KNOWLEDGE_SLUG)
        _integrate(env.client, practice_log_id=first)
        _integrate(env.client, practice_log_id=second)

        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 2

    def test_system_is_the_pillar_the_purpose_maps_to(self, env: Env) -> None:
        log_id = _log_practice(env.client, STEADINESS_SLUG)
        _integrate(env.client, practice_log_id=log_id)

        rows = env.query("SELECT system, metric_name, period FROM outcome_metrics")
        assert rows == [("healing", "practice_integration", "daily")]

    def test_self_knowledge_maps_to_intelligence(self, env: Env) -> None:
        log_id = _log_practice(env.client, SELF_KNOWLEDGE_SLUG)
        _integrate(env.client, practice_log_id=log_id)

        assert env.query("SELECT system FROM outcome_metrics")[0][0] == "intelligence"

    @pytest.mark.parametrize("delta,expected", [(-2, -2.0), (-1, -1.0), (0, 0.0), (2, 2.0)])
    def test_value_is_the_capacity_delta(self, env: Env, delta: int, expected: float) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, capacity_delta=delta)

        assert env.query("SELECT value FROM outcome_metrics")[0][0] == expected

    def test_value_defaults_to_one_when_no_delta_is_given(self, env: Env) -> None:
        """The practice happened. That is worth one, not zero."""
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id)

        assert env.query("SELECT value FROM outcome_metrics")[0][0] == 1.0

    def test_the_outcome_row_belongs_to_the_caller(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id)

        assert env.query("SELECT user_id FROM outcome_metrics")[0][0] == TEST_USER_ID


# ─── Atomicity ──────────────────────────────────────────────────────────


class TestAtomicity:
    def test_a_failed_outcome_write_leaves_no_orphan_integration_row(
        self, env: Env, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The link row and the derived row land together or not at all.

        The two writes share one session and one transaction, so a
        failure on the second discards the first. Without that an
        integration entry could exist with nothing on the dashboard to
        show for it, and no way to tell from the data that anything was
        lost.

        The rollback is the session dependency's, not the route's:
        ``get_db_session`` rolls back on any exception, in the app and in
        the fixture alike. The caller sees a 500 because the error
        middleware converts it, and no traceback reaches the user.
        """
        log_id = _log_practice(env.client)

        async def _boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("outcome store is down")

        monkeypatch.setattr(repository, "record_outcome_metric", _boom)

        response = _integrate(env.client, practice_log_id=log_id, capacity_delta=1)

        assert response.status_code == 500
        assert "outcome store is down" not in response.text
        assert env.query("SELECT count(*) FROM integration_entries")[0][0] == 0
        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 0

    def test_the_practice_log_row_itself_survives(
        self, env: Env, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failed integration must not undo the practice that happened.

        It was committed by its own request, so it is outside this
        transaction entirely.
        """
        log_id = _log_practice(env.client)

        async def _boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("outcome store is down")

        monkeypatch.setattr(repository, "record_outcome_metric", _boom)
        assert _integrate(env.client, practice_log_id=log_id).status_code == 500

        assert env.query("SELECT count(*) FROM practice_log")[0][0] == 1


# ─── Encryption ─────────────────────────────────────────────────────────


class TestNoteEncryption:
    def test_note_round_trips_through_the_api(self, client: TestClient) -> None:
        log_id = _log_practice(client)
        note = "It did change what I did next, which surprised me."
        body = _integrate(client, practice_log_id=log_id, note=note).json()

        assert body["note"] == note

    def test_note_is_ciphertext_in_the_raw_column(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        note = "It did change what I did next, which surprised me."
        _integrate(env.client, practice_log_id=log_id, note=note)

        raw = env.query("SELECT note FROM integration_entries")[0][0]
        assert raw != note
        assert note not in raw
        assert len(raw) > len(note)

    def test_absent_note_stays_null(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id)

        assert env.query("SELECT note FROM integration_entries")[0][0] is None

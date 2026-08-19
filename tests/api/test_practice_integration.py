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
import os
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
from alchymine.config import get_settings
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


# ─── Idempotency ────────────────────────────────────────────────────────


class TestIdempotency:
    """One completion is one record, however many times it is saved.

    The daily protocol renders the self-check and the integration prompt
    side by side on a completed card. They are two controls over one
    practice, and both post here with the same ``practice_log_id``. A
    plain insert per call gave that completion two link rows and two
    outcome rows, so every count downstream read double.

    The key is ``(user_id, practice_log_id)``. The second call merges
    into the row the first one wrote:

    - a field the caller did not send never clears one already stored,
      so a note-only save cannot erase a capacity reading;
    - both notes survive, appended as separate paragraphs, because they
      are two pieces of the user's own writing about the same practice
      and neither is ours to discard;
    - the same text saved twice is stored once, so a retry after a
      timeout is not a second paragraph;
    - the derived outcome row is recomputed from the merged row rather
      than from the request body, so it does not matter which prompt the
      user fills in first.
    """

    def test_two_posts_for_one_completion_write_one_row(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, note="What I noticed.")
        _integrate(env.client, practice_log_id=log_id, capacity_delta=1)

        assert env.query("SELECT count(*) FROM integration_entries")[0][0] == 1

    def test_two_posts_for_one_completion_write_one_outcome_row(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, note="What I noticed.")
        _integrate(env.client, practice_log_id=log_id, capacity_delta=1)

        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 1

    def test_the_second_post_returns_the_same_row(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        first = _integrate(env.client, practice_log_id=log_id, note="First.")
        second = _integrate(env.client, practice_log_id=log_id, capacity_delta=1)

        assert second.json()["id"] == first.json()["id"]

    def test_the_second_post_answers_200_not_201(self, env: Env) -> None:
        """201 means a resource was created. The second save updates one."""
        log_id = _log_practice(env.client)
        assert _integrate(env.client, practice_log_id=log_id).status_code == 201
        assert _integrate(env.client, practice_log_id=log_id).status_code == 200

    def test_both_notes_survive_the_merge(self, env: Env) -> None:
        """The self-check answer and the integration note are both the
        user's writing about one practice. Losing either is data loss."""
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, note="Settling, mostly.")
        body = _integrate(
            env.client,
            practice_log_id=log_id,
            capacity_delta=1,
            note="It changed what I did next.",
        ).json()

        assert "Settling, mostly." in body["note"]
        assert "It changed what I did next." in body["note"]

    def test_a_replayed_identical_post_stores_the_note_once(self, env: Env) -> None:
        """A retry after a timeout is not a second paragraph."""
        log_id = _log_practice(env.client)
        note = "Settling, mostly."
        _integrate(env.client, practice_log_id=log_id, note=note)
        body = _integrate(env.client, practice_log_id=log_id, note=note).json()

        assert body["note"] == note

    def test_a_later_save_does_not_clear_an_earlier_capacity_delta(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, capacity_delta=2)
        body = _integrate(env.client, practice_log_id=log_id, note="And a note.").json()

        assert body["capacity_delta"] == 2

    def test_a_later_save_does_not_clear_earlier_journal_links(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        intention = _journal(env.client, "intention")
        _integrate(env.client, practice_log_id=log_id, intention_entry_id=intention)
        body = _integrate(env.client, practice_log_id=log_id, capacity_delta=1).json()

        assert body["intention_entry_id"] == intention

    def test_journal_links_from_both_saves_land_on_one_row(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        intention = _journal(env.client, "intention")
        reflection = _journal(env.client, "integration")
        _integrate(env.client, practice_log_id=log_id, intention_entry_id=intention)
        body = _integrate(
            env.client, practice_log_id=log_id, reflection_entry_id=reflection
        ).json()

        assert body["intention_entry_id"] == intention
        assert body["reflection_entry_id"] == reflection

    def test_the_outcome_value_catches_up_with_a_later_capacity_delta(self, env: Env) -> None:
        """Self-check first, reading second: the dashboard shows the reading."""
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, note="What I noticed.")
        _integrate(env.client, practice_log_id=log_id, capacity_delta=2)

        assert env.query("SELECT value FROM outcome_metrics") == [(2.0,)]

    def test_a_later_note_only_save_does_not_downgrade_the_outcome_value(self, env: Env) -> None:
        """Reading first, self-check second: the reading still stands.

        The value is recomputed from the merged row, not from the body
        of whichever call happened to arrive last.
        """
        log_id = _log_practice(env.client)
        _integrate(env.client, practice_log_id=log_id, capacity_delta=2)
        _integrate(env.client, practice_log_id=log_id, note="What I noticed.")

        assert env.query("SELECT value FROM outcome_metrics") == [(2.0,)]

    def test_the_merged_note_is_still_ciphertext_at_rest(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        first = "Settling, mostly."
        second = "It changed what I did next."
        _integrate(env.client, practice_log_id=log_id, note=first)
        _integrate(env.client, practice_log_id=log_id, note=second)

        raw = env.query("SELECT note FROM integration_entries")[0][0]
        assert first not in raw
        assert second not in raw

    def test_two_completions_still_get_two_rows(self, env: Env) -> None:
        """The key is the completion, not the user. Idempotency must not
        collapse a week of practice into one row."""
        first = _log_practice(env.client, STEADINESS_SLUG)
        second = _log_practice(env.client, SELF_KNOWLEDGE_SLUG)
        _integrate(env.client, practice_log_id=first)
        _integrate(env.client, practice_log_id=second)

        assert env.query("SELECT count(*) FROM integration_entries")[0][0] == 2
        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 2

    def test_the_same_practice_logged_twice_gets_two_rows(self, env: Env) -> None:
        """Doing the same practice morning and evening is two completions."""
        morning = _log_practice(env.client, STEADINESS_SLUG)
        evening = _log_practice(env.client, STEADINESS_SLUG)
        _integrate(env.client, practice_log_id=morning)
        _integrate(env.client, practice_log_id=evening)

        assert env.query("SELECT count(*) FROM integration_entries")[0][0] == 2

    def test_another_users_completion_is_a_separate_row(self, env: Env) -> None:
        """Cross-user isolation survives the merge key."""
        mine = _log_practice(env.client)
        _integrate(env.client, practice_log_id=mine)

        with as_other_user():
            theirs = _log_practice(env.client)
            _integrate(env.client, practice_log_id=theirs)

        owners = env.query("SELECT DISTINCT user_id FROM integration_entries ORDER BY user_id")
        assert len(owners) == 2
        assert env.query("SELECT count(*) FROM integration_entries")[0][0] == 2


# ─── The total note cap ─────────────────────────────────────────────────


@contextmanager
def small_note_cap(cap: int = 40) -> Iterator[None]:
    """Shrink the merged-note ceiling for the duration of a block.

    The shipped default is 20000 characters, which would take four
    max-size posts to reach. The behaviour under the cap is the same at
    any size, so the tests move the cap rather than the volume.
    """
    original = os.environ.get("INTEGRATION_NOTE_TOTAL_CHAR_CAP")
    os.environ["INTEGRATION_NOTE_TOTAL_CHAR_CAP"] = str(cap)
    get_settings.cache_clear()
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("INTEGRATION_NOTE_TOTAL_CHAR_CAP", None)
        else:
            os.environ["INTEGRATION_NOTE_TOTAL_CHAR_CAP"] = original
        get_settings.cache_clear()


class TestNoteGrowthCap:
    """One entry's note accumulates across saves, so it needs a ceiling.

    The ceiling refuses rather than truncates. Half a sentence stored
    under the user's own name, with no sign that the rest was dropped,
    is worse than a save that plainly did not land.
    """

    def test_a_note_that_would_pass_the_cap_is_refused(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with small_note_cap(40):
            assert _integrate(env.client, practice_log_id=log_id, note="a" * 30).status_code == 201
            response = _integrate(env.client, practice_log_id=log_id, note="b" * 30)

        assert response.status_code == 422

    def test_the_refusal_leaves_the_earlier_note_intact(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with small_note_cap(40):
            _integrate(env.client, practice_log_id=log_id, note="a" * 30)
            _integrate(env.client, practice_log_id=log_id, note="b" * 30)
            body = _integrate(env.client, practice_log_id=log_id, capacity_delta=1).json()

        assert body["note"] == "a" * 30

    def test_the_refusal_writes_nothing(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with small_note_cap(40):
            _integrate(env.client, practice_log_id=log_id, note="a" * 30)
            _integrate(env.client, practice_log_id=log_id, capacity_delta=2, note="b" * 30)
            body = _integrate(env.client, practice_log_id=log_id).json()

        assert body["capacity_delta"] is None
        assert env.query("SELECT count(*) FROM outcome_metrics")[0][0] == 1

    def test_the_refusal_says_what_happened_without_a_traceback(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with small_note_cap(40):
            _integrate(env.client, practice_log_id=log_id, note="a" * 30)
            response = _integrate(env.client, practice_log_id=log_id, note="b" * 30)

        detail = response.json()["detail"]
        assert "full" in detail.lower()
        assert "Traceback" not in response.text
        assert "IntegrationNoteFull" not in response.text

    def test_the_refused_text_is_not_echoed_back(self, env: Env) -> None:
        """Nothing is gained by repeating it, and it travels into logs."""
        log_id = _log_practice(env.client)
        refused = "something I would rather not see in a log line"
        with small_note_cap(40):
            _integrate(env.client, practice_log_id=log_id, note="a" * 30)
            response = _integrate(env.client, practice_log_id=log_id, note=refused)

        assert refused not in response.text

    def test_a_full_entry_still_accepts_a_save_with_no_note(self, env: Env) -> None:
        log_id = _log_practice(env.client)
        with small_note_cap(40):
            _integrate(env.client, practice_log_id=log_id, note="a" * 38)
            response = _integrate(env.client, practice_log_id=log_id, capacity_delta=1)

        assert response.status_code == 200
        assert response.json()["capacity_delta"] == 1

    def test_a_full_entry_still_accepts_a_replayed_note(self, env: Env) -> None:
        """A retry after a timeout adds nothing, so it cannot overflow."""
        log_id = _log_practice(env.client)
        note = "a" * 38
        with small_note_cap(40):
            _integrate(env.client, practice_log_id=log_id, note=note)
            response = _integrate(env.client, practice_log_id=log_id, note=note)

        assert response.status_code == 200
        assert response.json()["note"] == note

    def test_the_shipped_default_leaves_room_for_ordinary_writing(self, env: Env) -> None:
        """Three max-size posts on one practice fit under the default.

        The fourth is where 20000 runs out, and that is the point: the
        ceiling is sized for a client looping on a save, not for anyone
        writing at length about a single practice.
        """
        log_id = _log_practice(env.client)
        for index in range(3):
            response = _integrate(env.client, practice_log_id=log_id, note=f"{index}{'x' * 4999}")
            assert response.status_code in (200, 201), response.text

        assert len(_integrate(env.client, practice_log_id=log_id).json()["note"]) == 15004


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

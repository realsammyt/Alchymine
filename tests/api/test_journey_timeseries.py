"""Tests for ``GET /api/v1/journey/timeseries``.

A read-only aggregation over the caller's own practice log and the
loops closed against it. Auth is required; no plan gate applies, for
the same reason none applies to the rest of the practice layer: reading
back what you already did is not a paid surface.

The properties worth naming, because each is a bug somebody would
otherwise ship:

- The window is bounded server-side. A client cannot ask for a year and
  cannot ask for zero days; both are refused by validation rather than
  clamped, so a caller finds out its request was wrong.
- The series is scoped to the caller. Another user's practice log
  contributes nothing, whatever the query string says.
- A brand-new user gets a full, zero-filled window rather than an empty
  body or a 404. The page has one shape to render, and "you have not
  started yet" is a state, not a failure.
- A loop lands on the day of the practice it closed. The practice day is
  the user's local day; the derived outcome row is stamped in UTC, and
  folding on that stamp would misplace an evening loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from dataclasses import dataclass
from typing import Any

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
from alchymine.db import repository
from alchymine.db.base import Base
from alchymine.engine.practice.journey import (
    JOURNEY_WINDOW_DEFAULT,
    JOURNEY_WINDOW_MAX,
    JOURNEY_WINDOW_MIN,
)

from .conftest import TEST_USER_ID, override_account

OTHER_USER_ID = "user-2"
PATH = "/api/v1/journey/timeseries"
TODAY = "2026-08-18"

BUNDLED_PACK_ID = "alchymine-foundations"
STEADINESS_SLUG = "find-the-floor"


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid Fernet key, so the encrypted columns can be written."""
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@dataclass
class Env:
    """A client plus a way to seed the database behind it."""

    client: TestClient
    _loop: asyncio.AbstractEventLoop
    _factory: async_sessionmaker[AsyncSession]

    def run(self, fn: Any) -> Any:
        async def _run() -> Any:
            async with self._factory() as session:
                result = await fn(session)
                await session.commit()
                return result

        return self._loop.run_until_complete(_run())

    def log_practice(
        self,
        day_key: str,
        *,
        user_id: str = TEST_USER_ID,
        purpose: str = "steadiness",
        status: str = "completed",
    ) -> str:
        async def _write(session: AsyncSession) -> str:
            entry = await repository.create_practice_log_entry(
                session,
                user_id=user_id,
                pack_id=BUNDLED_PACK_ID,
                practice_slug=STEADINESS_SLUG,
                primary_purpose=purpose,
                purposes=[purpose],
                category="somatic",
                day_key=day_key,
                status=status,
            )
            return entry.id

        return self.run(_write)

    def close_loop(
        self,
        practice_log_id: str,
        *,
        user_id: str = TEST_USER_ID,
        purpose: str = "steadiness",
        capacity_delta: int | None = None,
    ) -> None:
        async def _write(session: AsyncSession) -> None:
            await repository.upsert_integration_entry(
                session,
                user_id=user_id,
                practice_log_id=practice_log_id,
                purpose=purpose,
                intention_entry_id=None,
                reflection_entry_id=None,
                capacity_delta=capacity_delta,
                note=None,
            )

        self.run(_write)

    def get(self, **params: Any) -> Any:
        query: dict[str, Any] = {"today": TODAY}
        query.update(params)
        return self.client.get(PATH, params=query)


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
        yield Env(TestClient(app), loop, factory)
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        loop.run_until_complete(engine.dispose())
        loop.close()


@pytest.fixture
def anonymous_client(env: Env) -> Iterator[TestClient]:
    """A client with the test auth override removed."""
    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        yield env.client
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


# ─── Auth and gating ────────────────────────────────────────────────────


class TestAccess:
    def test_requires_auth(self, anonymous_client: TestClient) -> None:
        assert anonymous_client.get(PATH, params={"today": TODAY}).status_code == 401

    def test_is_not_plan_gated(self, env: Env) -> None:
        """Reading your own journey is not a paid surface."""
        override_account(TEST_USER_ID, "free")
        assert env.get().status_code == 200


# ─── The window ─────────────────────────────────────────────────────────


class TestWindow:
    def test_defaults_to_the_default_window(self, env: Env) -> None:
        body = env.get().json()

        assert body["window_days"] == JOURNEY_WINDOW_DEFAULT
        assert len(body["days"]) == JOURNEY_WINDOW_DEFAULT

    def test_days_are_oldest_first_and_end_on_today(self, env: Env) -> None:
        body = env.get(days=7).json()

        keys = [day["day_key"] for day in body["days"]]
        assert keys == sorted(keys)
        assert keys[0] == "2026-08-12"
        assert keys[-1] == TODAY
        assert body["start_day"] == "2026-08-12"
        assert body["day_key"] == TODAY

    @pytest.mark.parametrize("days", [JOURNEY_WINDOW_MIN, 30, JOURNEY_WINDOW_MAX])
    def test_accepts_the_bounded_range(self, env: Env, days: int) -> None:
        body = env.get(days=days).json()
        assert len(body["days"]) == days

    @pytest.mark.parametrize("days", [0, -1, JOURNEY_WINDOW_MIN - 1, JOURNEY_WINDOW_MAX + 1, 3650])
    def test_refuses_a_window_outside_the_bounds(self, env: Env, days: int) -> None:
        """Refused, not clamped: a caller should learn its request was wrong."""
        assert env.get(days=days).status_code == 422

    def test_today_is_required(self, env: Env) -> None:
        assert env.client.get(PATH).status_code == 422

    @pytest.mark.parametrize("today", ["2026-13-01", "18-08-2026", "2026-W33-5", "yesterday"])
    def test_refuses_a_today_that_is_not_a_calendar_date(self, env: Env, today: str) -> None:
        assert env.get(today=today).status_code == 422


# ─── Empty history ──────────────────────────────────────────────────────


class TestEmptyHistory:
    def test_a_new_user_gets_a_full_zero_filled_window(self, env: Env) -> None:
        response = env.get(days=7)

        assert response.status_code == 200
        body = response.json()
        assert len(body["days"]) == 7
        assert all(day["completed"] == 0 for day in body["days"])
        assert all(day["loops"] == 0 for day in body["days"])
        assert all(day["average_shift"] is None for day in body["days"])

    def test_totals_are_zero_and_anchors_are_null(self, env: Env) -> None:
        body = env.get().json()

        assert body["totals"] == {
            "days_practiced": 0,
            "completed": 0,
            "loops_closed": 0,
            "first_practice_day": None,
            "first_loop_day": None,
        }

    def test_by_purpose_is_zero_filled_across_all_five(self, env: Env) -> None:
        body = env.get().json()

        assert body["by_purpose"] == {
            "self-knowledge": 0,
            "steadiness": 0,
            "stewardship": 0,
            "expression": 0,
            "reframing": 0,
        }


# ─── The series ─────────────────────────────────────────────────────────


class TestSeries:
    def test_a_completion_lands_on_its_own_day(self, env: Env) -> None:
        env.log_practice("2026-08-15")

        body = env.get(days=7).json()
        by_day = {day["day_key"]: day for day in body["days"]}

        assert by_day["2026-08-15"]["completed"] == 1
        assert by_day["2026-08-15"]["purposes"] == ["steadiness"]
        assert by_day["2026-08-14"]["completed"] == 0

    def test_a_skip_is_not_counted_as_practice(self, env: Env) -> None:
        env.log_practice(TODAY, status="skipped")

        body = env.get(days=7).json()

        assert body["days"][-1]["completed"] == 0
        assert body["totals"]["completed"] == 0
        assert body["totals"]["days_practiced"] == 0

    def test_history_older_than_the_window_is_not_shown(self, env: Env) -> None:
        env.log_practice("2026-01-04")
        env.log_practice(TODAY)

        body = env.get(days=7).json()

        assert body["totals"]["completed"] == 1

    def test_by_purpose_counts_the_window(self, env: Env) -> None:
        env.log_practice(TODAY, purpose="expression")
        env.log_practice("2026-08-17", purpose="expression")
        env.log_practice("2026-08-16", purpose="reframing")

        body = env.get(days=7).json()

        assert body["by_purpose"]["expression"] == 2
        assert body["by_purpose"]["reframing"] == 1
        assert body["by_purpose"]["stewardship"] == 0

    def test_totals_describe_the_window(self, env: Env) -> None:
        env.log_practice(TODAY)
        env.log_practice(TODAY)
        env.log_practice("2026-08-16")

        body = env.get(days=7).json()

        assert body["totals"]["completed"] == 3
        assert body["totals"]["days_practiced"] == 2


# ─── Loops ──────────────────────────────────────────────────────────────


class TestLoops:
    def test_a_loop_lands_on_the_day_of_the_practice_it_closed(self, env: Env) -> None:
        log_id = env.log_practice("2026-08-15")
        env.close_loop(log_id, capacity_delta=2)

        body = env.get(days=7).json()
        by_day = {day["day_key"]: day for day in body["days"]}

        assert by_day["2026-08-15"]["loops"] == 1
        assert by_day["2026-08-15"]["average_shift"] == 2.0
        assert body["totals"]["loops_closed"] == 1

    def test_a_loop_without_a_self_report_reads_as_one(self, env: Env) -> None:
        """The same value the derived outcome row carries for that loop."""
        log_id = env.log_practice(TODAY)
        env.close_loop(log_id, capacity_delta=None)

        body = env.get(days=7).json()

        assert body["days"][-1]["average_shift"] == 1.0

    def test_a_practice_without_a_loop_still_appears(self, env: Env) -> None:
        env.log_practice(TODAY)

        body = env.get(days=7).json()

        assert body["days"][-1]["completed"] == 1
        assert body["days"][-1]["loops"] == 0
        assert body["days"][-1]["average_shift"] is None

    def test_several_loops_on_one_day_average(self, env: Env) -> None:
        env.close_loop(env.log_practice(TODAY), capacity_delta=2)
        env.close_loop(env.log_practice(TODAY), capacity_delta=-1)

        body = env.get(days=7).json()

        assert body["days"][-1]["loops"] == 2
        assert body["days"][-1]["average_shift"] == 0.5


# ─── Anchors ────────────────────────────────────────────────────────────


class TestAnchors:
    def test_first_practice_day_reaches_back_past_the_window(self, env: Env) -> None:
        """ "Practicing since March" is unanswerable from thirty days of rows."""
        env.log_practice("2026-03-04")
        env.log_practice(TODAY)

        body = env.get(days=7).json()

        assert body["totals"]["first_practice_day"] == "2026-03-04"
        assert body["totals"]["completed"] == 1

    def test_first_loop_day_is_the_practice_day_not_the_write_day(self, env: Env) -> None:
        log_id = env.log_practice("2026-03-04")
        env.close_loop(log_id)

        body = env.get().json()

        assert body["totals"]["first_loop_day"] == "2026-03-04"

    def test_first_loop_day_is_null_when_nothing_has_closed(self, env: Env) -> None:
        env.log_practice(TODAY)

        body = env.get().json()

        assert body["totals"]["first_practice_day"] == TODAY
        assert body["totals"]["first_loop_day"] is None

    @pytest.mark.parametrize("status", ["skipped", "started"])
    def test_a_history_with_no_completion_has_no_first_practice_day(
        self, env: Env, status: str
    ) -> None:
        """The anchor renders as "Practicing since X". A skip is not that.

        ``POST /practice/log`` takes the status from the client, so a
        user can hold a log full of rows without ever having practiced.
        An unfiltered anchor turns that into a non-null date, and the
        page's empty-state gate reads exactly this field: the user would
        get a chart of empty columns captioned with a day they never
        practiced on, instead of the invitation to start.
        """
        env.log_practice("2026-03-04", status=status)
        env.log_practice(TODAY, status=status)

        body = env.get(days=7).json()

        assert body["totals"]["first_practice_day"] is None
        assert body["totals"]["completed"] == 0
        assert body["totals"]["days_practiced"] == 0

    def test_the_anchor_is_the_first_completion_not_the_first_row(self, env: Env) -> None:
        env.log_practice("2026-03-04", status="skipped")
        env.log_practice("2026-04-01", status="started")
        env.log_practice("2026-05-06")

        body = env.get().json()

        assert body["totals"]["first_practice_day"] == "2026-05-06"

    def test_a_loop_on_an_uncompleted_practice_still_has_a_first_loop_day(self, env: Env) -> None:
        """The asymmetry with the practice anchor is deliberate, so pin it.

        ``POST /practice/integration`` accepts a log row of any status
        and writes the derived ``practice_integration`` outcome row
        either way, which is what the dashboard counts. Filtering loops
        to completed practices here would make the journey report fewer
        loops than the dashboard for the same events, which is the drift
        :func:`~alchymine.engine.practice.journey.loop_shift_value`
        exists to prevent. A ``started`` practice is a real experience to
        reflect on; the log status says so in as many words.

        There is no reachable contradiction on screen: a user with no
        completion at all gets the empty state, where neither anchor is
        rendered.
        """
        env.close_loop(env.log_practice("2026-03-04", status="started"))

        body = env.get().json()

        assert body["totals"]["first_loop_day"] == "2026-03-04"
        assert body["totals"]["first_practice_day"] is None


# ─── Ownership ──────────────────────────────────────────────────────────


class TestOwnership:
    def test_another_users_practice_is_not_in_the_series(self, env: Env) -> None:
        env.log_practice(TODAY, user_id=OTHER_USER_ID)

        body = env.get(days=7).json()

        assert body["totals"]["completed"] == 0
        assert body["totals"]["first_practice_day"] is None

    def test_another_users_loop_is_not_in_the_series(self, env: Env) -> None:
        log_id = env.log_practice(TODAY, user_id=OTHER_USER_ID)
        env.close_loop(log_id, user_id=OTHER_USER_ID, capacity_delta=2)

        body = env.get(days=7).json()

        assert body["totals"]["loops_closed"] == 0
        assert body["totals"]["first_loop_day"] is None

    def test_a_user_id_in_the_query_string_is_ignored(self, env: Env) -> None:
        env.log_practice(TODAY)
        env.log_practice(TODAY, user_id=OTHER_USER_ID)

        body = env.get(days=7, user_id=OTHER_USER_ID).json()

        assert body["totals"]["completed"] == 1

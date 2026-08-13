"""``GET /admin/usage`` — what the money actually went on.

Every number in the response is checked against a hand-summed fixture
rather than against another query, because a rollup that agrees with
itself proves nothing. The fixture is six rows whose totals are written
out longhand at the top of the module, so a change in the aggregation can
only pass by being right.

Two sources, deliberately: gate numbers (calls, ceilings) come from
``usage_counters`` and every dollar comes from ``usage_records``. Counters
answer "are we blocked"; the ledger answers "what did it cost".
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import get_current_admin
from alchymine.api.deps import set_db_engine
from alchymine.api.main import app
from alchymine.api.routers import admin as admin_module
from alchymine.config import get_settings
from alchymine.db.base import Base
from alchymine.db.models import UsageRecord, User
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_LLM_CALLS,
    current_month_key,
    current_period_key,
    increment_and_get,
)

URL = "/api/v1/admin/usage"

USER_A = "user-a"
USER_B = "user-b"

TODAY = current_period_key()
MONTH = current_month_key()
# Another day inside the same month, so the two windows differ. Which day
# does not matter: the endpoint filters period_key by equality.
OTHER_DAY = f"{MONTH}-01" if not TODAY.endswith("-01") else f"{MONTH}-02"

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

# The fixture, summed by hand.
#
# today:  chat 2000 + chat 1000 + art 67000 + unattributed 500 = 70_500
# month:  today 70_500 + chat 4000 + report_narrative 9000     = 83_500
TODAY_MICROS = 70_500
MONTH_MICROS = 83_500
SEEDED_LLM_CALLS = 138


@contextmanager
def _env(**overrides: object) -> Iterator[None]:
    values = {key.upper(): str(value) for key, value in overrides.items()}
    with patch.dict(os.environ, values, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()


def _record(**overrides: object) -> UsageRecord:
    row: dict[str, object] = {
        "user_id": USER_A,
        "scope": USER_A,
        "surface": "chat",
        "meter": "llm_calls",
        "provider": "anthropic",
        "model": HAIKU,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "images": 0,
        "cost_micros": 0,
        "estimated": False,
        "period_key": TODAY,
        "month_key": MONTH,
    }
    row.update(overrides)
    return UsageRecord(**row)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def seeded_db() -> Iterator[async_sessionmaker[AsyncSession]]:
    """An in-memory database holding the six-row fixture and one counter."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _seed() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add_all(
                [
                    User(id="admin-1", email="admin@test.com", is_admin=True, plan="beta"),
                    User(id=USER_A, email="a@test.com", plan="beta"),
                    User(id=USER_B, email="b@test.com", plan="pro"),
                ]
            )
            session.add_all(
                [
                    # today
                    _record(input_tokens=1000, output_tokens=100, cost_micros=2000),
                    _record(
                        input_tokens=500, output_tokens=50, cost_micros=1000, estimated=True
                    ),
                    _record(
                        user_id=USER_B,
                        scope=USER_B,
                        surface="art",
                        meter="art_generations",
                        provider="google",
                        model="gemini-test",
                        images=1,
                        cost_micros=67_000,
                    ),
                    _record(
                        user_id=None,
                        scope="unattributed",
                        surface="report_narrative",
                        model=SONNET,
                        input_tokens=100,
                        output_tokens=10,
                        cost_micros=500,
                    ),
                    # earlier in the same month
                    _record(cost_micros=4000, period_key=OTHER_DAY),
                    _record(
                        user_id=USER_B,
                        scope=USER_B,
                        surface="report_narrative",
                        model=SONNET,
                        cost_micros=9000,
                        period_key=OTHER_DAY,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())
    set_db_engine(engine)
    asyncio.run(
        increment_and_get(
            scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS, amount=SEEDED_LLM_CALLS
        )
    )

    async def _session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[admin_module.get_db] = _session
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(admin_module.get_db, None)
        set_db_engine(None)
        asyncio.run(engine.dispose())


@pytest.fixture(autouse=True)
def _as_admin(seeded_db) -> Iterator[None]:
    admin = User(id="admin-1", email="admin@test.com", is_admin=True, is_active=True)
    app.dependency_overrides[get_current_admin] = lambda: admin
    yield
    app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _get(client: TestClient, **params: object) -> dict:
    response = client.get(URL, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ── Access ───────────────────────────────────────────────────────────────


class TestItIsAdminOnly:
    def test_an_anonymous_caller_is_refused(self, client: TestClient) -> None:
        app.dependency_overrides.pop(get_current_admin, None)
        response = client.get(URL)

        assert response.status_code in (401, 403)

    def test_nothing_leaks_in_the_refusal(self, client: TestClient) -> None:
        app.dependency_overrides.pop(get_current_admin, None)
        response = client.get(URL)

        assert "a@test.com" not in response.text
        assert "cost_micros" not in response.text


# ── The two window blocks ────────────────────────────────────────────────


class TestTodayBlock:
    def test_spend_reconciles_with_the_hand_summed_fixture(self, client: TestClient) -> None:
        today = _get(client)["today"]

        assert today["period_key"] == TODAY
        assert today["spend_micros"] == TODAY_MICROS

    def test_cents_are_derived_once_at_aggregate_time_with_a_ceiling(
        self, client: TestClient
    ) -> None:
        """70,500 micros is 7.05 cents, which must never round down to 7."""
        assert _get(client)["today"]["spend_cents"] == 8

    def test_the_ceiling_and_what_is_left_of_it_come_from_config(
        self, client: TestClient
    ) -> None:
        today = _get(client)["today"]

        assert today["ceiling_micros"] == 15_000_000
        assert today["remaining_micros"] == 15_000_000 - TODAY_MICROS

    def test_remaining_goes_negative_rather_than_hiding_an_overshoot(
        self, client: TestClient
    ) -> None:
        with _env(monthly_llm_spend_budget_usd=0.6, daily_spend_headroom_factor=1.0):
            today = _get(client)["today"]

        assert today["ceiling_micros"] == 20_000
        assert today["remaining_micros"] == 20_000 - TODAY_MICROS < 0

    def test_the_gate_numbers_come_from_the_counters_not_the_ledger(
        self, client: TestClient
    ) -> None:
        """Six ledger rows, 138 counted calls. They measure different things."""
        today = _get(client)["today"]

        assert today["llm_calls"] == SEEDED_LLM_CALLS
        assert today["llm_call_ceiling"] == 2000
        assert today["record_count"] == 4

    def test_estimated_rows_are_counted_so_their_share_is_visible(
        self, client: TestClient
    ) -> None:
        """More than a few percent means the disconnect path needs a look."""
        today = _get(client)["today"]

        assert today["estimated_record_count"] == 1
        assert today["record_count"] == 4


class TestMonthBlock:
    def test_spend_reconciles_with_the_hand_summed_fixture(self, client: TestClient) -> None:
        month = _get(client)["month"]

        assert month["month_key"] == MONTH
        assert month["spend_micros"] == MONTH_MICROS
        assert month["spend_cents"] == 9  # 8.35 cents, ceiling

    def test_the_budget_and_what_is_left_of_it_come_from_config(
        self, client: TestClient
    ) -> None:
        month = _get(client)["month"]

        assert month["budget_micros"] == 300_000_000
        assert month["remaining_micros"] == 300_000_000 - MONTH_MICROS

    def test_percent_of_budget_is_reported_to_one_decimal(self, client: TestClient) -> None:
        with _env(monthly_llm_spend_budget_usd=0.1):
            month = _get(client)["month"]

        # 83,500 of 100,000 micros.
        assert month["budget_micros"] == 100_000
        assert month["pct_of_budget"] == 83.5

    def test_a_zero_budget_reports_zero_percent_rather_than_dividing_by_it(
        self, client: TestClient
    ) -> None:
        with _env(monthly_llm_spend_budget_usd=0.0):
            month = _get(client)["month"]

        assert month["budget_micros"] == 0
        assert month["pct_of_budget"] == 0.0


# ── Breakdowns ───────────────────────────────────────────────────────────


class TestBySurface:
    def test_today_partitions_the_day_exactly(self, client: TestClient) -> None:
        rows = {row["surface"]: row for row in _get(client)["by_surface"]["today"]}

        assert rows["chat"] == {
            "surface": "chat",
            "calls": 2,
            "cost_micros": 3000,
            "cost_cents": 1,
        }
        assert rows["art"]["cost_micros"] == 67_000
        assert sum(row["cost_micros"] for row in rows.values()) == TODAY_MICROS

    def test_the_month_block_covers_the_wider_window(self, client: TestClient) -> None:
        rows = {row["surface"]: row for row in _get(client)["by_surface"]["month"]}

        assert rows["chat"]["calls"] == 3
        assert rows["chat"]["cost_micros"] == 7000
        assert rows["report_narrative"]["cost_micros"] == 9000
        assert sum(row["cost_micros"] for row in rows.values()) == MONTH_MICROS

    def test_unattributed_spend_gets_its_own_row(self, client: TestClient) -> None:
        """Section 5.5: visible, rather than buried inside a surface."""
        rows = {row["surface"]: row for row in _get(client)["by_surface"]["today"]}

        assert rows["unattributed"]["calls"] == 1
        assert rows["unattributed"]["cost_micros"] == 500
        # And it is a relabel, not an extra: the row it came from is not
        # also counted under report_narrative today.
        assert "report_narrative" not in rows

    def test_the_unattributed_row_is_present_in_both_windows(self, client: TestClient) -> None:
        """A missing row reads as "not measured"; a zero reads as "none"."""
        body = _get(client)

        assert "unattributed" in {row["surface"] for row in body["by_surface"]["today"]}
        assert "unattributed" in {row["surface"] for row in body["by_surface"]["month"]}

    def test_rows_are_ordered_by_what_they_cost(self, client: TestClient) -> None:
        costs = [row["cost_micros"] for row in _get(client)["by_surface"]["today"]]

        assert costs == sorted(costs, reverse=True)


class TestByModel:
    def test_tokens_are_summed_per_model(self, client: TestClient) -> None:
        rows = {row["model"]: row for row in _get(client)["by_model"]["today"]}

        assert rows[HAIKU]["calls"] == 2
        assert rows[HAIKU]["input_tokens"] == 1500
        assert rows[HAIKU]["output_tokens"] == 150
        assert rows[HAIKU]["cost_micros"] == 3000

    def test_both_cache_fields_are_reported(self, client: TestClient) -> None:
        """Slice 5's acceptance criterion is read off this block."""
        row = {r["model"]: r for r in _get(client)["by_model"]["today"]}[HAIKU]

        assert row["cache_read_input_tokens"] == 0
        assert row["cache_creation_input_tokens"] == 0

    def test_gemini_rows_appear_beside_the_claude_ones(self, client: TestClient) -> None:
        rows = {row["model"]: row for row in _get(client)["by_model"]["today"]}

        assert rows["gemini-test"]["cost_micros"] == 67_000

    def test_the_month_block_is_wider_than_the_day(self, client: TestClient) -> None:
        today = {row["model"]: row for row in _get(client)["by_model"]["today"]}
        month = {row["model"]: row for row in _get(client)["by_model"]["month"]}

        assert today[HAIKU]["cost_micros"] == 3000
        assert month[HAIKU]["cost_micros"] == 7000


class TestTopUsers:
    def test_the_costliest_user_comes_first(self, client: TestClient) -> None:
        rows = _get(client)["top_users"]

        assert [row["user_id"] for row in rows] == [USER_B, USER_A]

    def test_each_row_carries_its_plan_and_allowance_context(
        self, client: TestClient
    ) -> None:
        """The view that answers what a p95 active user actually costs."""
        rows = {row["user_id"]: row for row in _get(client)["top_users"]}

        assert rows[USER_A]["email"] == "a@test.com"
        assert rows[USER_A]["plan"] == "beta"
        assert rows[USER_A]["allowance_cents"] == 555
        assert rows[USER_B]["plan"] == "pro"
        assert rows[USER_B]["allowance_cents"] == 275

    def test_spend_is_the_month_to_date_figure(self, client: TestClient) -> None:
        rows = {row["user_id"]: row for row in _get(client)["top_users"]}

        assert rows[USER_A]["calls"] == 3
        assert rows[USER_A]["cost_micros"] == 7000
        assert rows[USER_B]["cost_micros"] == 76_000
        assert rows[USER_B]["cost_cents"] == 8

    def test_percent_of_allowance_is_measured_against_the_plan(
        self, client: TestClient
    ) -> None:
        rows = {row["user_id"]: row for row in _get(client)["top_users"]}

        # 76,000 micros against 275 cents (2,750,000 micros).
        assert rows[USER_B]["pct_of_allowance"] == 2.8
        assert rows[USER_A]["pct_of_allowance"] == 0.1

    def test_unattributed_spend_has_no_user_row(self, client: TestClient) -> None:
        rows = _get(client)["top_users"]

        assert all(row["user_id"] is not None for row in rows)
        assert len(rows) == 2


class TestTheTopParameter:
    def test_it_defaults_to_twenty(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        params = schema["paths"]["/api/v1/admin/usage"]["get"]["parameters"]
        top = next(param for param in params if param["name"] == "top")

        assert top["schema"]["default"] == 20

    def test_it_truncates_the_list(self, client: TestClient) -> None:
        rows = _get(client, top=1)["top_users"]

        assert [row["user_id"] for row in rows] == [USER_B]

    def test_one_is_allowed(self, client: TestClient) -> None:
        assert client.get(URL, params={"top": 1}).status_code == 200

    def test_a_hundred_is_allowed(self, client: TestClient) -> None:
        assert client.get(URL, params={"top": 100}).status_code == 200

    def test_zero_is_refused(self, client: TestClient) -> None:
        assert client.get(URL, params={"top": 0}).status_code == 422

    def test_more_than_a_hundred_is_refused(self, client: TestClient) -> None:
        assert client.get(URL, params={"top": 101}).status_code == 422


class TestTheEnvelope:
    def test_as_of_is_an_instant_the_reader_can_trust(self, client: TestClient) -> None:
        from datetime import UTC, datetime

        as_of = datetime.fromisoformat(_get(client)["as_of"])

        assert as_of.tzinfo is not None
        assert abs((datetime.now(UTC) - as_of).total_seconds()) < 60

    def test_an_empty_ledger_answers_with_zeros_rather_than_nulls(
        self, client: TestClient, seeded_db
    ) -> None:
        async def _wipe() -> None:
            from sqlalchemy import delete

            async with seeded_db() as session:
                await session.execute(delete(UsageRecord))
                await session.commit()

        asyncio.run(_wipe())
        body = _get(client)

        assert body["today"]["spend_micros"] == 0
        assert body["today"]["spend_cents"] == 0
        assert body["month"]["spend_micros"] == 0
        assert body["by_model"]["today"] == []
        assert body["top_users"] == []
        # The one row that is always there, so zero reads as zero.
        assert body["by_surface"]["today"] == [
            {"surface": "unattributed", "calls": 0, "cost_micros": 0, "cost_cents": 0}
        ]

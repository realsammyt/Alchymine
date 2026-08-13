"""The sixth paid surface: PATCH .../layers/{system}/reassess (issue #243).

The design's chokepoint table lists five. This route makes a sixth paid
Claude call, through the same ``NarrativeGenerator`` the report worker
uses, and until now it was ungated and unattributed.

Half of it is free, which is why the gate is applied inside the handler
rather than as a route dependency: re-running a coordinator graph is
deterministic and belongs to every account, while rewriting the narrative
costs money. The tests below pin that seam in both directions.

``test_plan_gate.py`` covers the gate's own behaviour, parametrized over
all six gates. What is here is the wiring: that this route carries it,
that it refuses before anything is written, and that a tripped global
breaker still reaches the caller instead of being swallowed into a null
narrative.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import Account, get_current_account
from alchymine.api.deps import get_db_session, set_db_engine
from alchymine.api.main import app
from alchymine.db.base import Base
from alchymine.db.usage_counters import (
    METER_SPEND_MICROS_MONTHLY,
    CostCeilingExceeded,
    current_month_key,
    increment_and_get,
)

USER_ID = "u-reassess"
URL = f"/api/v1/profile/{USER_ID}/layers/healing/reassess"
BODY = {"assessment_responses": {"q1": 3}, "regenerate_narrative": True}


def _account(plan: str = "beta") -> Account:
    return Account(
        user_id=USER_ID,
        email="reassess@example.com",
        plan=plan,
        plan_status="active",
        is_admin=False,
        plan_period_end=None,
        trial_ends_at=None,
    )


@pytest.fixture
def counters() -> Iterator[None]:
    """An empty database: counters for the gate, users for the route.

    Both are needed because the two halves of this route read different
    things. The gate opens its own session through ``deps``, which is why
    the engine is set on the singleton as well as overridden as the route
    dependency.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    set_db_engine(engine)
    app.dependency_overrides[get_db_session] = _session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        set_db_engine(None)
        asyncio.run(engine.dispose())


@pytest.fixture
def client(counters) -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_account, None)


def _as(client: TestClient, plan: str = "beta") -> TestClient:
    app.dependency_overrides[get_current_account] = lambda: _account(plan)
    return client


class TestTheGateIsWired:
    def test_free_is_refused_before_anything_runs(self, client: TestClient) -> None:
        response = _as(client, "free").patch(URL, json=BODY)

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == "plan_upgrade_required"
        assert response.json()["detail"]["upgrade_url"] == "/pricing"

    def test_a_spent_allowance_renders_the_upsell(self, client: TestClient) -> None:
        asyncio.run(
            increment_and_get(
                scope=USER_ID,
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=current_month_key(),
                amount=555 * 10_000,  # the beta allowance, in micros
            )
        )

        response = _as(client, "beta").patch(URL, json=BODY)

        assert response.status_code == 429
        detail = response.json()["detail"]
        assert detail["code"] == "plan_allowance_reached"
        assert detail["meter"] == METER_SPEND_MICROS_MONTHLY
        retry_at = datetime.fromisoformat(detail["retry_at"])
        assert retry_at > datetime.now(UTC)

    def test_the_deterministic_half_stays_open_to_free(self, client: TestClient) -> None:
        """Re-running the graph costs nothing, so free keeps it.

        404 is the honest answer for a user with no profile seeded. What
        matters is that it is not a 402: the gate did not fire.
        """
        body = {**BODY, "regenerate_narrative": False}

        response = _as(client, "free").patch(URL, json=body)

        assert response.status_code != 402
        assert response.status_code == 404

    def test_someone_elses_profile_is_still_refused(self, client: TestClient) -> None:
        other = f"/api/v1/profile/{USER_ID}-stranger/layers/healing/reassess"

        response = _as(client, "beta").patch(other, json=BODY)

        assert response.status_code == 403


class TestTheBreakerReachesTheCaller:
    """A capped budget is not a narrative that failed to write."""

    def _run_to_the_narrative(self, client: TestClient, error: Exception):  # noqa: ANN202
        """Drive the handler past the graph and into the narrative block."""
        profile = MagicMock()
        profile.intake.assessment_responses = {}
        profile.intake.full_name = "Maria Elena Vasquez"
        profile.intake.birth_date = "1992-03-15"
        profile.intake.intention = "family"
        profile.intake.resolved_intentions = ["family"]
        profile.identity = None

        graph = MagicMock()
        graph.invoke.return_value = {"results": {"healing": {}}, "status": "success"}

        generator = MagicMock()
        generator.generate = AsyncMock(side_effect=error)

        with (
            patch(
                "alchymine.api.routers.profile.repository.get_profile",
                AsyncMock(return_value=profile),
            ),
            patch(
                "alchymine.api.routers.profile.repository.update_layer",
                AsyncMock(return_value=None),
            ),
            patch(
                "alchymine.api.routers.profile._get_graph_builders",
                return_value={"healing": lambda include_quality_gate=False: graph},
            ),
            patch("alchymine.llm.narrative.NarrativeGenerator", return_value=generator),
        ):
            return _as(client, "beta").patch(URL, json=BODY)

    def test_a_tripped_breaker_is_a_503_not_a_null_narrative(self, client: TestClient) -> None:
        response = self._run_to_the_narrative(
            client,
            CostCeilingExceeded(
                meter="spend_micros_daily",
                scope="global",
                retry_at=datetime.now(UTC) + timedelta(hours=2),
            ),
        )

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "llm_temporarily_unavailable"

    def test_an_ordinary_narrative_failure_still_degrades_quietly(self, client: TestClient) -> None:
        """The control. A flaky model must not take the reassessment down."""
        response = self._run_to_the_narrative(client, RuntimeError("model said no"))

        assert response.status_code == 200
        assert response.json()["narrative"] is None

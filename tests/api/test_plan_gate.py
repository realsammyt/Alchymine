"""Tests for the per-plan entitlement and allowance gate.

This is the first thing in the product that can tell a user no, so the
tests pin both halves of that: *who* gets refused, and *what the refusal
looks like on the wire*. A quota rejection is a sales moment rather than
a fault, which is why the body carries an upgrade url and the frontend
renders it as a wait state instead of an error.

The gate is mounted on a minimal app here rather than on the real
routers, so a failure points at the gate and not at whatever else the
report or chat endpoint happens to be doing that day. The four real
chokepoints are covered in ``test_plan_allowance_routes.py``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import Account, get_current_account
from alchymine.api.deps import set_db_engine
from alchymine.api.entitlements import (
    UPGRADE_URL,
    require_art,
    require_brand_logo,
    require_chat,
    require_report,
    require_report_download,
)
from alchymine.db.models import UsageCounter, UsageRecord
from alchymine.db.usage_counters import (
    METER_SPEND_MICROS_MONTHLY,
    CostCeilingExceeded,
    current_month_key,
    increment_and_get,
    next_month_start,
)

ALL_GATES = [require_report, require_report_download, require_chat, require_art, require_brand_logo]
SPENDING_GATES = [require_report, require_chat, require_art, require_brand_logo]

# Every plan in the config default, and the allowance each one buys.
# Restated here rather than imported so a silent edit to the config
# default shows up as a test failure instead of a passing tautology.
PLAN_ALLOWANCE_CENTS = {
    "free": 0,
    "beta": 555,
    "blueprint": 99,
    "pro": 275,
    "founding": 333,
}
PAID_PLANS = ["beta", "blueprint", "pro", "founding"]

USER_ID = "u-gate"


def _account(plan: str = "beta", user_id: str = USER_ID) -> Account:
    return Account(
        user_id=user_id,
        email=f"{user_id}@example.com",
        plan=plan,
        plan_status="active",
        is_admin=False,
        plan_period_end=None,
        trial_ends_at=None,
    )


class _Env:
    """A counters table the gate can read, plus a way to put spend on it.

    The engine is set on the ``deps`` singleton rather than injected: the
    gate opens its own session through ``deps`` in production, and the
    test is worth nothing if it exercises a different path. Setup runs on
    a dedicated loop while requests run on the TestClient's own loop,
    which is safe because an in-memory SQLite engine uses a StaticPool and
    so shares one connection across both.
    """

    def __init__(self, engine, loop) -> None:
        self._engine = engine
        self._loop = loop

    def spend(self, micros: int, *, user_id: str = USER_ID, month: str | None = None) -> None:
        """Record *micros* of delivered spend on the user's monthly meter."""
        self._loop.run_until_complete(
            increment_and_get(
                scope=user_id,
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=month or current_month_key(),
                amount=micros,
            )
        )

    def run(self, coro):
        """Drive a coroutine on the loop that owns this engine."""
        return self._loop.run_until_complete(coro)

    def client(self, gate, account: Account) -> TestClient:
        """A minimal app with one gated route, called as *account*."""
        api = FastAPI()

        @api.get("/gated")
        async def gated(acct: Account = Depends(gate)) -> dict:
            from alchymine.llm.attribution import current_attribution

            return {
                "user_id": acct.user_id,
                "plan": acct.effective_plan,
                "surface": current_attribution()[1],
            }

        api.dependency_overrides[get_current_account] = lambda: account
        return TestClient(api)


@pytest.fixture
def env():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    loop = asyncio.new_event_loop()

    async def _setup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(UsageCounter.__table__.create)
            # The ledger writes a row per delivered call as well as
            # charging the meter, and a failed insert would mark it
            # degraded rather than record the spend.
            await conn.run_sync(UsageRecord.__table__.create)

    loop.run_until_complete(_setup())
    set_db_engine(engine)
    try:
        yield _Env(engine, loop)
    finally:
        set_db_engine(None)
        loop.run_until_complete(engine.dispose())
        loop.close()


# ─── Entitlement: free is refused everywhere ─────────────────────────────


class TestEntitlement:
    """Free gets the deterministic surfaces and nothing that costs money."""

    @pytest.mark.parametrize("gate", ALL_GATES)
    def test_free_is_refused_on_every_surface(self, env, gate) -> None:
        response = env.client(gate, _account(plan="free")).get("/gated")

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == "plan_upgrade_required"

    @pytest.mark.parametrize("plan", PAID_PLANS)
    @pytest.mark.parametrize("gate", ALL_GATES)
    def test_paid_plans_pass_when_under_allowance(self, env, gate, plan) -> None:
        response = env.client(gate, _account(plan=plan)).get("/gated")

        assert response.status_code == 200
        assert response.json()["plan"] == plan

    def test_a_lapsed_plan_is_refused_like_free(self, env) -> None:
        """effective_plan, not plan: a closed window stops costing money."""
        lapsed = Account(
            user_id="u-lapsed",
            email="lapsed@example.com",
            plan="pro",
            plan_status="canceled",
            is_admin=False,
            plan_period_end=datetime.now(UTC) - timedelta(days=1),
            trial_ends_at=None,
        )

        response = env.client(require_chat, lapsed).get("/gated")

        assert response.status_code == 402
        assert response.json()["detail"]["plan"] == "free"

    def test_the_refusal_carries_the_whole_envelope(self, env) -> None:
        detail = env.client(require_chat, _account(plan="free")).get("/gated").json()["detail"]

        assert set(detail) == {"code", "message", "retry_at", "meter", "plan", "upgrade_url"}
        assert detail["plan"] == "free"
        assert detail["upgrade_url"] == UPGRADE_URL == "/pricing"
        # Waiting does not fix an entitlement refusal — upgrading does.
        assert detail["retry_at"] is None
        assert detail["meter"] is None
        assert detail["message"]

    def test_free_is_refused_before_the_meter_is_consulted(self, env) -> None:
        """Free has a zero allowance, so it would 429 on an empty meter.

        Entitlement runs first precisely so the answer is "upgrade" rather
        than "you have used up the nothing you were given".
        """
        detail = env.client(require_chat, _account(plan="free")).get("/gated").json()["detail"]

        assert detail["code"] == "plan_upgrade_required"


# ─── Allowance: the month's spend is gone ────────────────────────────────


class TestAllowance:
    """Spent budget reads as a 429 with a date, not a 402 with a price."""

    @pytest.mark.parametrize("plan", PAID_PLANS)
    def test_exhausted_allowance_is_429(self, env, plan) -> None:
        env.spend(PLAN_ALLOWANCE_CENTS[plan] * 10_000)

        response = env.client(require_chat, _account(plan=plan)).get("/gated")

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "plan_allowance_reached"

    def test_one_micro_under_the_allowance_still_passes(self, env) -> None:
        """The ceiling is inclusive: at the number is spent, below it is not."""
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000 - 1)

        assert env.client(require_chat, _account(plan="pro")).get("/gated").status_code == 200

    def test_beta_does_not_bind_at_realistic_volume(self, env) -> None:
        """555 cents is an abuse stop, not a budget.

        It exists so the measurement cohort's cost distribution is not
        truncated by the cap that is supposed to be measuring it. A busy
        beta month (200 chat turns on Sonnet plus a report) must clear it.
        """
        two_hundred_sonnet_turns = 200 * 15_300
        a_report = 5 * 40_000
        env.spend(two_hundred_sonnet_turns + a_report)

        assert env.client(require_chat, _account(plan="beta")).get("/gated").status_code == 200

    def test_the_429_carries_the_whole_envelope(self, env) -> None:
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000)

        detail = env.client(require_chat, _account(plan="pro")).get("/gated").json()["detail"]

        assert set(detail) == {"code", "message", "retry_at", "meter", "plan", "upgrade_url"}
        assert detail["code"] == "plan_allowance_reached"
        assert detail["meter"] == "spend_micros_monthly"
        assert detail["plan"] == "pro"
        assert detail["upgrade_url"] == "/pricing"

    def test_retry_at_is_the_first_of_next_month_utc(self, env) -> None:
        """A monthly allowance that says "try again tomorrow" is a lie."""
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000)

        body = env.client(require_chat, _account(plan="pro")).get("/gated").json()
        retry_at = datetime.fromisoformat(body["detail"]["retry_at"])

        assert retry_at.utcoffset() == timedelta(0)
        assert (retry_at.day, retry_at.hour, retry_at.minute, retry_at.second) == (1, 0, 0, 0)
        assert retry_at > datetime.now(UTC)

    def test_the_meter_is_scoped_to_one_user(self, env) -> None:
        """One account burning its month must not close another's."""
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000)

        other = _account(plan="pro", user_id="u-other")
        assert env.client(require_chat, other).get("/gated").status_code == 200

    def test_last_month_spend_does_not_count_against_this_month(self, env) -> None:
        """The month key is the reset: no job runs at the boundary."""
        now = datetime.now(UTC)
        last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000, month=last_month)

        assert env.client(require_chat, _account(plan="pro")).get("/gated").status_code == 200

    def test_next_month_spend_does_not_count_either(self, env) -> None:
        """The rollover reads a different row, in both directions."""
        env.spend(
            PLAN_ALLOWANCE_CENTS["pro"] * 10_000,
            month=next_month_start().strftime("%Y-%m"),
        )

        assert env.client(require_chat, _account(plan="pro")).get("/gated").status_code == 200

    def test_the_gate_reads_the_month_meter_not_the_day_meter(self, env) -> None:
        """Encoding the period in the meter name is what prevents this bug.

        A daily-keyed read would return 0 for a month's spend and report
        "no spend" when the truth is "wrong row".
        """
        with patch(
            "alchymine.api.entitlements.check_ceiling", new=AsyncMock(return_value=0)
        ) as checked:
            env.client(require_chat, _account(plan="pro")).get("/gated")

        kwargs = checked.await_args.kwargs
        assert kwargs["meter"] == "spend_micros_monthly"
        assert kwargs["period_key"] == current_month_key()
        assert kwargs["scope"] == USER_ID
        assert kwargs["ceiling"] == PLAN_ALLOWANCE_CENTS["pro"] * 10_000


class TestTheLedgerAndTheGateAgree:
    """The one integration this slice actually rests on.

    Slice 2 writes the meter and slice 3 reads it. They meet on a
    ``(scope, meter, period_key)`` tuple that nothing else checks: if the
    two ever disagreed on the month key or the scope, the gate would read
    an empty counter forever and no allowance would ever bind, silently
    and in production only. Seeding the meter by hand (as the tests above
    do, for speed) would not catch that, so this one spends through the
    real ledger path.
    """

    def test_spend_recorded_by_the_ledger_closes_the_allowance(self, env) -> None:
        from alchymine.llm.attribution import attributed
        from alchymine.llm.ledger import record_usage

        async def _spend_through_the_ledger() -> None:
            with attributed(user_id=USER_ID, surface="chat"):
                task = await record_usage(
                    meter="art_generations",
                    provider="google",
                    model="gemini-test",
                    images=1,
                    cost_micros_override=PLAN_ALLOWANCE_CENTS["pro"] * 10_000,
                )
                if task is not None:
                    await task

        env.run(_spend_through_the_ledger())

        response = env.client(require_chat, _account(plan="pro")).get("/gated")

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "plan_allowance_reached"

    def test_another_user_s_ledger_spend_does_not_close_this_one(self, env) -> None:
        from alchymine.llm.attribution import attributed
        from alchymine.llm.ledger import record_usage

        async def _spend_as_someone_else() -> None:
            with attributed(user_id="u-somebody-else", surface="chat"):
                task = await record_usage(
                    meter="art_generations",
                    provider="google",
                    model="gemini-test",
                    images=1,
                    cost_micros_override=PLAN_ALLOWANCE_CENTS["pro"] * 10_000,
                )
                if task is not None:
                    await task

        env.run(_spend_as_someone_else())

        assert env.client(require_chat, _account(plan="pro")).get("/gated").status_code == 200


# ─── The download gate has no spend meter ────────────────────────────────


class TestDownloadGateSkipsTheMeter:
    """PDF bytes were already paid for when the report was generated."""

    def test_exhausted_allowance_still_allows_the_download(self, env) -> None:
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000 * 10)

        client = env.client(require_report_download, _account(plan="pro"))
        assert client.get("/gated").status_code == 200

    def test_but_free_still_cannot_download(self, env) -> None:
        client = env.client(require_report_download, _account(plan="free"))
        assert client.get("/gated").status_code == 402

    def test_the_meter_is_never_read_at_all(self, env) -> None:
        with patch(
            "alchymine.api.entitlements.check_ceiling", new=AsyncMock(return_value=0)
        ) as checked:
            env.client(require_report_download, _account(plan="pro")).get("/gated")

        checked.assert_not_awaited()


# ─── An unreachable meter is our fault, not the user's ───────────────────


class TestMeterUnavailable:
    """Fail closed, but do not sell an upgrade for our own outage."""

    def test_unreadable_meter_is_not_rendered_as_an_upsell(self, env) -> None:
        """meter_unavailable belongs to the 503 handler, not to the gate.

        Blocking is right (an unreadable meter cannot authorize spend),
        but telling the user to buy something because our database is
        unreachable is not.
        """
        with patch(
            "alchymine.db.usage_counters.get_count",
            new=AsyncMock(side_effect=RuntimeError("counter table is gone")),
        ):
            client = env.client(require_chat, _account(plan="pro"))
            with pytest.raises(CostCeilingExceeded) as exc:
                client.get("/gated")

        assert exc.value.reason == "meter_unavailable"


# ─── The copy is user-facing ─────────────────────────────────────────────


class TestCopy:
    """House style is a hard rule on anything a person reads."""

    BANNED = (
        "delve",
        "leverage",
        "navigate",
        "robust",
        "comprehensive",
        "seamless",
        "ensure",
        "foster",
        "utilize",
    )

    def _assert_house_style(self, message: str) -> None:
        assert "—" not in message, "no em-dashes in user-facing copy"
        for word in self.BANNED:
            assert word not in message.lower(), f"banned vocabulary: {word}"
        assert len(message) < 120, "upsell copy stays short"

    @pytest.mark.parametrize("gate", ALL_GATES)
    def test_entitlement_copy_follows_house_style(self, env, gate) -> None:
        message = env.client(gate, _account(plan="free")).get("/gated").json()["detail"]["message"]

        self._assert_house_style(message)

    @pytest.mark.parametrize("gate", SPENDING_GATES)
    def test_allowance_copy_follows_house_style(self, env, gate) -> None:
        env.spend(PLAN_ALLOWANCE_CENTS["pro"] * 10_000)

        message = env.client(gate, _account(plan="pro")).get("/gated").json()["detail"]["message"]

        self._assert_house_style(message)

    def test_each_surface_names_what_it_is_selling(self, env) -> None:
        """One generic string for five surfaces is not an upsell."""
        messages = {
            env.client(gate, _account(plan="free")).get("/gated").json()["detail"]["message"]
            for gate in SPENDING_GATES
        }

        assert len(messages) == len(SPENDING_GATES)


# ─── Attribution ─────────────────────────────────────────────────────────


class TestSurfaceAttribution:
    """The gate is where a ledger row learns which surface spent the money."""

    @pytest.mark.parametrize(
        ("gate", "surface"),
        [
            (require_report, "report"),
            (require_chat, "chat"),
            (require_art, "art"),
            (require_brand_logo, "brand_logo"),
        ],
    )
    def test_the_surface_is_set_for_the_egress_sites(self, env, gate, surface) -> None:
        """Closes the surface='unknown' gap: every gated route names itself."""
        from alchymine.llm.attribution import set_attribution

        set_attribution(user_id=None, surface=None, request_id=None)

        body = env.client(gate, _account(plan="pro")).get("/gated").json()

        assert body["surface"] == surface

    async def test_a_refused_request_attributes_no_surface(self) -> None:
        """Nothing is going to spend, so nothing should look like it did.

        Awaited directly rather than driven through TestClient: a request
        runs in its own task with its own copied context, so a ContextVar
        set inside one is invisible here and the assertion would pass
        without testing anything.
        """
        from alchymine.llm.attribution import current_attribution, set_attribution

        set_attribution(user_id=None, surface=None, request_id=None)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await require_chat(_account(plan="free"))

        assert exc.value.status_code == 402
        assert current_attribution()[1] is None

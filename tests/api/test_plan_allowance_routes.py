"""The four product chokepoints, gated by plan.

``test_plan_gate.py`` pins the gate's own behaviour on a minimal app.
This module pins the wiring: that each real route carries the right gate,
that the two art caps stack without interfering, that chat produces a
real status code instead of an SSE error frame, and that swapping the
routes from ``get_current_user`` to ``get_current_account`` did not
quietly change who can read whose report.

Gating table, from ``docs/plans/2026-08-13-unit-economics.md`` section 9:

===============================  ===========  =========
Route                            entitlement  allowance
===============================  ===========  =========
``POST /reports``                yes          yes
``GET  /reports/{id}/pdf``       yes          no
``POST /chat``                   yes          yes
``POST /art/generate``           yes          yes
``POST /art/brand/logo``         yes          yes
===============================  ===========  =========
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import Account, get_current_account
from alchymine.api.deps import get_db_session, set_db_engine
from alchymine.api.main import app
from alchymine.api.routers.generative_art import _gemini_dependency
from alchymine.config import get_settings
from alchymine.db.base import Base
from alchymine.db.models import Report, User
from alchymine.db.usage_counters import (
    METER_SPEND_MICROS_MONTHLY,
    current_month_key,
    increment_and_get,
)
from alchymine.llm.gemini import GeminiImageResult

OWNER_ID = "user-1"  # matches TEST_USER_ID in tests/api/conftest.py
STRANGER_ID = "user-stranger"

# The chokepoints that meter spend, as (name, callable) so a single
# parametrize can drive all four.
INTAKE = {
    "full_name": "Maria Elena Vasquez",
    "birth_date": "1992-03-15",
    "birth_time": "14:14",
    "birth_city": "Mexico City",
    "intention": "family",
}


def _image() -> GeminiImageResult:
    return GeminiImageResult(
        image_bytes=b"\x89PNG\r\n\x1a\n",
        mime_type="image/png",
        prompt="a quiet shoreline",
        model="gemini-test",
        generated_at=datetime.now(UTC),
    )


def _account(plan: str, user_id: str = OWNER_ID) -> Account:
    return Account(
        user_id=user_id,
        email=f"{user_id}@example.com",
        plan=plan,
        plan_status="active",
        is_admin=False,
        plan_period_end=None,
        trial_ends_at=None,
    )


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report and chat rows use EncryptedString columns."""
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chat streams a canned reply rather than reaching a paid API."""
    monkeypatch.setenv("LLM_BACKEND", "none")


class _Env:
    """A TestClient where the routes, the meters and the plan all agree."""

    def __init__(self, client: TestClient, factory, loop) -> None:
        self.client = client
        self._factory = factory
        self._loop = loop
        self.gemini: MagicMock | None = None

    def as_plan(self, plan: str, user_id: str = OWNER_ID) -> None:
        """Call every subsequent request as an account on *plan*."""
        account = _account(plan, user_id)
        app.dependency_overrides[get_current_account] = lambda: account

    def spend(self, micros: int, *, user_id: str = OWNER_ID) -> None:
        """Put delivered spend on the user's monthly meter."""
        self._loop.run_until_complete(
            increment_and_get(
                scope=user_id,
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=current_month_key(),
                amount=micros,
            )
        )

    def exhaust_month(self, plan: str, *, user_id: str = OWNER_ID) -> None:
        self.spend(get_settings().allowance_cents_for(plan) * 10_000, user_id=user_id)

    def add_report(self, report_id: str, *, user_id: str | None, pdf: bool = True) -> None:
        async def _add() -> None:
            async with self._factory() as session:
                session.add(
                    Report(
                        id=report_id,
                        status="complete",
                        user_id=user_id,
                        created_by_sub=user_id,
                        user_input="a report",
                        result={"ok": True},
                        pdf_data=b"%PDF-1.4 fake" if pdf else None,
                    )
                )
                await session.commit()

        self._loop.run_until_complete(_add())


@pytest.fixture
def env(tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    loop = asyncio.new_event_loop()

    async def _setup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(User(id=OWNER_ID, email="owner@example.com", is_active=True))
            session.add(User(id=STRANGER_ID, email="stranger@example.com", is_active=True))
            await session.commit()

    loop.run_until_complete(_setup())

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    gemini = MagicMock()
    gemini.is_available = True
    gemini.generate_image = AsyncMock(side_effect=lambda _prompt: _image())

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[_gemini_dependency] = lambda: gemini
    set_db_engine(engine)

    # The report route dispatches a Celery task. Under CELERY_ALWAYS_EAGER
    # that would run the whole pipeline inline, which is not what any test
    # here is about.
    with (
        patch("alchymine.api.routers.reports.generate_report_task"),
        patch("alchymine.llm.art_storage.get_art_cache_root", return_value=tmp_path),
    ):
        environment = _Env(TestClient(app), factory, loop)
        environment.gemini = gemini
        environment.as_plan("beta")
        try:
            yield environment
        finally:
            app.dependency_overrides.pop(get_db_session, None)
            app.dependency_overrides.pop(_gemini_dependency, None)
            app.dependency_overrides.pop(get_current_account, None)
            set_db_engine(None)
            loop.run_until_complete(engine.dispose())
            loop.close()


# ── The four chokepoints ─────────────────────────────────────────────


def _post_report(env: _Env):
    return env.client.post("/api/v1/reports", json={"intake": INTAKE})


def _post_chat(env: _Env):
    return env.client.post("/api/v1/chat", json={"message": "How do I set a goal?"})


def _post_art(env: _Env):
    return env.client.post("/api/v1/art/generate", json={})


def _post_logo(env: _Env):
    return env.client.post("/api/v1/art/brand/logo")


METERED = [
    ("report", _post_report),
    ("chat", _post_chat),
    ("art", _post_art),
    ("brand_logo", _post_logo),
]


class TestFreeIsRefused:
    """An allowance of zero is what makes the free-tier rule structural."""

    @pytest.mark.parametrize(("name", "call"), METERED)
    def test_free_gets_402_on_every_paid_surface(self, env, name, call) -> None:
        env.as_plan("free")

        response = call(env)

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == "plan_upgrade_required"

    def test_free_cannot_download_a_pdf_either(self, env) -> None:
        """The bytes are already paid for, but the plan still has to include them."""
        env.add_report("rep-free", user_id=OWNER_ID)
        env.as_plan("free")

        response = env.client.get("/api/v1/reports/rep-free/pdf")

        assert response.status_code == 402
        assert response.json()["detail"]["code"] == "plan_upgrade_required"

    @pytest.mark.parametrize(("name", "call"), METERED)
    def test_a_refused_call_never_reaches_the_generator(self, env, name, call) -> None:
        env.as_plan("free")

        call(env)

        assert env.gemini.generate_image.call_count == 0


class TestPaidPlansPass:
    """Beta at 555 cents should never bind, which is the point of beta."""

    @pytest.mark.parametrize("plan", ["beta", "blueprint", "pro", "founding"])
    def test_report_is_accepted(self, env, plan) -> None:
        env.as_plan(plan)

        assert _post_report(env).status_code == 202

    @pytest.mark.parametrize("plan", ["beta", "blueprint", "pro", "founding"])
    def test_chat_streams(self, env, plan) -> None:
        env.as_plan(plan)

        response = _post_chat(env)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

    @pytest.mark.parametrize("plan", ["beta", "blueprint", "pro", "founding"])
    def test_art_is_generated(self, env, plan) -> None:
        env.as_plan(plan)

        assert _post_art(env).status_code == 201

    @pytest.mark.parametrize("plan", ["beta", "blueprint", "pro", "founding"])
    def test_a_logo_is_generated(self, env, plan) -> None:
        env.as_plan(plan)

        assert _post_logo(env).status_code == 201

    def test_a_pdf_downloads(self, env) -> None:
        env.add_report("rep-ok", user_id=OWNER_ID)
        env.as_plan("pro")

        response = env.client.get("/api/v1/reports/rep-ok/pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"


class TestAllowanceExhausted:
    """The month's money is gone, and the answer says when it comes back."""

    @pytest.mark.parametrize(("name", "call"), METERED)
    def test_exhausted_allowance_is_429(self, env, name, call) -> None:
        env.as_plan("pro")
        env.exhaust_month("pro")

        response = call(env)

        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "plan_allowance_reached"

    @pytest.mark.parametrize(("name", "call"), METERED)
    def test_the_envelope_is_complete_on_every_surface(self, env, name, call) -> None:
        env.as_plan("pro")
        env.exhaust_month("pro")

        detail = call(env).json()["detail"]

        assert set(detail) == {"code", "message", "retry_at", "meter", "plan", "upgrade_url"}
        assert detail["meter"] == "spend_micros_monthly"
        assert detail["plan"] == "pro"
        assert detail["upgrade_url"] == "/pricing"
        assert datetime.fromisoformat(detail["retry_at"]).day == 1

    def test_the_pdf_download_has_no_spend_check(self, env) -> None:
        """Serving stored bytes costs nothing, so it is not metered."""
        env.add_report("rep-paid", user_id=OWNER_ID)
        env.as_plan("pro")
        env.exhaust_month("pro")

        assert env.client.get("/api/v1/reports/rep-paid/pdf").status_code == 200

    @pytest.mark.parametrize(("name", "call"), METERED)
    def test_an_exhausted_call_never_reaches_the_generator(self, env, name, call) -> None:
        env.as_plan("pro")
        env.exhaust_month("pro")

        call(env)

        assert env.gemini.generate_image.call_count == 0

    def test_one_user_burning_their_month_does_not_close_anothers(self, env) -> None:
        env.exhaust_month("pro", user_id=STRANGER_ID)
        env.as_plan("pro", user_id=OWNER_ID)

        assert _post_chat(env).status_code == 200


class TestChatFailsBeforeTheStream:
    """A 429 inside an SSE body is a 200 as far as the browser is concerned."""

    def test_the_refusal_is_a_status_code_not_an_error_frame(self, env) -> None:
        env.as_plan("pro")
        env.exhaust_month("pro")

        response = _post_chat(env)

        assert response.status_code == 429
        assert not response.headers["content-type"].startswith("text/event-stream")
        assert "event: error" not in response.text

    def test_the_entitlement_refusal_is_a_status_code_too(self, env) -> None:
        env.as_plan("free")

        response = _post_chat(env)

        assert response.status_code == 402
        assert "event: error" not in response.text

    def test_no_message_is_persisted_when_the_gate_refuses(self, env) -> None:
        """The gate runs before the endpoint body, so nothing is written."""
        from sqlalchemy import func, select

        from alchymine.db.models import ChatMessage

        env.as_plan("free")
        _post_chat(env)

        async def _count() -> int:
            async with env._factory() as session:
                result = await session.execute(select(func.count()).select_from(ChatMessage))
                return int(result.scalar_one())

        assert env._loop.run_until_complete(_count()) == 0


class TestArtCapsStack:
    """Two independent caps on the same route, each able to trip alone."""

    def test_the_daily_cap_still_applies_under_the_allowance(self, env) -> None:
        env.as_plan("pro")
        cap = get_settings().daily_art_generations_per_user

        for _ in range(cap):
            assert _post_art(env).status_code == 201

        response = _post_art(env)
        assert response.status_code == 429
        assert response.json()["detail"]["code"] == "daily_art_cap_reached"

    def test_the_allowance_trips_before_the_daily_cap_is_touched(self, env) -> None:
        """A first-of-the-month request with no budget must not spend a slot."""
        from alchymine.db.usage_counters import METER_ART_GENERATIONS, get_count

        env.as_plan("pro")
        env.exhaust_month("pro")

        assert _post_art(env).status_code == 429

        async def _art_count() -> int:
            return await get_count(scope=OWNER_ID, meter=METER_ART_GENERATIONS)

        assert env._loop.run_until_complete(_art_count()) == 0

    def test_the_two_caps_report_different_codes(self, env) -> None:
        """The client tells them apart by code, so they must not collide."""
        env.as_plan("pro")
        for _ in range(get_settings().daily_art_generations_per_user):
            _post_art(env)
        daily = _post_art(env).json()["detail"]["code"]

        env.exhaust_month("pro")
        monthly = _post_art(env).json()["detail"]["code"]

        assert daily == "daily_art_cap_reached"
        assert monthly == "plan_allowance_reached"

    def test_the_logo_route_shares_both_caps(self, env) -> None:
        """Both art routes hit the same generator, so both share the bill."""
        env.as_plan("pro")
        for _ in range(get_settings().daily_art_generations_per_user):
            _post_art(env)

        assert _post_logo(env).status_code == 429


class TestOwnershipSurvivesTheDependencySwap:
    """The routes read the account now, not the raw JWT subject."""

    def test_a_stranger_still_cannot_read_someone_elses_pdf(self, env) -> None:
        env.add_report("rep-owned", user_id=OWNER_ID)
        env.as_plan("pro", user_id=STRANGER_ID)

        assert env.client.get("/api/v1/reports/rep-owned/pdf").status_code == 403

    def test_the_owner_still_can(self, env) -> None:
        env.add_report("rep-owned-2", user_id=OWNER_ID)
        env.as_plan("pro", user_id=OWNER_ID)

        assert env.client.get("/api/v1/reports/rep-owned-2/pdf").status_code == 200

    def test_a_report_is_created_against_the_account_id(self, env) -> None:
        from sqlalchemy import select

        env.as_plan("pro", user_id=STRANGER_ID)
        assert _post_report(env).status_code == 202

        async def _owner() -> str | None:
            async with env._factory() as session:
                result = await session.execute(select(Report.user_id))
                return result.scalars().first()

        assert env._loop.run_until_complete(_owner()) == STRANGER_ID

    def test_art_is_stored_against_the_account_id(self, env) -> None:
        from sqlalchemy import select

        from alchymine.db.models import GeneratedImage

        env.as_plan("pro", user_id=STRANGER_ID)
        assert _post_art(env).status_code == 201

        async def _owner() -> str | None:
            async with env._factory() as session:
                result = await session.execute(select(GeneratedImage.user_id))
                return result.scalars().first()

        assert env._loop.run_until_complete(_owner()) == STRANGER_ID


class TestMeterOutageIsNotAnUpsell:
    """Fail closed, but under the 503 that already exists for our faults."""

    @pytest.mark.parametrize(("name", "call"), METERED)
    def test_an_unreadable_meter_renders_503(self, env, name, call) -> None:
        env.as_plan("pro")

        with patch(
            "alchymine.db.usage_counters.get_count",
            new=AsyncMock(side_effect=RuntimeError("counters are unreachable")),
        ):
            response = call(env)

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "llm_temporarily_unavailable"

"""Tests for the ``Account`` value object and ``get_current_account()``.

``get_current_account`` is the entitlement-aware sibling of
``get_current_admin``: it decodes the JWT, re-reads the user from Postgres,
and hands back a frozen snapshot of what that account is allowed to do.

Two properties matter enough to pin with tests:

- **The plan comes from the database, never the token.** Access tokens live
  30 minutes and refresh tokens 7 days, so a plan claim baked into a JWT
  would give a cancelled subscriber a week of inference we are paying for.
- **A lapsed window degrades to free.** ``effective_plan`` reads the clock,
  so a subscription that ended stops costing money at the period end rather
  than at the user's next token refresh.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alchymine.api.auth import Account, create_access_token, get_current_account
from alchymine.db.base import Base
from alchymine.db.models import User

# ─── Helpers ──────────────────────────────────────────────────────────────


def _request() -> Request:
    """A bare ASGI request with no cookies, since these tests pass the token."""
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """An in-memory SQLite session with the schema created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _add_user(db: AsyncSession, **kwargs) -> User:
    user = User(**kwargs)
    db.add(user)
    await db.commit()
    return user


# ─── The dependency ───────────────────────────────────────────────────────


class TestGetCurrentAccount:
    """401 on an unusable token, 403 on a disabled account, Account otherwise."""

    async def test_no_token_is_401(self, db):
        with pytest.raises(HTTPException) as exc:
            await get_current_account(_request(), None, db)
        assert exc.value.status_code == 401

    async def test_malformed_token_is_401(self, db):
        with pytest.raises(HTTPException) as exc:
            await get_current_account(_request(), "not-a-jwt", db)
        assert exc.value.status_code == 401

    async def test_expired_token_is_401(self, db):
        await _add_user(db, id="u-exp", email="exp@test.com")
        token = create_access_token({"sub": "u-exp"}, expires_delta=timedelta(minutes=-5))

        with pytest.raises(HTTPException) as exc:
            await get_current_account(_request(), token, db)
        assert exc.value.status_code == 401

    async def test_refresh_token_is_rejected(self, db):
        """Only access tokens open a gated surface."""
        from alchymine.api.auth import create_refresh_token

        await _add_user(db, id="u-ref", email="ref@test.com")

        with pytest.raises(HTTPException) as exc:
            await get_current_account(_request(), create_refresh_token({"sub": "u-ref"}), db)
        assert exc.value.status_code == 401

    async def test_missing_user_row_is_401(self, db):
        """A validly signed token for a deleted account is not authenticated."""
        token = create_access_token({"sub": "ghost"})

        with pytest.raises(HTTPException) as exc:
            await get_current_account(_request(), token, db)
        assert exc.value.status_code == 401

    async def test_disabled_account_is_403(self, db):
        """Same split as get_current_admin: known user, revoked access."""
        await _add_user(db, id="u-off", email="off@test.com", is_active=False)
        token = create_access_token({"sub": "u-off"})

        with pytest.raises(HTTPException) as exc:
            await get_current_account(_request(), token, db)
        assert exc.value.status_code == 403

    async def test_valid_user_returns_account(self, db):
        period_end = datetime.now(UTC) + timedelta(days=20)
        await _add_user(
            db,
            id="u-pro",
            email="pro@test.com",
            plan="pro",
            plan_status="active",
            plan_period_end=period_end,
        )
        token = create_access_token({"sub": "u-pro"})

        account = await get_current_account(_request(), token, db)

        assert isinstance(account, Account)
        assert account.user_id == "u-pro"
        assert account.email == "pro@test.com"
        assert account.plan == "pro"
        assert account.plan_status == "active"
        assert account.is_admin is False
        assert account.effective_plan == "pro"

    async def test_plan_is_read_from_the_database_not_the_token(self, db):
        """A stale or forged plan claim in the JWT changes nothing."""
        await _add_user(db, id="u-free", email="free@test.com", plan="free")
        token = create_access_token({"sub": "u-free", "plan": "founding"})

        account = await get_current_account(_request(), token, db)

        assert account.plan == "free"
        assert account.effective_plan == "free"

    async def test_admin_flag_travels_on_the_account(self, db):
        await _add_user(db, id="u-adm", email="adm@test.com", is_admin=True)
        token = create_access_token({"sub": "u-adm"})

        account = await get_current_account(_request(), token, db)
        assert account.is_admin is True


# ─── effective_plan ───────────────────────────────────────────────────────


def _account(**kwargs) -> Account:
    defaults = {
        "user_id": "u-1",
        "email": "u@test.com",
        "plan": "pro",
        "plan_status": "active",
        "is_admin": False,
        "plan_period_end": None,
        "trial_ends_at": None,
    }
    return Account(**{**defaults, **kwargs})


class TestEffectivePlan:
    """A paid plan whose window has closed is a free plan."""

    def test_no_period_end_keeps_the_plan(self):
        """Founding (lifetime) and beta have no window to lapse."""
        assert _account(plan="founding").effective_plan == "founding"

    def test_future_period_end_keeps_the_plan(self):
        future = datetime.now(UTC) + timedelta(days=1)
        assert _account(plan="pro", plan_period_end=future).effective_plan == "pro"

    def test_past_period_end_degrades_to_free(self):
        past = datetime.now(UTC) - timedelta(seconds=1)
        assert _account(plan="pro", plan_period_end=past).effective_plan == "free"

    def test_lapsed_blueprint_window_degrades_to_free(self):
        """A $33 one-time purchase buys 33 days of COGS, not a perpetual one."""
        past = datetime.now(UTC) - timedelta(days=1)
        assert _account(plan="blueprint", plan_period_end=past).effective_plan == "free"

    def test_naive_period_end_is_treated_as_utc(self):
        """SQLite hands back naive datetimes; comparing them must not explode."""
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
        assert _account(plan="pro", plan_period_end=past).effective_plan == "free"

    def test_free_stays_free(self):
        assert _account(plan="free").effective_plan == "free"

    def test_account_is_immutable(self):
        """The snapshot must not drift mid-request."""
        from dataclasses import FrozenInstanceError

        account = _account()
        with pytest.raises(FrozenInstanceError):
            account.plan = "founding"  # type: ignore[misc]

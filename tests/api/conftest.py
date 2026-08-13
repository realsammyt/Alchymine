"""Shared fixtures for API tests.

Resets the in-memory rate limiter between tests so that tests running
in sequence do not hit the 100 request/minute ceiling.

Also provides a global override of get_current_user so that all API
tests receive an authenticated test user without needing a real JWT.
"""

from __future__ import annotations

import asyncio

import pytest

from sqlalchemy.ext.asyncio import create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import Account, get_current_account, get_current_user
from alchymine.api.deps import set_db_engine
from alchymine.api.main import app
from alchymine.db.models import UsageCounter, UsageRecord

# The test user sub used across API tests.
TEST_USER_ID = "user-1"

# The plan the default test account is on. Beta rather than free: every
# account that exists today is a beta tester (migration 0017), and a free
# default would turn every pre-existing test of a paid surface into an
# assertion about the 402 upsell instead of about the route.
TEST_USER_PLAN = "beta"


async def _test_current_user() -> dict:
    """Return a fake authenticated user for tests."""
    return {"sub": TEST_USER_ID, "email": "test@example.com"}


def test_account(user_id: str = TEST_USER_ID, plan: str = TEST_USER_PLAN) -> Account:
    """Build the entitlement snapshot the gated routes read."""
    return Account(
        user_id=user_id,
        email=f"{user_id}@example.com",
        plan=plan,
        plan_status="active",
        is_admin=False,
        plan_period_end=None,
        trial_ends_at=None,
    )


def override_account(user_id: str, plan: str = TEST_USER_PLAN) -> None:
    """Call the gated routes as *user_id*, on *plan*.

    Modules that override ``get_current_user`` to switch identity need
    this alongside it: the four paid chokepoints read the account, not
    the raw JWT subject, so overriding only the token dependency would
    leave them acting as the default test user.
    """
    app.dependency_overrides[get_current_account] = lambda: test_account(user_id, plan)


async def _test_current_account() -> Account:
    """Return a fake entitled account, attributing spend the way the real one does."""
    from alchymine.llm.attribution import set_attribution

    # The production dependency sets this, and the ledger reads it to name
    # the owner of a paid call. Overriding without it would make every
    # test row unattributed and hide attribution regressions.
    set_attribution(user_id=TEST_USER_ID, surface=None, request_id=None)
    return test_account()


@pytest.fixture(autouse=True)
def _override_auth(request: pytest.FixtureRequest) -> None:
    """Override the auth dependencies for all API tests except test_auth.py.

    The auth test module validates real JWT handling, so it must not have
    get_current_user overridden — the token check needs to be live there.

    ``get_current_account`` is overridden alongside it because the four
    paid chokepoints depend on it through their plan gate, and it reads
    the user from Postgres, which most route tests do not stand up.
    """
    # Skip the override for the auth integration tests
    if "test_auth" in request.fspath.basename:
        yield
        return

    app.dependency_overrides[get_current_user] = _test_current_user
    app.dependency_overrides[get_current_account] = _test_current_account
    yield
    # Only clear the auth overrides; other overrides (e.g. DB session) are
    # managed by their own fixtures.
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_account, None)


@pytest.fixture(scope="session")
def _meter_loop():
    """One event loop for every counters engine in the session.

    The engines themselves stay per-test (an in-memory SQLite database
    dies with its engine, and the app's own lifespan shutdown disposes
    whatever engine is current, so a shared one would vanish on the
    first TestClient teardown). The *loop* is shared because closing one
    per test raced aiosqlite's connection worker: the worker calls back
    into the loop shortly after ``dispose()`` returns, and a closed loop
    turns that into "Event loop is closed" from a thread nobody is
    watching. Kept open until every engine is gone, there is nothing to
    race.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def _readable_spend_meter(_meter_loop) -> None:
    """Give the plan gate an empty, readable spend meter by default.

    The four paid chokepoints now read a monthly spend counter through
    the ``deps`` engine singleton, and that read FAILS CLOSED: an
    unreachable counter is a 503, not a free pass. Without an engine the
    singleton would build one from ``DATABASE_URL`` and try to reach a
    real Postgres, so every route test would 503 on a database that is
    not there.

    Modules that stand up their own engine (``set_db_engine`` in their
    own fixture) override this one for the duration of the test and
    still get their own counters, because this runs first and theirs
    runs second.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(UsageCounter.__table__.create)
            await conn.run_sync(UsageRecord.__table__.create)

    _meter_loop.run_until_complete(_create())
    set_db_engine(engine)
    try:
        yield
    finally:
        set_db_engine(None)
        _meter_loop.run_until_complete(engine.dispose())


@pytest.fixture(autouse=True)
def _reset_guardrails() -> None:
    """Clear safety guardrail session counters before every test.

    The guardrails module tracks per-user operation counts in a global
    dict keyed by session/user ID.  Without clearing between tests,
    tests that create reports accumulate against the 3-per-hour limit
    and later tests get 429 responses.
    """
    from alchymine.safety.guardrails import reset_session

    reset_session(TEST_USER_ID)
    yield
    reset_session(TEST_USER_ID)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clear the rate limiter's request history before every test.

    The RateLimitMiddleware stores timestamps in ``_requests`` (a defaultdict).
    Clearing it ensures each test starts with a fresh budget.

    Also resets the per-user chat rate limiter introduced in #165.
    """
    from alchymine.api.routers.chat import reset_chat_rate_limit

    reset_chat_rate_limit()  # clear chat endpoint rate limiter

    for middleware in app.user_middleware:
        # middleware.cls is the class, middleware.kwargs holds init args
        pass  # user_middleware is the config, not the instances

    # Walk the middleware stack to find the live RateLimitMiddleware instance.
    # In Starlette, app.middleware_stack is the composed ASGI app; the actual
    # middleware objects are nested inside it.
    _clear_rate_limit_state(app.middleware_stack)


def _clear_rate_limit_state(obj: object) -> None:
    """Recursively walk the middleware stack to find and clear RateLimitMiddleware."""
    from alchymine.api.middleware import RateLimitMiddleware

    if isinstance(obj, RateLimitMiddleware):
        # Clear both the legacy _requests dict and the current _local_counts dict.
        requests_dict = getattr(obj, "_requests", None)
        if requests_dict is not None:
            requests_dict.clear()
        local_counts = getattr(obj, "_local_counts", None)
        if local_counts is not None:
            local_counts.clear()
        return

    # BaseHTTPMiddleware stores the next app in .app
    inner = getattr(obj, "app", None)
    if inner is not None and inner is not obj:
        _clear_rate_limit_state(inner)

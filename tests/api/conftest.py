"""Shared fixtures for API tests.

Resets the in-memory rate limiter between tests so that tests running
in sequence do not hit the 100 request/minute ceiling.

Also provides a global override of get_current_user so that all API
tests receive an authenticated test user without needing a real JWT.
"""

from __future__ import annotations

import pytest

from alchymine.api.auth import get_current_user
from alchymine.api.main import app

# The test user sub used across API tests.
TEST_USER_ID = "user-1"


async def _test_current_user() -> dict:
    """Return a fake authenticated user for tests."""
    return {"sub": TEST_USER_ID, "email": "test@example.com"}


@pytest.fixture(autouse=True)
def _override_auth(request: pytest.FixtureRequest) -> None:
    """Override get_current_user for all API tests except test_auth.py.

    The auth test module validates real JWT handling, so it must not have
    get_current_user overridden — the token check needs to be live there.
    """
    # Skip the override for the auth integration tests
    if "test_auth" in request.fspath.basename:
        yield
        return

    app.dependency_overrides[get_current_user] = _test_current_user
    yield
    # Only clear the auth override; other overrides (e.g. DB session) are
    # managed by their own fixtures.
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clear the rate limiter's request history before every test.

    The RateLimitMiddleware stores timestamps in ``_requests`` (a defaultdict).
    Clearing it ensures each test starts with a fresh budget.
    """
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

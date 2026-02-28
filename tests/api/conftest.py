"""Shared fixtures for API tests.

Resets the in-memory rate limiter between tests so that tests running
in sequence do not hit the 100 request/minute ceiling.
"""

from __future__ import annotations

import pytest

from alchymine.api.main import app


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
        obj._requests.clear()
        return

    # BaseHTTPMiddleware stores the next app in .app
    inner = getattr(obj, "app", None)
    if inner is not None and inner is not obj:
        _clear_rate_limit_state(inner)

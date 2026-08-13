"""Who a paid model call belongs to, carried on ContextVars.

The three egress sites that spend money — Claude generate, Claude stream,
Gemini image generation — sit deep under ``alchymine/llm/`` with no
request, no session and no user in scope. Something has to carry the user
id down to them so a ledger row can name an owner, and a ContextVar is the
only mechanism that survives the whole call chain (route dependency to
async generator to ``asyncio.gather`` branch) without threading an
argument through every function in between.

This module imports **nothing**. Both the API and the Celery worker import
it, and ``alchymine.db.usage_counters`` already documents the import cycle
that ``alchymine.api.deps`` creates, so a leaf is the only safe shape.

Three properties this relies on, all of them standard asyncio behaviour:

- **Async generators run in their caller's context.** Per-generator
  contexts were proposed in PEP 568 and never implemented, so a value set
  in a route handler is visible inside the ``StreamingResponse`` body that
  handler returns. That is what makes SSE chat attributable.
- **Task creation copies the current context.** ``asyncio.gather`` wraps
  each coroutine in a Task, so the five concurrent narrative calls in
  ``narrative.py`` all inherit the same user id.
- **A value set inside a task cannot leak out of it.** Each request runs
  in its own task with its own copied context, so nothing needs resetting
  between requests and one user's id can never be read by the next.

Threads are the exception: a new thread starts with a fresh, empty
context. ``alchymine.workers.tasks._run_async`` copies the context across
that boundary explicitly.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

# Surface values, mirroring usage_records.surface.
SURFACE_UNKNOWN = "unknown"

_user_id: ContextVar[str | None] = ContextVar("alchymine_user_id", default=None)
_surface: ContextVar[str | None] = ContextVar("alchymine_surface", default=None)
_request_id: ContextVar[str | None] = ContextVar("alchymine_request_id", default=None)


def set_attribution(
    *,
    user_id: str | None,
    surface: str | None,
    request_id: str | None = None,
) -> None:
    """Attribute everything this context does from here on to *user_id*.

    Called by ``get_current_account`` on the request path. ``request_id``
    comes from ``RequestIdMiddleware`` via ``request.state``; the Celery
    path leaves it ``None``, which is honest — there is no HTTP request.
    """
    _user_id.set(user_id)
    _surface.set(surface)
    _request_id.set(request_id)


def set_surface(surface: str | None) -> None:
    """Name the surface this context is about to spend on.

    Split from :func:`set_attribution` because the user id and the
    surface are learned in two different places: the auth dependency
    knows who is calling, and only the route knows what they are calling
    it for. Setting both at once from the route would mean re-reading
    the request id just to avoid clearing it.
    """
    _surface.set(surface)


def current_attribution() -> tuple[str | None, str | None, str | None]:
    """Return ``(user_id, surface, request_id)`` for the current context.

    All three are ``None`` when nothing has been set. The ledger treats
    that as unattributed spend: it records the row globally and warns,
    rather than blocking, because a missing ContextVar is an internal
    wiring defect and not a reason to take report generation down.
    """
    return _user_id.get(), _surface.get(), _request_id.get()


@contextmanager
def attributed(
    *,
    user_id: str | None,
    surface: str | None,
    request_id: str | None = None,
) -> Iterator[None]:
    """Scope attribution to a block, restoring what was there before.

    Used where there is no request to hang the value on — the Celery
    report task wraps its narrative section with this.
    """
    tokens = (
        _user_id.set(user_id),
        _surface.set(surface),
        _request_id.set(request_id),
    )
    try:
        yield
    finally:
        _user_id.reset(tokens[0])
        _surface.reset(tokens[1])
        _request_id.reset(tokens[2])

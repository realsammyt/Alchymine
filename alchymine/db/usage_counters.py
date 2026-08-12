"""Atomic usage counters — the primitive under every cost ceiling.

Counters are keyed by ``(scope, meter, period_key)``:

``scope``
    ``"global"`` for a system-wide breaker, or a user id for a per-user cap.
``meter``
    What is being counted, e.g. ``"llm_calls"`` or ``"art_generations"``.
``period_key``
    The UTC calendar date the count belongs to. This is what makes every
    ceiling reset at UTC midnight without a scheduled job.

Postgres is the source of truth. Increments run as a single
``INSERT .. ON CONFLICT .. DO UPDATE .. RETURNING`` so two workers racing
on the same counter cannot lose an increment to a read-modify-write gap.

There is deliberately no Redis cache in front of this. A cost meter that
can serve a stale "you still have budget" is worse than one extra
round-trip on a path that is about to make a paid API call.

Every ceiling FAILS CLOSED: if the counter cannot be read or written, the
caller is blocked rather than allowed through unmetered.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db.base import get_async_session_factory
from alchymine.db.models import UsageCounter

logger = logging.getLogger(__name__)

# Scope value used for system-wide counters (as opposed to per-user ones).
GLOBAL_SCOPE = "global"

# Meter names. Keep these stable — they are persisted in every row.
METER_LLM_CALLS = "llm_calls"
METER_ART_GENERATIONS = "art_generations"


class CostCeilingExceeded(RuntimeError):
    """Raised when a metered call must not proceed.

    Carries machine-readable fields so callers can render a structured
    "temporarily unavailable" state instead of a stack trace. Raising
    rather than returning a boolean is deliberate: a forgotten return
    value would silently mean "unlimited".
    """

    def __init__(
        self,
        *,
        meter: str,
        scope: str,
        retry_at: datetime,
        reason: str = "ceiling_reached",
    ) -> None:
        super().__init__(f"Cost ceiling reached for meter={meter!r} scope={scope!r} ({reason})")
        self.meter = meter
        self.scope = scope
        self.retry_at = retry_at
        self.reason = reason


# ─── Period helpers ─────────────────────────────────────────────────────


def current_period_key(now: datetime | None = None) -> str:
    """Return the UTC calendar date that *now* falls in, as ``YYYY-MM-DD``."""
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%d")


def next_period_start(now: datetime | None = None) -> datetime:
    """Return the next UTC midnight — when the current period's count resets."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    return (moment + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


# ─── Session plumbing ───────────────────────────────────────────────────


@asynccontextmanager
async def _counter_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session dedicated to counter writes.

    Counters always run in their own transaction rather than joining the
    caller's. A count must land whether or not the work it authorized
    later succeeds, and the LLM chokepoints that call this have no
    request-scoped session to borrow.
    """
    # Imported inside the function: alchymine.api.deps imports alchymine.db,
    # so a module-level import would close an import cycle. deps owns the
    # pooled singleton engine, which is what we want to reuse here.
    from alchymine.api.deps import get_db_engine

    factory = get_async_session_factory(get_db_engine())
    async with factory() as session:
        yield session


# ─── Counter operations ─────────────────────────────────────────────────


async def increment_and_get(
    *,
    scope: str,
    meter: str,
    period_key: str | None = None,
    amount: int = 1,
) -> int:
    """Add *amount* to a counter and return its new value, atomically.

    Raises whatever the database raises — callers that must fail closed
    should go through :func:`consume`.
    """
    key = period_key or current_period_key()

    async with _counter_session() as session:
        bind = session.get_bind()
        insert = sqlite_insert if bind.dialect.name == "sqlite" else pg_insert
        table = UsageCounter.__table__
        stmt = (
            insert(table)
            .values(scope=scope, meter=meter, period_key=key, count=amount)
            .on_conflict_do_update(
                index_elements=["scope", "meter", "period_key"],
                set_={"count": table.c.count + amount, "updated_at": datetime.now(UTC)},
            )
            .returning(table.c.count)
        )
        result = await session.execute(stmt)
        new_count = result.scalar_one()
        await session.commit()
        return int(new_count)


async def get_count(*, scope: str, meter: str, period_key: str | None = None) -> int:
    """Return the current value of a counter, or 0 if it has never been used."""
    key = period_key or current_period_key()

    async with _counter_session() as session:
        stmt = select(UsageCounter.count).where(
            UsageCounter.scope == scope,
            UsageCounter.meter == meter,
            UsageCounter.period_key == key,
        )
        result = await session.execute(stmt)
        return int(result.scalar_one_or_none() or 0)


async def consume(
    *,
    scope: str,
    meter: str,
    ceiling: int,
    period_key: str | None = None,
    amount: int = 1,
) -> int:
    """Record usage and block the caller once *ceiling* is passed.

    Call this immediately before the spend it meters, so a blocked call is
    never actually made. Returns the new count on success.

    Raises
    ------
    CostCeilingExceeded
        When the ceiling is already met, or when the counter itself could
        not be reached. The second case is the fail-closed path: an
        unreachable meter blocks spending instead of permitting it.
    """
    try:
        new_count = await increment_and_get(
            scope=scope, meter=meter, period_key=period_key, amount=amount
        )
    except Exception as exc:
        logger.error(
            "Cost meter unavailable (meter=%s scope=%s) — blocking the call: %s",
            meter,
            scope,
            exc,
        )
        raise CostCeilingExceeded(
            meter=meter,
            scope=scope,
            retry_at=next_period_start(),
            reason="meter_unavailable",
        ) from exc

    if new_count > ceiling:
        raise CostCeilingExceeded(
            meter=meter,
            scope=scope,
            retry_at=next_period_start(),
        )
    return new_count

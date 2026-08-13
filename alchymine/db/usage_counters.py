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

from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db.base import get_async_session_factory
from alchymine.db.models import UsageCounter

logger = logging.getLogger(__name__)

# Scope value used for system-wide counters (as opposed to per-user ones).
GLOBAL_SCOPE = "global"

# Meter names. Keep these stable — they are persisted in every row.
#
# The period shape is baked into the spend meter names on purpose.
# ``get_count(scope=user, meter="spend")`` with no period_key silently
# defaults to today's date key and would return 0 for a monthly meter,
# reading as "no spend" when the truth is "wrong row". Encoding `daily` and
# `monthly` in the name makes that mistake impossible to write.
METER_LLM_CALLS = "llm_calls"
METER_ART_GENERATIONS = "art_generations"
METER_SPEND_MICROS_DAILY = "spend_micros_daily"
METER_SPEND_MICROS_MONTHLY = "spend_micros_monthly"


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


def current_month_key(now: datetime | None = None) -> str:
    """Return the UTC calendar month that *now* falls in, as ``YYYY-MM``.

    The period key for monthly meters (per-user spend allowances). It fits
    the ``String(16)`` ``period_key`` column with room to spare.
    """
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m")


def next_month_start(now: datetime | None = None) -> datetime:
    """Return the next UTC month boundary — the retry_at for monthly meters.

    A monthly allowance that tells the user to try again tomorrow is a lie,
    so monthly ceilings report the first of next month instead.
    """
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    if moment.month == 12:
        return datetime(moment.year + 1, 1, 1, tzinfo=UTC)
    return datetime(moment.year, moment.month + 1, 1, tzinfo=UTC)


# ─── Ledger health ──────────────────────────────────────────────────────
#
# The cost ledger writes one row per delivered paid call. If that INSERT
# fails, we have spent money we cannot account for. Raising at the point of
# failure would not unspend it — it would only convert a logging fault into
# a user-visible one after the reply was already delivered — so the rule is:
# loud now, and block the NEXT cost-bearing call.
#
# Process-local by design. In the common case (Postgres unreachable) the
# counter read in check_ceiling hits the same database and fails closed on
# its own; this flag covers what that misses, an INSERT that fails for a
# non-connectivity reason such as a constraint violation while reads still
# succeed. Each process therefore tracks its own writes, which is exactly
# the blast radius that matters.

_ledger_degraded = False


def mark_ledger_degraded(reason: str) -> None:
    """Record that a ledger write failed, blocking the next metered call."""
    global _ledger_degraded
    if not _ledger_degraded:
        logger.error(
            "LEDGER_DEGRADED — a usage record could not be written (%s). Cost-bearing "
            "calls are blocked until a ledger write succeeds.",
            reason,
        )
    _ledger_degraded = True


def clear_ledger_degraded() -> None:
    """Record that a ledger write succeeded, reopening the gate."""
    global _ledger_degraded
    if _ledger_degraded:
        logger.info("LEDGER_RECOVERED — usage records are being written again.")
    _ledger_degraded = False


def ledger_is_degraded() -> bool:
    """Return True while the last ledger write in this process failed."""
    return _ledger_degraded


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
        stmt = (
            insert(UsageCounter)
            .values(scope=scope, meter=meter, period_key=key, count=amount)
            .on_conflict_do_update(
                index_elements=["scope", "meter", "period_key"],
                set_={"count": UsageCounter.count + amount, "updated_at": datetime.now(UTC)},
            )
            .returning(UsageCounter.count)
        )
        result = await session.execute(stmt)
        new_count = result.scalar_one()
        await session.commit()
        return int(new_count)


async def refund(
    *,
    scope: str,
    meter: str,
    period_key: str | None = None,
    amount: int = 1,
) -> None:
    """Give back usage that was charged but delivered nothing.

    Pairs with :func:`consume` on paths that must reserve the budget
    *before* spending it: charge first so an exhausted ceiling blocks the
    call, then hand the unit back if the call produced nothing.

    Clamps at zero rather than going negative, so a double refund cannot
    mint free allowance. A counter that does not exist yet is left alone.
    """
    key = period_key or current_period_key()

    async with _counter_session() as session:
        stmt = (
            update(UsageCounter)
            .where(
                UsageCounter.scope == scope,
                UsageCounter.meter == meter,
                UsageCounter.period_key == key,
            )
            .values(
                count=case(
                    (UsageCounter.count >= amount, UsageCounter.count - amount),
                    else_=0,
                ),
                updated_at=datetime.now(UTC),
            )
        )
        await session.execute(stmt)
        await session.commit()


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

    **Counts here are attempts, by design** (issue #220). The increment
    happens first and the ceiling check second, so a blocked call still
    moves the counter. That is deliberate: ``llm_calls`` and
    ``art_generations`` measure pressure on a resource, and a client in a
    retry loop against an exhausted cap *should* read as 40 attempts rather
    than 3. Suppressing blocked attempts would erase the abuse signal the
    meter exists for while changing no gate behaviour — once the count is
    past the ceiling, every later call is blocked however far it has
    drifted, and the counter resets at UTC midnight either way.

    Money is metered differently. Spend is never charged speculatively: the
    flow is :func:`check_ceiling`, then the paid call, then
    :func:`increment_and_get` with what it actually cost. See section 3 of
    ``docs/plans/2026-08-13-unit-economics.md``.

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


def _retry_at_for(period_key: str | None) -> datetime:
    """When the counter behind *period_key* resets.

    Inferred from the key's shape rather than the meter name: ``YYYY-MM`` is
    a monthly counter, anything else is the daily default.
    """
    if period_key is not None and len(period_key) == 7:
        return next_month_start()
    return next_period_start()


async def check_ceiling(
    *,
    scope: str,
    meter: str,
    ceiling: int,
    period_key: str | None = None,
) -> int:
    """Return the current count, raising if it is at or past *ceiling*.

    The read-only half of a spend meter. Does not increment: a ledger that
    counts money we did not spend is simply wrong, and it would produce
    false upsells. The caller checks, makes the paid call, then records what
    it actually cost.

    The cost of that ordering is a bounded overshoot — a call authorized at
    99% of budget still runs to completion — and the bound is concurrency,
    not one call: several callers can pass this read before any of them
    records. The report path fires five concurrent paid calls, so one report
    at the ceiling can overshoot by five calls' cost. The atomic count
    breaker, not this function, is the hard backstop for the pathological
    case.

    Raises
    ------
    CostCeilingExceeded
        When the ceiling is already met; when the counter cannot be read;
        or when a ledger write has failed since the last successful one. All
        three are the fail-closed direction — an unreadable or untrustworthy
        meter blocks spending rather than permitting it unmetered.
    """
    if ledger_is_degraded():
        logger.error(
            "Blocking a cost-bearing call (meter=%s scope=%s): the usage ledger is "
            "degraded, so spend cannot be accounted for.",
            meter,
            scope,
        )
        raise CostCeilingExceeded(
            meter=meter,
            scope=scope,
            retry_at=_retry_at_for(period_key),
            reason="meter_unavailable",
        )

    try:
        count = await get_count(scope=scope, meter=meter, period_key=period_key)
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
            retry_at=_retry_at_for(period_key),
            reason="meter_unavailable",
        ) from exc

    if count >= ceiling:
        raise CostCeilingExceeded(
            meter=meter,
            scope=scope,
            retry_at=_retry_at_for(period_key),
        )
    return count

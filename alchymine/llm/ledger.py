"""The dollar-denominated cost ledger.

``usage_counters`` answers "are we blocked". This module answers "what did
it cost". One ``usage_records`` row per delivered paid call, priced from
the model that actually served it, plus two running spend meters:

- ``global`` / ``spend_micros_daily`` — every call, attributed or not.
- ``<user_id>`` / ``spend_micros_monthly`` — attributed calls only.

Everything is in **micro-dollars**, never cents. Rounding a Haiku chat
turn up to a whole cent inflates it by 96%, which at the allowance level
means telling users they are out of budget at roughly half their real
usage. Cents are derived once, at aggregate time, with a ceiling.

Rows are written *after* the call returns, never before. We cannot price a
call before making it, and a ledger that counts money we did not spend
would produce false upsells.

:func:`record_usage` does not raise a failure into its caller. The reply
has already been delivered by the time it runs, so raising would convert a
bookkeeping failure into a user-visible fault without unspending anything.
Instead a failed write is logged at ERROR with the whole row as JSON — so
the spend is reconstructible — and marks the ledger degraded, which blocks
the *next* cost-bearing call at ``charge_paid_call``.

The write runs as a detached task under ``asyncio.shield``. A cancelled
caller (a browser that went away mid-stream, which is precisely when the
recording matters) would otherwise abandon the write at its first await:
``CancelledError`` is a ``BaseException`` and walks past every ``except
Exception`` net in this module. Cancellation still reaches the caller; only
the write is protected from it.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.config import get_settings
from alchymine.db.base import get_async_session_factory
from alchymine.db.models import UsageRecord
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_SPEND_MICROS_DAILY,
    METER_SPEND_MICROS_MONTHLY,
    clear_ledger_degraded,
    current_month_key,
    current_period_key,
    increment_and_get,
    ledger_is_degraded,
    mark_ledger_degraded,
)
from alchymine.llm.attribution import SURFACE_UNKNOWN, current_attribution

logger = logging.getLogger(__name__)

# Scope value for a call that reached an egress site with no attribution.
UNATTRIBUTED_SCOPE = "unattributed"

# Strong references to in-flight detached writes. Without this the event
# loop holds only a weak reference and a write can be garbage-collected
# mid-flight, which is a documented way to lose asyncio tasks silently.
_pending_writes: set[asyncio.Task[None]] = set()

__all__ = [
    "UNATTRIBUTED_SCOPE",
    "cost_micros",
    "flush_pending_writes",
    "ledger_is_degraded",
    "log_ledger_status",
    "record_usage",
]


def cost_micros(
    *,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
) -> int:
    """Price one Anthropic call in micro-dollars.

    All four usage fields are priced. Cache reads bill at 0.1x the base
    input price and 5-minute cache writes at 1.25x, so pricing only
    ``input_tokens`` and ``output_tokens`` would under-count every cached
    call the moment prompt caching is switched on.

    Integer arithmetic throughout, no floats, multiplying before dividing so
    the two floor divisions together truncate less than one micro-dollar per
    record. Negative token counts clamp to zero: a garbage usage field must
    not mint negative spend.
    """
    price_in, price_out = get_settings().llm_price_for(model)

    tokens_in = max(0, input_tokens)
    tokens_out = max(0, output_tokens)
    cache_read = max(0, cache_read_input_tokens)
    cache_write = max(0, cache_creation_input_tokens)

    return (
        tokens_in * price_in
        + tokens_out * price_out
        + (cache_read * price_in) // 10
        + (cache_write * price_in * 5) // 4
    )


@asynccontextmanager
async def _ledger_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session dedicated to ledger writes.

    Its own transaction, never the caller's: the record of a call that has
    already been paid for must land whether or not the surrounding work
    succeeds, and the egress sites have no request-scoped session anyway.

    Imported inside the function for the reason ``usage_counters`` spells
    out — ``alchymine.api.deps`` imports ``alchymine.db``, so a module-level
    import would close a cycle. deps owns the pooled singleton engine, which
    is what we want to reuse.
    """
    from alchymine.api.deps import get_db_engine

    factory = get_async_session_factory(get_db_engine())
    async with factory() as session:
        yield session


async def record_usage(
    *,
    meter: str,
    provider: str,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    images: int = 0,
    cost_micros_override: int | None = None,
    estimated: bool = False,
    surface: str | None = None,
) -> asyncio.Task[None] | None:
    """Write one ledger row for a delivered paid call and charge the meters.

    Parameters
    ----------
    meter:
        ``llm_calls`` or ``art_generations`` — what kind of unit this was.
    provider, model:
        ``anthropic``/``google`` and the exact model id that served the
        request. The Claude fallback chain can change the model mid-request,
        so callers pass what actually answered, not what they asked for.
    cost_micros_override:
        Pre-computed cost, for providers with no token accounting (Gemini
        images are a flat per-image figure). When ``None`` the cost is
        priced from the token counts.
    estimated:
        True when the token counts were inferred rather than reported — a
        client that disconnected mid-stream. These rows are a floor, not a
        measurement, and ``/admin/usage`` reports their share.
    surface:
        Overrides the ContextVar. Used where the call site knows better
        than the request scope does.

    Returns
    -------
    asyncio.Task | None
        The detached write, already awaited on the normal path. Callers
        ignore it; tests use it (or :func:`flush_pending_writes`) to wait
        for a write that outlived a cancelled caller.

    Raises only ``CancelledError``, and only when the caller's own scope is
    being cancelled — the write itself still completes. See the module
    docstring.
    """
    settings = get_settings()
    if not settings.usage_ledger_enabled:
        # A ledger that is switched off cannot be degraded, and leaving the
        # flag set would make the kill switch block every paid call with no
        # way to clear it. Turning the ledger off is how an operator stops a
        # write storm; it must not be the thing that takes the app down.
        clear_ledger_degraded()
        return None

    user_id, context_surface, request_id = current_attribution()
    resolved_surface = surface or context_surface or SURFACE_UNKNOWN

    if cost_micros_override is not None:
        cost = max(0, cost_micros_override)
    else:
        cost = cost_micros(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
        )

    row: dict[str, Any] = {
        "user_id": user_id,
        "scope": user_id or UNATTRIBUTED_SCOPE,
        "surface": resolved_surface,
        "meter": meter,
        "provider": provider,
        "model": model,
        "input_tokens": max(0, input_tokens),
        "output_tokens": max(0, output_tokens),
        "cache_read_input_tokens": max(0, cache_read_input_tokens),
        "cache_creation_input_tokens": max(0, cache_creation_input_tokens),
        "images": max(0, images),
        "cost_micros": cost,
        "estimated": estimated,
        "period_key": current_period_key(),
        "month_key": current_month_key(),
        "request_id": request_id,
    }

    if user_id is None:
        # Not fail-closed on purpose. The fail-closed rail is about the meter
        # being unreachable: if we cannot read a counter we cannot know
        # whether there is budget, so we block. A missing ContextVar is a
        # different thing — an internal wiring defect — and blocking on it
        # would take down report generation because of a logging bug. The
        # per-user allowance simply cannot be enforced for this call, which
        # is why the global meter below still gets charged.
        logger.warning(
            "Unattributed paid call recorded (surface=%s request_id=%s model=%s "
            "cost_micros=%d) — no user id was set at the egress site.",
            resolved_surface,
            request_id,
            model,
            cost,
        )

    return await _write_detached(row)


async def _write_detached(row: dict[str, Any]) -> asyncio.Task[None] | None:
    """Run the write as its own task, then wait for it under a shield.

    The point is the disconnect path. When a browser goes away mid-stream,
    uvicorn cancels the request task, and a plain ``await`` in the recording
    code would raise ``CancelledError`` before the row ever reached the
    database — losing the cost of a call we were billed for in full.

    A separate task does not inherit the caller's cancellation, and
    ``shield`` means the caller still waits for the write on the normal path
    while a cancelled caller lets it finish in the background. Task creation
    copies the current context, so attribution survives either way (the row
    is fully resolved before this point regardless).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - every caller is async today
        await _persist(row)
        return None

    task = loop.create_task(_persist(row))
    _pending_writes.add(task)
    task.add_done_callback(_pending_writes.discard)
    await asyncio.shield(task)
    return task


async def _persist(row: dict[str, Any]) -> None:
    """Write the row and charge both meters, declaring recovery only if both land."""
    wrote_row = await _write_row(row)
    charged = await _charge_spend_meters(row)
    if wrote_row and charged:
        # Only now. Clearing after the INSERT alone would announce recovery
        # while the meters are still failing, which after the block in
        # charge_paid_call would let calls through against a counter that is
        # not moving — the exact "spending against a number we know is
        # wrong" case the flag exists to prevent.
        clear_ledger_degraded()


async def flush_pending_writes() -> None:
    """Wait for every detached ledger write to finish.

    For shutdown and for tests. A write that outlived its cancelled caller
    is still in flight, and dropping it on the way out would lose exactly
    the spend this design went out of its way to capture.
    """
    while _pending_writes:
        await asyncio.gather(*list(_pending_writes), return_exceptions=True)


def log_ledger_status(component: str) -> None:
    """Announce at startup whether spend is being recorded at all.

    A disabled ledger is a silent blackout otherwise: every paid call still
    goes out, nothing is written, and the first sign of trouble is an empty
    usage table weeks later when somebody asks what the beta cost.
    """
    if get_settings().usage_ledger_enabled:
        logger.info("Usage ledger enabled (%s) — paid calls are being recorded.", component)
        return
    logger.warning(
        "USAGE LEDGER DISABLED (%s) — paid calls are NOT being recorded. Spend is "
        "going out unmetered and unattributed. Set USAGE_LEDGER_ENABLED=true and "
        "restart to turn recording back on.",
        component,
    )


async def _write_row(row: dict[str, Any]) -> bool:
    """INSERT the ledger row. Returns True on success.

    On failure the whole row goes to the log as JSON and the ledger is
    marked degraded. A cancellation gets the same bookkeeping — the spend
    stays reconstructible — and is then re-raised, because swallowing it
    would break cancellation for whoever is unwinding.
    """
    try:
        async with _ledger_session() as session:
            session.add(UsageRecord(**row))
            await session.commit()
    except BaseException as exc:  # noqa: BLE001 - see docstring
        _degrade("insert failed", row, exc)
        if not isinstance(exc, Exception):
            raise
        return False
    return True


async def _charge_spend_meters(row: dict[str, Any]) -> bool:
    """Add this call's cost to the global daily and per-user monthly meters.

    The global meter is charged for every call including unattributed ones,
    so spend we cannot name still cannot escape the budget. The per-user
    meter is skipped when there is no user to charge.
    """
    cost = int(row["cost_micros"])
    try:
        await increment_and_get(
            scope=GLOBAL_SCOPE,
            meter=METER_SPEND_MICROS_DAILY,
            period_key=row["period_key"],
            amount=cost,
        )
        if row["user_id"] is not None:
            await increment_and_get(
                scope=str(row["user_id"]),
                meter=METER_SPEND_MICROS_MONTHLY,
                period_key=row["month_key"],
                amount=cost,
            )
    except BaseException as exc:  # noqa: BLE001 - see _write_row
        # Same class of loss as a failed INSERT: spend that happened is now
        # invisible to the ceiling that is supposed to bound it, so the next
        # cost-bearing call blocks rather than spending against a number we
        # know is wrong.
        _degrade("spend meter increment failed", row, exc)
        if not isinstance(exc, Exception):
            raise
        return False
    return True


def _degrade(reason: str, row: dict[str, Any], exc: BaseException) -> None:
    """Log the whole row as JSON, then block the next cost-bearing call."""
    logger.error(
        "LEDGER_WRITE_FAILED reason=%s error=%s row=%s",
        reason,
        exc,
        json.dumps(row, default=str, sort_keys=True),
    )
    mark_ledger_degraded(reason)

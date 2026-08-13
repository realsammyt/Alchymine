"""The monthly budget alert, and the kill switch that deliberately is not here.

The daily ceiling in ``cost_guard`` is a runaway stop: it blocks calls. The
monthly budget is a different instrument. Crossing 80% of it logs at ERROR
and stops nothing, because an automatic monthly cutoff converts an
overspend into an outage of unknown length, potentially weeks, and the
person who should make that call is a human looking at the number. Design
section 7.1 of ``docs/plans/2026-08-13-unit-economics.md``.

**Where the check runs, and why here.** It rides the ledger's post-write
path rather than ``GET /admin/usage``, because an alert that only fires
when an admin happens to open a page is not an alert: by then they are
already reading the number it would have told them. The endpoint still
reports month-to-date spend and percent of budget on every request, so the
two agree; this module is what puts a line in the log without anyone
looking.

**And why that is affordable.** One aggregate per paid call would be a real
cost on a hot path. So the read is throttled to at most one per process per
``_CHECK_MIN_INTERVAL_SECONDS``, and each threshold announces once per
month per process. The worst case is a five-minute delay on a number that
moves over weeks.

Source of truth is ``usage_records``, the same table the admin readout
sums, so the alert and the page can never disagree about the month.
"""

from __future__ import annotations

import logging
import threading
from time import monotonic

from sqlalchemy import func, select

from alchymine.config import get_settings
from alchymine.db.models import UsageRecord
from alchymine.db.usage_counters import current_month_key

logger = logging.getLogger(__name__)

__all__ = ["MONTHLY_ALERT_FRACTION", "check_monthly_budget", "reset_budget_alerts"]

# Crossing this share of the monthly budget is the thing worth saying out
# loud. 80% leaves enough month to react in without crying wolf at every
# busy week.
MONTHLY_ALERT_FRACTION = 0.8

# The two moments worth a separate line: the warning, and the fact.
_ALERT_TIERS: tuple[tuple[int, float], ...] = (
    (80, MONTHLY_ALERT_FRACTION),
    (100, 1.0),
)

# How often the aggregate may actually run. Not an env var: it trades log
# latency against query load on a number that moves over weeks, and no
# deployment has a reason to want a different answer.
_CHECK_MIN_INTERVAL_SECONDS = 300.0

# Guarded by a lock rather than trusting asyncio's single thread: the
# Celery path runs its coroutines in a worker thread, so two threads really
# can reach this at once. Same reasoning as the ledger's degraded state.
_lock = threading.Lock()
_last_check_at: float | None = None
_announced: set[tuple[str, int]] = set()


def reset_budget_alerts() -> None:
    """Forget the throttle and every announcement. For tests and shutdown."""
    global _last_check_at
    with _lock:
        _last_check_at = None
        _announced.clear()


def _claim_check(force: bool) -> bool:
    """Return True if this caller should run the aggregate now."""
    global _last_check_at
    now = monotonic()
    with _lock:
        if not force and _last_check_at is not None:
            if now - _last_check_at < _CHECK_MIN_INTERVAL_SECONDS:
                return False
        _last_check_at = now
        return True


def _claim_announcement(month_key: str, threshold: int) -> bool:
    """Return True the first time *threshold* is crossed in *month_key*."""
    with _lock:
        key = (month_key, threshold)
        if key in _announced:
            return False
        _announced.add(key)
        return True


async def _month_to_date_micros(month_key: str) -> int:
    """Sum every recorded micro-dollar in *month_key*."""
    # Imported inside the function for the reason usage_counters spells out:
    # alchymine.api.deps imports alchymine.db, so a module-level import
    # would close a cycle.
    from alchymine.api.deps import get_db_engine
    from alchymine.db.base import get_async_session_factory

    factory = get_async_session_factory(get_db_engine())
    async with factory() as session:
        result = await session.execute(
            select(func.coalesce(func.sum(UsageRecord.cost_micros), 0)).where(
                UsageRecord.month_key == month_key
            )
        )
        return int(result.scalar_one())


async def check_monthly_budget(*, force: bool = False) -> None:
    """Log at ERROR when month-to-date spend crosses a budget threshold.

    Blocks nothing, ever. Set *force* to skip the interval throttle (tests,
    and the admin readout, which has already paid for the read).

    Never raises. This runs on the path that records a call the user has
    already been served, so a failure here must not become their problem —
    it is logged and dropped.
    """
    settings = get_settings()
    budget_micros = settings.monthly_llm_spend_budget_micros()
    if budget_micros <= 0:
        # Nothing to be a percentage of. A zero budget already blocks every
        # paid call through the daily ceiling, which is loud on its own.
        return

    if not _claim_check(force):
        return

    month_key = current_month_key()
    try:
        spent = await _month_to_date_micros(month_key)
    except Exception as exc:  # noqa: BLE001 - see docstring
        logger.warning(
            "Could not read month-to-date spend for the budget alert (%s): %s",
            month_key,
            exc,
        )
        return

    pct = spent * 100.0 / budget_micros
    for threshold, fraction in _ALERT_TIERS:
        if spent < budget_micros * fraction:
            continue
        if not _claim_announcement(month_key, threshold):
            continue
        logger.error(
            "COST_BUDGET_ALERT threshold=%d%% month=%s spend_micros=%d budget_micros=%d "
            "pct_of_budget=%.1f — month-to-date LLM spend has crossed %d%% of the monthly "
            "budget. Nothing has been stopped: there is no automatic monthly cutoff, "
            "because that would turn an overspend into an outage of unknown length. "
            "Read GET /admin/usage and decide.",
            threshold,
            month_key,
            spent,
            budget_micros,
            pct,
            threshold,
        )

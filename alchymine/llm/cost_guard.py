"""Global daily circuit breaker for paid LLM egress.

Every chokepoint that spends money with an external model provider —
Claude generate, Claude stream, Gemini image generation — charges one
call against a single shared daily counter before it goes out. One
counter, not one per vendor, because the bill is one number.

The breaker counts calls rather than tokens or dollars. That is enough to
stop the failure modes it exists for (a retry loop, a leaked key, a
scripted client hammering an endpoint overnight) without building a spend
ledger. See ``Settings.global_daily_llm_call_ceiling``.

Callers must let :class:`CostCeilingExceeded` propagate. Catching it into
a fallback would answer the user with canned text, and catching it into a
``None`` would render a placeholder, while the real situation is that
spending is capped and somebody needs to know.
"""

from __future__ import annotations

import logging

from alchymine.config import get_settings
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_LLM_CALLS,
    CostCeilingExceeded,
    consume,
    ledger_is_degraded,
    next_period_start,
)

logger = logging.getLogger(__name__)


async def charge_paid_call() -> None:
    """Charge one paid model call against the global daily breaker.

    Call this immediately before the egress so a blocked call is never
    actually made.

    Raises
    ------
    CostCeilingExceeded
        When the day's ceiling is spent, when the meter itself is
        unreachable, or when the last ledger write failed (all fail closed).
    """
    settings = get_settings()

    # A ledger that could not record the previous call cannot account for
    # this one either, and spending money we cannot account for is the thing
    # this whole mechanism exists to prevent. The block is skipped when the
    # ledger is switched off: an operator who disables it has decided to fly
    # without spend accounting for a while, and a flag that a disabled
    # ledger can no longer clear would turn that switch into an outage.
    if settings.usage_ledger_enabled and ledger_is_degraded():
        logger.error(
            "COST_BREAKER_TRIPPED reason=ledger_degraded — the last usage record could "
            "not be written, so paid model calls are blocked until a write succeeds "
            "or the degraded window lapses"
        )
        raise CostCeilingExceeded(
            meter=METER_LLM_CALLS,
            scope=GLOBAL_SCOPE,
            # A "check back then" hint rather than a promise: recovery
            # actually happens on the next successful write, which is
            # usually much sooner than the period rollover.
            retry_at=next_period_start(),
            reason="meter_unavailable",
        )

    try:
        await consume(
            scope=GLOBAL_SCOPE,
            meter=METER_LLM_CALLS,
            ceiling=settings.global_daily_llm_call_ceiling,
        )
    except CostCeilingExceeded as exc:
        # Logged at ERROR with an explicit marker: this is a business
        # event someone should act on, not the routine per-IP throttling
        # that the rate-limit middleware emits all day.
        logger.error(
            "COST_BREAKER_TRIPPED reason=%s retry_at=%s — paid model calls are blocked "
            "until the daily counter resets",
            exc.reason,
            exc.retry_at.isoformat(),
        )
        raise

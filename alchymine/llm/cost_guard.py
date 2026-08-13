"""Global daily circuit breaker for paid LLM egress.

Every chokepoint that spends money with an external model provider —
Claude generate, Claude stream, Gemini image generation — passes through
this one function before it goes out. One guard, not one per vendor,
because the bill is one number.

Two global breakers live here, and they measure different things:

**Calls.** The original breaker from PR #214. Enough on its own to stop a
retry loop, a leaked key, or a scripted client hammering an endpoint
overnight. See ``Settings.global_daily_llm_call_ceiling``.

**Dollars.** The daily slice of the monthly budget, derived from
``Settings.daily_global_spend_ceiling_micros``. At $15/day and roughly a
cent a call, spend binds first for typical traffic; the 2000-call ceiling
binds first only for unusually cheap calls, which is exactly the case a
dollar ceiling would miss. Neither replaces the other, so the count breaker
stays as the outer backstop.

The spend gate is a read, never a charge: money is metered on delivery by
``alchymine.llm.ledger``, because we cannot price a call before making it.
The cost of that ordering is a bounded overshoot, and the bound is
concurrency rather than one call — see :func:`check_ceiling`.

Only global breakers belong here. Per-user entitlement and allowance live
at the route layer (``alchymine.api.entitlements``) and render as a 402 or
429 upsell; what trips in this module is nobody's fault and renders as a
503 that clears on a schedule we can name.

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
    METER_SPEND_MICROS_DAILY,
    CostCeilingExceeded,
    check_ceiling,
    claim_ledger_admission,
    consume,
    current_period_key,
    next_period_start,
)

logger = logging.getLogger(__name__)


async def charge_paid_call() -> None:
    """Charge one paid model call against the global daily breakers.

    Call this immediately before the egress so a blocked call is never
    actually made.

    Three gates, in this order, and the order is load-bearing:

    1. **Ledger health.** A ledger that could not record the previous call
       cannot account for this one either.
    2. **The call count.** Charged, not just read, so a blocked attempt
       still moves the counter and a retry loop still shows up as one.
    3. **The daily spend ceiling.** Read only. Money is recorded on
       delivery, so there is nothing to charge here.

    Spend is checked last because a call the count breaker already refused
    should not also be priced, and because a call refused on dollars should
    still register as an attempt on the count meter.

    Raises
    ------
    CostCeilingExceeded
        When the day's call ceiling is spent, when the day's dollar ceiling
        is spent, when either meter is unreachable, or when the last ledger
        write failed. Every one of those fails closed.
    """
    settings = get_settings()

    # A ledger that could not record the previous call cannot account for
    # this one either, and spending money we cannot account for is the thing
    # this whole mechanism exists to prevent. This is the only place that
    # claims the half-open probe, which is why the ledger check sits here
    # rather than in check_ceiling: one gate, one claim per call.
    #
    # The block is skipped when the ledger is switched off: an operator who
    # disables it has decided to fly without spend accounting for a while,
    # and a flag that a disabled ledger can no longer clear would turn that
    # switch into an outage.
    if settings.usage_ledger_enabled and not claim_ledger_admission():
        logger.error(
            "COST_BREAKER_TRIPPED reason=ledger_degraded — the last usage record could "
            "not be written, so paid model calls are blocked until a probe call's "
            "write succeeds"
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
            "COST_BREAKER_TRIPPED meter=%s reason=%s retry_at=%s — paid model calls are "
            "blocked until the daily counter resets",
            METER_LLM_CALLS,
            exc.reason,
            exc.retry_at.isoformat(),
        )
        raise

    ceiling_micros = settings.daily_global_spend_ceiling_micros()
    try:
        await check_ceiling(
            scope=GLOBAL_SCOPE,
            meter=METER_SPEND_MICROS_DAILY,
            ceiling=ceiling_micros,
            period_key=current_period_key(),
        )
    except CostCeilingExceeded as exc:
        logger.error(
            "COST_BREAKER_TRIPPED meter=%s reason=%s ceiling_micros=%d retry_at=%s — the "
            "day's share of the monthly LLM budget is spent, so paid model calls are "
            "blocked until the counter resets. Raise MONTHLY_LLM_SPEND_BUDGET_USD (or "
            "DAILY_SPEND_HEADROOM_FACTOR) and restart if this is legitimate traffic.",
            METER_SPEND_MICROS_DAILY,
            exc.reason,
            ceiling_micros,
            exc.retry_at.isoformat(),
        )
        raise

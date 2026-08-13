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
)

logger = logging.getLogger(__name__)


async def charge_paid_call() -> None:
    """Charge one paid model call against the global daily breaker.

    Call this immediately before the egress so a blocked call is never
    actually made.

    Raises
    ------
    CostCeilingExceeded
        When the day's ceiling is spent, or when the meter itself is
        unreachable (fail closed).
    """
    try:
        await consume(
            scope=GLOBAL_SCOPE,
            meter=METER_LLM_CALLS,
            ceiling=get_settings().global_daily_llm_call_ceiling,
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

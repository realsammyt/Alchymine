"""Per-plan entitlement and monthly allowance gates for the paid surfaces.

Two kinds of "no" exist in this codebase and they are deliberately kept
apart (design section 7.2, ``docs/plans/2026-08-13-unit-economics.md``):

**The global breakers** live in ``charge_paid_call`` and belong to us.
Nobody did anything wrong, the limit clears on a schedule we can name,
and it renders as a 503 wait state.

**This module** owns what is specific to one account: whether their plan
includes a paid surface at all, and whether this month's allowance is
spent. It renders 402 or 429 with an upgrade url, because a quota
rejection is a sales moment rather than a fault. The frontend switches on
``detail.code`` and shows these yellow, never red.

Two orderings here are load-bearing:

- **Entitlement is checked before the meter.** Free has an allowance of
  zero, so an allowance-first gate would tell a free user they had used
  up the nothing they were given. Upgrading is the answer, so 402 is the
  answer.
- **``meter_unavailable`` is re-raised, not converted.** An unreadable
  counter still blocks the call, but it is our outage and not this
  user's budget, so it stays on the 503 path instead of becoming an
  upsell.

Spend is read, never charged, here: the ledger records what a call
actually cost after it is delivered (``alchymine/llm/ledger.py``). That
ordering means a call authorized at 99% of an allowance still completes,
which is the accepted overshoot documented on :func:`check_ceiling`.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status

from alchymine.api.auth import Account, get_current_account
from alchymine.config import get_settings
from alchymine.db.usage_counters import (
    METER_SPEND_MICROS_MONTHLY,
    CostCeilingExceeded,
    check_ceiling,
    current_month_key,
)
from alchymine.llm.attribution import set_surface

logger = logging.getLogger(__name__)

# Where a refused user goes to fix it. Sent in the body rather than
# hardcoded in the frontend so the path can move without a redeploy of
# both halves.
UPGRADE_URL = "/pricing"

CODE_UPGRADE_REQUIRED = "plan_upgrade_required"
CODE_ALLOWANCE_REACHED = "plan_allowance_reached"

# Allowances are configured in cents because that is what a human reads;
# the meters count micro-dollars because per-call cents would round a
# half-cent chat turn up to a whole one and tell users they were out of
# budget at roughly half their real usage.
MICROS_PER_CENT = 10_000


def allowance_micros_for(plan: str) -> int:
    """Return *plan*'s spend allowance in micro-dollars, per calendar month.

    **Every plan is metered by UTC calendar month in v1, including
    blueprint.** The design says two different things about this:
    section 2.2 describes blueprint's 99 cents as "per 33-day window",
    while section 3.3 defines exactly one monthly period key shape,
    ``YYYY-MM``, which is what the ledger writes. This resolves in favour
    of 3.3.

    The consequence is real and accepted: a 33-day window that straddles
    a month boundary has its meter reset partway through, so such a buyer
    can spend up to two allowances inside one window. The leak is bounded
    at one extra allowance per sale (99 provisional cents), there is no
    purchase flow yet to produce one, and every figure here is revisited
    once beta data exists. Building a second, window-keyed meter to close
    a 99-cent hole before anything can buy it is not the trade.

    ``plan_period_end`` still bounds the *duration* of the grant: once
    the window closes, ``Account.effective_plan`` degrades to free and
    the entitlement gate refuses outright. So the exposure is bounded in
    time regardless of how the meter resets.

    Pinned by ``TestBlueprintIsMeteredByCalendarMonth``. Revisit with the
    provisional-numbers register (design section 10).
    """
    return get_settings().allowance_cents_for(plan) * MICROS_PER_CENT


def _envelope(
    *,
    code: str,
    message: str,
    plan: str,
    retry_at: str | None,
    meter: str | None,
) -> dict[str, str | None]:
    """The response body both refusals share.

    The keys are identical across 402 and 429 so the frontend has one
    shape to parse and switches on ``code`` rather than on status. An
    entitlement refusal carries ``retry_at`` and ``meter`` as ``None``
    rather than omitting them: waiting does not fix a plan, and no meter
    is what refused, so inventing values for those fields would be a
    small lie the client would then render.
    """
    return {
        "code": code,
        "message": message,
        "retry_at": retry_at,
        "meter": meter,
        "plan": plan,
        "upgrade_url": UPGRADE_URL,
    }


class PlanGate:
    """A route dependency that refuses callers whose plan cannot pay.

    A callable instance rather than a closure factory so each gate is a
    stable object: ``app.dependency_overrides`` needs a key it can name,
    and a factory would mint a new function per call site.

    *surface* is both the copy selector and the attribution value written
    to ``usage_records.surface``, which is what closes the
    ``surface='unknown'`` gap on the ledger.

    *meter_spend* is False for surfaces that serve bytes already paid
    for. ``GET /reports/{id}/pdf`` re-reads a stored PDF, so it is an
    entitlement question with no marginal cost to meter, and it needs
    its own wording while keeping the ``report`` surface.

    The copy is passed in rather than looked up by surface for that
    reason, and because two gates that sell the same thing should say so
    at the call site instead of in a dictionary three screens away.

    All strings are DRAFT, awaiting sign-off. House style is a hard rule:
    no em-dashes, no AI-tell vocabulary, warm but plain, short enough to
    read inside a banner, and specific about what is being offered.
    """

    def __init__(
        self,
        surface: str,
        *,
        upgrade_message: str,
        allowance_message: str | None = None,
    ) -> None:
        self.surface = surface
        self.meter_spend = allowance_message is not None
        self._upgrade_message = upgrade_message
        self._allowance_message = allowance_message

    async def __call__(
        self,
        account: Account = Depends(get_current_account),
    ) -> Account:
        plan = account.effective_plan

        if plan == "free":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=_envelope(
                    code=CODE_UPGRADE_REQUIRED,
                    message=self._upgrade_message,
                    plan=plan,
                    retry_at=None,
                    meter=None,
                ),
            )

        if self.meter_spend:
            await self._check_allowance(account, plan)

        # Only now, once the call is actually going to happen. A refused
        # request has nothing to attribute, and leaving a surface behind
        # would make the context look like a call that never ran.
        set_surface(self.surface)
        return account

    async def _check_allowance(self, account: Account, plan: str) -> None:
        try:
            await check_ceiling(
                scope=account.user_id,
                meter=METER_SPEND_MICROS_MONTHLY,
                ceiling=allowance_micros_for(plan),
                period_key=current_month_key(),
            )
        except CostCeilingExceeded as exc:
            if exc.reason != "ceiling_reached":
                # The meter itself is unreachable. Blocking is right, but
                # this is our outage, so it stays on the 503 path rather
                # than becoming a sales pitch for an internal fault.
                raise

            logger.info(
                "Monthly allowance reached (user=%s plan=%s surface=%s)",
                account.user_id,
                plan,
                self.surface,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=_envelope(
                    code=CODE_ALLOWANCE_REACHED,
                    message=self._allowance_message or self._upgrade_message,
                    plan=plan,
                    retry_at=exc.retry_at.isoformat(),
                    meter=METER_SPEND_MICROS_MONTHLY,
                ),
            ) from exc


# The five gated surfaces. Module-level singletons so routes share one
# instance per surface and tests have something to override.
#
# Note on the two "report" gates: their surface is route-layer bookkeeping
# only and will never appear in usage_records. Neither route makes a paid
# call. POST /reports queues a Celery task, and the narrative generation
# that actually spends money runs in the worker under its own
# attributed(surface="report_narrative") block (workers/tasks.py:496), in
# a different context entirely. GET /reports/{id}/pdf just serves stored
# bytes. Do not go looking for surface='report' rows in the ledger.
require_report = PlanGate(
    "report",
    upgrade_message="Full reports are part of a paid plan. Upgrade to generate yours.",
    allowance_message="You've used this month's included reports. Upgrade to keep going.",
)
require_report_download = PlanGate(
    "report",
    upgrade_message="Report downloads are part of a paid plan. Upgrade to get the PDF.",
)
require_chat = PlanGate(
    "chat",
    upgrade_message="Coaching chat is part of a paid plan. Upgrade to start a conversation.",
    allowance_message="You've used this month's included coaching. Upgrade to keep going.",
)
require_art = PlanGate(
    "art",
    upgrade_message="Image generation is part of a paid plan. Upgrade to make yours.",
    allowance_message="You've used this month's included images. Upgrade to keep going.",
)
require_brand_logo = PlanGate(
    "brand_logo",
    upgrade_message="Logo generation is part of a paid plan. Upgrade to make yours.",
    allowance_message="You've used this month's included images. Upgrade to keep going.",
)

"""Wealth lever prioritization engine.

Deterministic algorithm that orders the five wealth levers
(EARN, KEEP, GROW, PROTECT, TRANSFER) based on a user's financial context,
risk tolerance, intention, and numerology life path.

No LLM involvement — pure rule-based scoring.
"""

from __future__ import annotations

from alchymine.engine.profile import Intention, RiskTolerance, WealthContext, WealthLever

# ─── Income range classification ──────────────────────────────────────────

# Income ranges considered "low" — EARN gets a priority boost
_LOW_INCOME_KEYWORDS: frozenset[str] = frozenset(
    {
        "under $25k",
        "$0-$25k",
        "under $50k",
        "$25k-$50k",
        "<$25k",
        "<$50k",
        "0-25k",
        "25k-50k",
    }
)

# Income ranges considered "high" — GROW and TRANSFER get a boost
_HIGH_INCOME_KEYWORDS: frozenset[str] = frozenset(
    {
        "$150k-$200k",
        "$200k+",
        "over $200k",
        "$200k-$500k",
        "$500k+",
        ">$200k",
        "150k-200k",
        "200k+",
    }
)


def _classify_income(income_range: str | None) -> str:
    """Classify income as 'low', 'moderate', or 'high'."""
    if income_range is None:
        return "moderate"
    normalized = income_range.strip().lower()
    if normalized in _LOW_INCOME_KEYWORDS:
        return "low"
    if normalized in _HIGH_INCOME_KEYWORDS:
        return "high"
    return "moderate"


# ─── Scoring rules ───────────────────────────────────────────────────────

# Base scores: each lever starts with a neutral score
_BASE_SCORE: float = 10.0

# Adjustments from wealth context
_CONTEXT_LOW_INCOME_EARN_BOOST: float = 30.0
_CONTEXT_HAS_INVESTMENTS_GROW_BOOST: float = 15.0
_CONTEXT_HAS_BUSINESS_EARN_BOOST: float = 20.0
_CONTEXT_HAS_REAL_ESTATE_KEEP_BOOST: float = 10.0
_CONTEXT_DEPENDENTS_PROTECT_BOOST: float = 20.0
_CONTEXT_DEPENDENTS_TRANSFER_BOOST: float = 15.0
_CONTEXT_HIGH_DEBT_KEEP_BOOST: float = 20.0
_CONTEXT_HIGH_INCOME_GROW_BOOST: float = 10.0
_CONTEXT_HIGH_INCOME_TRANSFER_BOOST: float = 8.0

# Adjustments from risk tolerance
_RISK_AGGRESSIVE_GROW_BOOST: float = 15.0
_RISK_AGGRESSIVE_EARN_BOOST: float = 5.0
_RISK_CONSERVATIVE_PROTECT_BOOST: float = 15.0
_RISK_CONSERVATIVE_KEEP_BOOST: float = 10.0
_RISK_MODERATE_GROW_BOOST: float = 5.0
_RISK_MODERATE_KEEP_BOOST: float = 5.0

# Adjustments from intention
_INTENTION_BOOSTS: dict[Intention, dict[WealthLever, float]] = {
    Intention.MONEY: {WealthLever.EARN: 20.0, WealthLever.GROW: 15.0},
    Intention.CAREER: {WealthLever.EARN: 15.0, WealthLever.GROW: 5.0},
    Intention.BUSINESS: {WealthLever.EARN: 20.0, WealthLever.GROW: 10.0},
    Intention.FAMILY: {WealthLever.PROTECT: 20.0, WealthLever.TRANSFER: 15.0},
    Intention.LEGACY: {
        WealthLever.TRANSFER: 25.0,
        WealthLever.PROTECT: 10.0,
        WealthLever.GROW: 5.0,
    },
    Intention.LOVE: {WealthLever.PROTECT: 10.0, WealthLever.KEEP: 5.0},
    Intention.HEALTH: {WealthLever.KEEP: 10.0, WealthLever.PROTECT: 10.0},
    Intention.PURPOSE: {WealthLever.EARN: 10.0, WealthLever.GROW: 10.0, WealthLever.TRANSFER: 5.0},
}

# Life path number modulations
# Builder paths (4, 8, 22) favour EARN and KEEP
# Creative paths (3, 5) favour EARN
# Service paths (2, 6, 9, 33) favour PROTECT and TRANSFER
# Master number 11 favours GROW and TRANSFER
_LIFE_PATH_BOOSTS: dict[int, dict[WealthLever, float]] = {
    1: {WealthLever.EARN: 8.0},
    2: {WealthLever.PROTECT: 5.0, WealthLever.TRANSFER: 3.0},
    3: {WealthLever.EARN: 8.0},
    4: {WealthLever.KEEP: 8.0, WealthLever.EARN: 5.0},
    5: {WealthLever.EARN: 5.0, WealthLever.GROW: 5.0},
    6: {WealthLever.PROTECT: 8.0, WealthLever.TRANSFER: 5.0},
    7: {WealthLever.GROW: 8.0, WealthLever.KEEP: 5.0},
    8: {WealthLever.EARN: 8.0, WealthLever.GROW: 5.0},
    9: {WealthLever.TRANSFER: 8.0, WealthLever.PROTECT: 3.0},
    11: {WealthLever.GROW: 5.0, WealthLever.TRANSFER: 5.0},
    22: {WealthLever.EARN: 8.0, WealthLever.KEEP: 8.0},
    33: {WealthLever.PROTECT: 8.0, WealthLever.TRANSFER: 8.0},
}


def prioritize_levers(
    wealth_context: WealthContext | None,
    risk_tolerance: RiskTolerance,
    intention: Intention,
    life_path: int,
) -> list[WealthLever]:
    """Prioritize the 5 wealth levers based on user context.

    Returns an ordered list of all 5 WealthLever values from highest
    to lowest priority. The ordering is fully deterministic.

    Parameters
    ----------
    wealth_context : WealthContext | None
        Voluntarily provided financial context. If None, defaults are used.
    risk_tolerance : RiskTolerance
        The user's financial risk tolerance level.
    intention : Intention
        The user's primary intention/goal.
    life_path : int
        Numerology Life Path number (1-9, 11, 22, 33).

    Returns
    -------
    list[WealthLever]
        All 5 wealth levers ordered by priority (highest first).
    """
    # Initialize all levers with base score
    scores: dict[WealthLever, float] = {lever: _BASE_SCORE for lever in WealthLever}

    # 1. Apply wealth context adjustments
    if wealth_context is not None:
        income_class = _classify_income(wealth_context.income_range)

        if income_class == "low":
            scores[WealthLever.EARN] += _CONTEXT_LOW_INCOME_EARN_BOOST
        elif income_class == "high":
            scores[WealthLever.GROW] += _CONTEXT_HIGH_INCOME_GROW_BOOST
            scores[WealthLever.TRANSFER] += _CONTEXT_HIGH_INCOME_TRANSFER_BOOST

        if wealth_context.has_investments:
            scores[WealthLever.GROW] += _CONTEXT_HAS_INVESTMENTS_GROW_BOOST

        if wealth_context.has_business:
            scores[WealthLever.EARN] += _CONTEXT_HAS_BUSINESS_EARN_BOOST

        if wealth_context.has_real_estate:
            scores[WealthLever.KEEP] += _CONTEXT_HAS_REAL_ESTATE_KEEP_BOOST

        if wealth_context.dependents is not None and wealth_context.dependents > 0:
            scores[WealthLever.PROTECT] += _CONTEXT_DEPENDENTS_PROTECT_BOOST
            scores[WealthLever.TRANSFER] += _CONTEXT_DEPENDENTS_TRANSFER_BOOST

        if wealth_context.debt_level is not None and wealth_context.debt_level.lower() in (
            "high",
            "very high",
        ):
            scores[WealthLever.KEEP] += _CONTEXT_HIGH_DEBT_KEEP_BOOST

    # 2. Apply risk tolerance adjustments
    if risk_tolerance == RiskTolerance.AGGRESSIVE:
        scores[WealthLever.GROW] += _RISK_AGGRESSIVE_GROW_BOOST
        scores[WealthLever.EARN] += _RISK_AGGRESSIVE_EARN_BOOST
    elif risk_tolerance == RiskTolerance.CONSERVATIVE:
        scores[WealthLever.PROTECT] += _RISK_CONSERVATIVE_PROTECT_BOOST
        scores[WealthLever.KEEP] += _RISK_CONSERVATIVE_KEEP_BOOST
    else:  # MODERATE
        scores[WealthLever.GROW] += _RISK_MODERATE_GROW_BOOST
        scores[WealthLever.KEEP] += _RISK_MODERATE_KEEP_BOOST

    # 3. Apply intention adjustments
    intention_boosts = _INTENTION_BOOSTS.get(intention, {})
    for lever, boost in intention_boosts.items():
        scores[lever] += boost

    # 4. Apply life path adjustments
    path_boosts = _LIFE_PATH_BOOSTS.get(life_path, {})
    for lever, boost in path_boosts.items():
        scores[lever] += boost

    # Sort by score descending, with enum definition order as tiebreaker
    lever_order = list(WealthLever)
    sorted_levers = sorted(
        scores.items(),
        key=lambda item: (-item[1], lever_order.index(item[0])),
    )

    return [lever for lever, _score in sorted_levers]

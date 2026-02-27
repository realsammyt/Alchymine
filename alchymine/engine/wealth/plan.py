"""90-day wealth activation plan generator.

Generates a deterministic 3-phase plan based on a user's wealth archetype,
lever priorities, and risk tolerance. No LLM — all content is templated.
"""

from __future__ import annotations

from dataclasses import dataclass

from alchymine.engine.profile import RiskTolerance, WealthLever

from .archetype import WealthArchetype


@dataclass(frozen=True)
class PlanPhase:
    """A single phase in the 90-day activation plan."""

    name: str
    days: tuple[int, int]
    focus_lever: WealthLever
    actions: tuple[str, ...]
    milestones: tuple[str, ...]


@dataclass(frozen=True)
class ActivationPlan:
    """Complete 90-day wealth activation plan."""

    wealth_archetype: str
    phases: tuple[PlanPhase, ...]
    daily_habits: tuple[str, ...]
    weekly_reviews: tuple[str, ...]


# ─── Action templates per lever ──────────────────────────────────────────

_LEVER_ACTIONS: dict[WealthLever, dict[str, tuple[str, ...]]] = {
    WealthLever.EARN: {
        "foundation": (
            "Audit all current income streams and document exact amounts",
            "Identify your top 3 marketable skills and rate them 1-10",
            "Research 5 ways to increase income in your current role or field",
            "Set a specific income target for the next 90 days",
        ),
        "building": (
            "Launch one new income stream or side project",
            "Negotiate a raise, rate increase, or new contract",
            "Build a portfolio or pitch deck for your highest-value skill",
            "Network with 3 people earning more than you in your field",
        ),
        "acceleration": (
            "Scale your highest-performing income stream",
            "Automate or delegate low-value tasks to protect earning time",
            "Create a system for recurring revenue (retainer, subscription, etc.)",
            "Set income targets for the next quarter and year",
        ),
    },
    WealthLever.KEEP: {
        "foundation": (
            "Track every expense for 30 days without judgment",
            "Identify your top 3 spending leaks (subscriptions, impulse buys, fees)",
            "Create a zero-based budget for next month",
            "Set up automatic savings transfers on payday",
        ),
        "building": (
            "Reduce top spending leaks by 50%",
            "Optimize tax strategy (review deductions, contributions, structure)",
            "Build a 30-day expense buffer in checking account",
            "Negotiate lower rates on recurring bills (insurance, phone, etc.)",
        ),
        "acceleration": (
            "Achieve a target savings rate (e.g., 20% of income)",
            "Create a system to review and cut expenses quarterly",
            "Optimize tax-advantaged accounts to max contribution",
            "Build a personal financial dashboard for net worth tracking",
        ),
    },
    WealthLever.GROW: {
        "foundation": (
            "Define your investment thesis: timeline, risk level, goals",
            "Open or review investment accounts (brokerage, retirement)",
            "Research and select 3 low-cost diversified investment options",
            "Set up automatic monthly investment contributions",
        ),
        "building": (
            "Diversify across at least 3 asset classes",
            "Review portfolio allocation and rebalance if needed",
            "Research one alternative investment (real estate, private, etc.)",
            "Increase investment contribution by 5% of income",
        ),
        "acceleration": (
            "Create a long-term investment plan with 5-year milestones",
            "Build a diversified portfolio aligned with your risk tolerance",
            "Set up quarterly portfolio review and rebalancing schedule",
            "Research advanced strategies (tax-loss harvesting, etc.)",
        ),
    },
    WealthLever.PROTECT: {
        "foundation": (
            "Audit all insurance coverage (health, life, disability, property)",
            "Build an emergency fund: target 1 month of expenses",
            "Create or update your will and beneficiary designations",
            "Review all account passwords and set up two-factor authentication",
        ),
        "building": (
            "Increase emergency fund to 3 months of expenses",
            "Close coverage gaps identified in insurance audit",
            "Set up a living will and healthcare directive",
            "Create a financial information document for your family",
        ),
        "acceleration": (
            "Build emergency fund to 6 months of expenses",
            "Establish an umbrella insurance policy if net worth justifies it",
            "Create a comprehensive estate plan with professional guidance",
            "Set up annual insurance and protection review schedule",
        ),
    },
    WealthLever.TRANSFER: {
        "foundation": (
            "Define your legacy vision: who and what do you want to support?",
            "Research basic estate planning options in your jurisdiction",
            "Identify 3 causes or people you want to benefit from your wealth",
            "Calculate your current net worth and document all assets",
        ),
        "building": (
            "Set up a giving plan (charitable donations, family support)",
            "Research tax-efficient giving strategies (donor-advised fund, etc.)",
            "Create or update beneficiary designations on all accounts",
            "Start conversations with family about financial legacy",
        ),
        "acceleration": (
            "Formalize your estate plan with legal documentation",
            "Establish a systematic giving strategy (% of income or net worth)",
            "Create an ethical will or legacy letter for your family",
            "Set up annual legacy review to adjust for life changes",
        ),
    },
}

# ─── Milestones per lever ────────────────────────────────────────────────

_LEVER_MILESTONES: dict[WealthLever, dict[str, tuple[str, ...]]] = {
    WealthLever.EARN: {
        "foundation": (
            "All income streams documented with exact monthly amounts",
            "Income growth target set and written down",
        ),
        "building": (
            "One new income stream launched or raise secured",
            "Income increased by at least 10% from baseline",
        ),
        "acceleration": (
            "Recurring revenue system operational",
            "90-day income target achieved or exceeded",
        ),
    },
    WealthLever.KEEP: {
        "foundation": (
            "30 days of expense tracking completed",
            "Budget created and automated savings activated",
        ),
        "building": (
            "Top spending leaks reduced by 50%",
            "30-day expense buffer established",
        ),
        "acceleration": (
            "Target savings rate achieved consistently for 30 days",
            "Financial dashboard operational with net worth tracking",
        ),
    },
    WealthLever.GROW: {
        "foundation": (
            "Investment thesis documented",
            "Automatic investment contributions activated",
        ),
        "building": (
            "Portfolio diversified across 3+ asset classes",
            "Investment contribution increased by 5%",
        ),
        "acceleration": (
            "5-year investment plan documented",
            "Quarterly rebalancing schedule established",
        ),
    },
    WealthLever.PROTECT: {
        "foundation": (
            "Insurance audit completed with gaps identified",
            "Emergency fund started (1 month target)",
        ),
        "building": (
            "All insurance gaps closed",
            "Emergency fund at 3 months of expenses",
        ),
        "acceleration": (
            "Emergency fund at 6 months of expenses",
            "Comprehensive estate plan in place",
        ),
    },
    WealthLever.TRANSFER: {
        "foundation": (
            "Legacy vision statement written",
            "Net worth documented with all assets listed",
        ),
        "building": (
            "Giving plan established with specific allocations",
            "All beneficiary designations updated",
        ),
        "acceleration": (
            "Estate plan formalized with legal documentation",
            "Annual legacy review scheduled",
        ),
    },
}

# ─── Daily habits by risk tolerance ──────────────────────────────────────

_DAILY_HABITS: dict[RiskTolerance, tuple[str, ...]] = {
    RiskTolerance.CONSERVATIVE: (
        "Review yesterday's spending for 2 minutes",
        "Read one financial article or book chapter",
        "Affirm your financial security intention",
        "Check that automatic savings are on track",
        "Practice gratitude for current financial position",
    ),
    RiskTolerance.MODERATE: (
        "Review yesterday's spending for 2 minutes",
        "Read one financial or market article",
        "Affirm your wealth-building intention",
        "Identify one small action to improve finances today",
        "Track progress toward your 90-day financial goal",
    ),
    RiskTolerance.AGGRESSIVE: (
        "Review yesterday's spending and income for 2 minutes",
        "Scan market news and opportunities for 5 minutes",
        "Affirm your growth and abundance intention",
        "Take one bold action toward income growth today",
        "Track progress toward your 90-day financial goal",
    ),
}

# ─── Weekly review items by archetype ────────────────────────────────────

_ARCHETYPE_WEEKLY_REVIEWS: dict[str, tuple[str, ...]] = {
    "The Builder": (
        "Review progress on financial structure and systems",
        "Check that all automated money flows are working",
        "Assess progress toward quarterly milestones",
        "Plan next week's key financial action",
    ),
    "The Innovator": (
        "Review income from all creative revenue streams",
        "Assess which ideas are generating returns vs. draining energy",
        "Plan one creative monetization experiment for next week",
        "Check index fund contributions are on track",
    ),
    "The Sage Investor": (
        "Review portfolio performance and market insights",
        "Assess one investment decision from this week",
        "Plan research agenda for next week",
        "Check that action items aren't stalled by over-analysis",
    ),
    "The Connector": (
        "Review giving and receiving balance this week",
        "Assess progress on family financial security goals",
        "Plan one relationship-building financial conversation",
        "Check that personal savings are prioritized before giving",
    ),
    "The Warrior": (
        "Review income growth and competitive positioning",
        "Assess risk exposure and ensure it's within limits",
        "Plan one bold financial move for next week",
        "Check emergency fund and protection are adequate",
    ),
    "The Mystic Trader": (
        "Review alignment between investments and values",
        "Assess progress on practical financial foundations",
        "Plan one impact-aligned financial action for next week",
        "Check budget basics are covered before impact investing",
    ),
    "The Community Banker": (
        "Review savings and security progress",
        "Assess one area to stretch beyond financial comfort zone",
        "Plan a community-beneficial financial action for next week",
        "Check investment growth is keeping pace with goals",
    ),
    "The Entertainer": (
        "Review all income streams and creative revenue",
        "Assess financial automation systems are running smoothly",
        "Plan one fun financial milestone for next week",
        "Complete the 30-minute financial review commitment",
    ),
}

# Default weekly review for unrecognized archetypes
_DEFAULT_WEEKLY_REVIEWS: tuple[str, ...] = (
    "Review progress on the current phase's focus lever",
    "Check all automated financial systems are on track",
    "Assess one financial win and one area for improvement",
    "Plan the single most important financial action for next week",
)


def generate_activation_plan(
    wealth_archetype: WealthArchetype,
    lever_priorities: list[WealthLever],
    risk_tolerance: RiskTolerance,
) -> ActivationPlan:
    """Generate a 90-day wealth activation plan.

    Creates a 3-phase plan:
    - Phase 1 (Days 1-30): Foundation — focus on #1 lever priority
    - Phase 2 (Days 31-60): Building — expand to #2 lever
    - Phase 3 (Days 61-90): Acceleration — integrate #3 lever

    Parameters
    ----------
    wealth_archetype : WealthArchetype
        The user's mapped wealth archetype.
    lever_priorities : list[WealthLever]
        Ordered list of wealth levers from highest to lowest priority.
    risk_tolerance : RiskTolerance
        The user's financial risk tolerance level.

    Returns
    -------
    ActivationPlan
        A complete 90-day plan with phases, daily habits, and weekly reviews.
    """
    # Ensure we have at least 3 levers (should always be 5, but defensive)
    if len(lever_priorities) < 3:
        # Pad with remaining levers in enum order
        existing = set(lever_priorities)
        for lever in WealthLever:
            if lever not in existing:
                lever_priorities.append(lever)
            if len(lever_priorities) >= 3:
                break

    phase_configs = [
        ("Foundation", (1, 30), lever_priorities[0], "foundation"),
        ("Building", (31, 60), lever_priorities[1], "building"),
        ("Acceleration", (61, 90), lever_priorities[2], "acceleration"),
    ]

    phases: list[PlanPhase] = []
    for phase_name, days, focus_lever, template_key in phase_configs:
        actions = _LEVER_ACTIONS.get(focus_lever, {}).get(template_key, ())
        milestones = _LEVER_MILESTONES.get(focus_lever, {}).get(template_key, ())

        phases.append(
            PlanPhase(
                name=phase_name,
                days=days,
                focus_lever=focus_lever,
                actions=actions,
                milestones=milestones,
            )
        )

    daily_habits = _DAILY_HABITS.get(risk_tolerance, _DAILY_HABITS[RiskTolerance.MODERATE])
    weekly_reviews = _ARCHETYPE_WEEKLY_REVIEWS.get(
        wealth_archetype.name,
        _DEFAULT_WEEKLY_REVIEWS,
    )

    return ActivationPlan(
        wealth_archetype=wealth_archetype.name,
        phases=tuple(phases),
        daily_habits=daily_habits,
        weekly_reviews=weekly_reviews,
    )

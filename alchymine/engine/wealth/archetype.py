"""Wealth archetype mapping engine.

Maps a user's numerology life path, Jungian archetype, and risk tolerance
to one of 8 wealth archetypes. Each wealth archetype defines primary levers,
strengths, blind spots, and recommended actions.

Algorithm: Score each wealth archetype based on life path match +
Jungian archetype alignment + risk tolerance compatibility.
Return the highest scoring. Fully deterministic — no LLM, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass

from alchymine.engine.profile import ArchetypeType, RiskTolerance, WealthLever


@dataclass(frozen=True)
class WealthArchetype:
    """A wealth archetype describing a user's financial personality."""

    name: str
    description: str
    primary_levers: tuple[WealthLever, ...]
    strengths: tuple[str, ...]
    blind_spots: tuple[str, ...]
    recommended_actions: tuple[str, ...]


# ─── The 8 Wealth Archetypes ────────────────────────────────────────────

WEALTH_ARCHETYPES: dict[str, WealthArchetype] = {
    "The Builder": WealthArchetype(
        name="The Builder",
        description=(
            "Systematic wealth creator who builds enduring financial structures. "
            "Excels at disciplined accumulation, strategic planning, and creating "
            "enterprises that generate long-term compounding returns."
        ),
        primary_levers=(WealthLever.EARN, WealthLever.GROW, WealthLever.KEEP),
        strengths=(
            "Disciplined saving and budgeting",
            "Long-term strategic planning",
            "Building scalable income systems",
            "Patience with compound growth",
        ),
        blind_spots=(
            "Over-conservatism may miss growth opportunities",
            "Rigidity in financial plans when markets shift",
            "Difficulty delegating financial decisions",
            "May sacrifice lifestyle for accumulation",
        ),
        recommended_actions=(
            "Create a structured 5-year wealth accumulation plan",
            "Automate savings and investment contributions",
            "Build or acquire an income-producing asset",
            "Establish clear financial milestones with quarterly reviews",
            "Diversify income streams beyond primary employment",
        ),
    ),
    "The Innovator": WealthArchetype(
        name="The Innovator",
        description=(
            "Creative wealth generator who monetizes ideas and innovation. "
            "Thrives in new markets, alternative investments, and turning "
            "creative talents into revenue streams."
        ),
        primary_levers=(WealthLever.EARN, WealthLever.GROW),
        strengths=(
            "Spotting emerging opportunities early",
            "Monetizing creative skills and ideas",
            "Adapting quickly to market changes",
            "Building multiple diverse income streams",
        ),
        blind_spots=(
            "Scattered focus across too many ventures",
            "Undervaluing consistent boring investments",
            "Feast-or-famine income cycles",
            "Neglecting financial record-keeping",
        ),
        recommended_actions=(
            "Choose one creative revenue stream and scale it to profitability",
            "Set up automatic transfers to a boring index fund",
            "Track all income streams in a single dashboard",
            "Create a financial buffer for feast-or-famine cycles",
            "Monetize your top creative skill within 30 days",
        ),
    ),
    "The Sage Investor": WealthArchetype(
        name="The Sage Investor",
        description=(
            "Research-driven wealth grower who makes decisions based on deep "
            "analysis and evidence. Excels at value investing, risk assessment, "
            "and building a knowledge-based investment portfolio."
        ),
        primary_levers=(WealthLever.GROW, WealthLever.KEEP),
        strengths=(
            "Thorough research before financial decisions",
            "Emotional discipline during market volatility",
            "Understanding of risk-reward dynamics",
            "Long-term value-oriented thinking",
        ),
        blind_spots=(
            "Analysis paralysis delaying investment entry",
            "Over-researching at the expense of action",
            "Missing time-sensitive opportunities",
            "Intellectual arrogance about financial knowledge",
        ),
        recommended_actions=(
            "Set a research time limit per investment decision (max 7 days)",
            "Build a diversified evidence-based portfolio",
            "Create a personal investment thesis and update it quarterly",
            "Teach one financial concept to someone else each month",
            "Automate investment contributions to bypass analysis paralysis",
        ),
    ),
    "The Connector": WealthArchetype(
        name="The Connector",
        description=(
            "Relationship-driven wealth builder who creates prosperity through "
            "partnerships, networks, and community. Excels at collaborative "
            "ventures and building financial security for loved ones."
        ),
        primary_levers=(WealthLever.EARN, WealthLever.PROTECT, WealthLever.TRANSFER),
        strengths=(
            "Building wealth through partnerships and networks",
            "Creating family financial security",
            "Generous spirit that attracts opportunities",
            "Strong negotiation through relationship skills",
        ),
        blind_spots=(
            "Difficulty negotiating fair compensation for self",
            "Over-giving that depletes personal resources",
            "Avoiding financial conflict in relationships",
            "Putting others' financial needs before own",
        ),
        recommended_actions=(
            "Establish a non-negotiable personal savings allocation before giving",
            "Set up life insurance and estate planning basics",
            "Practice stating your financial worth in negotiations",
            "Create a giving budget that protects your financial foundation",
            "Build a financial advisory network of trusted peers",
        ),
    ),
    "The Warrior": WealthArchetype(
        name="The Warrior",
        description=(
            "High-energy wealth builder who pursues aggressive growth through "
            "bold action. Thrives in competitive markets, entrepreneurship, "
            "and high-stakes financial decisions."
        ),
        primary_levers=(WealthLever.EARN, WealthLever.GROW),
        strengths=(
            "Bold decisive action on financial opportunities",
            "Resilience during financial setbacks",
            "Competitive drive for income growth",
            "Willingness to take calculated risks",
        ),
        blind_spots=(
            "Excessive risk-taking tied to ego",
            "Tying self-worth to net worth",
            "Burnout from relentless financial striving",
            "Neglecting protection and insurance",
        ),
        recommended_actions=(
            "Define a maximum risk exposure per investment (e.g., 5% of portfolio)",
            "Separate identity from financial outcomes with a values statement",
            "Build an emergency fund equal to 6 months of expenses",
            "Channel competitive energy into income growth, not speculation",
            "Schedule quarterly financial health check-ins (not just returns)",
        ),
    ),
    "The Mystic Trader": WealthArchetype(
        name="The Mystic Trader",
        description=(
            "Intuition-guided wealth creator who aligns financial decisions "
            "with purpose and impact. Drawn to conscious capitalism, impact "
            "investing, and wealth as a tool for transformation."
        ),
        primary_levers=(WealthLever.GROW, WealthLever.TRANSFER),
        strengths=(
            "Aligning investments with values and purpose",
            "Intuitive sense for market timing and trends",
            "Creating wealth that serves a larger mission",
            "Patience with long-term purpose-driven investments",
        ),
        blind_spots=(
            "Neglecting practical financial foundations",
            "Spiritual bypassing of money management basics",
            "Overly idealistic investment choices",
            "Difficulty charging for spiritual or purpose work",
        ),
        recommended_actions=(
            "Build a practical budget before pursuing impact investments",
            "Allocate a specific percentage for impact investing (e.g., 20%)",
            "Create a bridge between purpose and profit in your career",
            "Set up the financial basics: emergency fund, insurance, will",
            "Track both financial returns and impact metrics monthly",
        ),
    ),
    "The Community Banker": WealthArchetype(
        name="The Community Banker",
        description=(
            "Steady, community-oriented wealth steward who builds financial "
            "security for self and community. Excels at reliable wealth "
            "preservation, mutual aid, and collective prosperity."
        ),
        primary_levers=(WealthLever.KEEP, WealthLever.PROTECT, WealthLever.TRANSFER),
        strengths=(
            "Steady disciplined approach to money management",
            "Building financial security for family and community",
            "Trustworthy stewardship of shared resources",
            "Practical no-nonsense budgeting skills",
        ),
        blind_spots=(
            "Avoiding ambitious financial goals",
            "Under-investing due to fear of loss",
            "Guilt about personal wealth accumulation",
            "Staying in a financial comfort zone",
        ),
        recommended_actions=(
            "Set one ambitious financial goal outside your comfort zone",
            "Increase investment allocation by 5% annually",
            "Explore community investment options (CDFIs, co-ops)",
            "Create a personal wealth milestone that excites you",
            "Build financial literacy through a monthly book or course",
        ),
    ),
    "The Entertainer": WealthArchetype(
        name="The Entertainer",
        description=(
            "Unconventional wealth creator who monetizes personality, humor, "
            "and social presence. Thrives in attention-economy businesses, "
            "creative monetization, and turning joy into revenue."
        ),
        primary_levers=(WealthLever.EARN, WealthLever.GROW),
        strengths=(
            "Monetizing personality and social presence",
            "Creative unconventional income strategies",
            "Attracting opportunities through charisma",
            "Seeing financial opportunities others miss",
        ),
        blind_spots=(
            "Casual attitude toward financial planning",
            "Using humor to avoid financial conversations",
            "Inconsistent income management",
            "Avoiding the boring but essential financial basics",
        ),
        recommended_actions=(
            "Automate all essential financial actions (savings, bills, investments)",
            "Build a personal brand monetization strategy",
            "Set up a system to capture income from all creative sources",
            "Commit to one 30-minute weekly financial review",
            "Create a fun reward system tied to financial milestones",
        ),
    ),
}


# ─── Scoring tables ──────────────────────────────────────────────────────

# Life path numbers that strongly align with each wealth archetype
_LIFE_PATH_MATCHES: dict[str, frozenset[int]] = {
    "The Builder": frozenset({4, 8, 22}),
    "The Innovator": frozenset({3, 5}),
    "The Sage Investor": frozenset({7}),
    "The Connector": frozenset({2, 6, 33}),
    "The Warrior": frozenset({1, 8}),
    "The Mystic Trader": frozenset({9, 11}),
    "The Community Banker": frozenset({2, 6}),
    "The Entertainer": frozenset({5}),
}

# Jungian archetypes that align with each wealth archetype
_ARCHETYPE_MATCHES: dict[str, frozenset[ArchetypeType]] = {
    "The Builder": frozenset({ArchetypeType.RULER}),
    "The Innovator": frozenset({ArchetypeType.CREATOR, ArchetypeType.EXPLORER}),
    "The Sage Investor": frozenset({ArchetypeType.SAGE}),
    "The Connector": frozenset({ArchetypeType.LOVER, ArchetypeType.CAREGIVER}),
    "The Warrior": frozenset({ArchetypeType.HERO, ArchetypeType.REBEL}),
    "The Mystic Trader": frozenset({ArchetypeType.MYSTIC}),
    "The Community Banker": frozenset({ArchetypeType.EVERYMAN, ArchetypeType.CAREGIVER}),
    "The Entertainer": frozenset({ArchetypeType.JESTER}),
}

# Risk tolerance compatibility per wealth archetype
# Each maps to a set of compatible risk levels with score weight
_RISK_COMPATIBILITY: dict[str, dict[RiskTolerance, float]] = {
    "The Builder": {
        RiskTolerance.CONSERVATIVE: 1.0,
        RiskTolerance.MODERATE: 0.7,
        RiskTolerance.AGGRESSIVE: 0.3,
    },
    "The Innovator": {
        RiskTolerance.CONSERVATIVE: 0.2,
        RiskTolerance.MODERATE: 0.7,
        RiskTolerance.AGGRESSIVE: 1.0,
    },
    "The Sage Investor": {
        RiskTolerance.CONSERVATIVE: 0.6,
        RiskTolerance.MODERATE: 1.0,
        RiskTolerance.AGGRESSIVE: 0.5,
    },
    "The Connector": {
        RiskTolerance.CONSERVATIVE: 0.8,
        RiskTolerance.MODERATE: 1.0,
        RiskTolerance.AGGRESSIVE: 0.3,
    },
    "The Warrior": {
        RiskTolerance.CONSERVATIVE: 0.1,
        RiskTolerance.MODERATE: 0.5,
        RiskTolerance.AGGRESSIVE: 1.0,
    },
    "The Mystic Trader": {
        RiskTolerance.CONSERVATIVE: 0.3,
        RiskTolerance.MODERATE: 0.8,
        RiskTolerance.AGGRESSIVE: 0.7,
    },
    "The Community Banker": {
        RiskTolerance.CONSERVATIVE: 1.0,
        RiskTolerance.MODERATE: 0.8,
        RiskTolerance.AGGRESSIVE: 0.1,
    },
    "The Entertainer": {
        RiskTolerance.CONSERVATIVE: 0.2,
        RiskTolerance.MODERATE: 0.8,
        RiskTolerance.AGGRESSIVE: 0.9,
    },
}

# ─── Scoring weights ────────────────────────────────────────────────────

LIFE_PATH_WEIGHT: float = 40.0
ARCHETYPE_WEIGHT: float = 35.0
RISK_TOLERANCE_WEIGHT: float = 25.0


def _score_wealth_archetypes(
    life_path: int,
    archetype_primary: ArchetypeType,
    risk_tolerance: RiskTolerance,
) -> dict[str, float]:
    """Score all 8 wealth archetypes and return the score dict.

    Scoring algorithm:
    1. Life path match: +LIFE_PATH_WEIGHT if the user's life path is in the
       archetype's compatible set.
    2. Jungian archetype match: +ARCHETYPE_WEIGHT if the user's primary Jungian
       archetype is in the wealth archetype's compatible set.
    3. Risk tolerance compatibility: +RISK_TOLERANCE_WEIGHT * compatibility factor.
    """
    scores: dict[str, float] = {}

    for name in WEALTH_ARCHETYPES:
        score = 0.0

        # Life path match
        if life_path in _LIFE_PATH_MATCHES[name]:
            score += LIFE_PATH_WEIGHT

        # Jungian archetype match
        if archetype_primary in _ARCHETYPE_MATCHES[name]:
            score += ARCHETYPE_WEIGHT

        # Risk tolerance compatibility
        risk_factor = _RISK_COMPATIBILITY[name].get(risk_tolerance, 0.5)
        score += RISK_TOLERANCE_WEIGHT * risk_factor

        scores[name] = score

    return scores


def map_wealth_archetype(
    life_path: int,
    archetype_primary: ArchetypeType,
    risk_tolerance: RiskTolerance,
) -> WealthArchetype:
    """Map a user's numerology, archetype, and risk tolerance to a wealth archetype.

    This is the main entry point for the wealth archetype engine.
    Fully deterministic — same inputs always produce the same output.

    Parameters
    ----------
    life_path : int
        Numerology Life Path number (1-9, 11, 22, 33).
    archetype_primary : ArchetypeType
        The user's primary Jungian archetype.
    risk_tolerance : RiskTolerance
        The user's financial risk tolerance level.

    Returns
    -------
    WealthArchetype
        The highest-scoring wealth archetype for this user.
    """
    scores = _score_wealth_archetypes(life_path, archetype_primary, risk_tolerance)

    # Select the highest-scoring archetype.
    # Ties broken by definition order (dict insertion order is stable in Python 3.7+).
    best_name = max(scores, key=lambda name: scores[name])

    return WEALTH_ARCHETYPES[best_name]


def get_wealth_archetype_scores(
    life_path: int,
    archetype_primary: ArchetypeType,
    risk_tolerance: RiskTolerance,
) -> dict[str, float]:
    """Expose raw scoring for debugging and transparency.

    Returns a dictionary of all 8 wealth archetypes with their computed scores.
    """
    return _score_wealth_archetypes(life_path, archetype_primary, risk_tolerance)

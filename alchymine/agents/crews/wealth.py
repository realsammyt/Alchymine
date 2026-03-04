"""Wealth crew — 6 domain agents for the Generational Wealth system.

Agents:
    WealthArchetypeAnalyst — Wealth archetype mapping
    LeverCalculator        — Lever prioritization
    DebtStrategist         — Snowball/avalanche debt analysis
    BudgetAnalyst          — Income/expense analysis
    WealthValidator        — Financial disclaimer + ethics validation
    WealthNarrative        — Generate wealth guidance narratives

CRITICAL: All financial calculations are deterministic. No LLM
involvement in number generation. Financial data is classified as
Sensitive — encrypted, isolated, never sent to LLM.
"""

from __future__ import annotations

from typing import Any

from .base import AgentRole, AgentTask, DomainAgent, SystemCrew

_SYSTEM = "wealth"

_WEALTH_DISCLAIMER = (
    "This is not financial advice. Please consult a qualified "
    "financial advisor for personalised recommendations."
)


# ─── WealthArchetypeAnalyst ────────────────────────────────────────


class WealthArchetypeAnalyst(DomainAgent):
    """Maps user profile to one of 8 wealth archetypes."""

    def __init__(self) -> None:
        super().__init__(
            name="WealthArchetypeAnalyst",
            role=AgentRole.ANALYST,
            goal=(
                "Map the user's life path number, primary archetype, "
                "and risk tolerance to a wealth archetype that describes "
                "their financial personality."
            ),
            backstory=(
                "Wealth psychologist who maps numerological and Jungian "
                "archetype patterns onto one of 8 wealth archetypes. "
                "Each archetype reveals financial strengths, blind spots, "
                "and lever affinities. All mapping is deterministic."
            ),
            system=_SYSTEM,
            tools=["wealth.map_wealth_archetype"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Map user data to a wealth archetype."""
        from alchymine.engine.wealth import map_wealth_archetype

        life_path = context.get("life_path")
        archetype_primary = context.get("archetype_primary")
        risk_tolerance = context.get("risk_tolerance", "moderate")

        if life_path is None or not archetype_primary:
            return {
                "wealth_archetype": None,
                "wealth_archetype_error": "Missing life_path or archetype_primary",
            }

        archetype = map_wealth_archetype(life_path, archetype_primary, risk_tolerance)
        return {
            "wealth_archetype": {
                "name": archetype.name,
                "description": archetype.description,
                "primary_levers": [
                    lev.value if hasattr(lev, "value") else str(lev)
                    for lev in archetype.primary_levers
                ],
                "strengths": list(archetype.strengths),
                "blind_spots": list(archetype.blind_spots),
            },
        }


# ─── LeverCalculator ──────────────────────────────────────────────


class LeverCalculator(DomainAgent):
    """Prioritizes the 5 wealth levers based on user context."""

    def __init__(self) -> None:
        super().__init__(
            name="LeverCalculator",
            role=AgentRole.CALCULATOR,
            goal=(
                "Prioritize the five wealth levers (EARN, KEEP, GROW, "
                "PROTECT, TRANSFER) based on the user's financial context, "
                "risk tolerance, intention, and life path number."
            ),
            backstory=(
                "Financial strategist who uses a deterministic scoring "
                "algorithm to order wealth levers by priority. Factors in "
                "income level, existing assets, risk tolerance, life goals, "
                "and numerological life path. No LLM involvement — pure "
                "rule-based scoring."
            ),
            system=_SYSTEM,
            tools=["wealth.prioritize_levers"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Prioritize wealth levers from user context."""
        from alchymine.engine.profile import Intention, RiskTolerance, WealthContext
        from alchymine.engine.wealth import prioritize_levers

        life_path = context.get("life_path")
        risk_tolerance_str = context.get("risk_tolerance", "moderate")
        intention_str = context.get("intention")
        wealth_context_data = context.get("wealth_context")

        if life_path is None or intention_str is None:
            return {
                "lever_priorities": None,
                "lever_error": "Missing life_path or intention",
            }

        # Convert to enums
        try:
            risk_tolerance = RiskTolerance(risk_tolerance_str)
        except ValueError:
            risk_tolerance = RiskTolerance.MODERATE

        try:
            intention = (
                Intention(intention_str.value)
                if hasattr(intention_str, "value")
                else Intention(intention_str)
            )
        except ValueError:
            intention = Intention.PURPOSE

        # Build WealthContext if data provided
        wealth_context = None
        if wealth_context_data is not None:
            if isinstance(wealth_context_data, dict):
                wealth_context = WealthContext(**wealth_context_data)
            else:
                wealth_context = wealth_context_data

        levers = prioritize_levers(
            wealth_context=wealth_context,
            risk_tolerance=risk_tolerance,
            intentions=[intention],
            life_path=life_path,
        )

        return {
            "lever_priorities": [
                lev.value if hasattr(lev, "value") else str(lev) for lev in levers
            ],
        }


# ─── DebtStrategist ────────────────────────────────────────────────


class DebtStrategist(DomainAgent):
    """Analyzes debt using snowball and avalanche strategies."""

    def __init__(self) -> None:
        super().__init__(
            name="DebtStrategist",
            role=AgentRole.ANALYST,
            goal=(
                "Analyze the user's debts using both snowball and "
                "avalanche strategies and provide a comparison showing "
                "total interest paid and time to payoff under each."
            ),
            backstory=(
                "Debt elimination specialist who calculates month-by-month "
                "payoff schedules using two proven strategies: snowball "
                "(smallest balances first for psychological wins) and "
                "avalanche (highest interest first for cost minimization). "
                "All calculations use Decimal for financial precision."
            ),
            system=_SYSTEM,
            tools=[
                "wealth.calculate_snowball",
                "wealth.calculate_avalanche",
                "wealth.compare_strategies",
            ],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compare debt payoff strategies from user's debt data."""
        from decimal import Decimal

        from alchymine.engine.wealth import compare_strategies
        from alchymine.engine.wealth.debt import Debt, DebtType

        debts_data = context.get("debts")
        extra_payment = context.get("extra_monthly_payment", 0)

        if not debts_data or not isinstance(debts_data, list):
            return {"debt_analysis": None, "debt_error": "No debts provided"}

        # Build Debt objects
        debts = []
        for d in debts_data:
            if isinstance(d, dict):
                debts.append(
                    Debt(
                        name=d.get("name", "Unknown"),
                        balance=Decimal(str(d.get("balance", 0))),
                        interest_rate=Decimal(str(d.get("interest_rate", 0))),
                        minimum_payment=Decimal(str(d.get("minimum_payment", 0))),
                        debt_type=DebtType(d.get("debt_type", "other")),
                    )
                )
            elif isinstance(d, Debt):
                debts.append(d)

        if not debts:
            return {"debt_analysis": None, "debt_error": "No valid debts parsed"}

        comparison = compare_strategies(
            debts=debts,
            extra_payment=Decimal(str(extra_payment)),
        )

        return {
            "debt_analysis": {
                "snowball_months": comparison.snowball.months_to_payoff,
                "snowball_total_interest": float(comparison.snowball.total_interest),
                "avalanche_months": comparison.avalanche.months_to_payoff,
                "avalanche_total_interest": float(comparison.avalanche.total_interest),
                "recommended_strategy": comparison.faster_strategy,
                "interest_saved": float(comparison.interest_savings),
            },
        }


# ─── BudgetAnalyst ─────────────────────────────────────────────────


class BudgetAnalyst(DomainAgent):
    """Analyzes income and expenses for budget insights."""

    def __init__(self) -> None:
        super().__init__(
            name="BudgetAnalyst",
            role=AgentRole.ANALYST,
            goal=(
                "Analyze the user's income and expense data to calculate "
                "savings rate, expense ratios, and budget health indicators."
            ),
            backstory=(
                "Budget analyst who calculates deterministic financial "
                "metrics from user-provided income and expense data. "
                "Focuses on savings rate, needs/wants/savings ratios, "
                "and identifies areas of opportunity. Never accesses "
                "real bank data — works only with user-provided figures."
            ),
            system=_SYSTEM,
            tools=["budget.analyze"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate budget metrics from income and expenses."""
        monthly_income = context.get("monthly_income", 0)
        monthly_expenses = context.get("monthly_expenses", 0)
        expense_categories = context.get("expense_categories", {})

        if monthly_income <= 0:
            return {"budget_analysis": None, "budget_error": "Missing or zero income"}

        savings = monthly_income - monthly_expenses
        savings_rate = round(savings / monthly_income, 4) if monthly_income > 0 else 0.0

        # Classify expense categories
        needs_keywords = {
            "housing",
            "rent",
            "mortgage",
            "utilities",
            "food",
            "groceries",
            "transport",
            "transportation",
            "insurance",
            "healthcare",
            "childcare",
        }
        total_needs = sum(v for k, v in expense_categories.items() if k.lower() in needs_keywords)
        total_wants = monthly_expenses - total_needs

        needs_ratio = round(total_needs / monthly_income, 4) if monthly_income > 0 else 0.0
        wants_ratio = round(total_wants / monthly_income, 4) if monthly_income > 0 else 0.0

        return {
            "budget_analysis": {
                "monthly_income": monthly_income,
                "monthly_expenses": monthly_expenses,
                "monthly_savings": savings,
                "savings_rate": savings_rate,
                "needs_ratio": needs_ratio,
                "wants_ratio": wants_ratio,
                "savings_ratio": round(savings_rate, 4),
            },
        }


# ─── WealthValidator ──────────────────────────────────────────────


class WealthValidator(DomainAgent):
    """Validates wealth outputs for financial disclaimers and ethics."""

    def __init__(self) -> None:
        super().__init__(
            name="WealthValidator",
            role=AgentRole.VALIDATOR,
            goal=(
                "Ensure all wealth outputs include financial disclaimers, "
                "contain no guaranteed-returns language, and pass ethics "
                "checks. Verify all calculations are deterministic."
            ),
            backstory=(
                "Financial compliance validator who enforces the rule that "
                "all financial calculations must be deterministic (never "
                "LLM-generated), disclaimers must be present, and no "
                "specific investment advice is given."
            ),
            system=_SYSTEM,
            tools=["quality.validate_wealth_output"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate wealth outputs against quality gates."""
        from alchymine.agents.quality.validators import validate_wealth_output

        output: dict[str, Any] = {
            "disclaimers": context.get("disclaimers", [_WEALTH_DISCLAIMER]),
            "calculations": {},
        }

        # Collect any numeric calculation values
        budget = context.get("budget_analysis")
        if budget and isinstance(budget, dict):
            for key in ("savings_rate", "needs_ratio", "wants_ratio"):
                if key in budget:
                    output["calculations"][key] = budget[key]

        debt = context.get("debt_analysis")
        if debt and isinstance(debt, dict):
            for key in ("interest_saved", "snowball_total_interest", "avalanche_total_interest"):
                if key in debt:
                    output["calculations"][key] = debt[key]

        gate_result = validate_wealth_output(output)
        return {
            "wealth_quality": {
                "passed": gate_result.passed,
                "details": gate_result.details,
                "gate_name": gate_result.gate_name,
            },
        }


# ─── WealthNarrative ──────────────────────────────────────────────


class WealthNarrative(DomainAgent):
    """Generates wealth guidance narratives."""

    def __init__(self) -> None:
        super().__init__(
            name="WealthNarrative",
            role=AgentRole.GUIDE,
            goal=(
                "Generate a cohesive wealth guidance narrative that "
                "integrates archetype insights, lever priorities, debt "
                "analysis, and budget metrics."
            ),
            backstory=(
                "Financial narrator who weaves deterministic wealth "
                "calculations into an educational, empowering story. "
                "Never gives specific investment advice. Always includes "
                "disclaimers. Focuses on principles and education."
            ),
            system=_SYSTEM,
            tools=["narrative.generate"],
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a wealth narrative from upstream agent data."""
        sections: list[str] = [_WEALTH_DISCLAIMER]

        # Wealth archetype
        archetype = context.get("wealth_archetype")
        if archetype and isinstance(archetype, dict):
            name = archetype.get("name", "your archetype")
            sections.append(
                f"Your wealth archetype is {name}. "
                f"Understanding your financial personality can help you "
                f"make decisions that align with your natural strengths."
            )

        # Lever priorities
        levers = context.get("lever_priorities")
        if levers and isinstance(levers, list):
            top_levers = levers[:3]
            sections.append(f"Your top wealth focus areas are: {', '.join(top_levers)}.")

        # Debt analysis
        debt = context.get("debt_analysis")
        if debt and isinstance(debt, dict):
            strategy = debt.get("recommended_strategy", "")
            saved = debt.get("interest_saved", 0)
            if strategy:
                sections.append(
                    f"For debt payoff, the {strategy} strategy may save you "
                    f"approximately ${saved:.2f} in interest."
                )

        # Budget
        budget = context.get("budget_analysis")
        if budget and isinstance(budget, dict):
            savings_rate = budget.get("savings_rate", 0)
            sections.append(f"Your current savings rate is {savings_rate:.1%}.")

        narrative = "\n\n".join(sections)
        return {
            "wealth_narrative": narrative,
            "disclaimers": [_WEALTH_DISCLAIMER],
        }


# ─── Crew assembly ─────────────────────────────────────────────────


def build_wealth_crew() -> SystemCrew:
    """Assemble the Wealth system crew with all 6 agents and tasks."""
    archetype_analyst = WealthArchetypeAnalyst()
    lever_calculator = LeverCalculator()
    debt_strategist = DebtStrategist()
    budget_analyst = BudgetAnalyst()
    wealth_validator = WealthValidator()
    wealth_narrative = WealthNarrative()

    agents = [
        archetype_analyst,
        lever_calculator,
        debt_strategist,
        budget_analyst,
        wealth_validator,
        wealth_narrative,
    ]

    tasks = [
        AgentTask(
            name="map_wealth_archetype",
            description="Map user profile to a wealth archetype.",
            agent=archetype_analyst,
            expected_output="Dict with wealth archetype details.",
        ),
        AgentTask(
            name="prioritize_levers",
            description="Prioritize 5 wealth levers by user context.",
            agent=lever_calculator,
            expected_output="Dict with ordered lever priorities.",
        ),
        AgentTask(
            name="analyze_debt",
            description="Compare snowball vs. avalanche debt strategies.",
            agent=debt_strategist,
            expected_output="Dict with debt strategy comparison.",
        ),
        AgentTask(
            name="analyze_budget",
            description="Calculate savings rate and expense ratios.",
            agent=budget_analyst,
            expected_output="Dict with budget analysis metrics.",
        ),
        AgentTask(
            name="validate_wealth",
            description="Run financial disclaimer and ethics validation.",
            agent=wealth_validator,
            expected_output="Dict with wealth quality gate result.",
        ),
        AgentTask(
            name="generate_wealth_narrative",
            description="Generate educational wealth guidance narrative.",
            agent=wealth_narrative,
            expected_output="Narrative text with disclaimers.",
        ),
    ]

    return SystemCrew(name=_SYSTEM, agents=agents, tasks=tasks)

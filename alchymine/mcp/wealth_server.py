"""Wealth MCP server — archetype mapping, lever priorities, debt strategies.

Exposes the Generational Wealth system's deterministic engines
as MCP tools for Claude and other LLMs.

CRITICAL: All monetary calculations use Decimal precision.
Financial data is classified as Sensitive and never sent to LLMs.
"""

from __future__ import annotations

from decimal import Decimal

from alchymine.engine.profile import ArchetypeType, Intention, RiskTolerance, WealthContext
from alchymine.engine.wealth import compare_strategies, map_wealth_archetype, prioritize_levers
from alchymine.engine.wealth.debt import Debt, DebtType

from .base import MCPServer

server = MCPServer(name="alchymine-wealth", version="1.0.0")


# ─── Tool: map_wealth_archetype ─────────────────────────────────────────


@server.tool(
    name="map_wealth_archetype",
    description=(
        "Map a user's numerology life path, Jungian archetype, and risk "
        "tolerance to one of 8 wealth archetypes. Returns archetype name, "
        "description, primary levers, strengths, blind spots, and actions."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "life_path": {
                "type": "integer",
                "description": "Numerology Life Path number (1-9, 11, 22, 33)",
            },
            "archetype": {
                "type": "string",
                "description": (
                    "Primary Jungian archetype. One of: creator, sage, explorer, "
                    "mystic, ruler, lover, hero, caregiver, jester, innocent, rebel, everyman"
                ),
            },
            "risk_tolerance": {
                "type": "string",
                "description": "Financial risk tolerance: conservative, moderate, or aggressive",
            },
        },
        "required": ["life_path", "archetype", "risk_tolerance"],
    },
)
def map_wealth_archetype_tool(life_path: int, archetype: str, risk_tolerance: str) -> dict:
    """Map inputs to a wealth archetype."""
    arch_type = ArchetypeType(archetype)
    risk = RiskTolerance(risk_tolerance)
    result = map_wealth_archetype(life_path, arch_type, risk)
    return {
        "name": result.name,
        "description": result.description,
        "primary_levers": [lever.value for lever in result.primary_levers],
        "strengths": list(result.strengths),
        "blind_spots": list(result.blind_spots),
        "recommended_actions": list(result.recommended_actions),
    }


# ─── Tool: prioritize_levers ────────────────────────────────────────────


@server.tool(
    name="prioritize_levers",
    description=(
        "Prioritize the 5 wealth levers (EARN, KEEP, GROW, PROTECT, TRANSFER) "
        "based on financial context, risk tolerance, intention, and life path. "
        "Returns all 5 levers in priority order."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "risk_tolerance": {
                "type": "string",
                "description": "conservative, moderate, or aggressive",
            },
            "intention": {
                "type": "string",
                "description": (
                    "Primary intention: career, love, purpose, money, health, "
                    "family, business, or legacy"
                ),
            },
            "life_path": {
                "type": "integer",
                "description": "Numerology Life Path number (1-9, 11, 22, 33)",
            },
            "context": {
                "type": "object",
                "description": (
                    "Optional wealth context. Keys: income_range (str), "
                    "has_investments (bool), has_business (bool), "
                    "has_real_estate (bool), dependents (int), debt_level (str)"
                ),
            },
        },
        "required": ["risk_tolerance", "intention", "life_path"],
    },
)
def prioritize_levers_tool(
    risk_tolerance: str,
    intention: str,
    life_path: int,
    context: dict | None = None,
) -> list[str]:
    """Prioritize wealth levers based on user context."""
    risk = RiskTolerance(risk_tolerance)
    intent = Intention(intention)

    wealth_context = None
    if context is not None:
        wealth_context = WealthContext(**context)

    levers = prioritize_levers(
        wealth_context=wealth_context,
        risk_tolerance=risk,
        intentions=[intent],
        life_path=life_path,
    )
    return [lever.value for lever in levers]


# ─── Tool: compare_debt_strategies ──────────────────────────────────────


@server.tool(
    name="compare_debt_strategies",
    description=(
        "Compare snowball vs. avalanche debt payoff strategies. Returns "
        "total paid, total interest, months to payoff, interest savings, "
        "and which strategy is faster. All monetary values use exact "
        "decimal arithmetic."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "debts": {
                "type": "array",
                "description": (
                    "List of debt objects. Each must have: name (str), "
                    "balance (str, decimal), interest_rate (str, decimal as %), "
                    "minimum_payment (str, decimal). Optional: debt_type (str)."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "balance": {"type": "string"},
                        "interest_rate": {"type": "string"},
                        "minimum_payment": {"type": "string"},
                        "debt_type": {"type": "string"},
                    },
                    "required": ["name", "balance", "interest_rate", "minimum_payment"],
                },
            },
            "extra_payment": {
                "type": "string",
                "description": "Optional extra monthly payment above minimums (decimal string)",
            },
        },
        "required": ["debts"],
    },
)
def compare_debt_strategies_tool(debts: list[dict], extra_payment: str | None = None) -> dict:
    """Compare snowball vs. avalanche debt payoff strategies."""
    debt_objects = []
    for d in debts:
        debt_type = DebtType(d["debt_type"]) if "debt_type" in d else DebtType.OTHER
        debt_objects.append(
            Debt(
                name=d["name"],
                balance=Decimal(d["balance"]),
                interest_rate=Decimal(d["interest_rate"]),
                minimum_payment=Decimal(d["minimum_payment"]),
                debt_type=debt_type,
            )
        )

    extra = Decimal(extra_payment) if extra_payment else Decimal("0")
    comparison = compare_strategies(debt_objects, extra)

    return {
        "snowball": {
            "total_paid": str(comparison.snowball.total_paid),
            "total_interest": str(comparison.snowball.total_interest),
            "months_to_payoff": comparison.snowball.months_to_payoff,
        },
        "avalanche": {
            "total_paid": str(comparison.avalanche.total_paid),
            "total_interest": str(comparison.avalanche.total_interest),
            "months_to_payoff": comparison.avalanche.months_to_payoff,
        },
        "interest_savings": str(comparison.interest_savings),
        "faster_strategy": comparison.faster_strategy,
        "months_difference": comparison.months_difference,
    }


# ─── Resource: system info ──────────────────────────────────────────────


@server.resource(
    uri="alchymine://wealth/info",
    name="Wealth System Info",
    description="Metadata about the Wealth MCP server and its available tools.",
)
def wealth_info() -> dict:
    """Return metadata about the Wealth system."""
    return {
        "name": server.name,
        "version": server.version,
        "tools": [t["name"] for t in server.list_tools()],
        "description": (
            "Generational Wealth system — wealth archetype mapping, lever "
            "prioritization, and debt payoff strategy comparison. All "
            "calculations are deterministic and use exact decimal arithmetic. "
            "Financial data is Sensitive and never sent to LLMs."
        ),
    }

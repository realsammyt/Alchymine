"""Tests for the Wealth MCP server."""

import pytest

from alchymine.mcp.wealth_server import server


# ─── Test: tool listing ──────────────────────────────────────────────────


def test_lists_all_tools():
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    assert names == {
        "map_wealth_archetype",
        "prioritize_levers",
        "compare_debt_strategies",
    }


def test_tool_schemas_valid():
    for tool in server.list_tools():
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema


# ─── Test: resource listing ──────────────────────────────────────────────


def test_lists_resources():
    resources = server.list_resources()
    assert len(resources) == 1
    assert resources[0]["uri"] == "alchymine://wealth/info"


@pytest.mark.asyncio
async def test_read_info_resource():
    result = await server.read_resource("alchymine://wealth/info")
    assert result["name"] == "alchymine-wealth"
    assert len(result["tools"]) == 3


# ─── Test: map_wealth_archetype ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_map_wealth_archetype_builder():
    result = await server.call_tool(
        "map_wealth_archetype",
        {
            "life_path": 4,
            "archetype": "ruler",
            "risk_tolerance": "conservative",
        },
    )
    assert result["name"] == "The Builder"
    assert "description" in result
    assert "primary_levers" in result
    assert isinstance(result["primary_levers"], list)
    assert "strengths" in result
    assert "blind_spots" in result
    assert "recommended_actions" in result


@pytest.mark.asyncio
async def test_map_wealth_archetype_warrior():
    result = await server.call_tool(
        "map_wealth_archetype",
        {
            "life_path": 1,
            "archetype": "hero",
            "risk_tolerance": "aggressive",
        },
    )
    assert result["name"] == "The Warrior"


@pytest.mark.asyncio
async def test_map_wealth_archetype_deterministic():
    r1 = await server.call_tool(
        "map_wealth_archetype",
        {"life_path": 7, "archetype": "sage", "risk_tolerance": "moderate"},
    )
    r2 = await server.call_tool(
        "map_wealth_archetype",
        {"life_path": 7, "archetype": "sage", "risk_tolerance": "moderate"},
    )
    assert r1 == r2


@pytest.mark.asyncio
async def test_map_wealth_archetype_missing_field():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool(
            "map_wealth_archetype",
            {"life_path": 4, "archetype": "ruler"},
        )


@pytest.mark.asyncio
async def test_map_wealth_archetype_invalid_archetype():
    with pytest.raises(ValueError):
        await server.call_tool(
            "map_wealth_archetype",
            {"life_path": 4, "archetype": "invalid", "risk_tolerance": "moderate"},
        )


# ─── Test: prioritize_levers ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prioritize_levers_basic():
    result = await server.call_tool(
        "prioritize_levers",
        {
            "risk_tolerance": "moderate",
            "intention": "money",
            "life_path": 8,
        },
    )
    assert isinstance(result, list)
    assert len(result) == 5
    assert set(result) == {"EARN", "KEEP", "GROW", "PROTECT", "TRANSFER"}


@pytest.mark.asyncio
async def test_prioritize_levers_with_context():
    result = await server.call_tool(
        "prioritize_levers",
        {
            "risk_tolerance": "conservative",
            "intention": "family",
            "life_path": 6,
            "context": {
                "income_range": "$50k-$75k",
                "has_investments": False,
                "has_business": False,
                "has_real_estate": False,
                "dependents": 2,
                "debt_level": "moderate",
            },
        },
    )
    assert isinstance(result, list)
    assert len(result) == 5
    # With family intention + dependents, PROTECT should be high priority
    assert result[0] == "PROTECT"


@pytest.mark.asyncio
async def test_prioritize_levers_missing_field():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool(
            "prioritize_levers",
            {"risk_tolerance": "moderate", "intention": "money"},
        )


# ─── Test: compare_debt_strategies ──────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_debt_strategies_basic():
    result = await server.call_tool(
        "compare_debt_strategies",
        {
            "debts": [
                {
                    "name": "Credit Card A",
                    "balance": "5000.00",
                    "interest_rate": "19.99",
                    "minimum_payment": "100.00",
                    "debt_type": "credit_card",
                },
                {
                    "name": "Student Loan",
                    "balance": "15000.00",
                    "interest_rate": "5.50",
                    "minimum_payment": "200.00",
                    "debt_type": "student_loan",
                },
            ],
            "extra_payment": "100.00",
        },
    )
    assert "snowball" in result
    assert "avalanche" in result
    assert "interest_savings" in result
    assert "faster_strategy" in result
    assert "months_difference" in result

    # Both strategies should have valid data
    for strategy_key in ["snowball", "avalanche"]:
        s = result[strategy_key]
        assert "total_paid" in s
        assert "total_interest" in s
        assert "months_to_payoff" in s
        # Total paid should be parseable as a decimal string
        assert float(s["total_paid"]) > 0


@pytest.mark.asyncio
async def test_compare_debt_strategies_no_extra():
    result = await server.call_tool(
        "compare_debt_strategies",
        {
            "debts": [
                {
                    "name": "Loan",
                    "balance": "1000.00",
                    "interest_rate": "10.00",
                    "minimum_payment": "50.00",
                },
            ],
        },
    )
    assert result["snowball"]["months_to_payoff"] > 0
    assert result["avalanche"]["months_to_payoff"] > 0


@pytest.mark.asyncio
async def test_compare_debt_strategies_empty_debts():
    result = await server.call_tool(
        "compare_debt_strategies",
        {"debts": []},
    )
    assert result["snowball"]["months_to_payoff"] == 0
    assert result["avalanche"]["months_to_payoff"] == 0


@pytest.mark.asyncio
async def test_compare_debt_strategies_missing_debts():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("compare_debt_strategies", {})


@pytest.mark.asyncio
async def test_compare_debt_strategies_deterministic():
    debts = [
        {
            "name": "A",
            "balance": "3000.00",
            "interest_rate": "15.00",
            "minimum_payment": "75.00",
        },
        {
            "name": "B",
            "balance": "1000.00",
            "interest_rate": "22.00",
            "minimum_payment": "50.00",
        },
    ]
    r1 = await server.call_tool("compare_debt_strategies", {"debts": debts})
    r2 = await server.call_tool("compare_debt_strategies", {"debts": debts})
    assert r1 == r2

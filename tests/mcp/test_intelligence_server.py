"""Tests for the Intelligence MCP server."""

import pytest

from alchymine.mcp.intelligence_server import server


# ─── Test: tool listing ──────────────────────────────────────────────────


def test_lists_all_tools():
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    assert names == {
        "calculate_numerology",
        "calculate_astrology",
        "assess_personality",
        "calculate_biorhythm",
    }


def test_tool_schemas_have_required_fields():
    for tool in server.list_tools():
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema


# ─── Test: resource listing ──────────────────────────────────────────────


def test_lists_resources():
    resources = server.list_resources()
    assert len(resources) == 1
    assert resources[0]["uri"] == "alchymine://intelligence/info"


@pytest.mark.asyncio
async def test_read_info_resource():
    result = await server.read_resource("alchymine://intelligence/info")
    assert result["name"] == "alchymine-intelligence"
    assert "tools" in result
    assert len(result["tools"]) == 4


# ─── Test: calculate_numerology ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_numerology_valid():
    result = await server.call_tool(
        "calculate_numerology",
        {"name": "John Smith", "birth_date": "1990-03-15"},
    )
    assert "life_path" in result
    assert "expression" in result
    assert "soul_urge" in result
    assert "personality" in result
    assert "personal_year" in result
    assert "personal_month" in result
    assert "maturity" in result
    assert "is_master_number" in result
    assert isinstance(result["life_path"], int)
    assert 1 <= result["life_path"] <= 33


@pytest.mark.asyncio
async def test_calculate_numerology_deterministic():
    r1 = await server.call_tool(
        "calculate_numerology",
        {"name": "Jane Doe", "birth_date": "1985-07-22"},
    )
    r2 = await server.call_tool(
        "calculate_numerology",
        {"name": "Jane Doe", "birth_date": "1985-07-22"},
    )
    assert r1 == r2


@pytest.mark.asyncio
async def test_calculate_numerology_missing_name():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("calculate_numerology", {"birth_date": "1990-01-01"})


@pytest.mark.asyncio
async def test_calculate_numerology_invalid_date():
    with pytest.raises(ValueError):
        await server.call_tool(
            "calculate_numerology",
            {"name": "Test", "birth_date": "not-a-date"},
        )


# ─── Test: calculate_astrology ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_astrology_valid():
    result = await server.call_tool(
        "calculate_astrology",
        {"birth_date": "1992-03-15"},
    )
    assert result["sun_sign"] == "Pisces"
    assert "sun_degree" in result
    assert isinstance(result["sun_degree"], float)


@pytest.mark.asyncio
async def test_calculate_astrology_cancer():
    result = await server.call_tool(
        "calculate_astrology",
        {"birth_date": "1990-07-04"},
    )
    assert result["sun_sign"] == "Cancer"


@pytest.mark.asyncio
async def test_calculate_astrology_missing_date():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("calculate_astrology", {})


# ─── Test: assess_personality ────────────────────────────────────────────


def _make_big_five_responses():
    """Create a full set of Big Five responses (all neutral 3)."""
    return {f"bf_{t}{i}": 3 for t in "eacno" for i in range(1, 5)}


def _make_enneagram_responses():
    """Create a full set of Enneagram responses."""
    return {f"enn_{i}": 3 for i in range(1, 10)}


@pytest.mark.asyncio
async def test_assess_personality_valid():
    result = await server.call_tool(
        "assess_personality",
        {
            "big_five_responses": _make_big_five_responses(),
            "enneagram_responses": _make_enneagram_responses(),
        },
    )
    assert "big_five" in result
    assert "enneagram" in result
    bf = result["big_five"]
    assert all(k in bf for k in ["openness", "conscientiousness", "extraversion",
                                  "agreeableness", "neuroticism"])
    assert all(0 <= v <= 100 for v in bf.values())
    enn = result["enneagram"]
    assert 1 <= enn["primary_type"] <= 9
    assert 1 <= enn["wing"] <= 9


@pytest.mark.asyncio
async def test_assess_personality_missing_big_five():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool(
            "assess_personality",
            {"enneagram_responses": _make_enneagram_responses()},
        )


# ─── Test: calculate_biorhythm ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_biorhythm_valid():
    result = await server.call_tool(
        "calculate_biorhythm",
        {"birth_date": "1990-01-01", "target_date": "2024-06-15"},
    )
    assert "physical" in result
    assert "emotional" in result
    assert "intellectual" in result
    assert -1.0 <= result["physical"] <= 1.0
    assert 0 <= result["physical_percentage"] <= 100
    assert result["days_alive"] > 0
    assert result["evidence_rating"] == "LOW"
    assert "methodology_note" in result


@pytest.mark.asyncio
async def test_calculate_biorhythm_same_day():
    result = await server.call_tool(
        "calculate_biorhythm",
        {"birth_date": "2000-01-01", "target_date": "2000-01-01"},
    )
    assert result["days_alive"] == 0
    # At day 0, all cycles should be at sin(0) = 0
    assert result["physical"] == 0.0
    assert result["emotional"] == 0.0
    assert result["intellectual"] == 0.0


@pytest.mark.asyncio
async def test_calculate_biorhythm_target_before_birth():
    with pytest.raises(ValueError):
        await server.call_tool(
            "calculate_biorhythm",
            {"birth_date": "2000-01-01", "target_date": "1999-12-31"},
        )


@pytest.mark.asyncio
async def test_calculate_biorhythm_missing_target():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool(
            "calculate_biorhythm",
            {"birth_date": "1990-01-01"},
        )

"""Tests for the Perspective MCP server."""

import pytest

from alchymine.mcp.perspective_server import server


# ─── Test: tool listing ──────────────────────────────────────────────────


def test_lists_all_tools():
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    assert names == {"detect_biases", "assess_kegan_stage", "apply_framework"}


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
    assert resources[0]["uri"] == "alchymine://perspective/info"


@pytest.mark.asyncio
async def test_read_info_resource():
    result = await server.read_resource("alchymine://perspective/info")
    assert result["name"] == "alchymine-perspective"
    assert len(result["tools"]) == 3


# ─── Test: detect_biases ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_detect_biases_confirmation_bias():
    result = await server.call_tool(
        "detect_biases",
        {"text": "I knew it all along! This proves my point exactly as I expected."},
    )
    assert isinstance(result, list)
    assert len(result) > 0
    bias_types = {b["bias_type"] for b in result}
    assert "confirmation_bias" in bias_types
    # Check structure of each bias entry
    for bias in result:
        assert "bias_type" in bias
        assert "bias_name" in bias
        assert "description" in bias
        assert "matched_phrases" in bias
        assert "confidence" in bias
        assert "source" in bias
        assert 0 <= bias["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_detect_biases_sunk_cost():
    result = await server.call_tool(
        "detect_biases",
        {"text": "I've already invested so much time, I can't give up now after all the effort."},
    )
    bias_types = {b["bias_type"] for b in result}
    assert "sunk_cost_fallacy" in bias_types


@pytest.mark.asyncio
async def test_detect_biases_no_bias():
    result = await server.call_tool(
        "detect_biases",
        {"text": "The data shows a clear trend over the past five quarters."},
    )
    # May or may not detect biases; result should be a list
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_detect_biases_empty_text():
    result = await server.call_tool(
        "detect_biases",
        {"text": ""},
    )
    assert result == []


@pytest.mark.asyncio
async def test_detect_biases_missing_text():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("detect_biases", {})


# ─── Test: assess_kegan_stage ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assess_kegan_stage_socialized():
    result = await server.call_tool(
        "assess_kegan_stage",
        {
            "responses": {
                "self_awareness": 3,
                "perspective_taking": 3,
                "relationship_to_authority": 3.5,
                "conflict_tolerance": 2.5,
                "systems_thinking": 2.5,
            },
        },
    )
    assert result["stage"] == "socialized"
    assert result["stage_number"] == 3
    assert result["name"] == "Socialized"
    assert "description" in result
    assert "strengths" in result
    assert isinstance(result["strengths"], list)
    assert "growth_edges" in result
    assert "source" in result
    assert "methodology" in result


@pytest.mark.asyncio
async def test_assess_kegan_stage_self_authoring():
    result = await server.call_tool(
        "assess_kegan_stage",
        {
            "responses": {
                "self_awareness": 4,
                "perspective_taking": 4,
                "relationship_to_authority": 4.5,
                "conflict_tolerance": 4,
                "systems_thinking": 3.5,
            },
        },
    )
    assert result["stage"] == "self-authoring"
    assert result["stage_number"] == 4


@pytest.mark.asyncio
async def test_assess_kegan_stage_minimal_dimensions():
    result = await server.call_tool(
        "assess_kegan_stage",
        {
            "responses": {
                "self_awareness": 5,
                "systems_thinking": 5,
            },
        },
    )
    assert result["stage"] == "self-transforming"
    assert result["stage_number"] == 5


@pytest.mark.asyncio
async def test_assess_kegan_stage_too_few_dimensions():
    with pytest.raises(ValueError, match="At least 2 valid dimensions"):
        await server.call_tool(
            "assess_kegan_stage",
            {"responses": {"self_awareness": 3}},
        )


@pytest.mark.asyncio
async def test_assess_kegan_stage_invalid_score():
    with pytest.raises(ValueError, match="must be between 1 and 5"):
        await server.call_tool(
            "assess_kegan_stage",
            {"responses": {"self_awareness": 0, "perspective_taking": 3}},
        )


@pytest.mark.asyncio
async def test_assess_kegan_stage_missing_responses():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("assess_kegan_stage", {})


# ─── Test: apply_framework — weighted_matrix ─────────────────────────────


@pytest.mark.asyncio
async def test_apply_framework_weighted_matrix():
    result = await server.call_tool(
        "apply_framework",
        {
            "framework_type": "weighted_matrix",
            "decision": "Choose a new city to live in",
            "options": {
                "options": ["City A", "City B", "City C"],
                "criteria": [
                    {
                        "name": "Cost of Living",
                        "weight": 0.4,
                        "scores": {"City A": 8, "City B": 5, "City C": 7},
                    },
                    {
                        "name": "Job Market",
                        "weight": 0.6,
                        "scores": {"City A": 6, "City B": 9, "City C": 7},
                    },
                ],
            },
        },
    )
    assert "ranked_options" in result
    assert "criteria_breakdown" in result
    assert "methodology" in result
    assert len(result["ranked_options"]) == 3
    # Each ranked option should have option name and weighted_score
    for opt in result["ranked_options"]:
        assert "option" in opt
        assert "weighted_score" in opt


# ─── Test: apply_framework — pros_cons ───────────────────────────────────


@pytest.mark.asyncio
async def test_apply_framework_pros_cons():
    result = await server.call_tool(
        "apply_framework",
        {
            "framework_type": "pros_cons",
            "decision": "Accept the job offer",
            "options": {
                "pros": ["Higher salary", "Better location", "Growth potential"],
                "cons": ["Longer commute"],
            },
        },
    )
    assert result["option"] == "Accept the job offer"
    assert result["pro_count"] == 3
    assert result["con_count"] == 1
    assert result["balance_score"] > 0  # More pros than cons
    assert "assessment" in result
    assert "methodology" in result


# ─── Test: apply_framework — six_hats ────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_framework_six_hats():
    result = await server.call_tool(
        "apply_framework",
        {
            "framework_type": "six_hats",
            "decision": "Launch a new product",
            "options": {
                "perspectives": {
                    "white": "Market research shows 30% growth potential",
                    "red": "I feel excited but nervous",
                    "black": "Competition is fierce, could fail",
                    "yellow": "Could establish market leadership",
                },
            },
        },
    )
    assert result["problem"] == "Launch a new product"
    assert "hats" in result
    assert len(result["hats"]) == 6
    assert "missing_hats" in result
    assert set(result["missing_hats"]) == {"blue", "green"}
    assert "coverage_score" in result
    # 4 out of 6 hats provided
    assert abs(result["coverage_score"] - 4 / 6) < 0.01
    assert "synthesis" in result
    assert "methodology" in result


# ─── Test: apply_framework — invalid ─────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_framework_invalid_type():
    with pytest.raises(ValueError, match="Unknown framework"):
        await server.call_tool(
            "apply_framework",
            {
                "framework_type": "nonexistent",
                "decision": "Test",
                "options": {},
            },
        )


@pytest.mark.asyncio
async def test_apply_framework_missing_fields():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool(
            "apply_framework",
            {"framework_type": "pros_cons"},
        )

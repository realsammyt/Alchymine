"""Tests for the Creative MCP server."""

import pytest

from alchymine.mcp.creative_server import server


# ─── Test: tool listing ──────────────────────────────────────────────────


def test_lists_all_tools():
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    assert names == {
        "assess_guilford",
        "generate_style_fingerprint",
        "suggest_projects",
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
    assert resources[0]["uri"] == "alchymine://creative/info"


@pytest.mark.asyncio
async def test_read_info_resource():
    result = await server.read_resource("alchymine://creative/info")
    assert result["name"] == "alchymine-creative"
    assert len(result["tools"]) == 3


# ─── Test: assess_guilford ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assess_guilford_direct_scores():
    result = await server.call_tool(
        "assess_guilford",
        {
            "responses": {
                "fluency": 75,
                "flexibility": 60,
                "originality": 85,
                "elaboration": 50,
                "sensitivity": 70,
                "redefinition": 40,
            },
        },
    )
    assert result["fluency"] == 75.0
    assert result["flexibility"] == 60.0
    assert result["originality"] == 85.0
    assert result["elaboration"] == 50.0
    assert result["sensitivity"] == 70.0
    assert result["redefinition"] == 40.0


@pytest.mark.asyncio
async def test_assess_guilford_question_scores():
    result = await server.call_tool(
        "assess_guilford",
        {
            "responses": {
                "fluency_1": 70,
                "fluency_2": 80,
                "fluency_3": 90,
                "flexibility_1": 50,
                "flexibility_2": 60,
                "flexibility_3": 70,
                "originality_1": 60,
                "originality_2": 60,
                "originality_3": 60,
                "elaboration_1": 40,
                "elaboration_2": 40,
                "elaboration_3": 40,
                "sensitivity_1": 80,
                "sensitivity_2": 80,
                "sensitivity_3": 80,
                "redefinition_1": 30,
                "redefinition_2": 30,
                "redefinition_3": 30,
            },
        },
    )
    assert result["fluency"] == 80.0  # avg of 70, 80, 90
    assert result["flexibility"] == 60.0  # avg of 50, 60, 70
    assert result["originality"] == 60.0
    assert result["elaboration"] == 40.0
    assert result["sensitivity"] == 80.0
    assert result["redefinition"] == 30.0


@pytest.mark.asyncio
async def test_assess_guilford_empty_responses():
    result = await server.call_tool(
        "assess_guilford",
        {"responses": {}},
    )
    # All scores should default to 0 when no responses provided
    for key in ["fluency", "flexibility", "originality",
                "elaboration", "sensitivity", "redefinition"]:
        assert result[key] == 0.0


@pytest.mark.asyncio
async def test_assess_guilford_missing_responses():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("assess_guilford", {})


# ─── Test: generate_style_fingerprint ───────────────────────────────────


@pytest.mark.asyncio
async def test_generate_style_fingerprint_full():
    result = await server.call_tool(
        "generate_style_fingerprint",
        {
            "guilford_scores": {
                "fluency": 80,
                "flexibility": 70,
                "originality": 90,
                "elaboration": 50,
                "sensitivity": 60,
                "redefinition": 40,
            },
            "creative_dna": {
                "structure_vs_improvisation": 0.7,
                "collaboration_vs_solitude": 0.3,
                "convergent_vs_divergent": 0.8,
                "primary_sensory_mode": "visual",
                "creative_peak": "morning",
            },
        },
    )
    assert "guilford_summary" in result
    assert "dna_summary" in result
    assert "dominant_components" in result
    assert "creative_style" in result
    assert "overall_score" in result
    assert len(result["dominant_components"]) == 3
    assert result["dominant_components"][0] == "originality"  # highest score


@pytest.mark.asyncio
async def test_generate_style_fingerprint_without_dna():
    result = await server.call_tool(
        "generate_style_fingerprint",
        {
            "guilford_scores": {
                "fluency": 50,
                "flexibility": 50,
                "originality": 50,
                "elaboration": 50,
                "sensitivity": 50,
                "redefinition": 50,
            },
        },
    )
    assert "guilford_summary" in result
    assert "dna_summary" in result
    assert result["overall_score"] == 50.0


@pytest.mark.asyncio
async def test_generate_style_fingerprint_missing_scores():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("generate_style_fingerprint", {})


# ─── Test: suggest_projects ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_projects_beginner():
    result = await server.call_tool(
        "suggest_projects",
        {
            "guilford_scores": {
                "fluency": 90,
                "flexibility": 50,
                "originality": 70,
                "elaboration": 40,
                "sensitivity": 30,
                "redefinition": 20,
            },
            "skill_level": "beginner",
        },
    )
    assert isinstance(result, list)
    assert len(result) > 0
    for proj in result:
        assert "title" in proj
        assert "description" in proj
        assert "type" in proj


@pytest.mark.asyncio
async def test_suggest_projects_intermediate():
    result = await server.call_tool(
        "suggest_projects",
        {
            "guilford_scores": {
                "fluency": 80,
                "flexibility": 80,
                "originality": 80,
                "elaboration": 80,
                "sensitivity": 80,
                "redefinition": 80,
            },
            "skill_level": "intermediate",
        },
    )
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_suggest_projects_default_skill_level():
    result = await server.call_tool(
        "suggest_projects",
        {
            "guilford_scores": {
                "fluency": 60,
                "flexibility": 60,
                "originality": 60,
                "elaboration": 60,
                "sensitivity": 60,
                "redefinition": 60,
            },
        },
    )
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_suggest_projects_missing_scores():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("suggest_projects", {})

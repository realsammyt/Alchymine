"""Tests for the Healing MCP server."""

import pytest

from alchymine.mcp.healing_server import server

# ─── Test: tool listing ──────────────────────────────────────────────────


def test_lists_all_tools():
    tools = server.list_tools()
    names = {t["name"] for t in tools}
    assert names == {
        "detect_crisis",
        "match_modalities",
        "get_breathwork",
        "list_skills",
        "run_skill",
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
    assert resources[0]["uri"] == "alchymine://healing/info"


@pytest.mark.asyncio
async def test_read_info_resource():
    result = await server.read_resource("alchymine://healing/info")
    assert result["name"] == "alchymine-healing"
    assert "ethics_note" in result


# ─── Test: detect_crisis ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_detect_crisis_positive():
    result = await server.call_tool(
        "detect_crisis",
        {"text": "I feel suicidal and want to end my life"},
    )
    assert result is not None
    assert result["severity"] == "emergency"
    assert len(result["matched_keywords"]) > 0
    assert len(result["resources"]) > 0
    assert len(result["disclaimers"]) > 0


@pytest.mark.asyncio
async def test_detect_crisis_medium_severity():
    result = await server.call_tool(
        "detect_crisis",
        {"text": "I feel completely hopeless and helpless"},
    )
    assert result is not None
    assert result["severity"] == "medium"


@pytest.mark.asyncio
async def test_detect_crisis_high_severity():
    result = await server.call_tool(
        "detect_crisis",
        {"text": "I am experiencing domestic violence"},
    )
    assert result is not None
    assert result["severity"] == "high"


@pytest.mark.asyncio
async def test_detect_crisis_negative():
    result = await server.call_tool(
        "detect_crisis",
        {"text": "I had a great day and feel wonderful"},
    )
    assert result is None


@pytest.mark.asyncio
async def test_detect_crisis_empty_text():
    result = await server.call_tool(
        "detect_crisis",
        {"text": ""},
    )
    assert result is None


@pytest.mark.asyncio
async def test_detect_crisis_missing_text():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("detect_crisis", {})


# ─── Test: match_modalities ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_match_modalities_valid():
    result = await server.call_tool(
        "match_modalities",
        {
            "archetype": "creator",
            "big_five": {
                "openness": 75.0,
                "conscientiousness": 60.0,
                "extraversion": 50.0,
                "agreeableness": 65.0,
                "neuroticism": 40.0,
            },
            "intention": "purpose",
        },
    )
    assert isinstance(result, list)
    assert len(result) > 0
    for item in result:
        assert "modality" in item
        assert "skill_trigger" in item
        assert "preference_score" in item
        assert "difficulty_level" in item
        assert 0 <= item["preference_score"] <= 1


@pytest.mark.asyncio
async def test_match_modalities_different_archetype():
    result = await server.call_tool(
        "match_modalities",
        {
            "archetype": "hero",
            "big_five": {
                "openness": 40.0,
                "conscientiousness": 80.0,
                "extraversion": 70.0,
                "agreeableness": 50.0,
                "neuroticism": 60.0,
            },
            "intention": "health",
        },
    )
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_match_modalities_missing_archetype():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool(
            "match_modalities",
            {
                "big_five": {
                    "openness": 50.0,
                    "conscientiousness": 50.0,
                    "extraversion": 50.0,
                    "agreeableness": 50.0,
                    "neuroticism": 50.0,
                },
                "intention": "career",
            },
        )


@pytest.mark.asyncio
async def test_match_modalities_invalid_archetype():
    with pytest.raises(ValueError):
        await server.call_tool(
            "match_modalities",
            {
                "archetype": "invalid_type",
                "big_five": {
                    "openness": 50.0,
                    "conscientiousness": 50.0,
                    "extraversion": 50.0,
                    "agreeableness": 50.0,
                    "neuroticism": 50.0,
                },
                "intention": "career",
            },
        )


# ─── Test: get_breathwork ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_breathwork_foundation():
    result = await server.call_tool(
        "get_breathwork",
        {"difficulty": "foundation"},
    )
    assert "name" in result
    assert "inhale_seconds" in result
    assert "hold_seconds" in result
    assert "exhale_seconds" in result
    assert "hold_empty_seconds" in result
    assert "cycles" in result
    assert "description" in result
    assert result["difficulty"] == "foundation"


@pytest.mark.asyncio
async def test_get_breathwork_with_intention():
    result = await server.call_tool(
        "get_breathwork",
        {"difficulty": "foundation", "intention": "calm"},
    )
    assert result["name"] in ["coherence", "relaxing_4_7_8", "box_breathing"]


@pytest.mark.asyncio
async def test_get_breathwork_developing():
    result = await server.call_tool(
        "get_breathwork",
        {"difficulty": "developing", "intention": "energy"},
    )
    assert "name" in result
    # At developing level with energy intention, should get wim_hof_lite or box_breathing
    assert result["name"] in ["wim_hof_lite", "box_breathing"]


@pytest.mark.asyncio
async def test_get_breathwork_missing_difficulty():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("get_breathwork", {})


@pytest.mark.asyncio
async def test_get_breathwork_invalid_difficulty():
    with pytest.raises(ValueError):
        await server.call_tool(
            "get_breathwork",
            {"difficulty": "impossible"},
        )


# ─── Test: list_skills ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_skills_all():
    result = await server.call_tool("list_skills", {})
    assert isinstance(result, list)
    assert len(result) >= 15
    for item in result:
        assert "name" in item
        assert "title" in item
        assert "modality" in item
        assert "evidence_rating" in item
        assert "duration_minutes" in item


@pytest.mark.asyncio
async def test_list_skills_by_modality():
    result = await server.call_tool("list_skills", {"modality": "breathwork"})
    assert isinstance(result, list)
    assert len(result) >= 1
    for item in result:
        assert item["modality"] == "breathwork"


@pytest.mark.asyncio
async def test_list_skills_unknown_modality():
    result = await server.call_tool("list_skills", {"modality": "nonexistent"})
    assert result == []


# ─── Test: run_skill ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_skill_valid():
    result = await server.call_tool("run_skill", {"name": "breathwork-box-breathing"})
    assert result["name"] == "breathwork-box-breathing"
    assert result["title"] == "Box Breathing (4-4-4-4)"
    assert result["modality"] == "breathwork"
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) > 0
    assert result["evidence_rating"] == "B"
    assert isinstance(result["contraindications"], list)
    assert result["duration_minutes"] == 6
    assert "description" in result


@pytest.mark.asyncio
async def test_run_skill_not_found():
    with pytest.raises(ValueError, match="Skill not found"):
        await server.call_tool("run_skill", {"name": "nonexistent-skill"})


@pytest.mark.asyncio
async def test_run_skill_missing_name():
    with pytest.raises(ValueError, match="Missing required argument"):
        await server.call_tool("run_skill", {})

"""MCP healing server reads the same skill set as REST (#265).

Before this, the MCP server built its own registry from the bundled
directory only, so a skill mounted through ``HEALING_SKILLS_EXTERNAL_DIR``
was visible over REST and invisible over MCP. Both now resolve through
``engine.healing.skills.get_skill_registry``.

Fixture skills use invented names. Nothing here names a real
practitioner, publisher or tradition-holder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from alchymine.engine.healing.skills import (
    SkillRegistry,
    build_skill_registry,
    set_skill_registry,
)
from alchymine.mcp.healing_server import server


@pytest.fixture(autouse=True)
def _clear_global_registry() -> Any:
    set_skill_registry(None)
    yield
    set_skill_registry(None)


@pytest.fixture
def external_dir(tmp_path: Path) -> Path:
    d = tmp_path / "external"
    d.mkdir()
    (d / "invented-shore-walking.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "invented-shore-walking",
                "modality": "nature_healing",
                "title": "Shore Walking",
                "description": "Walk a stretch of shoreline slowly and notice the footing.",
                "steps": ["Find a stretch of shore.", "Walk it slowly.", "Turn around."],
                "evidence_rating": "D",
                "contraindications": [],
                "duration_minutes": 20,
                "bundled": False,
                "license": "Apache-2.0",
                "attribution": "Wren Halloway",
                "source_url": "https://example.invalid/skills",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return d


@pytest.mark.asyncio
async def test_list_skills_sees_external_dir(external_dir: Path) -> None:
    set_skill_registry(build_skill_registry(external_dir))
    result = await server.call_tool("list_skills", {})
    names = {item["name"] for item in result}
    assert "invented-shore-walking" in names
    assert "breathwork-box-breathing" in names


@pytest.mark.asyncio
async def test_run_skill_resolves_an_external_skill(external_dir: Path) -> None:
    set_skill_registry(build_skill_registry(external_dir))
    result = await server.call_tool("run_skill", {"name": "invented-shore-walking"})
    assert result["title"] == "Shore Walking"


@pytest.mark.asyncio
async def test_run_skill_carries_attribution(external_dir: Path) -> None:
    """Attribution travels with the content, not only with the REST payload."""
    set_skill_registry(build_skill_registry(external_dir))
    result = await server.call_tool("run_skill", {"name": "invented-shore-walking"})
    assert result["license"] == "Apache-2.0"
    assert result["attribution"] == "Wren Halloway"
    assert result["source_url"] == "https://example.invalid/skills"


@pytest.mark.asyncio
async def test_bundled_skill_reports_its_own_licensing() -> None:
    result = await server.call_tool("run_skill", {"name": "breathwork-box-breathing"})
    assert result["license"] == "CC-BY-NC-SA-4.0"
    assert result["attribution"] == "Alchymine Contributors"


@pytest.mark.asyncio
async def test_mcp_and_rest_share_one_registry(external_dir: Path) -> None:
    """One loader path, so the two surfaces cannot drift apart."""
    from alchymine.api.routers.healing_skills import get_skill_registry as rest_registry

    fixture: SkillRegistry = build_skill_registry(external_dir)
    set_skill_registry(fixture)

    rest_names = {s.name for s in rest_registry().list_all()}
    mcp_names = {item["name"] for item in await server.call_tool("list_skills", {})}
    assert rest_names == mcp_names

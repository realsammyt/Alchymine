"""Healing skills API endpoints — public reference data, no auth required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

# The registry is built in the engine, not here, so the MCP server mounts
# the same bundled-plus-external skill set from the same configuration.
# Building it in this router is what let the two surfaces drift apart
# (issue #265), and it is where a mistyped HEALING_SKILLS_EXTERNAL_DIR
# used to be warned past instead of raised.
from alchymine.engine.healing.skills import (
    SkillDefinition,
    SkillNotFoundError,
    SkillRegistry,
    get_skill_registry,
)

router = APIRouter()


@router.get("/healing/skills")
async def list_healing_skills(
    modality: str | None = Query(None, description="Optional modality filter"),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> list[SkillDefinition]:
    """List all healing skills, optionally filtered by modality."""
    if modality is not None:
        return registry.list_by_modality(modality)
    return registry.list_all()


@router.get("/healing/skills/{name}")
async def get_healing_skill(
    name: str,
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillDefinition:
    """Return a single healing skill by name."""
    try:
        return registry.get(name)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}") from exc

"""Healing skills API endpoints — public reference data, no auth required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from alchymine.engine.healing.skills import (
    SkillDefinition,
    SkillNotFoundError,
    SkillRegistry,
    get_default_yaml_dir,
)

router = APIRouter()

# Module-level registry, loaded on first request and reused thereafter.
_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    """FastAPI dependency that returns the lazy-loaded SkillRegistry."""
    global _registry
    if _registry is None:
        reg = SkillRegistry()
        reg.load_directory(get_default_yaml_dir())
        _registry = reg
    return _registry


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

"""Practice library endpoints — read-only views onto the mounted packs.

Auth is required on every route but no plan gate is applied: nothing
here costs money, and gating the retention loop would defeat the loop.

The registry is built at application startup, so these handlers never
touch the filesystem.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.practice import (
    PackManifest,
    PackNotFoundError,
    PracticeDefinition,
    PracticeNotFoundError,
    PracticeRegistry,
    get_practice_registry,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────


class PracticeResponse(BaseModel):
    """A practice plus the two facts that only the registry knows.

    The definition is nested rather than flattened so the wire shape
    cannot drift from the schema: adding a field to
    :class:`PracticeDefinition` surfaces here without a second edit.
    """

    model_config = ConfigDict(frozen=True)

    pack_id: str = Field(..., description="The pack this practice belongs to")
    progression_depth: int = Field(
        ..., description="Longest path from a root in the pack's builds_on graph; a root is 0"
    )
    practice: PracticeDefinition


class PackResponse(BaseModel):
    """A pack manifest, including its license and attribution."""

    model_config = ConfigDict(frozen=True)

    manifest: PackManifest
    practice_count: int


# ─────────────────────────────────────────────────────────────────────
# Dependency
# ─────────────────────────────────────────────────────────────────────


def registry_dependency() -> PracticeRegistry:
    """FastAPI dependency returning the process-global registry."""
    return get_practice_registry()


def _to_response(
    registry: PracticeRegistry, pack_id: str, practice: PracticeDefinition
) -> PracticeResponse:
    return PracticeResponse(
        pack_id=pack_id,
        progression_depth=registry.progression_depth(pack_id, practice.slug),
        practice=practice,
    )


# ─────────────────────────────────────────────────────────────────────
# Routes
#
# Literal paths are registered before parameterized siblings, so
# /practices/packs cannot be captured by /practices/{pack_id}/{slug}.
# ─────────────────────────────────────────────────────────────────────


@router.get("/practices", response_model=list[PracticeResponse])
async def list_practices(
    purpose: str | None = Query(None, description="Filter by one of the five purposes"),
    category: str | None = Query(None, description="Filter by practice category"),
    pack_id: str | None = Query(None, description="Filter to a single pack"),
    registry: PracticeRegistry = Depends(registry_dependency),
    _user: dict = Depends(get_current_user),
) -> list[PracticeResponse]:
    """List every practice in every mounted pack.

    Filters narrow the result. A value that matches nothing returns an
    empty list rather than an error, so the caller has one shape to
    handle instead of two.
    """
    return [
        _to_response(registry, item_pack_id, practice)
        for item_pack_id, practice in registry.list_practices(
            purpose=purpose, category=category, pack_id=pack_id
        )
    ]


@router.get("/practices/packs", response_model=list[PackResponse])
async def list_packs(
    registry: PracticeRegistry = Depends(registry_dependency),
    _user: dict = Depends(get_current_user),
) -> list[PackResponse]:
    """List the mounted pack manifests, with license and attribution."""
    return [
        PackResponse(
            manifest=manifest,
            practice_count=registry.practice_count(manifest.pack_id),
        )
        for manifest in registry.list_packs()
    ]


@router.get("/practices/{pack_id}/{slug}", response_model=PracticeResponse)
async def get_practice(
    pack_id: str,
    slug: str,
    registry: PracticeRegistry = Depends(registry_dependency),
    _user: dict = Depends(get_current_user),
) -> PracticeResponse:
    """Return one practice by its qualified id."""
    try:
        practice = registry.get(pack_id, slug)
    except PackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pack not found: {pack_id}") from exc
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Practice not found: {pack_id}/{slug}"
        ) from exc
    return _to_response(registry, pack_id, practice)

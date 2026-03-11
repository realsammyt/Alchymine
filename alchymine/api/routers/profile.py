"""Profile CRUD API endpoints.

Wires the ``alchymine.db.repository`` async CRUD functions to REST
endpoints under ``/api/v1/profile``.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_admin, get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Request / Response Schemas ────────────────────────────────────────


class ProfileCreateRequest(BaseModel):
    """Request body for creating a new user profile."""

    full_name: str = Field(..., min_length=2, max_length=200)
    birth_date: date
    intention: str = Field(..., min_length=1, max_length=50)
    intentions: list[str] | None = Field(None, min_length=1, max_length=3)
    birth_time: time | None = None
    birth_city: str | None = None
    assessment_responses: dict[str, Any] | None = None
    family_structure: str | None = None

    def resolved_intentions(self) -> list[str]:
        """Return the full intentions list, falling back to the single intention."""
        return self.intentions or [self.intention]


class IntakeResponse(BaseModel):
    """Intake data nested in profile responses."""

    full_name: str
    birth_date: date
    birth_time: time | None = None
    birth_city: str | None = None
    intention: str
    intentions: list[str] = Field(default_factory=list)
    assessment_responses: dict[str, Any] | None = None
    family_structure: str | None = None


class ProfileResponse(BaseModel):
    """Response schema for a user profile."""

    id: str
    version: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    intake: IntakeResponse | None = None
    identity: dict | None = None
    healing: dict | None = None
    wealth: dict | None = None
    creative: dict | None = None
    perspective: dict | None = None


class ProfileListResponse(BaseModel):
    """Response schema for profile listing."""

    profiles: list[ProfileResponse]
    count: int
    offset: int
    limit: int


class LayerUpdateRequest(BaseModel):
    """Request body for updating a profile layer."""

    data: dict[str, Any]


class ReassessRequest(BaseModel):
    """Request body for reassessing a specific system layer."""

    assessment_responses: dict[str, Any]
    regenerate_narrative: bool = False


class ReassessResponse(BaseModel):
    """Response schema for a reassessment."""

    system: str
    status: str
    updated_data: dict[str, Any]
    narrative: str | None = None


# ─── Helpers ───────────────────────────────────────────────────────────


def _user_to_response(user: User) -> ProfileResponse:
    """Convert a User ORM model to a ProfileResponse."""
    intake_resp = None
    if user.intake is not None:
        intake_resp = IntakeResponse(
            full_name=user.intake.full_name,
            birth_date=user.intake.birth_date,
            birth_time=user.intake.birth_time,
            birth_city=user.intake.birth_city,
            intention=user.intake.intention,
            intentions=user.intake.resolved_intentions,
            assessment_responses=user.intake.assessment_responses,
            family_structure=user.intake.family_structure,
        )

    def _layer_to_dict(layer: Any) -> dict | None:
        """Convert an ORM layer to a dict, excluding internal fields."""
        if layer is None:
            return None
        result = {}
        for col in layer.__table__.columns:
            if col.name not in ("id", "user_id"):
                try:
                    result[col.name] = getattr(layer, col.name)
                except Exception:
                    logger.warning(
                        "Failed to read column %s.%s",
                        layer.__tablename__,
                        col.name,
                    )
                    result[col.name] = None
        return result

    return ProfileResponse(
        id=user.id,
        version=user.version,
        created_at=user.created_at,
        updated_at=user.updated_at,
        intake=intake_resp,
        identity=_layer_to_dict(user.identity),
        healing=_layer_to_dict(user.healing),
        wealth=_layer_to_dict(user.wealth),
        creative=_layer_to_dict(user.creative),
        perspective=_layer_to_dict(user.perspective),
    )


# ─── Endpoints ─────────────────────────────────────────────────────────


@router.post("/profile", status_code=201)
async def create_profile(
    request: ProfileCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ProfileResponse:
    """Create a new user profile with intake data."""
    user = await repository.create_profile(
        session,
        full_name=request.full_name,
        birth_date=request.birth_date,
        intention=request.intention,
        intentions=request.resolved_intentions(),
        birth_time=request.birth_time,
        birth_city=request.birth_city,
        assessment_responses=request.assessment_responses,
        family_structure=request.family_structure,
        user_id=current_user["sub"],
    )
    try:
        return _user_to_response(user)
    except Exception:
        logger.exception("Failed to serialize profile for new user %s", user.id)
        raise


@router.get("/profile/{user_id}")
async def get_profile(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ProfileResponse:
    """Retrieve a user profile by ID."""
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    user = await repository.get_profile(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    try:
        return _user_to_response(user)
    except Exception:
        logger.exception("Failed to serialize profile %s", user_id)
        raise


@router.get("/profiles")
async def list_profiles(
    offset: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> ProfileListResponse:
    """List user profiles with pagination. Restricted to admin users."""
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422,
            detail="limit must be between 1 and 100",
        )
    if offset < 0:
        raise HTTPException(
            status_code=422,
            detail="offset must be >= 0",
        )

    users = await repository.list_profiles(session, offset=offset, limit=limit)
    try:
        profiles = [_user_to_response(u) for u in users]
    except Exception:
        logger.exception("Failed to serialize profile list (offset=%s, limit=%s)", offset, limit)
        raise
    return ProfileListResponse(
        profiles=profiles,
        count=len(users),
        offset=offset,
        limit=limit,
    )


@router.put("/profile/{user_id}/{layer}")
async def update_layer(
    user_id: str,
    layer: str,
    request: LayerUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ProfileResponse:
    """Update a specific layer of a user profile.

    Valid layers: ``intake``, ``identity``, ``healing``, ``wealth``,
    ``creative``, ``perspective``.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Coerce date/time strings from JSON into Python types for the ORM.
    coerced = dict(request.data)
    if "birth_date" in coerced and isinstance(coerced["birth_date"], str):
        try:
            coerced["birth_date"] = date.fromisoformat(coerced["birth_date"])
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid birth_date format: {coerced['birth_date']!r}",
            ) from exc
    if "birth_time" in coerced and isinstance(coerced["birth_time"], str):
        if coerced["birth_time"] == "":
            coerced["birth_time"] = None
        else:
            try:
                coerced["birth_time"] = time.fromisoformat(coerced["birth_time"])
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid birth_time format: {coerced['birth_time']!r}",
                ) from exc

    try:
        user = await repository.update_layer(session, user_id, layer, coerced)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return _user_to_response(user)
    except Exception:
        logger.exception("Failed to serialize profile %s after %s update", user_id, layer)
        raise


@router.delete("/profile/{user_id}", status_code=200)
async def delete_profile(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a user profile and all associated data."""
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    deleted = await repository.delete_profile(session, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"detail": "Profile deleted", "user_id": user_id}


# ─── Completeness ─────────────────────────────────────────────────────


@router.get("/profile/{user_id}/completeness")
async def get_profile_completeness(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return completeness metrics for all assessment sections of a profile."""
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from alchymine.api.schemas.completeness import compute_completeness

    user = await repository.get_profile(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    assessment_responses = user.intake.assessment_responses if user.intake is not None else None
    identity_layer: dict | None = None
    if user.identity is not None:
        identity_layer = {
            col.name: getattr(user.identity, col.name, None)
            for col in user.identity.__table__.columns
            if col.name not in ("id", "user_id")
        }

    return compute_completeness(assessment_responses, identity_layer)


# ─── Reassess ─────────────────────────────────────────────────────────


def _extract_identity_enrichment(identity: Any) -> dict[str, Any]:
    """Extract enrichment fields from an IdentityProfile ORM instance.

    IdentityProfile stores sub-models in JSON columns (``numerology``,
    ``astrology``, ``archetype``, ``personality``).  This helper reads
    those nested structures so the reassess endpoint can include them
    in ``request_data`` without silently failing.

    Returns a flat dict with any keys that could be resolved; missing or
    ``None`` columns are omitted.
    """
    result: dict[str, Any] = {}

    numerology: dict[str, Any] | None = getattr(identity, "numerology", None) or {}
    if numerology:
        life_path = numerology.get("life_path")
        if life_path is not None:
            result["life_path"] = life_path

    archetype: dict[str, Any] | None = getattr(identity, "archetype", None) or {}
    if archetype:
        primary = archetype.get("primary")
        if primary is not None:
            # Store as string — match_modalities() expects a string, not a dict
            result["archetype"] = primary
            result["archetype_primary"] = primary
        secondary = archetype.get("secondary")
        if secondary is not None:
            result["archetype_secondary"] = secondary

    personality: dict[str, Any] | None = getattr(identity, "personality", None)
    if personality is not None:
        result["big_five"] = personality

    astrology: dict[str, Any] | None = getattr(identity, "astrology", None) or {}
    if astrology:
        result["astrology"] = astrology
        for key in ("sun_sign", "moon_sign", "rising_sign"):
            val = astrology.get(key)
            if val is not None:
                result[key] = val

    return result


_VALID_REASSESS_SYSTEMS = {"creative", "wealth", "perspective", "healing", "intelligence"}

_GRAPH_BUILDERS: dict[str, Any] = {}


def _get_graph_builders() -> dict[str, Any]:
    """Lazy-import graph builders to avoid circular imports."""
    if not _GRAPH_BUILDERS:
        from alchymine.agents.orchestrator.graphs import (
            build_creative_graph,
            build_healing_graph,
            build_intelligence_graph,
            build_perspective_graph,
            build_wealth_graph,
        )

        _GRAPH_BUILDERS.update(
            {
                "creative": build_creative_graph,
                "healing": build_healing_graph,
                "intelligence": build_intelligence_graph,
                "wealth": build_wealth_graph,
                "perspective": build_perspective_graph,
            }
        )
    return _GRAPH_BUILDERS


@router.patch("/profile/{user_id}/layers/{system}/reassess")
async def reassess_layer(
    user_id: str,
    system: str,
    request: ReassessRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ReassessResponse:
    """Re-run a system's coordinator graph with new assessment responses.

    Merges the new responses with existing data, re-runs the graph, and
    updates the profile layer in the database.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if system not in _VALID_REASSESS_SYSTEMS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid system: {system}. Must be one of {sorted(_VALID_REASSESS_SYSTEMS)}",
        )

    user = await repository.get_profile(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if user.intake is None:
        raise HTTPException(status_code=422, detail="No intake data found")

    # Build request_data from existing intake + identity profile
    existing_responses = user.intake.assessment_responses or {}
    merged_responses = {**existing_responses, **request.assessment_responses}

    request_data: dict[str, Any] = {
        "full_name": user.intake.full_name,
        "birth_date": str(user.intake.birth_date),
        "intention": user.intake.intention,
        "intentions": user.intake.resolved_intentions,
        "assessment_responses": merged_responses,
    }

    # Enrich with identity data if available
    if user.identity is not None:
        enrichment = _extract_identity_enrichment(user.identity)
        for key, val in enrichment.items():
            if key not in request_data:
                request_data[key] = val

    # Run the coordinator graph
    builders = _get_graph_builders()
    graph = builders[system](include_quality_gate=False)
    initial_state = {
        "user_id": user_id,
        "request_data": request_data,
        "results": {},
        "errors": [],
        "status": "pending",
    }

    try:
        final_state = graph.invoke(initial_state)
    except Exception as exc:
        logger.exception("Reassessment graph failed for user %s system %s", user_id, system)
        raise HTTPException(status_code=500, detail="Reassessment processing failed") from exc

    results = final_state.get("results", {})
    status = final_state.get("status", "error")

    # Map system name to profile layer name where they differ
    _layer_map = {"intelligence": "identity"}
    layer_name = _layer_map.get(system, system)

    # Update the profile layer in DB
    try:
        await repository.update_layer(session, user_id, layer_name, results)
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Also update merged assessment responses in intake
    await repository.update_layer(
        session,
        user_id,
        "intake",
        {"assessment_responses": merged_responses},
    )

    # Optionally regenerate narrative
    narrative_text: str | None = None
    if request.regenerate_narrative and status != "error":
        try:
            from alchymine.llm.narrative import NarrativeGenerator

            generator = NarrativeGenerator()
            result = await generator.generate(system, results)
            narrative_text = result.narrative
        except Exception:
            logger.warning(
                "Narrative regeneration failed for user %s system %s",
                user_id,
                system,
            )

    return ReassessResponse(
        system=system,
        status=status,
        updated_data=results,
        narrative=narrative_text,
    )

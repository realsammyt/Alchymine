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

from alchymine.api.auth import get_current_user
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
    current_user: dict = Depends(get_current_user),
) -> ProfileListResponse:
    """List user profiles with pagination."""
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
    try:
        user = await repository.update_layer(session, user_id, layer, request.data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _user_to_response(user)


@router.delete("/profile/{user_id}", status_code=200)
async def delete_profile(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a user profile and all associated data."""
    deleted = await repository.delete_profile(session, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"detail": "Profile deleted", "user_id": user_id}

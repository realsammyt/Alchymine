"""Generative art API endpoints.

Provides personalized image generation via Gemini. All endpoints degrade
gracefully (``204 No Content``) when ``GEMINI_API_KEY`` is not
configured, so the frontend can render an on-brand placeholder.

Endpoints
---------
``POST /api/v1/art/generate``
    Generate a single hero image for the authenticated user. Body
    accepts an optional ``style_preset`` and an optional
    ``user_prompt_extension``. The extension is sanitized through the
    project content filter to block PII, harmful content, and ethics
    violations.

``GET /api/v1/art/{image_id}``
    Stream the raw image bytes back to the owning user. Returns 404 to
    requests from any other user (we deliberately do not leak existence
    via 403/200 split).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import User
from alchymine.llm.art_prompts import STYLE_PRESETS, build_studio_prompt
from alchymine.llm.art_storage import read_image, write_image
from alchymine.llm.gemini import GeminiClient, get_gemini_client
from alchymine.safety.content_filter import FilterAction, filter_content

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/art", tags=["art"])


# ── Request / response models ─────────────────────────────────────────


class ArtGenerateRequest(BaseModel):
    """Body for ``POST /art/generate``."""

    style_preset: str | None = Field(
        default=None,
        description=f"One of: {', '.join(sorted(STYLE_PRESETS.keys()))}",
    )
    user_prompt_extension: str | None = Field(
        default=None,
        max_length=400,
        description="Optional user-supplied theme to append to the base prompt",
    )


class ArtGenerateResponse(BaseModel):
    """Body returned on successful generation."""

    image_id: str
    url: str
    prompt: str


# ── Dependency wrappers ───────────────────────────────────────────────


def _gemini_dependency() -> GeminiClient:
    return get_gemini_client()


# ── Helpers ───────────────────────────────────────────────────────────


async def _load_identity_dict(session: AsyncSession, user_id: str) -> dict[str, object]:
    """Load the user's identity layer into a plain dict for the prompt builder.

    Returns an empty dict for users without an identity profile so the
    builder falls back to its default imagery rather than raising.
    """
    user: User | None = await repository.get_profile(session, user_id)
    if user is None or user.identity is None:
        return {}
    identity = user.identity
    return {
        "archetype": identity.archetype or {},
        "astrology": identity.astrology or {},
        "numerology": identity.numerology or {},
    }


def _validate_style_preset(preset: str | None) -> None:
    if preset is not None and preset not in STYLE_PRESETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid style_preset {preset!r}. Must be one of: {sorted(STYLE_PRESETS.keys())}"
            ),
        )


def _sanitize_extension(extension: str | None) -> str | None:
    """Run a user-supplied prompt extension through the content filter.

    Returns the cleaned text on success, or raises 400 on a hard block.
    """
    if not extension or not extension.strip():
        return None
    result = filter_content(
        extension,
        context="creative",
        redact_pii=True,
        check_crisis=False,
    )
    if result.action == FilterAction.BLOCK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt extension blocked: {result.blocked_reason}",
        )
    return result.filtered_text


# ── Routes ────────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=ArtGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Image generated and stored"},
        204: {"description": "Generative art is disabled or generation returned no image"},
        400: {"description": "Invalid style preset or blocked user prompt"},
        401: {"description": "Authentication required"},
    },
)
async def generate_art(
    request: ArtGenerateRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    gemini: GeminiClient = Depends(_gemini_dependency),
) -> Response | ArtGenerateResponse:
    """Generate a single personalized hero image for the authenticated user."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user")

    # Validate inputs early so 400s never reach the generator.
    _validate_style_preset(request.style_preset)
    cleaned_extension = _sanitize_extension(request.user_prompt_extension)

    if not gemini.is_available:
        # The frontend treats 204 as a signal to render its placeholder.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Build the personalized prompt from the user's identity layer.
    identity_dict = await _load_identity_dict(session, user_id)
    prompt = build_studio_prompt(
        identity_dict,
        user_extension=cleaned_extension,
        style_preset=request.style_preset,
    )

    result = await gemini.generate_image(prompt)
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Persist bytes to disk + metadata row to DB.
    image_row = await repository.create_generated_image(
        session,
        user_id=user_id,
        prompt=result.prompt,
        file_path="",  # placeholder, set after we know the row id
        mime_type=result.mime_type,
        style_preset=request.style_preset,
        model=result.model,
    )
    rel_path = write_image(
        user_id=user_id,
        image_id=image_row.id,
        image_bytes=result.image_bytes,
        mime_type=result.mime_type,
    )
    image_row.file_path = rel_path
    await session.flush()

    return ArtGenerateResponse(
        image_id=image_row.id,
        url=f"/api/v1/art/{image_row.id}",
        prompt=result.prompt,
    )


@router.get(
    "/{image_id}",
    responses={
        200: {"content": {"image/png": {}}, "description": "Raw image bytes"},
        401: {"description": "Authentication required"},
        404: {"description": "Image not found or not owned by the requesting user"},
    },
)
async def get_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Return the raw bytes of a previously generated image.

    Returns 404 (not 403) when the requesting user does not own the
    image, so we don't leak the existence of other users' images.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user")

    image = await repository.get_generated_image(session, image_id)
    if image is None or image.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    raw = read_image(image.file_path)
    if raw is None:
        # Row exists but the file is missing — treat as gone.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    return Response(content=raw, media_type=image.mime_type)

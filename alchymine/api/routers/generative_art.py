"""Generative art API endpoints.

Exposes image generation via Gemini, with graceful degradation to 204
when Gemini is unavailable. Generated images are stored in an in-memory
cache keyed by a UUID, retrievable via GET /art/{image_id}.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator

from alchymine.llm.art_prompts import build_report_hero_prompt
from alchymine.llm.gemini import GeminiClient

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache: {image_id: {"data_b64": str, "mime_type": str, "prompt_used": str}}
_image_cache: dict[str, dict] = {}


# ── Request / Response models ─────────────────────────────────────────────────


class GenerateArtRequest(BaseModel):
    """Request body for POST /art/generate.

    Provide either *prompt* (raw text) or *profile* (auto-builds prompt
    from user data). At least one is required.
    """

    prompt: Annotated[str | None, Field(default=None, description="Raw image generation prompt")]
    profile: Annotated[
        dict | None, Field(default=None, description="User profile dict for prompt building")
    ]

    @model_validator(mode="after")
    def require_prompt_or_profile(self) -> GenerateArtRequest:
        if self.prompt is None and self.profile is None:
            raise ValueError("Provide either 'prompt' or 'profile'")
        return self


class GenerateArtResponse(BaseModel):
    """Response body for a successful image generation."""

    image_id: str = Field(description="UUID for retrieving this image later")
    data_b64: str = Field(description="Base-64 encoded image bytes")
    mime_type: str = Field(description="Image MIME type, e.g. image/png")
    prompt_used: str = Field(description="The prompt that produced this image")


class RetrieveArtResponse(BaseModel):
    """Response body for GET /art/{image_id}."""

    image_id: str
    data_b64: str
    mime_type: str
    prompt_used: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/art/generate",
    response_model=GenerateArtResponse,
    responses={204: {"description": "Gemini unavailable — art generation disabled"}},
    summary="Generate a personalized image",
)
async def generate_art(body: GenerateArtRequest) -> GenerateArtResponse | Response:
    """Generate an image via Gemini from a prompt or user profile.

    Returns 204 (No Content) when Gemini is not configured or generation
    fails — the frontend should show a placeholder instead.
    """
    # Resolve the prompt
    if body.prompt:
        prompt = body.prompt
    else:
        prompt = build_report_hero_prompt(body.profile or {})

    client = GeminiClient()

    if not client.is_available:
        logger.info("[Art] Gemini unavailable — returning 204")
        return Response(status_code=204)

    result = await client.generate_image(prompt)

    if result is None:
        logger.info("[Art] Gemini generation returned None — returning 204")
        return Response(status_code=204)

    image_id = str(uuid.uuid4())
    _image_cache[image_id] = {
        "data_b64": result.data_b64,
        "mime_type": result.mime_type,
        "prompt_used": result.prompt_used,
    }

    logger.info("[Art] Generated image %s (mime=%s)", image_id, result.mime_type)
    return GenerateArtResponse(
        image_id=image_id,
        data_b64=result.data_b64,
        mime_type=result.mime_type,
        prompt_used=result.prompt_used,
    )


@router.get(
    "/art/{image_id}",
    response_model=RetrieveArtResponse,
    summary="Retrieve a cached generated image",
)
async def retrieve_art(image_id: str) -> RetrieveArtResponse:
    """Retrieve a previously generated image by its UUID.

    Returns 404 when the image_id is not found in cache.
    """
    cached = _image_cache.get(image_id)
    if cached is None:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found")

    return RetrieveArtResponse(
        image_id=image_id,
        data_b64=cached["data_b64"],
        mime_type=cached["mime_type"],
        prompt_used=cached["prompt_used"],
    )

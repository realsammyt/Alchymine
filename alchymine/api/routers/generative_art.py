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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import Account, get_current_user
from alchymine.api.deps import get_db_session
from alchymine.api.entitlements import require_art, require_brand_logo
from alchymine.config import get_settings
from alchymine.db import repository, usage_counters
from alchymine.db.models import User
from alchymine.db.usage_counters import (
    METER_ART_GENERATIONS,
    CostCeilingExceeded,
    consume,
    refund,
)
from alchymine.llm.art_prompts import (
    STYLE_PRESETS,
    build_brand_logo_prompt,
    build_studio_prompt,
    derive_brand_palette,
)
from alchymine.llm.art_storage import delete_image, read_image, write_image
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


class StylePresetOut(BaseModel):
    """Public metadata for a single style preset.

    The ``id`` corresponds to a key in
    :data:`alchymine.llm.art_prompts.STYLE_PRESETS`; the canonical
    suffix text lives only on the server. The ``name`` and
    ``description`` are short human-facing labels safe to render in UI.
    """

    id: str
    name: str
    description: str


# Short, human-readable metadata for each preset. The authoritative
# style suffix text lives in ``alchymine.llm.art_prompts.STYLE_PRESETS``
# — this dict is purely display copy for the frontend picker, keyed on
# the same preset ids. If ``STYLE_PRESETS`` grows a new key, add a
# matching entry here or the preset endpoint will 500.
_PRESET_METADATA: dict[str, tuple[str, str]] = {
    "mystical": ("Mystical", "Sacred geometry, indigo and gold"),
    "modern": ("Modern", "Clean, editorial, muted gradients"),
    "organic": ("Organic", "Botanical watercolour, earth tones"),
    "celestial": ("Celestial", "Starfields, nebulae, violet and silver"),
    "grounded": ("Grounded", "Stone, wood, terracotta, golden-hour"),
}


class ImageMetadata(BaseModel):
    """Public metadata for a single stored generated image (no bytes)."""

    id: str
    prompt: str
    style_preset: str | None
    created_at: str
    url: str


class ImageListResponse(BaseModel):
    """Response body for :func:`list_user_images`."""

    images: list[ImageMetadata]
    limit: int
    offset: int


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


async def _charge_daily_allowance(user_id: str) -> str:
    """Spend one of the user's daily image generations, or say when to return.

    Charged just before the Gemini call, so a capped request never
    reaches the generator. The global breaker in ``llm/cost_guard`` still
    applies underneath: this one only bounds what a single account can do
    to the bill on its own.

    Returns the period key the charge landed on, which the caller hands to
    :func:`_refund_daily_allowance`. A request charged at 23:59 whose
    refund fires after midnight has to credit the day it charged, not the
    day it finished.
    """
    period_key = usage_counters.current_period_key()
    try:
        await consume(
            scope=user_id,
            meter=METER_ART_GENERATIONS,
            ceiling=get_settings().daily_art_generations_per_user,
            period_key=period_key,
        )
    except CostCeilingExceeded as exc:
        if exc.reason != "ceiling_reached":
            # The meter itself is down. That is our problem, not the
            # user's allowance, and the app handler renders it as a 503.
            raise
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "daily_art_cap_reached",
                "message": (
                    "That's all of today's image generations. "
                    "Your next one unlocks at midnight UTC."
                ),
                "retry_at": exc.retry_at.isoformat(),
            },
        ) from exc
    return period_key


async def _refund_daily_allowance(user_id: str, period_key: str) -> None:
    """Give back an allowance slot that produced no image.

    The charge happens before the Gemini call so an exhausted cap blocks
    before we spend anything. That ordering means a generator that fails,
    is filtered, or returns an undecodable payload would otherwise cost
    the user one of their three for nothing.

    *period_key* is the one the charge used. Reading the clock here
    instead would send a post-midnight refund at a counter row that does
    not exist yet, where the clamp turns it into a silent no-op.
    """
    try:
        await refund(scope=user_id, meter=METER_ART_GENERATIONS, period_key=period_key)
    except Exception as exc:
        # Failing to refund costs the user one generation, which is the
        # safe direction to fail. It must never turn a 204 into a 500.
        logger.warning("Could not refund the art allowance for user %s: %s", user_id, exc)


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
        402: {"description": "Plan does not include image generation"},
        429: {
            "description": (
                "Daily per-user image allowance spent (code: daily_art_cap_reached) "
                "or the monthly plan allowance is gone (code: plan_allowance_reached)"
            )
        },
        503: {"description": "Generation is paused by the global spend breaker"},
    },
)
async def generate_art(
    request: ArtGenerateRequest,
    account: Account = Depends(require_art),
    session: AsyncSession = Depends(get_db_session),
    gemini: GeminiClient = Depends(_gemini_dependency),
) -> Response | ArtGenerateResponse:
    """Generate a single personalized hero image for the authenticated user.

    Two caps stack here and each can trip on its own: the plan's monthly
    spend allowance (checked in ``require_art``, before this body runs)
    and the 3-per-day count cap below.  They answer different questions,
    so they carry different codes.
    """
    user_id = account.user_id

    # Validate inputs early so 400s never reach the generator.
    _validate_style_preset(request.style_preset)
    cleaned_extension = _sanitize_extension(request.user_prompt_extension)

    if not gemini.is_available:
        # The frontend treats 204 as a signal to render its placeholder.
        # Checked before the cap so an unavailable generator, which costs
        # nothing, never spends one of the user's daily allowance.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    charged_period = await _charge_daily_allowance(user_id)

    # Everything from here can end without an image reaching the user: a
    # filtered prompt, an SDK hiccup, an undecodable payload, or the
    # global breaker tripping mid-flight. Each of those hands the slot
    # back, so only a delivered image actually costs the user one.
    try:
        # Build the personalized prompt from the user's identity layer.
        identity_dict = await _load_identity_dict(session, user_id)
        prompt = build_studio_prompt(
            identity_dict,
            user_extension=cleaned_extension,
            style_preset=request.style_preset,
        )
        result = await gemini.generate_image(prompt)
    except Exception:
        await _refund_daily_allowance(user_id, charged_period)
        raise

    if result is None:
        await _refund_daily_allowance(user_id, charged_period)
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
    "/presets",
    response_model=list[StylePresetOut],
    responses={
        200: {"description": "List of available style presets"},
    },
)
async def list_style_presets() -> list[StylePresetOut]:
    """Return the catalogue of style presets available to the studio.

    Source of truth for preset ids is
    :data:`alchymine.llm.art_prompts.STYLE_PRESETS` — this endpoint
    projects each key through :data:`_PRESET_METADATA` to produce the
    UI-facing label/description pair.
    """
    presets: list[StylePresetOut] = []
    for preset_id in STYLE_PRESETS:
        name, description = _PRESET_METADATA.get(
            preset_id, (preset_id.title(), "Personalized style")
        )
        presets.append(StylePresetOut(id=preset_id, name=name, description=description))
    return presets


@router.get(
    "/list",
    response_model=ImageListResponse,
    responses={
        200: {"description": "List of the authenticated user's stored images"},
        401: {"description": "Authentication required"},
    },
)
async def list_user_images(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ImageListResponse:
    """Return a page of the authenticated user's previously generated images.

    Only metadata is returned — clients must call
    ``GET /api/v1/art/{image_id}`` to stream the bytes. The default
    page size of 20 covers the studio gallery on mount.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user")

    rows = await repository.list_generated_images_for_user(
        session,
        user_id,
        limit=limit,
        offset=offset,
    )
    images = [
        ImageMetadata(
            id=row.id,
            prompt=row.prompt,
            style_preset=row.style_preset,
            # SQLAlchemy returns a datetime; ISO-8601 is the frontend format.
            created_at=row.created_at.isoformat() if row.created_at is not None else "",
            url=f"/api/v1/art/{row.id}",
        )
        for row in rows
    ]
    return ImageListResponse(images=images, limit=limit, offset=offset)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Image deleted"},
        401: {"description": "Authentication required"},
        404: {"description": "Image not found or not owned by the requesting user"},
    },
)
async def delete_user_image(
    image_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete a single stored image owned by the authenticated user.

    Mirrors :func:`get_image`: cross-user access returns 404 (not 403)
    to avoid leaking existence. If the DB row exists but the file on
    disk is already missing, the row is still removed and 204 is
    returned — the effective state is the same.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user")

    image = await repository.get_generated_image(session, image_id)
    if image is None or image.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Best-effort file unlink. We don't surface failures because the
    # DB row is the source of truth for "does this image exist" — a
    # stale file on disk without a row is orphaned and harmless.
    delete_image(image.file_path)
    await repository.delete_generated_image(session, image_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


# ── Brand endpoints ──────────────────────────────────────────────────


class BrandPaletteColor(BaseModel):
    """A single colour in the brand palette."""

    hex: str
    name: str


class BrandPaletteResponse(BaseModel):
    """Deterministic colour palette derived from the user's profile."""

    primary: BrandPaletteColor
    secondary: BrandPaletteColor
    accent: BrandPaletteColor
    neutral: BrandPaletteColor


class BrandLogoResponse(BaseModel):
    """Response from the logo generation endpoint."""

    image_id: str
    url: str
    prompt: str


@router.get(
    "/brand/palette",
    response_model=BrandPaletteResponse,
    responses={
        200: {"description": "Deterministic colour palette from user profile"},
        401: {"description": "Authentication required"},
    },
)
async def get_brand_palette(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> BrandPaletteResponse:
    """Return a personal brand colour palette derived from the user's identity.

    The palette is fully deterministic — same profile always yields
    the same colours. Element drives the base palette, archetype
    optionally shifts the accent.
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user")

    identity_dict = await _load_identity_dict(session, user_id)
    raw = derive_brand_palette(identity_dict)

    return BrandPaletteResponse(
        primary=BrandPaletteColor(**raw["primary"]),
        secondary=BrandPaletteColor(**raw["secondary"]),
        accent=BrandPaletteColor(**raw["accent"]),
        neutral=BrandPaletteColor(**raw["neutral"]),
    )


@router.post(
    "/brand/logo",
    response_model=BrandLogoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Logo generated and stored"},
        204: {"description": "Generative art is disabled or generation returned no image"},
        401: {"description": "Authentication required"},
        402: {"description": "Plan does not include logo generation"},
        429: {
            "description": (
                "Daily per-user image allowance spent (code: daily_art_cap_reached) "
                "or the monthly plan allowance is gone (code: plan_allowance_reached)"
            )
        },
        503: {"description": "Generation is paused by the global spend breaker"},
    },
)
async def generate_brand_logo(
    account: Account = Depends(require_brand_logo),
    session: AsyncSession = Depends(get_db_session),
    gemini: GeminiClient = Depends(_gemini_dependency),
) -> Response | BrandLogoResponse:
    """Generate a symbolic personal brand logo from the user's profile.

    Uses the user's archetype, element, and numerology to create a
    minimalist logo mark via Gemini image generation. Returns 204 when
    Gemini is unavailable.
    """
    user_id = account.user_id

    if not gemini.is_available:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Same allowance as the studio route, deliberately: this endpoint hits
    # the same paid generator, so counting it separately would just be a
    # second door to the same bill.
    charged_period = await _charge_daily_allowance(user_id)

    try:
        identity_dict = await _load_identity_dict(session, user_id)
        prompt = build_brand_logo_prompt(identity_dict)
        result = await gemini.generate_image(prompt)
    except Exception:
        await _refund_daily_allowance(user_id, charged_period)
        raise

    if result is None:
        await _refund_daily_allowance(user_id, charged_period)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    image_row = await repository.create_generated_image(
        session,
        user_id=user_id,
        prompt=result.prompt,
        file_path="",
        mime_type=result.mime_type,
        style_preset="brand-logo",
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

    return BrandLogoResponse(
        image_id=image_row.id,
        url=f"/api/v1/art/{image_row.id}",
        prompt=result.prompt,
    )

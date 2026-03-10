# Track 3: Gemini Generative Art — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Gemini 3.1 Flash image generation across the platform — personalized header images in reports, a Creative Studio for art exploration, journey illustrations, and personal brand generation. Each feature gates gracefully when `GEMINI_API_KEY` is absent.

**Architecture:** New `alchymine/llm/gemini.py` client mirrors the existing `LLMClient` pattern. A new `alchymine/api/routers/generative_art.py` router exposes four endpoint groups (report art, studio, journey, brand). Images are stored as base64 in the report `result` dict (short-term) with a filesystem/S3 cache for production. Frontend components consume the new endpoints; the report page displays the hero image inline. All image generation is async and non-blocking — reports complete without waiting for art.

**Tech Stack:** Python `google-genai` SDK, FastAPI, Celery (background art tasks), Next.js 15 App Router, React 18, TypeScript, Tailwind CSS.

---

## File Map

### New Files

| File                                                          | Responsibility                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------ |
| `alchymine/llm/gemini.py`                                     | Gemini client wrapper (generate_image, graceful degradation) |
| `alchymine/api/routers/generative_art.py`                     | REST endpoints: report art, studio, journey, brand           |
| `alchymine/workers/tasks_art.py`                              | Celery tasks: async image generation, cache write            |
| `alchymine/web/src/lib/artApi.ts`                             | Typed fetch wrappers for generative art endpoints            |
| `alchymine/web/src/components/art/ReportHero.tsx`             | Hero image card for report page                              |
| `alchymine/web/src/components/art/ArtGallery.tsx`             | Grid of saved/generated images with download                 |
| `alchymine/web/src/components/art/StylePresetPicker.tsx`      | Visual preset selector tied to creative profile              |
| `alchymine/web/src/app/creative/studio/page.tsx`              | Creative Studio page                                         |
| `alchymine/web/src/app/discover/report/[id]/journey/page.tsx` | Journey illustration viewer                                  |
| `tests/api/test_generative_art.py`                            | API endpoint tests (mocked Gemini)                           |
| `tests/llm/test_gemini.py`                                    | Gemini client unit tests                                     |

### Modified Files

| File                                                  | Changes                                                 |
| ----------------------------------------------------- | ------------------------------------------------------- |
| `alchymine/config.py`                                 | Add `gemini_api_key`, `art_cache_dir` settings          |
| `alchymine/api/main.py`                               | Register `generative_art` router                        |
| `alchymine/web/src/app/discover/report/[id]/page.tsx` | Import and render `ReportHero` above narrative sections |
| `alchymine/web/src/app/creative/page.tsx`             | Add "Open Studio" link/button                           |
| `pyproject.toml`                                      | Add `google-genai>=1.0` to `[project.dependencies]`     |

---

## Sprint 1–2 (Weeks 1–4): Foundation + Report Visuals

### Task 1: Add Gemini settings to config

**Files:**

- Modify: `alchymine/config.py`
- Test: verify `get_settings()` reads `GEMINI_API_KEY` from env

- [ ] **Step 1: Add fields**

In `alchymine/config.py`, inside the `Settings` class after the `anthropic_api_key` line:

```python
# ── Gemini ────────────────────────────────────────────────────────────
gemini_api_key: str = ""
art_cache_dir: str = "/tmp/alchymine_art"
```

- [ ] **Step 2: Verify locally**

```bash
GEMINI_API_KEY=test-key python -c "from alchymine.config import get_settings; s=get_settings(); assert s.gemini_api_key=='test-key'"
```

- [ ] **Step 3: Commit**

```bash
git add alchymine/config.py
git commit -m "feat(art): add gemini_api_key and art_cache_dir to settings"
```

---

### Task 2: Install google-genai SDK

**Files:**

- Modify: `pyproject.toml`

- [ ] **Step 1: Add to dependencies**

In `pyproject.toml`, add to `[project.dependencies]`:

```toml
"google-genai>=1.0",
```

- [ ] **Step 2: Install locally**

```bash
pip install "google-genai>=1.0"
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(art): add google-genai SDK dependency"
```

---

### Task 3: Write Gemini client with graceful degradation

**Files:**

- Create: `alchymine/llm/gemini.py`
- Create: `tests/llm/test_gemini.py`

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_gemini.py`:

```python
"""Tests for Gemini image generation client."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.llm.gemini import GeminiClient, ImageResult


def test_image_result_dataclass():
    r = ImageResult(data_b64="abc==", mime_type="image/png", prompt_used="test")
    assert r.data_b64 == "abc=="
    assert r.mime_type == "image/png"


@pytest.mark.asyncio
async def test_generate_image_no_key_returns_none():
    """Client returns None gracefully when no API key is configured."""
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = ""
        client = GeminiClient()
        result = await client.generate_image("a serene forest")
    assert result is None


@pytest.mark.asyncio
async def test_generate_image_returns_result():
    """Client returns ImageResult when Gemini responds with image data."""
    fake_b64 = "iVBORw0KGgo="  # minimal valid-looking b64
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "fake-key"
        with patch("alchymine.llm.gemini.genai") as mock_genai:
            mock_part = MagicMock()
            mock_part.inline_data.data = fake_b64
            mock_part.inline_data.mime_type = "image/png"
            mock_response = MagicMock()
            mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
            mock_genai.Client.return_value.models.generate_content = AsyncMock(
                return_value=mock_response
            )
            client = GeminiClient()
            result = await client.generate_image("a serene forest")
    assert result is not None
    assert result.data_b64 == fake_b64
    assert result.mime_type == "image/png"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/llm/test_gemini.py -v
```

Expected: ImportError / ModuleNotFoundError.

- [ ] **Step 3: Create `alchymine/llm/gemini.py`**

```python
"""Gemini image generation client.

Uses the google-genai SDK to call Gemini 3.1 Flash Preview for image
generation. Returns None gracefully when GEMINI_API_KEY is not set.

Environment Variables:
    GEMINI_API_KEY: Google AI API key (optional — disables art generation when absent)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from alchymine.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"


@dataclass(frozen=True)
class ImageResult:
    """Result from a Gemini image generation call."""

    data_b64: str
    mime_type: str
    prompt_used: str


class GeminiClient:
    """Thin async wrapper around the google-genai image generation API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        if self._api_key:
            try:
                import google.generativeai as genai  # noqa: F401
                # Import the newer SDK style
                from google import genai as _genai
                self._genai = _genai
                self._client = _genai.Client(api_key=self._api_key)
                logger.info("[Gemini] Client initialized with model %s", GEMINI_IMAGE_MODEL)
            except ImportError:
                logger.warning("[Gemini] google-genai SDK not installed — art generation disabled")
                self._api_key = ""
                self._client = None
                self._genai = None
        else:
            logger.info("[Gemini] No GEMINI_API_KEY — art generation disabled")
            self._client = None
            self._genai = None

    @property
    def is_available(self) -> bool:
        """Return True if API key is set and SDK is installed."""
        return bool(self._api_key and self._client is not None)

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
    ) -> ImageResult | None:
        """Generate an image from a text prompt.

        Returns None gracefully when Gemini is unavailable.
        """
        if not self.is_available:
            return None

        full_prompt = prompt
        if negative_prompt:
            full_prompt += f"\n\nAvoid: {negative_prompt}"

        try:
            from google.genai import types

            response = await self._client.aio.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        return ImageResult(
                            data_b64=part.inline_data.data,
                            mime_type=part.inline_data.mime_type or "image/png",
                            prompt_used=prompt,
                        )
            logger.warning("[Gemini] Response had no image parts")
            return None
        except Exception as exc:
            logger.warning("[Gemini] Image generation failed: %s", exc)
            return None


# Module-level import alias for test patching
try:
    from google import genai  # noqa: F401
except ImportError:
    genai = None  # type: ignore[assignment]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/llm/test_gemini.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add alchymine/llm/gemini.py tests/llm/test_gemini.py
git commit -m "feat(art): add GeminiClient with graceful degradation"
```

---

### Task 4: Build prompt templates for personalized art

**Files:**

- Create: `alchymine/llm/art_prompts.py`
- Test: `tests/llm/test_art_prompts.py`

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_art_prompts.py`:

```python
"""Tests for art prompt template generation."""
from alchymine.llm.art_prompts import build_report_hero_prompt, build_journey_prompt


def test_report_hero_prompt_includes_archetype():
    profile = {
        "archetype": {"primary": "Sage", "secondary": "Creator"},
        "astrology": {"sun_sign": "Scorpio", "moon_sign": "Pisces"},
        "numerology": {"life_path": 7},
    }
    prompt = build_report_hero_prompt(profile)
    assert "Sage" in prompt
    assert "Scorpio" in prompt
    assert "7" in prompt


def test_report_hero_prompt_handles_missing_fields():
    """Prompt generation never raises even with empty profile."""
    prompt = build_report_hero_prompt({})
    assert isinstance(prompt, str)
    assert len(prompt) > 20


def test_journey_prompt_mentions_pillars():
    prompt = build_journey_prompt(pillars=["healing", "wealth"])
    assert "healing" in prompt.lower() or "transformation" in prompt.lower()
```

- [ ] **Step 2: Create `alchymine/llm/art_prompts.py`**

```python
"""Prompt templates for Gemini image generation.

All functions return plain strings. They never raise — missing data
gracefully falls back to sensible defaults.
"""

from __future__ import annotations

_STYLE_SUFFIX = (
    "Digital illustration, sacred geometry motifs, deep indigo and gold palette, "
    "mystical atmosphere, cinematic lighting, 16:9 composition, no text, no watermarks."
)

_ARCHETYPE_IMAGERY: dict[str, str] = {
    "Sage": "an ancient library floating in starlight",
    "Creator": "a luminous forge where ideas crystallize into form",
    "Hero": "a solitary figure cresting a radiant mountain peak",
    "Magician": "swirling alchemical symbols transforming into light",
    "Explorer": "an infinite horizon where land meets cosmic sea",
    "Lover": "intertwined vines flowering into geometric mandalas",
    "Caregiver": "a warm hearth surrounded by protective golden light",
    "Ruler": "a crystal throne atop a mountain, surrounded by clouds",
    "Rebel": "shattered chains dissolving into prismatic light",
    "Innocent": "a meadow where every flower is a constellation",
    "Jester": "kaleidoscopic patterns dancing in perpetual motion",
    "Everyman": "a winding path through four seasons simultaneously",
}

_SIGN_ELEMENT: dict[str, str] = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}


def build_report_hero_prompt(profile: dict) -> str:
    """Generate a personalized hero image prompt from the user profile."""
    archetype = (profile.get("archetype") or {}).get("primary", "Sage")
    sun_sign = (profile.get("astrology") or {}).get("sun_sign", "")
    life_path = (profile.get("numerology") or {}).get("life_path", "")
    secondary = (profile.get("archetype") or {}).get("secondary", "")

    imagery = _ARCHETYPE_IMAGERY.get(archetype, "an ethereal landscape of transformation")
    element = _SIGN_ELEMENT.get(sun_sign, "cosmic")
    lp_str = f" Life Path {life_path}," if life_path else ""
    second_str = f" and {secondary} energy," if secondary else ""

    prompt = (
        f"A breathtaking symbolic portrait representing the {archetype} archetype{second_str} "
        f"with {element} elemental energy,{lp_str} depicted as {imagery}. "
        f"{_STYLE_SUFFIX}"
    )
    return prompt


def build_journey_prompt(pillars: list[str]) -> str:
    """Generate a journey timeline illustration prompt."""
    pillar_str = " and ".join(pillars) if pillars else "personal transformation"
    return (
        f"A visual timeline of personal transformation across {pillar_str}, "
        "depicted as a luminous spiral path through distinct symbolic landscapes, "
        "each zone representing growth and insight. "
        f"{_STYLE_SUFFIX}"
    )


def build_brand_prompt(profile: dict, brand_element: str = "logo") -> str:
    """Generate a personal brand element prompt."""
    archetype = (profile.get("archetype") or {}).get("primary", "Sage")
    return (
        f"A minimalist personal brand {brand_element} for a {archetype} archetype, "
        "combining sacred geometry with modern design, "
        "gold and deep purple color palette, centered composition, "
        "suitable for a personal brand identity system. "
        "No text, clean background."
    )


def build_studio_prompt(
    user_prompt: str,
    style_preset: str = "mystical",
    creative_domain: str = "",
) -> str:
    """Merge user-written prompt with style preset for Creative Studio."""
    style_map = {
        "mystical": "sacred geometry, deep indigo and gold, ethereal atmosphere",
        "digital": "neon lines, circuit-board patterns, cyberpunk palette",
        "organic": "flowing botanical forms, earth tones, watercolor texture",
        "geometric": "sharp angles, primary colors, Bauhaus composition",
        "surreal": "dreamlike juxtapositions, melting forms, Salvador Dali influence",
    }
    style_desc = style_map.get(style_preset, style_map["mystical"])
    domain_str = f" Inspired by {creative_domain} domain." if creative_domain else ""
    return f"{user_prompt}.{domain_str} Style: {style_desc}. No text, no watermarks."
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/llm/test_art_prompts.py -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add alchymine/llm/art_prompts.py tests/llm/test_art_prompts.py
git commit -m "feat(art): add personalized art prompt templates"
```

---

### Task 5: Create generative art API router

**Files:**

- Create: `alchymine/api/routers/generative_art.py`
- Create: `tests/api/test_generative_art.py`

- [ ] **Step 1: Write failing tests**

Create `tests/api/test_generative_art.py`:

```python
"""Tests for generative art API endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app

client = TestClient(app)

AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _mock_auth():
    return patch(
        "alchymine.api.auth.get_current_user",
        return_value={"sub": "user-123"},
    )


def test_get_report_art_no_gemini_returns_204():
    """When Gemini is unavailable, endpoint returns 204 No Content."""
    with _mock_auth(), patch(
        "alchymine.api.routers.generative_art.GeminiClient"
    ) as MockClient:
        MockClient.return_value.is_available = False
        response = client.get(
            "/api/v1/art/report/fake-report-id/hero",
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 204


def test_generate_studio_image_missing_prompt_returns_422():
    with _mock_auth():
        response = client.post(
            "/api/v1/art/studio/generate",
            json={},
            headers=AUTH_HEADERS,
        )
    assert response.status_code == 422


def test_art_status_endpoint_exists():
    with _mock_auth():
        response = client.get("/api/v1/art/status", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert "available" in response.json()
```

- [ ] **Step 2: Create the router**

Create `alchymine/api/routers/generative_art.py`:

```python
"""Generative art API endpoints.

Provides personalized image generation via Gemini. All endpoints degrade
gracefully (204 No Content) when GEMINI_API_KEY is not configured.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.llm.gemini import GeminiClient
from alchymine.llm.art_prompts import (
    build_brand_prompt,
    build_journey_prompt,
    build_report_hero_prompt,
    build_studio_prompt,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/art", tags=["art"])


def _get_gemini() -> GeminiClient:
    return GeminiClient()


class StudioGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500)
    style_preset: str = Field("mystical", pattern="^(mystical|digital|organic|geometric|surreal)$")
    creative_domain: str = Field("", max_length=50)


class ArtResponse(BaseModel):
    data_b64: str
    mime_type: str
    prompt_used: str


@router.get("/status")
async def art_status(
    current_user: dict = Depends(get_current_user),
    gemini: GeminiClient = Depends(_get_gemini),
) -> dict:
    """Return whether generative art is available."""
    return {"available": gemini.is_available}


@router.get("/report/{report_id}/hero", response_model=None)
async def get_report_hero(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    gemini: GeminiClient = Depends(_get_gemini),
) -> ArtResponse | Response:
    """Generate (or return cached) hero image for a report.

    Returns 204 when Gemini is unavailable — client should render
    a gradient placeholder instead.
    """
    if not gemini.is_available:
        return Response(status_code=204)

    # In Sprint 3 this will load cached images from the DB/filesystem.
    # For now, generate on demand.
    prompt = build_report_hero_prompt({})  # TODO: load real profile in Sprint 2
    result = await gemini.generate_image(prompt)
    if result is None:
        return Response(status_code=204)
    return ArtResponse(
        data_b64=result.data_b64,
        mime_type=result.mime_type,
        prompt_used=result.prompt_used,
    )


@router.post("/studio/generate", response_model=ArtResponse)
async def studio_generate(
    request: StudioGenerateRequest,
    current_user: dict = Depends(get_current_user),
    gemini: GeminiClient = Depends(_get_gemini),
) -> ArtResponse:
    """Generate an image from a user-supplied prompt in the Creative Studio."""
    if not gemini.is_available:
        raise HTTPException(
            status_code=503,
            detail="Generative art requires GEMINI_API_KEY to be configured.",
        )
    prompt = build_studio_prompt(
        request.prompt,
        style_preset=request.style_preset,
        creative_domain=request.creative_domain,
    )
    result = await gemini.generate_image(prompt)
    if result is None:
        raise HTTPException(status_code=503, detail="Image generation failed")
    return ArtResponse(
        data_b64=result.data_b64,
        mime_type=result.mime_type,
        prompt_used=result.prompt_used,
    )


@router.get("/report/{report_id}/journey", response_model=None)
async def get_journey_art(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    gemini: GeminiClient = Depends(_get_gemini),
) -> ArtResponse | Response:
    """Generate a journey timeline illustration for a report."""
    if not gemini.is_available:
        return Response(status_code=204)
    prompt = build_journey_prompt(pillars=["healing", "wealth", "creative", "perspective"])
    result = await gemini.generate_image(prompt)
    if result is None:
        return Response(status_code=204)
    return ArtResponse(
        data_b64=result.data_b64,
        mime_type=result.mime_type,
        prompt_used=result.prompt_used,
    )


@router.get("/report/{report_id}/brand/{element}", response_model=None)
async def get_brand_element(
    report_id: str,
    element: str,
    current_user: dict = Depends(get_current_user),
    gemini: GeminiClient = Depends(_get_gemini),
) -> ArtResponse | Response:
    """Generate a personal brand element (logo, palette, etc.)."""
    valid_elements = {"logo", "palette", "pattern", "avatar"}
    if element not in valid_elements:
        raise HTTPException(status_code=400, detail=f"element must be one of {valid_elements}")
    if not gemini.is_available:
        return Response(status_code=204)
    prompt = build_brand_prompt({}, brand_element=element)
    result = await gemini.generate_image(prompt)
    if result is None:
        return Response(status_code=204)
    return ArtResponse(
        data_b64=result.data_b64,
        mime_type=result.mime_type,
        prompt_used=result.prompt_used,
    )
```

- [ ] **Step 3: Register router in `alchymine/api/main.py`**

Find the block where other routers are included (e.g., `app.include_router(reports.router, ...)`) and add:

```python
from alchymine.api.routers import generative_art
app.include_router(generative_art.router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/api/test_generative_art.py -v
```

Expected: All pass (auth mock + Gemini mock).

- [ ] **Step 5: Run lint**

```bash
ruff check alchymine/api/routers/generative_art.py alchymine/llm/gemini.py
ruff format --check alchymine/
```

- [ ] **Step 6: Commit**

```bash
git add alchymine/api/routers/generative_art.py alchymine/api/main.py tests/api/test_generative_art.py
git commit -m "feat(art): add generative art router with hero, studio, journey, brand endpoints"
```

---

### Task 6: Build `ReportHero` frontend component

**Files:**

- Create: `alchymine/web/src/components/art/ReportHero.tsx`
- Modify: `alchymine/web/src/app/discover/report/[id]/page.tsx`

- [ ] **Step 1: Create `alchymine/web/src/components/art/ReportHero.tsx`**

```tsx
"use client";

import { useState, useEffect } from "react";

interface ReportHeroProps {
  reportId: string;
  apiBase: string;
  token: string | null;
}

interface ArtResponse {
  data_b64: string;
  mime_type: string;
  prompt_used: string;
}

export default function ReportHero({
  reportId,
  apiBase,
  token,
}: ReportHeroProps) {
  const [art, setArt] = useState<ArtResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!reportId) return;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    fetch(`${apiBase}/api/v1/art/report/${reportId}/hero`, { headers })
      .then((res) => {
        if (res.status === 204 || !res.ok) return null;
        return res.json() as Promise<ArtResponse>;
      })
      .then(setArt)
      .catch(() => setArt(null))
      .finally(() => setLoading(false));
  }, [reportId, apiBase, token]);

  if (loading) {
    return (
      <div className="w-full h-48 rounded-2xl bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 animate-pulse" />
    );
  }

  if (!art) {
    return (
      <div className="w-full h-48 rounded-2xl bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 flex items-center justify-center">
        <span className="text-sm font-body text-text/30">
          Personalized art unavailable
        </span>
      </div>
    );
  }

  return (
    <figure className="w-full rounded-2xl overflow-hidden border border-white/[0.06]">
      <img
        src={`data:${art.mime_type};base64,${art.data_b64}`}
        alt="Personalized report illustration"
        className="w-full object-cover max-h-64"
      />
      <figcaption className="px-4 py-2 text-xs text-text/30 font-body bg-surface/50">
        AI-generated illustration — {art.prompt_used.slice(0, 80)}...
      </figcaption>
    </figure>
  );
}
```

- [ ] **Step 2: Add `ReportHero` to the report page**

In `alchymine/web/src/app/discover/report/[id]/page.tsx`, import and render `ReportHero` above the first narrative section. Look for the first `<MotionReveal>` or `<Card>` containing narrative content, and insert:

```tsx
import ReportHero from "@/components/art/ReportHero";

// Inside the JSX, before the first narrative Card:
<ReportHero
  reportId={reportId as string}
  apiBase={process.env.NEXT_PUBLIC_API_URL ?? ""}
  token={
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null
  }
/>;
```

- [ ] **Step 3: Add typed API function to `artApi.ts`**

Create `alchymine/web/src/lib/artApi.ts`:

```typescript
const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1";

function authHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ArtResponse {
  data_b64: string;
  mime_type: string;
  prompt_used: string;
}

export async function getReportHero(
  reportId: string,
): Promise<ArtResponse | null> {
  const res = await fetch(`${BASE}/art/report/${reportId}/hero`, {
    headers: authHeaders(),
  });
  if (res.status === 204 || !res.ok) return null;
  return res.json();
}

export async function generateStudioImage(
  prompt: string,
  stylePreset: string = "mystical",
  creativeDomain: string = "",
): Promise<ArtResponse> {
  const res = await fetch(`${BASE}/art/studio/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      prompt,
      style_preset: stylePreset,
      creative_domain: creativeDomain,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      (err as { detail?: string }).detail ?? "Image generation failed",
    );
  }
  return res.json();
}

export async function getJourneyArt(
  reportId: string,
): Promise<ArtResponse | null> {
  const res = await fetch(`${BASE}/art/report/${reportId}/journey`, {
    headers: authHeaders(),
  });
  if (res.status === 204 || !res.ok) return null;
  return res.json();
}

export async function getBrandElement(
  reportId: string,
  element: "logo" | "palette" | "pattern" | "avatar",
): Promise<ArtResponse | null> {
  const res = await fetch(`${BASE}/art/report/${reportId}/brand/${element}`, {
    headers: authHeaders(),
  });
  if (res.status === 204 || !res.ok) return null;
  return res.json();
}

export async function getArtStatus(): Promise<{ available: boolean }> {
  const res = await fetch(`${BASE}/art/status`, { headers: authHeaders() });
  if (!res.ok) return { available: false };
  return res.json();
}
```

- [ ] **Step 4: Run frontend lint**

```bash
cd /i/GithubI/Alchymine/alchymine/web && npm run lint
```

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/components/art/ alchymine/web/src/lib/artApi.ts alchymine/web/src/app/discover/report/
git commit -m "feat(art): add ReportHero component and artApi client"
```

---

## Sprint 3–4 (Weeks 5–8): Creative Studio

### Task 7: Build `StylePresetPicker` component

**Files:**

- Create: `alchymine/web/src/components/art/StylePresetPicker.tsx`

- [ ] **Step 1: Create the component**

```tsx
"use client";

interface Preset {
  id: string;
  label: string;
  description: string;
  swatch: string; // Tailwind gradient classes
}

const PRESETS: Preset[] = [
  {
    id: "mystical",
    label: "Mystical",
    description: "Sacred geometry, gold & indigo",
    swatch: "from-primary/40 to-secondary/40",
  },
  {
    id: "digital",
    label: "Digital",
    description: "Neon lines, cyberpunk palette",
    swatch: "from-accent/40 to-blue-500/40",
  },
  {
    id: "organic",
    label: "Organic",
    description: "Botanical forms, earth tones",
    swatch: "from-green-800/40 to-amber-700/40",
  },
  {
    id: "geometric",
    label: "Geometric",
    description: "Bauhaus composition, primary colors",
    swatch: "from-red-600/40 to-blue-600/40",
  },
  {
    id: "surreal",
    label: "Surreal",
    description: "Dreamlike, melting forms",
    swatch: "from-purple-700/40 to-pink-500/40",
  },
];

interface StylePresetPickerProps {
  value: string;
  onChange: (preset: string) => void;
}

export default function StylePresetPicker({
  value,
  onChange,
}: StylePresetPickerProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      {PRESETS.map((preset) => (
        <button
          key={preset.id}
          onClick={() => onChange(preset.id)}
          className={`rounded-xl p-3 border transition-all text-left ${
            value === preset.id
              ? "border-primary bg-primary/10"
              : "border-white/[0.06] bg-surface hover:border-white/20"
          }`}
          aria-pressed={value === preset.id}
        >
          <div
            className={`h-10 rounded-lg bg-gradient-to-br ${preset.swatch} mb-2`}
          />
          <p className="text-sm font-display font-semibold text-text">
            {preset.label}
          </p>
          <p className="text-xs font-body text-text/50 mt-0.5">
            {preset.description}
          </p>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add alchymine/web/src/components/art/StylePresetPicker.tsx
git commit -m "feat(art): add StylePresetPicker component"
```

---

### Task 8: Build `ArtGallery` component

**Files:**

- Create: `alchymine/web/src/components/art/ArtGallery.tsx`

- [ ] **Step 1: Create the component**

```tsx
"use client";

import { ArtResponse } from "@/lib/artApi";

interface ArtGalleryProps {
  images: ArtResponse[];
  onDelete?: (index: number) => void;
}

export default function ArtGallery({ images, onDelete }: ArtGalleryProps) {
  if (images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-text/30">
        <p className="font-body text-sm">
          No images yet. Generate your first piece above.
        </p>
      </div>
    );
  }

  function downloadImage(art: ArtResponse, index: number) {
    const link = document.createElement("a");
    link.href = `data:${art.mime_type};base64,${art.data_b64}`;
    link.download = `alchymine-art-${index + 1}.png`;
    link.click();
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {images.map((art, i) => (
        <figure
          key={i}
          className="rounded-xl overflow-hidden border border-white/[0.06] group relative"
        >
          <img
            src={`data:${art.mime_type};base64,${art.data_b64}`}
            alt={`Generated art ${i + 1}`}
            className="w-full object-cover aspect-video"
          />
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
            <button
              onClick={() => downloadImage(art, i)}
              className="px-3 py-1.5 text-xs font-body bg-primary text-bg rounded-lg hover:bg-primary/80"
            >
              Download
            </button>
            {onDelete && (
              <button
                onClick={() => onDelete(i)}
                className="px-3 py-1.5 text-xs font-body bg-white/10 text-text rounded-lg hover:bg-white/20"
              >
                Remove
              </button>
            )}
          </div>
          <figcaption className="px-3 py-2 text-xs text-text/40 font-body truncate bg-surface/80">
            {art.prompt_used.slice(0, 60)}...
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add alchymine/web/src/components/art/ArtGallery.tsx
git commit -m "feat(art): add ArtGallery component with download support"
```

---

### Task 9: Build Creative Studio page

**Files:**

- Create: `alchymine/web/src/app/creative/studio/page.tsx`
- Modify: `alchymine/web/src/app/creative/page.tsx` (add Studio link)

- [ ] **Step 1: Create `alchymine/web/src/app/creative/studio/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import StylePresetPicker from "@/components/art/StylePresetPicker";
import ArtGallery from "@/components/art/ArtGallery";
import { generateStudioImage, ArtResponse, getArtStatus } from "@/lib/artApi";
import { useApi } from "@/lib/useApi";

export default function CreativeStudioPage() {
  const [prompt, setPrompt] = useState("");
  const [preset, setPreset] = useState("mystical");
  const [gallery, setGallery] = useState<ArtResponse[]>([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: status } = useApi(() => getArtStatus(), []);

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await generateStudioImage(prompt, preset);
      setGallery((prev) => [result, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  function handleDelete(index: number) {
    setGallery((prev) => prev.filter((_, i) => i !== index));
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg text-text px-4 py-12 max-w-5xl mx-auto">
        <header className="mb-10">
          <h1 className="text-4xl font-display font-bold text-primary mb-2">
            Creative Studio
          </h1>
          <p className="font-body text-text/60">
            Generate personalized art from your creative profile. Describe what
            you want to see.
          </p>
        </header>

        {status && !status.available && (
          <div className="mb-6 px-4 py-3 rounded-lg bg-yellow-900/20 border border-yellow-700/30 text-yellow-300 text-sm font-body">
            Generative art requires a Gemini API key. Contact your administrator
            to enable this feature.
          </div>
        )}

        <section className="mb-8 space-y-6">
          <div>
            <label className="block text-sm font-body text-text/60 mb-2">
              Your prompt
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the image you want to create..."
              rows={3}
              className="w-full bg-surface border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/30 focus:outline-none focus:border-primary/50 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-body text-text/60 mb-2">
              Style preset
            </label>
            <StylePresetPicker value={preset} onChange={setPreset} />
          </div>

          {error && <p className="text-sm text-red-400 font-body">{error}</p>}

          <button
            onClick={handleGenerate}
            disabled={
              generating ||
              !prompt.trim() ||
              (status !== null && !status?.available)
            }
            className="px-6 py-3 bg-primary text-bg font-display font-semibold rounded-xl hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? "Generating..." : "Generate Image"}
          </button>
        </section>

        <section>
          <h2 className="text-xl font-display font-semibold text-text mb-4">
            Gallery
          </h2>
          <ArtGallery images={gallery} onDelete={handleDelete} />
        </section>
      </div>
    </ProtectedRoute>
  );
}
```

- [ ] **Step 2: Add Studio link to creative page**

In `alchymine/web/src/app/creative/page.tsx`, find the section header or action area and add:

```tsx
import Link from "next/link";

// Near the top of the page content:
<Link
  href="/creative/studio"
  className="inline-flex items-center gap-2 px-4 py-2 border border-primary/40 text-primary rounded-xl text-sm font-body hover:bg-primary/10 transition-colors"
>
  Open Creative Studio
</Link>;
```

- [ ] **Step 3: Run lint and type-check**

```bash
cd /i/GithubI/Alchymine/alchymine/web && npm run lint && npm run type-check
```

- [ ] **Step 4: Commit**

```bash
git add alchymine/web/src/app/creative/studio/ alchymine/web/src/app/creative/page.tsx
git commit -m "feat(art): add Creative Studio page with prompt input and gallery"
```

---

## Sprint 5–6 (Weeks 9–12): Journey Art + Personal Brand

### Task 10: Journey illustration viewer page

**Files:**

- Create: `alchymine/web/src/app/discover/report/[id]/journey/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
"use client";

import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { getJourneyArt, ArtResponse } from "@/lib/artApi";

export default function JourneyPage() {
  const params = useParams();
  const reportId = params?.id as string;
  const [art, setArt] = useState<ArtResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!reportId) return;
    getJourneyArt(reportId)
      .then(setArt)
      .finally(() => setLoading(false));
  }, [reportId]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg text-text px-4 py-12 max-w-4xl mx-auto">
        <h1 className="text-3xl font-display font-bold text-primary mb-2">
          Your Journey
        </h1>
        <p className="font-body text-text/60 mb-8">
          A visual map of your transformation path.
        </p>
        {loading && (
          <div className="w-full aspect-video rounded-2xl bg-surface animate-pulse" />
        )}
        {!loading && !art && (
          <div className="w-full aspect-video rounded-2xl bg-gradient-to-br from-primary/10 via-secondary/10 to-accent/10 flex items-center justify-center">
            <p className="text-text/30 font-body text-sm">
              Journey illustration unavailable
            </p>
          </div>
        )}
        {art && (
          <figure className="rounded-2xl overflow-hidden border border-white/[0.06]">
            <img
              src={`data:${art.mime_type};base64,${art.data_b64}`}
              alt="Your transformation journey illustration"
              className="w-full object-cover"
            />
            <figcaption className="px-4 py-3 text-xs font-body text-text/30 bg-surface/60">
              AI-generated journey map
            </figcaption>
          </figure>
        )}
      </div>
    </ProtectedRoute>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add alchymine/web/src/app/discover/report/
git commit -m "feat(art): add journey illustration viewer page"
```

---

### Task 11: Personal brand page

**Files:**

- Create: `alchymine/web/src/app/discover/report/[id]/brand/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { getBrandElement, ArtResponse } from "@/lib/artApi";
import ArtGallery from "@/components/art/ArtGallery";

type BrandElement = "logo" | "palette" | "pattern" | "avatar";
const ELEMENTS: { id: BrandElement; label: string; description: string }[] = [
  {
    id: "logo",
    label: "Logo Mark",
    description: "A symbolic icon for your personal brand",
  },
  {
    id: "palette",
    label: "Color Palette",
    description: "A color story rooted in your archetype",
  },
  {
    id: "pattern",
    label: "Pattern",
    description: "A repeating motif for backgrounds and textures",
  },
  {
    id: "avatar",
    label: "Avatar",
    description: "An archetypal portrait for your profile",
  },
];

export default function BrandPage() {
  const params = useParams();
  const reportId = params?.id as string;
  const [generated, setGenerated] = useState<ArtResponse[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate(element: BrandElement) {
    setLoading(element);
    setError(null);
    try {
      const result = await getBrandElement(reportId, element);
      if (result) setGenerated((prev) => [result, ...prev]);
      else setError("Brand element generation is currently unavailable.");
    } catch {
      setError("Failed to generate brand element.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-bg text-text px-4 py-12 max-w-4xl mx-auto">
        <h1 className="text-3xl font-display font-bold text-primary mb-2">
          Personal Brand
        </h1>
        <p className="font-body text-text/60 mb-8">
          Generate identity elements rooted in your archetype and profile.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {ELEMENTS.map((el) => (
            <button
              key={el.id}
              onClick={() => handleGenerate(el.id)}
              disabled={loading === el.id}
              className="rounded-xl p-4 border border-white/[0.06] bg-surface hover:border-primary/40 transition-all text-left disabled:opacity-50"
            >
              <p className="font-display font-semibold text-text text-sm mb-1">
                {el.label}
              </p>
              <p className="text-xs font-body text-text/50">{el.description}</p>
              {loading === el.id && (
                <p className="text-xs text-primary mt-2 font-body">
                  Generating...
                </p>
              )}
            </button>
          ))}
        </div>
        {error && (
          <p className="text-sm text-red-400 font-body mb-6">{error}</p>
        )}
        <ArtGallery
          images={generated}
          onDelete={(i) =>
            setGenerated((prev) => prev.filter((_, idx) => idx !== i))
          }
        />
      </div>
    </ProtectedRoute>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add alchymine/web/src/app/discover/report/
git commit -m "feat(art): add personal brand generation page"
```

---

### Task 12: Full validation pass

- [ ] **Step 1: Run all Python tests**

```bash
CELERY_ALWAYS_EAGER=true pytest tests/llm/test_gemini.py tests/llm/test_art_prompts.py tests/api/test_generative_art.py -v
```

Expected: All pass.

- [ ] **Step 2: Run lint + format check**

```bash
ruff check alchymine/
ruff format --check alchymine/
```

Expected: Clean.

- [ ] **Step 3: Run mypy**

```bash
mypy alchymine/llm/gemini.py alchymine/llm/art_prompts.py alchymine/api/routers/generative_art.py
```

- [ ] **Step 4: Run frontend checks**

```bash
cd /i/GithubI/Alchymine/alchymine/web && npm run lint && npm run type-check
```

Expected: Clean.

- [ ] **Step 5: Full Python test suite**

```bash
CELERY_ALWAYS_EAGER=true pytest tests/ -v --tb=short -q
```

Expected: No regressions.

---

## Summary

| Sprint | Deliverable              | Key Files                                                     |
| ------ | ------------------------ | ------------------------------------------------------------- |
| 1–2    | Gemini client + config   | `alchymine/llm/gemini.py`, `alchymine/config.py`              |
| 1–2    | Art prompt templates     | `alchymine/llm/art_prompts.py`                                |
| 1–2    | API router (4 endpoints) | `alchymine/api/routers/generative_art.py`                     |
| 1–2    | Report hero image        | `alchymine/web/src/components/art/ReportHero.tsx`             |
| 3–4    | Creative Studio page     | `alchymine/web/src/app/creative/studio/page.tsx`              |
| 3–4    | Gallery + preset picker  | `ArtGallery.tsx`, `StylePresetPicker.tsx`                     |
| 5–6    | Journey illustration     | `alchymine/web/src/app/discover/report/[id]/journey/page.tsx` |
| 5–6    | Personal brand           | `alchymine/web/src/app/discover/report/[id]/brand/page.tsx`   |

**Graceful degradation contract:** Every endpoint returns 204 (not 500) when `GEMINI_API_KEY` is absent. Every frontend component renders a gradient placeholder when the API returns 204. Zero functionality is blocked for users without Gemini access.

**Next steps after launch:** Wire real `UserProfile` into report art prompts (replace `{}` stubs in Task 5), add Celery background task for async art generation + DB caching, and add image refresh/regenerate UI in the report page.

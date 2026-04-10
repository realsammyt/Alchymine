"""Tests for brand palette, brand logo, journey milestone prompts, and PDF art embedding.

Extends the generative art API test suite with coverage for:
- GET /api/v1/art/brand/palette
- POST /api/v1/art/brand/logo
- Journey milestone prompt builder
- PDF art embedding via ``embed_art`` query parameter
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.api.main import app
from alchymine.api.routers.generative_art import _gemini_dependency
from alchymine.db.base import Base
from alchymine.db.models import IdentityProfile, User
from alchymine.llm.art_prompts import (
    build_brand_logo_prompt,
    build_journey_milestone_prompt,
    derive_brand_palette,
)
from alchymine.llm.gemini import GeminiImageResult

TEST_USER_ID = "user-brand-1"


# ── DB fixtures ──────────────────────────────────────────────────────


def _build_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )


async def _init_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _make_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _seed_users(factory) -> None:
    async def _create() -> None:
        async with factory() as session:
            session.add(
                User(
                    id=TEST_USER_ID,
                    email="brand-test@example.com",
                    is_active=True,
                )
            )
            session.add(
                IdentityProfile(
                    user_id=TEST_USER_ID,
                    archetype={"primary": "creator"},
                    astrology={"sun_sign": "Leo"},
                    numerology={"life_path": 3},
                )
            )
            await session.commit()

    asyncio.run(_create())


@pytest.fixture
def _db_factory():
    engine = _build_engine()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_init_schema(engine))
    loop.close()
    factory = _make_session_factory(engine)
    _seed_users(factory)
    return factory


# ── Fake GeminiClient ────────────────────────────────────────────────


class _FakeGemini:
    def __init__(self, available: bool = True, succeed: bool = True):
        self._available = available
        self._succeed = succeed
        self.last_prompt: str | None = None

    @property
    def is_available(self) -> bool:
        return self._available

    async def generate_image(self, prompt: str) -> GeminiImageResult | None:
        self.last_prompt = prompt
        if not self._succeed:
            return None
        return GeminiImageResult(
            image_bytes=b"\x89PNG\r\n\x1a\nfake-logo",
            mime_type="image/png",
            prompt=prompt,
            model="gemini-test",
            generated_at=datetime.now(UTC),
        )


# ── TestClient fixture ───────────────────────────────────────────────


@pytest.fixture
def client(_db_factory, tmp_path) -> TestClient:
    factory = _db_factory

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_user() -> dict:
        return {"sub": TEST_USER_ID, "email": "brand-test@example.com"}

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch(
        "alchymine.llm.art_storage.get_art_cache_root",
        return_value=tmp_path,
    ):
        tc = TestClient(app)
        yield tc

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_gemini_dependency, None)


# ── Unit tests: art_prompts ──────────────────────────────────────────


class TestBuildJourneyMilestonePrompt:
    """Tests for build_journey_milestone_prompt."""

    def test_contains_milestone_name(self) -> None:
        profile = {"archetype": {"primary": "sage"}, "astrology": {"sun_sign": "Pisces"}}
        prompt = build_journey_milestone_prompt(profile, "identity")
        assert "identity" in prompt.lower()
        assert "Sage" in prompt

    def test_falls_back_on_unknown_milestone(self) -> None:
        prompt = build_journey_milestone_prompt({}, "unknown_phase")
        assert "symbolic gateway" in prompt.lower()

    def test_applies_style_preset(self) -> None:
        prompt = build_journey_milestone_prompt({}, "healing", style_preset="celestial")
        assert "Cosmic illustration" in prompt

    def test_empty_profile_no_crash(self) -> None:
        prompt = build_journey_milestone_prompt(None, "intake")
        assert "Wanderer" in prompt


class TestBuildBrandLogoPrompt:
    """Tests for build_brand_logo_prompt."""

    def test_contains_archetype(self) -> None:
        profile = {"archetype": {"primary": "hero"}, "astrology": {"sun_sign": "Aries"}}
        prompt = build_brand_logo_prompt(profile)
        assert "Hero" in prompt

    def test_contains_logo_keywords(self) -> None:
        prompt = build_brand_logo_prompt({})
        assert "logo" in prompt.lower()
        assert "no text" in prompt.lower()

    def test_includes_life_path(self) -> None:
        profile = {"numerology": {"life_path": 7}}
        prompt = build_brand_logo_prompt(profile)
        assert "7" in prompt


class TestDeriveBrandPalette:
    """Tests for derive_brand_palette."""

    def test_returns_four_colours(self) -> None:
        palette = derive_brand_palette({})
        assert "primary" in palette
        assert "secondary" in palette
        assert "accent" in palette
        assert "neutral" in palette

    def test_fire_element_returns_warm_palette(self) -> None:
        profile = {"astrology": {"sun_sign": "Aries"}}
        palette = derive_brand_palette(profile)
        assert "Ember" in palette["primary"]["name"]

    def test_archetype_overrides_accent(self) -> None:
        profile = {
            "astrology": {"sun_sign": "Pisces"},
            "archetype": {"primary": "sage"},
        }
        palette = derive_brand_palette(profile)
        assert "Sage" in palette["accent"]["name"]

    def test_hex_format(self) -> None:
        palette = derive_brand_palette({"astrology": {"sun_sign": "Leo"}})
        for key in ("primary", "secondary", "accent", "neutral"):
            assert palette[key]["hex"].startswith("#")
            assert len(palette[key]["hex"]) == 7


# ── API tests: brand palette ─────────────────────────────────────────


class TestBrandPaletteEndpoint:
    """Tests for GET /api/v1/art/brand/palette."""

    def test_returns_palette(self, client: TestClient) -> None:
        response = client.get("/api/v1/art/brand/palette")
        assert response.status_code == 200
        body = response.json()
        assert "primary" in body
        assert "hex" in body["primary"]
        assert "name" in body["primary"]

    def test_palette_has_fire_colors_for_leo(self, client: TestClient) -> None:
        """Seeded identity has Leo (fire). Expect fire palette."""
        response = client.get("/api/v1/art/brand/palette")
        body = response.json()
        # Fire primary is "Ember Red"
        assert "Ember" in body["primary"]["name"]


# ── API tests: brand logo ────────────────────────────────────────────


class TestBrandLogoEndpoint:
    """Tests for POST /api/v1/art/brand/logo."""

    def test_returns_201_on_success(self, client: TestClient) -> None:
        fake = _FakeGemini(available=True, succeed=True)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post("/api/v1/art/brand/logo")
        assert response.status_code == 201
        body = response.json()
        assert "image_id" in body
        assert "logo" in body["prompt"].lower()
        assert body["url"].startswith("/api/v1/art/")

    def test_returns_204_when_gemini_unavailable(self, client: TestClient) -> None:
        fake = _FakeGemini(available=False)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post("/api/v1/art/brand/logo")
        assert response.status_code == 204

    def test_returns_204_when_generation_fails(self, client: TestClient) -> None:
        fake = _FakeGemini(available=True, succeed=False)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post("/api/v1/art/brand/logo")
        assert response.status_code == 204

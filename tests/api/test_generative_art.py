"""Tests for the generative art API router.

Mocks GeminiClient at the module level so no real API calls are made.
Uses an in-memory SQLite DB so persistence and ownership checks run
end-to-end.
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
from alchymine.llm.gemini import GeminiImageResult


TEST_USER_ID = "user-art-1"
OTHER_USER_ID = "user-art-other"


# ── DB fixtures ─────────────────────────────────────────────────────────


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
                    email="art-test@example.com",
                    is_active=True,
                )
            )
            session.add(
                User(
                    id=OTHER_USER_ID,
                    email="other-art-test@example.com",
                    is_active=True,
                )
            )
            session.add(
                IdentityProfile(
                    user_id=TEST_USER_ID,
                    archetype={"primary": "sage"},
                    astrology={"sun_sign": "Pisces"},
                    numerology={"life_path": 7},
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


# ── Fake GeminiClient ───────────────────────────────────────────────────


class _FakeGemini:
    """Stand-in for GeminiClient that captures the last prompt."""

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
        # Echo the prompt back so the router persists the real personalized
        # text — this lets tests assert that the build_studio_prompt output
        # actually flowed through the request handler.
        return GeminiImageResult(
            image_bytes=b"\x89PNG\r\n\x1a\nfake-image",
            mime_type="image/png",
            prompt=prompt,
            model="gemini-test",
            generated_at=datetime.now(UTC),
        )


# ── Test client fixture ─────────────────────────────────────────────────


@pytest.fixture
def client(_db_factory, tmp_path) -> TestClient:
    """TestClient wired to the in-memory DB and a tmpdir art cache.

    Auth is overridden to return TEST_USER_ID.
    Gemini is overridden via dependency_overrides; individual tests
    swap their fake instances by calling client.app.dependency_overrides.
    """
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
        return {"sub": TEST_USER_ID, "email": "art-test@example.com"}

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    # Point the storage helper at a temp dir for the duration of the test
    with patch(
        "alchymine.llm.art_storage.get_art_cache_root",
        return_value=tmp_path,
    ):
        tc = TestClient(app)
        yield tc

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_gemini_dependency, None)


# ── POST /api/v1/art/generate ───────────────────────────────────────────


class TestGenerateArt:
    """Tests for POST /api/v1/art/generate."""

    def test_returns_201_on_success(self, client: TestClient) -> None:
        fake = _FakeGemini(available=True, succeed=True)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post(
            "/api/v1/art/generate",
            json={"style_preset": "celestial"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "image_id" in body
        assert body["url"] == f"/api/v1/art/{body['image_id']}"
        assert "Sage" in body["prompt"]  # personalized from seeded identity
        assert "Cosmic illustration" in body["prompt"]  # celestial style applied

    def test_returns_204_when_gemini_unavailable(self, client: TestClient) -> None:
        fake = _FakeGemini(available=False)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post(
            "/api/v1/art/generate",
            json={},
        )
        assert response.status_code == 204
        assert response.content == b""

    def test_returns_204_when_generation_fails(self, client: TestClient) -> None:
        """Even if available, a None result from the SDK collapses to 204."""
        fake = _FakeGemini(available=True, succeed=False)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post(
            "/api/v1/art/generate",
            json={},
        )
        assert response.status_code == 204

    def test_invalid_style_preset_returns_400(self, client: TestClient) -> None:
        fake = _FakeGemini(available=True, succeed=True)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post(
            "/api/v1/art/generate",
            json={"style_preset": "not-a-real-preset"},
        )
        assert response.status_code == 400
        assert "style_preset" in response.json()["detail"]

    def test_blocked_user_extension_returns_400(self, client: TestClient) -> None:
        """Content filter rejects extensions containing harmful patterns."""
        fake = _FakeGemini(available=True, succeed=True)
        app.dependency_overrides[_gemini_dependency] = lambda: fake

        response = client.post(
            "/api/v1/art/generate",
            json={
                "user_prompt_extension": "kill someone violently with illegal weapons",
            },
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "blocked" in detail.lower()

    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        """Removing the auth override produces 401 from the real dependency."""
        # Drop the auth override and the gemini override
        app.dependency_overrides.pop(get_current_user, None)

        response = client.post("/api/v1/art/generate", json={})
        assert response.status_code == 401


# ── GET /api/v1/art/{image_id} ──────────────────────────────────────────


class TestGetImage:
    """Tests for GET /api/v1/art/{image_id}."""

    def _create_image(self, client: TestClient) -> str:
        fake = _FakeGemini(available=True, succeed=True)
        app.dependency_overrides[_gemini_dependency] = lambda: fake
        response = client.post("/api/v1/art/generate", json={})
        assert response.status_code == 201
        return response.json()["image_id"]

    def test_returns_image_bytes_for_owner(self, client: TestClient) -> None:
        image_id = self._create_image(client)

        response = client.get(f"/api/v1/art/{image_id}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")
        assert response.content.startswith(b"\x89PNG")

    def test_returns_404_for_other_user(self, client: TestClient) -> None:
        image_id = self._create_image(client)

        async def _override_other() -> dict:
            return {"sub": OTHER_USER_ID, "email": "other-art-test@example.com"}

        app.dependency_overrides[get_current_user] = _override_other
        response = client.get(f"/api/v1/art/{image_id}")
        assert response.status_code == 404

    def test_returns_404_for_unknown_id(self, client: TestClient) -> None:
        response = client.get("/api/v1/art/no-such-image")
        assert response.status_code == 404

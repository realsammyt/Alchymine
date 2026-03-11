"""Tests for generative art API endpoints.

Covers:
- POST /art/generate — generate image from prompt (mocked Gemini)
- GET /art/{image_id} — retrieve cached image
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-minimum-32-characters-long")
os.environ.setdefault("CELERY_ALWAYS_EAGER", "true")

from alchymine.api.main import app  # noqa: E402
from alchymine.llm.gemini import ImageResult  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/art/generate
# ═══════════════════════════════════════════════════════════════════════════


class TestGenerateArt:
    """Tests for POST /api/v1/art/generate."""

    def test_generate_returns_204_when_gemini_unavailable(self, client: TestClient) -> None:
        """Returns 204 No Content when Gemini client is not available."""
        with patch("alchymine.api.routers.generative_art.GeminiClient") as MockClient:
            MockClient.return_value.is_available = False
            MockClient.return_value.generate_image = AsyncMock(return_value=None)
            response = client.post("/api/v1/art/generate", json={"prompt": "a serene forest"})
        assert response.status_code == 204

    def test_generate_returns_image_data_when_available(self, client: TestClient) -> None:
        """Returns base64 image data when Gemini responds successfully."""
        fake_result = ImageResult(
            data_b64="iVBORw0KGgo=",
            mime_type="image/png",
            prompt_used="a serene forest",
        )
        with patch("alchymine.api.routers.generative_art.GeminiClient") as MockClient:
            MockClient.return_value.is_available = True
            MockClient.return_value.generate_image = AsyncMock(return_value=fake_result)
            response = client.post("/api/v1/art/generate", json={"prompt": "a serene forest"})
        assert response.status_code == 200
        data = response.json()
        assert data["data_b64"] == "iVBORw0KGgo="
        assert data["mime_type"] == "image/png"
        assert "image_id" in data

    def test_generate_with_profile_uses_art_prompt_builder(self, client: TestClient) -> None:
        """When profile is provided, prompt is built from profile data."""
        fake_result = ImageResult(
            data_b64="abc123==",
            mime_type="image/png",
            prompt_used="built-prompt",
        )
        with patch("alchymine.api.routers.generative_art.GeminiClient") as MockClient:
            MockClient.return_value.is_available = True
            MockClient.return_value.generate_image = AsyncMock(return_value=fake_result)
            response = client.post(
                "/api/v1/art/generate",
                json={
                    "profile": {
                        "zodiac_sign": "Pisces",
                        "archetype": "The Visionary",
                        "system": "intelligence",
                    }
                },
            )
        assert response.status_code == 200

    def test_generate_requires_prompt_or_profile(self, client: TestClient) -> None:
        """Returns 422 when neither prompt nor profile is provided."""
        response = client.post("/api/v1/art/generate", json={})
        assert response.status_code == 422

    def test_generate_returns_204_when_generation_fails(self, client: TestClient) -> None:
        """Returns 204 when available but generation returns None."""
        with patch("alchymine.api.routers.generative_art.GeminiClient") as MockClient:
            MockClient.return_value.is_available = True
            MockClient.return_value.generate_image = AsyncMock(return_value=None)
            response = client.post("/api/v1/art/generate", json={"prompt": "a mountain"})
        assert response.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/art/{image_id}
# ═══════════════════════════════════════════════════════════════════════════


class TestRetrieveArt:
    """Tests for GET /api/v1/art/{image_id}."""

    def test_retrieve_returns_404_for_unknown_id(self, client: TestClient) -> None:
        response = client.get("/api/v1/art/nonexistent-image-id")
        assert response.status_code == 404

    def test_retrieve_returns_cached_image(self, client: TestClient) -> None:
        """Image stored during generate is retrievable by image_id."""
        fake_result = ImageResult(
            data_b64="iVBORw0KGgo=",
            mime_type="image/png",
            prompt_used="a serene forest",
        )
        with patch("alchymine.api.routers.generative_art.GeminiClient") as MockClient:
            MockClient.return_value.is_available = True
            MockClient.return_value.generate_image = AsyncMock(return_value=fake_result)
            gen_response = client.post(
                "/api/v1/art/generate", json={"prompt": "a serene forest"}
            )

        assert gen_response.status_code == 200
        image_id = gen_response.json()["image_id"]

        get_response = client.get(f"/api/v1/art/{image_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["data_b64"] == "iVBORw0KGgo="
        assert data["mime_type"] == "image/png"

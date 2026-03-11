"""Tests for Gemini image generation client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.llm.gemini import GeminiClient, ImageResult


def test_image_result_dataclass() -> None:
    r = ImageResult(data_b64="abc==", mime_type="image/png", prompt_used="test")
    assert r.data_b64 == "abc=="
    assert r.mime_type == "image/png"
    assert r.prompt_used == "test"


def test_gemini_client_is_available_false_when_no_key() -> None:
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = ""
        client = GeminiClient()
        assert client.is_available is False


def test_gemini_client_is_available_true_when_key_and_sdk_present() -> None:
    mock_sdk = MagicMock()
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "some-key"
        with patch("alchymine.llm.gemini.genai", mock_sdk):
            client = GeminiClient()
            assert client.is_available is True


@pytest.mark.asyncio
async def test_generate_image_no_key_returns_none() -> None:
    """Client returns None gracefully when no API key is configured."""
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = ""
        client = GeminiClient()
        result = await client.generate_image("a serene forest")
    assert result is None


@pytest.mark.asyncio
async def test_generate_image_returns_result() -> None:
    """Client returns ImageResult when Gemini responds with image data."""
    fake_b64 = "iVBORw0KGgo="
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "fake-key"
        with patch("alchymine.llm.gemini.genai") as mock_genai:
            mock_part = MagicMock()
            mock_part.inline_data.data = fake_b64
            mock_part.inline_data.mime_type = "image/png"
            mock_response = MagicMock()
            mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
            mock_genai.Client.return_value.aio.models.generate_content = AsyncMock(
                return_value=mock_response
            )
            client = GeminiClient()
            result = await client.generate_image("a serene forest")
    assert result is not None
    assert result.data_b64 == fake_b64
    assert result.mime_type == "image/png"
    assert result.prompt_used == "a serene forest"


@pytest.mark.asyncio
async def test_generate_image_sdk_unavailable_returns_none() -> None:
    """Client returns None gracefully when google-genai SDK is not installed."""
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "fake-key"
        with patch("alchymine.llm.gemini.genai", None):
            client = GeminiClient()
            result = await client.generate_image("a mountain sunrise")
    assert result is None


@pytest.mark.asyncio
async def test_generate_image_api_error_returns_none() -> None:
    """Client returns None and logs warning when Gemini API raises."""
    with patch("alchymine.llm.gemini.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "fake-key"
        with patch("alchymine.llm.gemini.genai") as mock_genai:
            mock_genai.Client.return_value.aio.models.generate_content = AsyncMock(
                side_effect=RuntimeError("API quota exceeded")
            )
            client = GeminiClient()
            result = await client.generate_image("a mountain sunrise")
    assert result is None

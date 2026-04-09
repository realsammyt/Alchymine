"""Tests for the Gemini image generation client.

These tests never hit the real Gemini API — every call is mocked.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.llm.gemini import (
    GeminiClient,
    GeminiImageResult,
    get_gemini_client,
)


def test_image_result_dataclass_holds_image_metadata() -> None:
    """GeminiImageResult is a frozen dataclass with the documented fields."""
    now = datetime.utcnow()
    result = GeminiImageResult(
        image_bytes=b"\x89PNG\r\n\x1a\n",
        mime_type="image/png",
        prompt="a serene forest",
        model="gemini-test",
        generated_at=now,
    )
    assert result.image_bytes == b"\x89PNG\r\n\x1a\n"
    assert result.mime_type == "image/png"
    assert result.prompt == "a serene forest"
    assert result.model == "gemini-test"
    assert result.generated_at == now


def test_client_unavailable_when_api_key_missing() -> None:
    """Client gracefully reports unavailable when no API key is configured."""
    client = GeminiClient(api_key=None, model="gemini-test")
    assert client.is_available is False


def test_client_unavailable_when_api_key_empty_string() -> None:
    """Empty string is treated identically to a missing key."""
    client = GeminiClient(api_key="", model="gemini-test")
    assert client.is_available is False


@pytest.mark.asyncio
async def test_generate_image_returns_none_when_unavailable() -> None:
    """generate_image returns None (not raises) when client is unavailable."""
    client = GeminiClient(api_key=None, model="gemini-test")
    result = await client.generate_image("a serene forest")
    assert result is None


def test_client_unavailable_when_sdk_missing() -> None:
    """If google-genai is not importable, the client must degrade gracefully."""
    # Patch the module-level _genai reference to None to simulate missing SDK.
    with patch("alchymine.llm.gemini._genai", None):
        client = GeminiClient(api_key="fake-key", model="gemini-test")
        assert client.is_available is False


@pytest.mark.asyncio
async def test_generate_image_returns_result_on_success() -> None:
    """Successful SDK call yields a GeminiImageResult with decoded bytes."""
    raw_bytes = b"\x89PNG\r\n\x1a\nfake-image-payload"

    fake_part = MagicMock()
    fake_part.inline_data = MagicMock()
    fake_part.inline_data.data = raw_bytes
    fake_part.inline_data.mime_type = "image/png"

    fake_response = MagicMock()
    fake_response.candidates = [MagicMock(content=MagicMock(parts=[fake_part]))]

    fake_genai_module = MagicMock()
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)
    fake_genai_module.Client.return_value = fake_client

    with patch("alchymine.llm.gemini._genai", fake_genai_module):
        client = GeminiClient(api_key="fake-key", model="gemini-test")
        assert client.is_available is True
        result = await client.generate_image("a serene forest")

    assert result is not None
    assert result.image_bytes == raw_bytes
    assert result.mime_type == "image/png"
    assert result.prompt == "a serene forest"
    assert result.model == "gemini-test"


@pytest.mark.asyncio
async def test_generate_image_returns_none_on_sdk_exception() -> None:
    """Network or auth errors are logged and swallowed — never raised."""
    fake_genai_module = MagicMock()
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(
        side_effect=RuntimeError("network unreachable")
    )
    fake_genai_module.Client.return_value = fake_client

    with patch("alchymine.llm.gemini._genai", fake_genai_module):
        client = GeminiClient(api_key="fake-key", model="gemini-test")
        result = await client.generate_image("a serene forest")

    assert result is None


@pytest.mark.asyncio
async def test_generate_image_returns_none_when_no_image_part() -> None:
    """Response with no inline image data returns None gracefully."""
    fake_response = MagicMock()
    fake_response.candidates = []

    fake_genai_module = MagicMock()
    fake_client = MagicMock()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)
    fake_genai_module.Client.return_value = fake_client

    with patch("alchymine.llm.gemini._genai", fake_genai_module):
        client = GeminiClient(api_key="fake-key", model="gemini-test")
        result = await client.generate_image("a serene forest")

    assert result is None


def test_get_gemini_client_returns_singleton() -> None:
    """The factory caches a single client instance per process."""
    fake_settings = MagicMock()
    fake_settings.gemini_api_key = ""
    fake_settings.gemini_model = "gemini-test"

    # Clear cache and patch settings so we never touch the real env file
    get_gemini_client.cache_clear()
    with patch("alchymine.llm.gemini.get_settings", return_value=fake_settings):
        a = get_gemini_client()
        b = get_gemini_client()
    assert a is b
    assert isinstance(a, GeminiClient)
    get_gemini_client.cache_clear()

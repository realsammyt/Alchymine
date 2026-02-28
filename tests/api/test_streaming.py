"""Tests for Streaming LLM API endpoints.

Covers:
- SSE narrative streaming endpoint
- Event format validation (data: chunks, event: done sentinel)
- Fallback behavior when no LLM backend is available
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestStreamNarrativeEndpoint:
    """GET /api/v1/stream/narrative"""

    def test_streaming_returns_200(self, client: TestClient) -> None:
        """The streaming endpoint should return 200 with event-stream media type."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            response = client.get(
                "/api/v1/stream/narrative?prompt=Tell+me+about+numerology"
            )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_streaming_ends_with_done_event(self, client: TestClient) -> None:
        """The stream must end with an event: done sentinel."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            response = client.get(
                "/api/v1/stream/narrative?prompt=Hello"
            )
        body = response.text
        assert "event: done\ndata: \n\n" in body

    def test_streaming_contains_data_events(self, client: TestClient) -> None:
        """The stream should contain data: events with content."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            response = client.get(
                "/api/v1/stream/narrative?prompt=Hello"
            )
        body = response.text
        # Should contain at least one data: line with content
        data_lines = [line for line in body.split("\n") if line.startswith("data: ") and line.strip() != "data:"]
        assert len(data_lines) > 0

    def test_streaming_fallback_content(self, client: TestClient) -> None:
        """When backend=none, the fallback message should be streamed."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            response = client.get(
                "/api/v1/stream/narrative?prompt=Hello"
            )
        body = response.text
        # The fallback message should appear across the data events
        assert "unavailable" in body.lower()

    def test_streaming_requires_prompt(self, client: TestClient) -> None:
        """The endpoint should require a prompt parameter."""
        response = client.get("/api/v1/stream/narrative")
        assert response.status_code == 422

    def test_streaming_with_system_prompt(self, client: TestClient) -> None:
        """The endpoint should accept an optional system_prompt."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            response = client.get(
                "/api/v1/stream/narrative"
                "?prompt=Hello"
                "&system_prompt=You+are+a+helpful+assistant"
            )
        assert response.status_code == 200

    def test_streaming_cache_control_headers(self, client: TestClient) -> None:
        """SSE responses should have no-cache headers."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            response = client.get(
                "/api/v1/stream/narrative?prompt=Hello"
            )
        assert response.headers.get("cache-control") == "no-cache"


class TestStreamGenerateMethod:
    """Test the LLMClient.stream_generate method directly."""

    @pytest.mark.asyncio
    async def test_stream_generate_none_backend(self) -> None:
        """stream_generate with backend=none should yield fallback words."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            from alchymine.llm.client import LLMClient

            client = LLMClient()

        chunks: list[str] = []
        async for chunk in client.stream_generate("test prompt"):
            chunks.append(chunk)

        full_text = "".join(chunks)
        assert "unavailable" in full_text.lower()
        assert len(chunks) > 1  # Should be word-by-word

    @pytest.mark.asyncio
    async def test_stream_generate_mock_ollama(self) -> None:
        """stream_generate should fall back to Ollama when Claude is unavailable."""
        with patch.dict(
            "os.environ",
            {"LLM_BACKEND": "ollama", "ANTHROPIC_API_KEY": ""},
            clear=False,
        ):
            from alchymine.llm.client import LLMClient

            client = LLMClient()

        # Mock the OllamaClient.stream_generate to yield test chunks
        async def mock_stream(*args, **kwargs):
            for chunk in ["Hello ", "world ", "test"]:
                yield chunk

        client._ollama_client.stream_generate = mock_stream  # type: ignore[assignment]

        chunks: list[str] = []
        async for chunk in client.stream_generate("test prompt"):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world test"

"""Regression guard: GET /stream/narrative must stay gone.

The endpoint was an authenticated, arbitrary-prompt proxy straight to the
LLM backend. Nothing in the frontend ever called it, so its only real
users would have been anyone holding a token who wanted free inference on
our account. It was removed rather than capped, because a prompt
passthrough with no product behind it has no version worth keeping.

Chat (``POST /api/v1/chat``) is the supported streaming surface: same SSE
shape, but scope-enforced, safety-filtered, and persisted.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_narrative_stream_route_is_gone(client: TestClient) -> None:
    response = client.get("/api/v1/stream/narrative", params={"prompt": "hello"})
    assert response.status_code == 404


def test_narrative_stream_route_is_absent_from_the_schema(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert not [path for path in paths if "stream/narrative" in path]

"""Tests for API middleware — error handling, request logging, rate limiting.

Covers:
- ErrorHandlerMiddleware catches unhandled exceptions and returns JSON
- RequestLoggingMiddleware produces log entries with method, path, status, duration
- RateLimitMiddleware rejects requests after limit is exceeded
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alchymine.api.middleware import (
    ErrorHandlerMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers — minimal FastAPI apps for isolated middleware testing
# ═══════════════════════════════════════════════════════════════════════════


def _make_error_app() -> FastAPI:
    """Create a minimal app with ErrorHandlerMiddleware and a crashing route."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/ok")
    async def ok() -> dict:
        return {"status": "ok"}

    @app.get("/crash")
    async def crash() -> dict:
        raise RuntimeError("Something went wrong")

    return app


def _make_logging_app() -> FastAPI:
    """Create a minimal app with RequestLoggingMiddleware."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/hello")
    async def hello() -> dict:
        return {"message": "hello"}

    return app


def _make_rate_limit_app(max_requests: int = 5, window_seconds: int = 60) -> FastAPI:
    """Create a minimal app with RateLimitMiddleware (low limit for testing)."""
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware, max_requests=max_requests, window_seconds=window_seconds
    )

    @app.get("/ping")
    async def ping() -> dict:
        return {"pong": True}

    return app


# ═══════════════════════════════════════════════════════════════════════════
# ErrorHandlerMiddleware
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorHandlerMiddleware:
    """Tests for ErrorHandlerMiddleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_error_app(), raise_server_exceptions=False)

    def test_normal_request_passes_through(self, client: TestClient) -> None:
        """Non-erroring requests pass through unmodified."""
        response = client.get("/ok")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_unhandled_exception_returns_500_json(self, client: TestClient) -> None:
        """Unhandled exception produces a 500 JSON response."""
        response = client.get("/crash")
        assert response.status_code == 500
        data = response.json()
        assert data["status_code"] == 500
        assert "detail" in data

    def test_error_detail_contains_exception_message(self, client: TestClient) -> None:
        """Error detail includes the exception's message text."""
        response = client.get("/crash")
        data = response.json()
        assert "Something went wrong" in data["detail"]

    def test_error_response_is_json_content_type(self, client: TestClient) -> None:
        """Error response has application/json content type."""
        response = client.get("/crash")
        assert "application/json" in response.headers["content-type"]


# ═══════════════════════════════════════════════════════════════════════════
# RequestLoggingMiddleware
# ═══════════════════════════════════════════════════════════════════════════


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_logging_app())

    def test_request_produces_log_entry(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Each request generates a log message."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        assert len(caplog.records) >= 1

    def test_log_contains_method(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Log message includes the HTTP method."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        assert any("GET" in msg for msg in log_messages)

    def test_log_contains_path(self, client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
        """Log message includes the request path."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        assert any("/hello" in msg for msg in log_messages)

    def test_log_contains_status_code(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Log message includes the response status code."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        assert any("200" in msg for msg in log_messages)

    def test_log_contains_duration(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Log message includes duration in milliseconds."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        # Duration should be something like "0.5ms" or "1.2ms"
        assert any("ms" in msg for msg in log_messages)


# ═══════════════════════════════════════════════════════════════════════════
# RateLimitMiddleware
# ═══════════════════════════════════════════════════════════════════════════


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_rate_limit_app(max_requests=5, window_seconds=60))

    def test_requests_within_limit_succeed(self, client: TestClient) -> None:
        """Requests within the rate limit return 200."""
        for _ in range(5):
            response = client.get("/ping")
            assert response.status_code == 200

    def test_request_exceeding_limit_returns_429(self, client: TestClient) -> None:
        """Request exceeding the rate limit returns 429."""
        for _ in range(5):
            client.get("/ping")
        response = client.get("/ping")
        assert response.status_code == 429

    def test_rate_limit_error_is_json(self, client: TestClient) -> None:
        """Rate limit error response is structured JSON."""
        for _ in range(5):
            client.get("/ping")
        response = client.get("/ping")
        data = response.json()
        assert data["status_code"] == 429
        assert "detail" in data

    def test_rate_limit_includes_retry_after(self, client: TestClient) -> None:
        """Rate limit response includes Retry-After header."""
        for _ in range(5):
            client.get("/ping")
        response = client.get("/ping")
        assert "retry-after" in response.headers

    def test_different_rate_limit_config(self) -> None:
        """Rate limiter respects custom max_requests configuration."""
        app = _make_rate_limit_app(max_requests=2, window_seconds=60)
        client = TestClient(app)
        # First 2 should pass
        assert client.get("/ping").status_code == 200
        assert client.get("/ping").status_code == 200
        # Third should be rejected
        assert client.get("/ping").status_code == 429

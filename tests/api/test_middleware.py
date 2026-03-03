"""Tests for API middleware — error handling, request logging, rate limiting.

Covers:
- ErrorHandlerMiddleware catches unhandled exceptions and returns JSON
- RequestLoggingMiddleware produces log entries with method, path, status, duration
- RateLimitMiddleware (Redis-backed):
  - Rate limiting with mocked Redis
  - Stricter auth route limits
  - Redis-unavailable fallback (logs warning, allows traffic)
  - Sliding window expiry
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alchymine.api.middleware import (
    DEFAULT_ROUTE_LIMITS,
    ErrorHandlerMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers — minimal FastAPI apps for isolated middleware testing
# ═══════════════════════════════════════════════════════════════════════════


def _make_error_app():
    """Create a minimal app with ErrorHandlerMiddleware and a crashing route."""
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    @app.get("/crash")
    async def crash():
        raise RuntimeError("Something went wrong")

    return app


def _make_logging_app():
    """Create a minimal app with RequestLoggingMiddleware."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/hello")
    async def hello():
        return {"message": "hello"}

    return app


def _make_rate_limit_app(
    max_requests=5,
    window_seconds=60,
    route_limits=None,
):
    """Create a minimal app with RateLimitMiddleware (low limit for testing)."""
    middleware_kwargs = dict(
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    if route_limits is not None:
        middleware_kwargs["route_limits"] = route_limits

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, **middleware_kwargs)

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    @app.get("/api/v1/auth/login")
    async def auth_login():
        return {"token": "fake"}

    @app.get("/api/v1/items")
    async def items():
        return {"items": []}

    return app


def _get_fake_redis():
    """Create a fresh fakeredis async instance."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def _patch_redis(fake_redis):
    """Return a context manager that patches redis.asyncio.from_url to return fake_redis.

    The fake_redis instance already responds to ping(), so the middleware
    connectivity check will succeed.
    """
    return patch("redis.asyncio.from_url", return_value=fake_redis)


# ═══════════════════════════════════════════════════════════════════════════
# ErrorHandlerMiddleware
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorHandlerMiddleware:
    """Tests for ErrorHandlerMiddleware."""

    @pytest.fixture
    def client(self):
        return TestClient(_make_error_app(), raise_server_exceptions=False)

    def test_normal_request_passes_through(self, client):
        """Non-erroring requests pass through unmodified."""
        response = client.get("/ok")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_unhandled_exception_returns_500_json(self, client):
        """Unhandled exception produces a 500 JSON response."""
        response = client.get("/crash")
        assert response.status_code == 500
        data = response.json()
        assert data["status_code"] == 500
        assert "detail" in data

    def test_error_detail_is_generic_safe_message(self, client):
        """Error detail is a generic safe message (never exposes internal exception text)."""
        response = client.get("/crash")
        data = response.json()
        assert "unexpected error" in data["detail"].lower()

    def test_error_response_is_json_content_type(self, client):
        """Error response has application/json content type."""
        response = client.get("/crash")
        assert "application/json" in response.headers["content-type"]


# ═══════════════════════════════════════════════════════════════════════════
# RequestLoggingMiddleware
# ═══════════════════════════════════════════════════════════════════════════


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    @pytest.fixture
    def client(self):
        return TestClient(_make_logging_app())

    def test_request_produces_log_entry(self, client, caplog):
        """Each request generates a log message."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        assert len(caplog.records) >= 1

    def test_log_contains_method(self, client, caplog):
        """Log message includes the HTTP method."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        assert any("GET" in msg for msg in log_messages)

    def test_log_contains_path(self, client, caplog):
        """Log message includes the request path."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        assert any("/hello" in msg for msg in log_messages)

    def test_log_contains_status_code(self, client, caplog):
        """Log message includes the response status code."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        assert any("200" in msg for msg in log_messages)

    def test_log_contains_duration(self, client, caplog):
        """Log message includes duration in milliseconds."""
        with caplog.at_level(logging.INFO, logger="alchymine.api"):
            client.get("/hello")
        log_messages = [r.message for r in caplog.records]
        # Duration should be something like "0.5ms" or "1.2ms"
        assert any("ms" in msg for msg in log_messages)


# ═══════════════════════════════════════════════════════════════════════════
# RateLimitMiddleware — Redis-backed
# ═══════════════════════════════════════════════════════════════════════════


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware with mocked Redis."""

    @pytest.fixture
    def fake_redis(self):
        return _get_fake_redis()

    @pytest.fixture
    def client(self, fake_redis):
        app = _make_rate_limit_app(max_requests=5, window_seconds=60)
        with _patch_redis(fake_redis):
            yield TestClient(app)

    def test_requests_within_limit_succeed(self, client):
        """Requests within the rate limit return 200."""
        for _ in range(5):
            response = client.get("/ping")
            assert response.status_code == 200

    def test_request_exceeding_limit_returns_429(self, client):
        """Request exceeding the rate limit returns 429."""
        for _ in range(5):
            client.get("/ping")
        response = client.get("/ping")
        assert response.status_code == 429

    def test_rate_limit_error_is_json(self, client):
        """Rate limit error response is structured JSON."""
        for _ in range(5):
            client.get("/ping")
        response = client.get("/ping")
        data = response.json()
        assert data["status_code"] == 429
        assert "detail" in data

    def test_rate_limit_includes_retry_after(self, client):
        """Rate limit response includes Retry-After header."""
        for _ in range(5):
            client.get("/ping")
        response = client.get("/ping")
        assert "retry-after" in response.headers

    def test_different_rate_limit_config(self, fake_redis):
        """Rate limiter respects custom max_requests configuration."""
        app = _make_rate_limit_app(max_requests=2, window_seconds=60)
        with _patch_redis(fake_redis):
            client = TestClient(app)
            # First 2 should pass
            assert client.get("/ping").status_code == 200
            assert client.get("/ping").status_code == 200
            # Third should be rejected
            assert client.get("/ping").status_code == 429


class TestRateLimitAuthRoutes:
    """Tests for stricter rate limits on auth routes."""

    @pytest.fixture
    def fake_redis(self):
        return _get_fake_redis()

    @pytest.fixture
    def client(self, fake_redis):
        app = _make_rate_limit_app(
            max_requests=100,
            window_seconds=60,
            route_limits=DEFAULT_ROUTE_LIMITS,
        )
        with _patch_redis(fake_redis):
            yield TestClient(app)

    def test_auth_route_has_stricter_limit(self, client):
        """Auth routes enforce the stricter 20 req/60s limit."""
        for i in range(20):
            response = client.get("/api/v1/auth/login")
            assert response.status_code == 200, f"Request {i+1} failed unexpectedly"
        # 21st should be rejected
        response = client.get("/api/v1/auth/login")
        assert response.status_code == 429

    def test_api_route_uses_default_limit(self, fake_redis):
        """Non-auth API routes use the default 100 req/60s limit."""
        app = _make_rate_limit_app(
            max_requests=100,
            window_seconds=60,
            route_limits=DEFAULT_ROUTE_LIMITS,
        )
        with _patch_redis(fake_redis):
            client = TestClient(app)
            # Send 100 requests — all should succeed
            for i in range(100):
                response = client.get("/api/v1/items")
                assert response.status_code == 200, f"Request {i+1} failed unexpectedly"
            # 101st should be rejected
            response = client.get("/api/v1/items")
            assert response.status_code == 429

    def test_non_api_route_uses_instance_defaults(self, fake_redis):
        """Routes outside /api/v1/ use the middleware's default limits."""
        app = _make_rate_limit_app(
            max_requests=3,
            window_seconds=60,
            route_limits=DEFAULT_ROUTE_LIMITS,
        )
        with _patch_redis(fake_redis):
            client = TestClient(app)
            for _ in range(3):
                assert client.get("/ping").status_code == 200
            assert client.get("/ping").status_code == 429


class TestRateLimitRedisFallback:
    """Tests for graceful degradation when Redis is unavailable."""

    def test_redis_unavailable_allows_traffic(self):
        """When Redis is down, requests are allowed through."""
        app = _make_rate_limit_app(max_requests=1, window_seconds=60)
        # Patch from_url to raise — simulates Redis being down
        with patch(
            "redis.asyncio.from_url",
            side_effect=ConnectionError("Connection refused"),
        ):
            client = TestClient(app)
            # Even with limit=1, all should pass because Redis is "down"
            for _ in range(10):
                response = client.get("/ping")
                assert response.status_code == 200

    def test_redis_unavailable_logs_warning(self, caplog):
        """When Redis is unavailable, a warning is logged."""
        app = _make_rate_limit_app(max_requests=1, window_seconds=60)

        with caplog.at_level(logging.WARNING, logger="alchymine.api"):
            with patch(
                "redis.asyncio.from_url",
                side_effect=ConnectionError("Connection refused"),
            ):
                client = TestClient(app)
                client.get("/ping")

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("Redis unavailable" in msg for msg in warning_messages)

    def test_redis_error_mid_request_allows_traffic(self):
        """If Redis raises during INCR, request is allowed through."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis gone"))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            app = _make_rate_limit_app(max_requests=1, window_seconds=60)
            client = TestClient(app)
            response = client.get("/ping")
            assert response.status_code == 200


class TestRateLimitSlidingWindow:
    """Tests for sliding window expiry behavior."""

    @pytest.fixture
    def fake_redis(self):
        return _get_fake_redis()

    def test_window_expiry_resets_counter(self, fake_redis):
        """After the window expires, the counter resets and requests succeed again."""
        app = _make_rate_limit_app(max_requests=2, window_seconds=1)
        with _patch_redis(fake_redis):
            client = TestClient(app)

            # Exhaust the limit
            assert client.get("/ping").status_code == 200
            assert client.get("/ping").status_code == 200
            assert client.get("/ping").status_code == 429

            # Simulate window expiry by deleting the Redis key
            # (fakeredis supports TTL but we cannot easily fast-forward time,
            #  so we manually expire the key to test the reset logic)
            loop = asyncio.new_event_loop()

            async def _expire_keys():
                keys = await fake_redis.keys("rate_limit:*")
                for key in keys:
                    await fake_redis.delete(key)

            loop.run_until_complete(_expire_keys())
            loop.close()

            # Now requests should succeed again
            assert client.get("/ping").status_code == 200
            assert client.get("/ping").status_code == 200

    def test_key_has_ttl_set(self, fake_redis):
        """Redis key gets a TTL equal to the window seconds."""
        window = 60
        app = _make_rate_limit_app(max_requests=100, window_seconds=window)
        with _patch_redis(fake_redis):
            client = TestClient(app)
            client.get("/ping")

        loop = asyncio.new_event_loop()

        async def _check_ttl():
            keys = await fake_redis.keys("rate_limit:*")
            assert len(keys) >= 1
            ttl = await fake_redis.ttl(keys[0])
            # TTL should be close to window (within a few seconds)
            assert 0 < ttl <= window

        loop.run_until_complete(_check_ttl())
        loop.close()

    def test_key_format_includes_ip_bucket_and_window(self, fake_redis):
        """Redis keys follow the format rate_limit:{ip}:{bucket}:{window}."""
        app = _make_rate_limit_app(max_requests=100, window_seconds=60)
        with _patch_redis(fake_redis):
            client = TestClient(app)
            client.get("/ping")

        loop = asyncio.new_event_loop()

        async def _check_key():
            keys = await fake_redis.keys("rate_limit:*")
            assert len(keys) >= 1
            key = keys[0]
            parts = key.split(":")
            assert parts[0] == "rate_limit"
            # Should have 4 parts: rate_limit, ip, bucket, window
            assert len(parts) == 4

        loop.run_until_complete(_check_key())
        loop.close()

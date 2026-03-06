"""Alchymine API middleware — error handling, request logging, rate limiting.

Three middleware classes:
- ErrorHandlerMiddleware: Catches unhandled exceptions, returns structured JSON errors.
- RequestLoggingMiddleware: Logs method, path, status code, and request duration.
- RateLimitMiddleware: Redis-backed sliding-window rate limiter per client IP.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import time
from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("alchymine.api")


def _get_redis_url() -> str:
    """Resolve the Redis URL from settings or environment.

    Attempts to import ``get_settings`` from the shared config module (being
    developed concurrently).  Falls back to the ``REDIS_URL`` environment
    variable, then to a sensible default.
    """
    try:
        from alchymine.config import get_settings  # type: ignore[import-untyped]

        return str(get_settings().redis_url)
    except Exception:  # noqa: BLE001
        return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


# ═══════════════════════════════════════════════════════════════════════════
# Error Handler Middleware
# ═══════════════════════════════════════════════════════════════════════════


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return structured JSON error responses.

    Any exception that is not already an HTTPException will be caught and
    converted to a 500 JSON response with ``{"detail": "...", "status_code": 500}``.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An unexpected error occurred. Please try again later.",
                    "status_code": 500,
                },
            )


# ═══════════════════════════════════════════════════════════════════════════
# Request Logging Middleware
# ═══════════════════════════════════════════════════════════════════════════


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and duration (ms).

    Uses stdlib logging at INFO level on the ``alchymine.api`` logger.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


# ═══════════════════════════════════════════════════════════════════════════
# Rate Limit Middleware — Redis-backed sliding window
# ═══════════════════════════════════════════════════════════════════════════

# Networks whose X-Forwarded-For headers are trusted (internal proxies only)
TRUSTED_PROXY_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("172.16.0.0/12"),  # Docker internal
    ipaddress.ip_network("10.0.0.0/8"),  # Private networks
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
]

# Default per-prefix limits: (max_requests, window_seconds)
DEFAULT_ROUTE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/": (20, 60),
    "/api/v1/admin/": (30, 60),
    "/api/v1/": (100, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding-window rate limiter.

    Limits requests per client IP within a configurable time window.
    Supports per-route-prefix limits via ``route_limits``.

    Uses Redis ``INCR`` + ``EXPIRE`` for atomic, multi-process-safe counting.
    If Redis is unavailable, logs a warning and allows traffic through
    (graceful degradation — never block users due to infrastructure issues).

    Parameters
    ----------
    app : ASGIApp
        The ASGI application.
    max_requests : int
        Default maximum requests allowed per window (default: 100).
    window_seconds : int
        Default length of the sliding window in seconds (default: 60).
    redis_url : str | None
        Redis connection URL.  If ``None``, resolved from settings / env var.
    route_limits : dict[str, tuple[int, int]] | None
        Mapping of route prefix to ``(max_requests, window_seconds)``.
        The first matching prefix wins (checked in insertion order).
        If ``None``, uses :data:`DEFAULT_ROUTE_LIMITS`.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        redis_url: str | None = None,
        route_limits: dict[str, tuple[int, int]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(app, **kwargs)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis_url = redis_url
        self.route_limits = route_limits if route_limits is not None else DEFAULT_ROUTE_LIMITS
        self._redis: Any = None
        self._redis_failed = False

    async def _get_redis(self) -> Any:
        """Lazily connect to Redis.  Returns ``None`` if unavailable."""
        if self._redis is not None:
            return self._redis
        if self._redis_failed:
            return None
        try:
            import redis.asyncio as aioredis

            url = self._redis_url or _get_redis_url()
            self._redis = aioredis.from_url(url, decode_responses=True)
            # Quick connectivity check
            await self._redis.ping()
            return self._redis
        except Exception:  # noqa: BLE001
            logger.warning(
                "Redis unavailable for rate limiting — falling back to allowing all traffic"
            )
            self._redis_failed = True
            self._redis = None
            return None

    def _get_client_ip(self, request: Request) -> str:
        """Extract the real client IP, trusting X-Forwarded-For only from known proxy networks."""
        peer_ip = request.client.host if request.client else None
        if peer_ip:
            try:
                addr = ipaddress.ip_address(peer_ip)
                if any(addr in net for net in TRUSTED_PROXY_NETWORKS):
                    forwarded = request.headers.get("x-forwarded-for")
                    if forwarded:
                        return forwarded.split(",")[0].strip()
            except ValueError:
                pass
        return peer_ip or "unknown"

    def _resolve_limits(self, path: str) -> tuple[int, int]:
        """Return ``(max_requests, window_seconds)`` for a given request path.

        Checks ``route_limits`` prefixes in order; falls back to the instance
        defaults.
        """
        for prefix, limits in self.route_limits.items():
            if path.startswith(prefix):
                return limits
        return (self.max_requests, self.window_seconds)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        path = request.url.path
        max_req, window = self._resolve_limits(path)

        redis_conn = await self._get_redis()
        if redis_conn is None:
            # Graceful fallback — Redis unavailable, allow traffic
            return await call_next(request)

        bucket = "default"
        for prefix in self.route_limits:
            if path.startswith(prefix):
                bucket = prefix.replace("/", "_").strip("_")
                break
        key = f"rate_limit:{client_ip}:{bucket}:{window}"
        try:
            current_count: int = await redis_conn.incr(key)
            if current_count == 1:
                # First request in this window — set expiry
                await redis_conn.expire(key, window)

            if current_count > max_req:
                ttl: int = await redis_conn.ttl(key)
                retry_after = ttl if ttl > 0 else window
                logger.warning(
                    "Rate limit exceeded for %s on %s %s (%d/%d)",
                    client_ip,
                    request.method,
                    path,
                    current_count,
                    max_req,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                        "status_code": 429,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                    },
                )
        except Exception:  # noqa: BLE001
            # Redis error mid-request — allow traffic and reset connection on next attempt
            logger.warning("Redis error during rate limiting — allowing request through")
            self._redis = None
            self._redis_failed = False
            return await call_next(request)

        response = await call_next(request)
        return response

"""Alchymine API middleware — error handling, request logging, rate limiting.

Three middleware classes:
- ErrorHandlerMiddleware: Catches unhandled exceptions, returns structured JSON errors.
- RequestLoggingMiddleware: Logs method, path, status code, and request duration.
- RateLimitMiddleware: Simple sliding-window in-memory rate limiter per client IP.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("alchymine.api")


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
        except Exception as exc:
            logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error: {exc}",
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
# Rate Limit Middleware
# ═══════════════════════════════════════════════════════════════════════════


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window in-memory rate limiter.

    Limits requests per client IP within a configurable time window.
    Not suitable for production multi-process deployments (use Redis-based
    rate limiting for that); this provides a foundation and works well
    for single-process development and testing.

    Parameters
    ----------
    app : ASGIApp
        The ASGI application.
    max_requests : int
        Maximum requests allowed per window (default: 100).
    window_seconds : int
        Length of the sliding window in seconds (default: 60).
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app, **kwargs)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Map of client_ip -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from the request."""
        # Prefer X-Forwarded-For header (behind proxy), fall back to client host
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, ip: str, now: float) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = now - self.window_seconds
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        now = time.monotonic()

        self._clean_old_requests(client_ip, now)

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded for %s on %s %s",
                client_ip,
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "status_code": 429,
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                },
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response

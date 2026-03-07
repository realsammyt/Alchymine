"""Health check endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from alchymine import __version__

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=None)
async def health_check() -> dict | JSONResponse:
    """Health check for load balancers and monitoring.

    Checks database and Redis connectivity. Returns 503 if any
    dependency is unhealthy.
    """
    checks: dict = {
        "status": "healthy",
        "version": __version__,
        "service": "alchymine-api",
        "db": "ok",
        "redis": "ok",
    }

    # ── Database check ──
    try:
        from alchymine.api.deps import get_db_engine

        engine = get_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Health check: DB unavailable: %s", exc)
        checks["db"] = "unavailable"
        checks["status"] = "degraded"

    # ── Redis check ──
    try:
        import redis.asyncio as aioredis

        from alchymine.config import get_settings

        r = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        try:
            await r.ping()
        finally:
            await r.close()
    except Exception as exc:
        logger.warning("Health check: Redis unavailable: %s", exc)
        checks["redis"] = "unavailable"
        checks["status"] = "degraded"

    if checks["status"] != "healthy":
        return JSONResponse(content=checks, status_code=503)

    return checks

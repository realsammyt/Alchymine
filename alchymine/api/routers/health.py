"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from alchymine import __version__

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": __version__,
        "service": "alchymine-api",
    }

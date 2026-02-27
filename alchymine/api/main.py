"""Alchymine API — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alchymine import __version__
from alchymine.api.routers import astrology, compatibility, health, numerology, reports, wealth


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown."""
    # Startup: validate engines, warm caches
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="Alchymine API",
    description=(
        "Open-Source AI-Powered Personal Transformation Operating System. "
        "Five systems: Personalized Intelligence, Ethical Healing, "
        "Generational Wealth, Creative Development, Perspective Enhancement."
    ),
    version=__version__,
    license_info={"name": "CC-BY-NC-SA 4.0", "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"},
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # overridden by env in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(numerology.router, prefix="/api/v1", tags=["numerology"])
app.include_router(astrology.router, prefix="/api/v1", tags=["astrology"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(wealth.router, prefix="/api/v1", tags=["wealth"])
app.include_router(compatibility.router, prefix="/api/v1", tags=["compatibility"])

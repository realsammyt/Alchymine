"""Alchymine API — FastAPI application entry point."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alchymine import __version__
from alchymine.api.deps import create_tables_if_enabled, dispose_engine
from alchymine.api.middleware import (
    ErrorHandlerMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
)
from alchymine.api.routers import (
    admin,
    astrology,
    auth,
    biorhythm,
    compatibility,
    creative,
    feedback,
    healing,
    health,
    integration,
    journal,
    numerology,
    outcomes,
    personality,
    perspective,
    profile,
    reports,
    spiral,
    streaming,
    wealth,
)
from alchymine.config import get_settings


class _JSONFormatter(logging.Formatter):
    """Minimal JSON log formatter using stdlib only."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def _configure_logging() -> None:
    """Configure structured JSON logging for the API."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: startup and shutdown."""
    await create_tables_if_enabled()
    yield
    await dispose_engine()


app = FastAPI(
    title="Alchymine API",
    description=(
        "Open-Source AI-Powered Personal Transformation Operating System. "
        "Five systems: Personalized Intelligence, Ethical Healing, "
        "Generational Wealth, Creative Development, Perspective Enhancement."
    ),
    version=__version__,
    license_info={
        "name": "CC-BY-NC-SA 4.0",
        "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    },
    lifespan=lifespan,
)

# Middleware (outermost first — execution order is bottom-to-top)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)  # type: ignore[arg-type]
app.add_middleware(RequestIdMiddleware)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(profile.router, prefix="/api/v1", tags=["profile"])
app.include_router(numerology.router, prefix="/api/v1", tags=["numerology"])
app.include_router(astrology.router, prefix="/api/v1", tags=["astrology"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(wealth.router, prefix="/api/v1", tags=["wealth"])
app.include_router(compatibility.router, prefix="/api/v1", tags=["compatibility"])
app.include_router(biorhythm.router, prefix="/api/v1", tags=["biorhythm"])
app.include_router(healing.router, prefix="/api/v1", tags=["healing"])
app.include_router(creative.router, prefix="/api/v1", tags=["creative"])
app.include_router(perspective.router, prefix="/api/v1", tags=["perspective"])
app.include_router(personality.router, prefix="/api/v1", tags=["personality"])
app.include_router(journal.router, prefix="/api/v1", tags=["journal"])
app.include_router(outcomes.router, prefix="/api/v1", tags=["outcomes"])
app.include_router(streaming.router, prefix="/api/v1", tags=["streaming"])
app.include_router(spiral.router, prefix="/api/v1", tags=["spiral"])
app.include_router(integration.router, prefix="/api/v1", tags=["integration"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])

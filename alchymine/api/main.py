"""Alchymine API — FastAPI application entry point."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    bridges,
    chat,
    compatibility,
    creative,
    feedback,
    generative_art,
    healing,
    healing_skills,
    health,
    integration,
    journal,
    numerology,
    outcomes,
    personality,
    perspective,
    practice,
    profile,
    reports,
    spiral,
    wealth,
)
from alchymine.config import get_settings
from alchymine.db.encryption import verify_encryption_key
from alchymine.db.usage_counters import CostCeilingExceeded
from alchymine.engine.practice import install_practice_registry
from alchymine.llm.ledger import flush_pending_writes, log_ledger_status
from alchymine.mcp.transport import mount_all_mcp_routers


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
    # First, and unguarded. Almost every table this app reads has at least
    # one encrypted column, so a process that cannot build a working Fernet
    # has nothing useful to serve. Raising here makes uvicorn log the
    # operator message and exit non-zero instead of passing the health check
    # and then 500ing on whichever request first reads a profile.
    verify_encryption_key()
    await create_tables_if_enabled()
    # Deliberately unguarded. A bad pack or a mistyped PRACTICE_PACK_DIRS
    # stops the container here, where the deploy's own health machinery
    # sees it, rather than becoming a 500 for whichever user reaches
    # /practices first.
    install_practice_registry()
    log_ledger_status("api")
    yield
    # Ledger writes are detached tasks so a disconnected client cannot take
    # one down with it. Draining them here keeps a shutdown from dropping
    # spend that was already delivered and billed.
    await flush_pending_writes()
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

# Middleware (innermost first — last added is outermost).
# CORS must be added AFTER RateLimit so it wraps it: otherwise 429
# short-circuit responses carry no CORS headers (browsers then surface a
# generic network error) and OPTIONS preflights count against the limit.
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)  # type: ignore[arg-type]
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)


# Exception handlers. Registered on the app, so they run inside the
# middleware stack and produce a real response — ErrorHandlerMiddleware
# never sees these and never flattens them into a generic 500.
@app.exception_handler(CostCeilingExceeded)
async def _cost_ceiling_handler(request: Request, exc: CostCeilingExceeded) -> JSONResponse:
    """Render a tripped cost ceiling as a structured "come back later" state.

    503 rather than 429: the ceiling is ours, not something this caller
    did wrong, and it clears on a schedule we can name.
    """
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "llm_temporarily_unavailable",
                "message": (
                    "This feature is taking a short break while we catch up on demand. "
                    "Please try again later."
                ),
                "retry_at": exc.retry_at.isoformat(),
            }
        },
    )


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
app.include_router(healing_skills.router, prefix="/api/v1", tags=["healing-skills"])
app.include_router(bridges.router, prefix="/api/v1", tags=["bridges"])
app.include_router(creative.router, prefix="/api/v1", tags=["creative"])
app.include_router(perspective.router, prefix="/api/v1", tags=["perspective"])
app.include_router(personality.router, prefix="/api/v1", tags=["personality"])
app.include_router(practice.router, prefix="/api/v1", tags=["practice"])
app.include_router(journal.router, prefix="/api/v1", tags=["journal"])
app.include_router(outcomes.router, prefix="/api/v1", tags=["outcomes"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(spiral.router, prefix="/api/v1", tags=["spiral"])
app.include_router(integration.router, prefix="/api/v1", tags=["integration"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(generative_art.router, prefix="/api/v1", tags=["art"])

# MCP transport — JSON-RPC 2.0 endpoints for all five systems
mcp_parent = APIRouter()
mount_all_mcp_routers(mcp_parent)
app.include_router(mcp_parent)

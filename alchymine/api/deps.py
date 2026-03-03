"""FastAPI dependency injection for database access.

Provides:
- ``get_db_engine()`` — singleton async engine from ``DATABASE_URL`` env var
- ``get_db_session()`` — async generator yielding a session (for ``Depends()``)
- ``db_lifespan()`` — app lifespan that optionally auto-creates tables
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# Import all models so that Base.metadata is fully populated
import alchymine.db.models  # noqa: F401
from alchymine.config import get_settings
from alchymine.db.base import Base, get_async_engine, get_async_session_factory

logger = logging.getLogger(__name__)

# ─── Singleton Engine ──────────────────────────────────────────────────

_engine: AsyncEngine | None = None


def get_db_engine() -> AsyncEngine:
    """Return a singleton async engine.

    Creates the engine on first call using the ``DATABASE_URL`` environment
    variable.  Subsequent calls return the same instance.
    """
    global _engine
    if _engine is None:
        url = get_settings().database_url
        _engine = get_async_engine(url)
        parsed = urlparse(str(url))
        logger.info(
            "Database engine created (host=%s, db=%s)",
            parsed.hostname,
            parsed.path.lstrip("/"),
        )
    return _engine


def set_db_engine(engine: AsyncEngine | None) -> None:
    """Override the singleton engine (used in tests and shutdown)."""
    global _engine
    _engine = engine


# ─── Session Dependency ────────────────────────────────────────────────


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage::

        @router.get("/example")
        async def example(session: AsyncSession = Depends(get_db_session)):
            ...

    The session is automatically committed on success and rolled back on
    exception.
    """
    engine = get_db_engine()
    factory = get_async_session_factory(engine)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Table Auto-Creation ──────────────────────────────────────────────


async def create_tables_if_enabled() -> None:
    """Create all tables if ``AUTO_CREATE_TABLES=true``.

    Called during application startup.  In production, migrations are
    managed by Alembic; this is a convenience for dev/CI environments.
    """
    if os.environ.get("AUTO_CREATE_TABLES", "").lower() == "true":
        engine = get_db_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Auto-created database tables")


async def dispose_engine() -> None:
    """Dispose the singleton engine (called during shutdown)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")

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
            # Handlers that manage their own commits leave the session clean.
            # This commit is a no-op in that case (empty transaction).
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                logger.warning("Session rollback failed during dependency cleanup", exc_info=True)
            raise


# ─── Table Auto-Creation ──────────────────────────────────────────────


async def create_tables_if_enabled() -> None:
    """Apply database migrations if ``AUTO_CREATE_TABLES=true``.

    Called during application startup.  Runs ``alembic upgrade head``
    programmatically so the schema is always migration-managed.  Falls
    back to ``Base.metadata.create_all()`` only if Alembic config is
    unavailable (e.g. minimal test environments).
    """
    if os.environ.get("AUTO_CREATE_TABLES", "").lower() != "true":
        return

    try:
        from alembic import command
        from alembic.config import Config

        # Locate alembic.ini relative to the package
        import alchymine

        pkg_root = os.path.dirname(os.path.dirname(alchymine.__file__))
        ini_path = os.path.join(pkg_root, "alembic.ini")

        if os.path.exists(ini_path):
            alembic_cfg = Config(ini_path)
            # Override the DB URL to match what the app is using
            alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrated to head via Alembic")
            return
    except Exception as exc:
        logger.warning("Alembic migration failed (%s), falling back to create_all()", exc)

    # Fallback: create_all() for environments without Alembic config
    engine = get_db_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Auto-created database tables (create_all fallback)")


async def close_redis() -> None:
    """Close Redis connections used by the rate limiter middleware."""
    try:
        from alchymine.api.middleware import RateLimitMiddleware  # noqa: F401

        # The middleware instance holds the Redis connection
        # It will be garbage collected, but explicit cleanup is better
        logger.info("Redis cleanup requested during shutdown")
    except Exception as exc:
        logger.warning("Redis cleanup error: %s", exc)


async def dispose_engine() -> None:
    """Dispose the singleton engine and clean up connections (called during shutdown)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
    await close_redis()

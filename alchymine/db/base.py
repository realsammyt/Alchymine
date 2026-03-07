"""SQLAlchemy declarative base, async engine factory, and session factory.

Production uses ``asyncpg`` (PostgreSQL).  Tests use ``aiosqlite`` (SQLite).
The driver is selected automatically based on the DATABASE_URL scheme.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from alchymine.config import get_settings

# ─── Declarative Base ───────────────────────────────────────────────────


class Base(AsyncAttrs, DeclarativeBase):
    """Shared declarative base for all Alchymine ORM models."""


# ─── Engine Factory ─────────────────────────────────────────────────────


def get_async_engine(
    url: str | None = None,
    *,
    echo: bool = False,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Parameters
    ----------
    url:
        Database URL.  Falls back to the centralized ``Settings.database_url``.
    echo:
        When *True*, emit SQL statements to the log (useful for debugging).
    """
    db_url = url or get_settings().database_url

    # SQLite needs special connect_args for async
    connect_args: dict = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    kwargs: dict = {
        "echo": echo,
        "connect_args": connect_args,
    }
    if not db_url.startswith("sqlite"):
        kwargs.update(
            {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
        )

    return create_async_engine(db_url, **kwargs)


# ─── Session Factory ───────────────────────────────────────────────────


def get_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to *engine*."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_async_session(
    engine: AsyncEngine | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency-injectable async session generator.

    Usage with FastAPI::

        @app.get("/")
        async def root(session: AsyncSession = Depends(get_async_session)):
            ...

    For standalone scripts, pass an explicit *engine*.
    """
    _engine = engine or get_async_engine()
    factory = get_async_session_factory(_engine)
    async with factory() as session:
        yield session

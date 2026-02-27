"""Alchymine database layer — async SQLAlchemy ORM + Alembic migrations.

This package provides:
- ``base``: Declarative base, engine factory, async session factory
- ``models``: SQLAlchemy ORM models mapping to UserProfile v2.0
- ``encryption``: Column-level Fernet encryption for sensitive data
- ``repository``: Async CRUD operations for profiles
"""

from alchymine.db.base import Base, get_async_engine, get_async_session

__all__ = [
    "Base",
    "get_async_engine",
    "get_async_session",
]

"""Async CRUD operations for Alchymine user profiles.

All database access goes through this module so that:
- Encryption/decryption is handled transparently by the ORM layer
- Session lifecycle is managed consistently
- Queries are easy to test (swap in SQLite session)

Functions
~~~~~~~~~
- ``create_profile``  — create a User with intake data and optional layers
- ``get_profile``     — fetch a full User by id (eager-loads all relationships)
- ``update_layer``    — update a specific layer (identity, healing, etc.)
- ``delete_profile``  — hard-delete a User and all dependent rows
- ``list_profiles``   — paginated user list
"""

from __future__ import annotations

from datetime import date, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from alchymine.db.models import (
    CreativeProfile,
    HealingProfile,
    IdentityProfile,
    IntakeData,
    PerspectiveProfile,
    User,
    WealthProfile,
)

# ─── Layer name → ORM class mapping ────────────────────────────────────

_LAYER_MAP: dict[str, type] = {
    "intake": IntakeData,
    "identity": IdentityProfile,
    "healing": HealingProfile,
    "wealth": WealthProfile,
    "creative": CreativeProfile,
    "perspective": PerspectiveProfile,
}


# ─── Helpers ────────────────────────────────────────────────────────────


def _eager_options() -> list:
    """Return selectinload options that eager-load all child relationships."""
    return [
        selectinload(User.intake),
        selectinload(User.identity),
        selectinload(User.healing),
        selectinload(User.wealth),
        selectinload(User.creative),
        selectinload(User.perspective),
    ]


# ─── CREATE ─────────────────────────────────────────────────────────────


async def create_profile(
    session: AsyncSession,
    *,
    full_name: str,
    birth_date: date,
    intention: str,
    birth_time: time | None = None,
    birth_city: str | None = None,
    assessment_responses: dict[str, Any] | None = None,
    family_structure: str | None = None,
) -> User:
    """Create a new user with intake data.

    Returns the newly created ``User`` with its ``intake`` relationship
    populated.
    """
    user = User()
    session.add(user)
    await session.flush()  # generate user.id

    intake = IntakeData(
        user_id=user.id,
        full_name=full_name,
        birth_date=birth_date,
        birth_time=birth_time,
        birth_city=birth_city,
        intention=intention,
        assessment_responses=assessment_responses,
        family_structure=family_structure,
    )
    session.add(intake)
    await session.flush()

    # Reload with relationships
    result = await session.execute(
        select(User).where(User.id == user.id).options(*_eager_options())
    )
    return result.scalar_one()


# ─── READ ───────────────────────────────────────────────────────────────


async def get_profile(session: AsyncSession, user_id: str) -> User | None:
    """Fetch a user profile by id, eager-loading all layers.

    Returns ``None`` if the user does not exist.
    """
    result = await session.execute(
        select(User).where(User.id == user_id).options(*_eager_options())
    )
    return result.scalar_one_or_none()


async def list_profiles(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
) -> list[User]:
    """Return a paginated list of users (most recent first)."""
    result = await session.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(*_eager_options())
    )
    return list(result.scalars().all())


# ─── UPDATE ─────────────────────────────────────────────────────────────


async def update_layer(
    session: AsyncSession,
    user_id: str,
    layer_name: str,
    data: dict[str, Any],
) -> User:
    """Create or update a specific profile layer.

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        The user whose layer to update.
    layer_name:
        One of ``"intake"``, ``"identity"``, ``"healing"``, ``"wealth"``,
        ``"creative"``, ``"perspective"``.
    data:
        Column-name → value mapping.  Unknown keys are silently ignored.

    Returns
    -------
    User
        The refreshed user with all relationships loaded.

    Raises
    ------
    ValueError
        If *layer_name* is not recognised.
    LookupError
        If no user with *user_id* exists.
    """
    if layer_name not in _LAYER_MAP:
        raise ValueError(
            f"Unknown layer {layer_name!r}. "
            f"Valid layers: {', '.join(sorted(_LAYER_MAP))}"
        )

    model_cls = _LAYER_MAP[layer_name]

    # Ensure the user exists
    user_check = await session.execute(select(User).where(User.id == user_id))
    if user_check.scalar_one_or_none() is None:
        raise LookupError(f"No user with id {user_id!r}")

    # Check if the layer row already exists by querying the child table directly.
    # This avoids SQLAlchemy identity-map caching issues with relationships.
    existing_result = await session.execute(
        select(model_cls).where(model_cls.user_id == user_id)  # type: ignore[attr-defined]
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        # Update existing row
        for key, value in data.items():
            if hasattr(existing, key) and key not in ("id", "user_id"):
                setattr(existing, key, value)
    else:
        # Create new layer row
        filtered = {
            k: v for k, v in data.items()
            if hasattr(model_cls, k) and k not in ("id", "user_id")
        }
        row = model_cls(user_id=user_id, **filtered)  # type: ignore[call-arg]
        session.add(row)

    await session.flush()

    # Expire any cached User so relationships are reloaded
    session.expire_all()

    # Reload with fresh relationships
    refreshed = await get_profile(session, user_id)
    assert refreshed is not None
    return refreshed


# ─── DELETE ─────────────────────────────────────────────────────────────


async def delete_profile(session: AsyncSession, user_id: str) -> bool:
    """Delete a user and all dependent rows.

    Returns ``True`` if a user was deleted, ``False`` if not found.
    """
    user = await get_profile(session, user_id)
    if user is None:
        return False
    await session.delete(user)
    await session.flush()
    return True

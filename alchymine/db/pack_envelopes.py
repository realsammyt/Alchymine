"""Purge cached protocol envelopes when a practice pack leaves the mounts.

``ecology_state.last_recommendation`` holds one JSON envelope per user:
the last protocol the ecology recommender emitted, kept so the stable-day
rule can replay it instead of recomputing. The envelope is not a
reference to the pack, it is a copy of part of it. Each selected practice
contributes its ``title``, ``summary``, ``purposes``, ``category`` and
``duration_minutes``, and the three ``slots`` carry its ``daily_prompts``
verbatim.

That copy is why an unmount has to reach this column. Removing a
directory from ``PRACTICE_PACK_DIRS`` is how a licensed pack is revoked
(design section 8.4), and until now revoking a license left the pack's
prose sitting in Postgres, per user, indefinitely.

Serving is already handled: ``ecology.compute_pack_fingerprint`` covers
the mounted pack set, so an unmount invalidates the replay. This module
is about what is still stored, not about what is served.

**What this deletes and what it does not.** It clears one column. It
never touches ``practice_log`` or ``integration_entries``: those rows are
the user's, they denormalize purpose and category at write time so they
outlive their pack on purpose, and the recommender reads history for
unmounted packs to decide what to decline. It leaves the rest of the
``ecology_state`` row alone too, including ``active_pack_ids``, so
remounting a directory restores the user's setup with nothing to
reconfigure.
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db.base import get_async_session_factory
from alchymine.db.models import EcologyState

if TYPE_CHECKING:
    from alchymine.engine.practice import PracticeRegistry

logger = logging.getLogger(__name__)

# SQLite stops at 999 bound parameters per statement, so the clearing
# UPDATE goes out in chunks rather than in one IN clause the size of the
# user base.
_UPDATE_CHUNK = 500


def envelope_pack_ids(envelope: object) -> set[str]:
    """Return every pack id a stored envelope names.

    Deliberately reads the payload shape rather than gating on
    ``envelope_version``: a version this build does not recognise still
    holds attributable pack content, and an envelope written by an older
    deploy is exactly the case where a purge matters most.

    Anything unreadable yields an empty set. Nothing can be attributed to
    a pack in that case, so nothing is purged on its account.
    """
    if not isinstance(envelope, Mapping):
        return set()
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        return set()

    found: set[str] = set()
    _collect_pack_ids(payload.get("items"), found)
    slots = payload.get("slots")
    if isinstance(slots, Mapping):
        for entries in slots.values():
            _collect_pack_ids(entries, found)
    return found


def _collect_pack_ids(entries: object, into: set[str]) -> None:
    """Add the ``pack_id`` of every mapping in *entries* to *into*."""
    if not isinstance(entries, Sequence) or isinstance(entries, str | bytes):
        return
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        pack_id = entry.get("pack_id")
        if isinstance(pack_id, str) and pack_id:
            into.add(pack_id)


async def purge_unmounted_pack_envelopes(
    session: AsyncSession,
    mounted_pack_ids: Collection[str],
    *,
    mount_dirs: Sequence[Path] | None = None,
) -> dict[str, int]:
    """Clear every cached envelope that names a pack outside *mounted_pack_ids*.

    Returns ``{pack_id: rows cleared that named it}``. A row naming two
    unmounted packs counts under both, so the values overlap and do not
    sum to the number of rows touched.

    The scan reads two columns from the rows that hold an envelope at
    all, which is bounded by the number of users who have ever been given
    a protocol. It runs at startup rather than per request, and a mount
    set that has not changed clears nothing and logs nothing.

    *mount_dirs* only appears in the log line. An unmounted pack's own
    directory is gone by definition, so what an operator needs to see is
    which directories are configured now.
    """
    mounted = set(mounted_pack_ids)
    rows = await session.execute(
        select(EcologyState.user_id, EcologyState.last_recommendation).where(
            EcologyState.last_recommendation.is_not(None)
        )
    )

    stale_user_ids: list[str] = []
    purged: dict[str, int] = {}
    for user_id, envelope in rows:
        unmounted = envelope_pack_ids(envelope) - mounted
        if not unmounted:
            continue
        stale_user_ids.append(user_id)
        for pack_id in unmounted:
            purged[pack_id] = purged.get(pack_id, 0) + 1

    if not stale_user_ids:
        return {}

    for start in range(0, len(stale_user_ids), _UPDATE_CHUNK):
        await session.execute(
            update(EcologyState)
            .where(EcologyState.user_id.in_(stale_user_ids[start : start + _UPDATE_CHUNK]))
            .values(last_recommendation=None)
        )
    await session.flush()

    configured = ", ".join(str(path) for path in mount_dirs) if mount_dirs else "none configured"
    for pack_id in sorted(purged):
        logger.warning(
            "PRACTICE PACK PURGE: pack %r is no longer mounted. Cleared its cached "
            "protocol envelope from %d ecology_state row(s). Practice history and "
            "integration entries for the pack are untouched, and so is every other "
            "column on those rows. Configured practice pack directories now: %s.",
            pack_id,
            purged[pack_id],
            configured,
        )
    return purged


async def purge_unmounted_pack_envelopes_at_startup(
    registry: PracticeRegistry,
) -> dict[str, int]:
    """Run the purge against *registry* in its own session, and never raise.

    Called from the API lifespan, right after the registry is installed,
    so a mount that disappeared between two starts takes its cached
    content with it.

    A failure here is logged at ERROR and swallowed. Cleaning a cache is
    not a reason to stop a container from starting, and nothing stale is
    served in the meantime: the recommender's pack fingerprint already
    refuses to replay an envelope computed against a different mount set.
    """
    try:
        # Imported here because alchymine.api.deps imports alchymine.db,
        # so a module-level import would close the cycle. deps owns the
        # pooled singleton engine, which is the one to reuse.
        from alchymine.api.deps import get_db_engine
        from alchymine.config import get_settings

        mount_dirs = get_settings().get_practice_pack_dirs()
        factory = get_async_session_factory(get_db_engine())
        async with factory() as session:
            purged = await purge_unmounted_pack_envelopes(
                session,
                {manifest.pack_id for manifest in registry.list_packs()},
                mount_dirs=mount_dirs,
            )
            await session.commit()
            return purged
    except Exception:
        logger.exception(
            "Could not purge cached practice envelopes at startup. Content from an "
            "unmounted pack may still sit in ecology_state.last_recommendation. It "
            "is not served (the recommender's pack fingerprint refuses to replay "
            "it), and the next start with a reachable database clears it."
        )
        return {}

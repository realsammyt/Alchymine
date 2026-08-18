"""Tests for purging cached protocol envelopes when a pack is unmounted.

``ecology_state.last_recommendation`` is a cache of pack-derived content:
titles, summaries and the three daily prompts, copied out of the mounted
pack when the recommender ran. Removing a directory from
``PRACTICE_PACK_DIRS`` is how a licensed pack is revoked, so the cache has
to go with the mount.

The load-bearing assertions are the two halves of that sentence. The
pack's cached content is gone, and the user's own rows are not: practice
history for an unmounted pack is what makes the recommender's decline
behavior work, and the user's recommender settings have to survive a
remount.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from alchymine.db.models import EcologyState, PracticeLogEntry, User
from alchymine.db.pack_envelopes import (
    envelope_pack_ids,
    purge_unmounted_pack_envelopes,
    purge_unmounted_pack_envelopes_at_startup,
)
from alchymine.engine.practice import PracticeRegistry, build_practice_registry
from tests.engine.practice.conftest import practice_dict, write_pack

DAY = "2026-08-18"
RECOMMENDED_AT = datetime(2026, 8, 18, 6, 30, tzinfo=UTC)


async def _user(session: AsyncSession) -> User:
    user = User()
    session.add(user)
    await session.flush()
    return user


def _envelope(*pack_ids: str, day_key: str = DAY) -> dict[str, Any]:
    """Build an envelope of the shape ``recommend_today`` emits.

    One item per pack id, with the pack-derived fields the real payload
    carries. The prompts matter: they are the pack's prose, verbatim, and
    they are the reason an unmount has to reach this column.
    """
    items = [
        {
            "pack_id": pack_id,
            "slug": f"{pack_id}-alpha",
            "title": f"{pack_id} alpha",
            "summary": "A short line about the practice.",
            "purpose": "self-knowledge",
            "purposes": ["self-knowledge"],
            "category": "reflection",
            "duration_minutes": 5,
            "reason": "You have not tried this one yet.",
            "reason_template": "never_practiced",
        }
        for pack_id in pack_ids
    ]
    slots = {
        slot: [
            {
                "pack_id": pack_id,
                "slug": f"{pack_id}-alpha",
                "prompt": f"{slot} prompt from {pack_id}?",
            }
            for pack_id in pack_ids
        ]
        for slot in ("morning", "day", "evening")
    }
    return {
        "envelope_version": 1,
        "day_key": day_key,
        "pack_fingerprint": "f" * 32,
        "payload": {
            "day_key": day_key,
            "generated_at": RECOMMENDED_AT.isoformat(),
            "protocol_size": len(items),
            "items": items,
            "slots": slots,
        },
    }


async def _state(
    session: AsyncSession, user_id: str, envelope: dict[str, Any] | None, **overrides: Any
) -> EcologyState:
    state = EcologyState(
        user_id=user_id,
        last_recommendation=envelope,
        last_recommended_at=RECOMMENDED_AT,
        **overrides,
    )
    session.add(state)
    await session.flush()
    return state


async def _stored(session: AsyncSession, user_id: str) -> dict[str, Any] | None:
    result = await session.execute(
        select(EcologyState.last_recommendation).where(EcologyState.user_id == user_id)
    )
    return result.scalar_one()


# ─── Reading pack ids out of an envelope ────────────────────────────────


def test_envelope_pack_ids_reads_items_and_slots() -> None:
    assert envelope_pack_ids(_envelope("kept", "retired")) == {"kept", "retired"}


def test_envelope_pack_ids_reads_a_pack_named_only_in_slots() -> None:
    """A shape with no readable items is still attributable through slots."""
    envelope = _envelope("retired")
    del envelope["payload"]["items"]

    assert envelope_pack_ids(envelope) == {"retired"}


@pytest.mark.parametrize("envelope", [None, {}, {"payload": "not-a-mapping"}, []])
def test_envelope_pack_ids_is_empty_for_an_unreadable_envelope(envelope: Any) -> None:
    assert envelope_pack_ids(envelope) == set()


# ─── The purge ──────────────────────────────────────────────────────────


async def test_purge_clears_an_envelope_naming_an_unmounted_pack(session: AsyncSession) -> None:
    user = await _user(session)
    await _state(session, user.id, _envelope("alchymine-foundations", "retired-pack"))

    purged = await purge_unmounted_pack_envelopes(session, {"alchymine-foundations"})

    assert purged == {"retired-pack": 1}
    assert await _stored(session, user.id) is None


async def test_purge_leaves_an_envelope_whose_packs_are_all_mounted(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    envelope = _envelope("alchymine-foundations")
    await _state(session, user.id, envelope)

    purged = await purge_unmounted_pack_envelopes(session, {"alchymine-foundations"})

    assert purged == {}
    assert await _stored(session, user.id) == envelope


async def test_purge_touches_only_the_rows_that_name_the_unmounted_pack(
    session: AsyncSession,
) -> None:
    kept_user = await _user(session)
    purged_user = await _user(session)
    kept_envelope = _envelope("alchymine-foundations")
    await _state(session, kept_user.id, kept_envelope)
    await _state(session, purged_user.id, _envelope("retired-pack"))

    purged = await purge_unmounted_pack_envelopes(session, {"alchymine-foundations"})

    assert purged == {"retired-pack": 1}
    assert await _stored(session, kept_user.id) == kept_envelope
    assert await _stored(session, purged_user.id) is None


async def test_purge_counts_every_row_naming_the_pack(session: AsyncSession) -> None:
    for _ in range(3):
        user = await _user(session)
        await _state(session, user.id, _envelope("retired-pack"))

    assert await purge_unmounted_pack_envelopes(session, {"alchymine-foundations"}) == {
        "retired-pack": 3
    }


async def test_purge_is_a_no_op_when_no_envelope_is_stored(session: AsyncSession) -> None:
    user = await _user(session)
    await _state(session, user.id, None)

    assert await purge_unmounted_pack_envelopes(session, set()) == {}


async def test_purge_with_nothing_mounted_clears_every_envelope(session: AsyncSession) -> None:
    user = await _user(session)
    await _state(session, user.id, _envelope("alchymine-foundations"))

    assert await purge_unmounted_pack_envelopes(session, set()) == {"alchymine-foundations": 1}
    assert await _stored(session, user.id) is None


# ─── The loud line ──────────────────────────────────────────────────────


async def test_purge_logs_a_warning_naming_the_pack_and_the_row_count(
    session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    for _ in range(2):
        user = await _user(session)
        await _state(session, user.id, _envelope("retired-pack"))

    with caplog.at_level(logging.WARNING, logger="alchymine.db.pack_envelopes"):
        await purge_unmounted_pack_envelopes(
            session, {"alchymine-foundations"}, mount_dirs=[Path("/mnt/packs")]
        )

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "retired-pack" in message
    assert "2" in message
    assert "/mnt/packs" in message.replace("\\", "/")


async def test_purge_logs_one_line_per_purged_pack(
    session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    user = await _user(session)
    await _state(session, user.id, _envelope("retired-one", "retired-two"))

    with caplog.at_level(logging.WARNING, logger="alchymine.db.pack_envelopes"):
        await purge_unmounted_pack_envelopes(session, set())

    named = {
        pack
        for pack in ("retired-one", "retired-two")
        if any(pack in record.getMessage() for record in caplog.records)
    }
    assert named == {"retired-one", "retired-two"}


async def test_purge_stays_quiet_when_nothing_is_stale(
    session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    user = await _user(session)
    await _state(session, user.id, _envelope("alchymine-foundations"))

    with caplog.at_level(logging.WARNING, logger="alchymine.db.pack_envelopes"):
        await purge_unmounted_pack_envelopes(session, {"alchymine-foundations"})

    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


# ─── What deliberately survives ─────────────────────────────────────────


async def test_purge_keeps_practice_history_for_the_unmounted_pack(
    session: AsyncSession,
) -> None:
    """History is the user's, not the pack's, and the recommender reads it."""
    user = await _user(session)
    await _state(session, user.id, _envelope("retired-pack"))
    session.add(
        PracticeLogEntry(
            user_id=user.id,
            pack_id="retired-pack",
            practice_slug="retired-pack-alpha",
            primary_purpose="self-knowledge",
            purposes=["self-knowledge"],
            category="reflection",
            occurred_at=RECOMMENDED_AT,
            day_key=DAY,
            reflection="I noticed the same argument starting again.",
        )
    )
    await session.flush()

    await purge_unmounted_pack_envelopes(session, set())

    rows = (
        (await session.execute(select(PracticeLogEntry).where(PracticeLogEntry.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].pack_id == "retired-pack"
    assert rows[0].reflection == "I noticed the same argument starting again."


async def test_purge_keeps_the_users_own_recommender_settings(session: AsyncSession) -> None:
    """Only the cache column is cleared, so a remount needs no reconfiguration."""
    user = await _user(session)
    await _state(
        session,
        user.id,
        _envelope("retired-pack"),
        protocol_size=7,
        active_pack_ids=["retired-pack", "alchymine-foundations"],
        rotation_cursor=3,
    )

    await purge_unmounted_pack_envelopes(session, {"alchymine-foundations"})

    state = (
        await session.execute(select(EcologyState).where(EcologyState.user_id == user.id))
    ).scalar_one()
    assert state.last_recommendation is None
    assert state.protocol_size == 7
    assert state.active_pack_ids == ["retired-pack", "alchymine-foundations"]
    assert state.rotation_cursor == 3
    assert state.last_recommended_at is not None


# ─── Wired to the registry ──────────────────────────────────────────────


async def test_startup_purge_uses_the_mounted_registry(
    session: AsyncSession, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _user(session)
    await _state(session, user.id, _envelope("retired-pack"))
    await session.commit()

    monkeypatch.setattr("alchymine.api.deps.get_db_engine", lambda: engine)
    purged = await purge_unmounted_pack_envelopes_at_startup(PracticeRegistry([]))

    assert purged == {"retired-pack": 1}
    assert await _stored(session, user.id) is None


async def test_startup_purge_survives_an_unreachable_database(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A cleanup task does not get to stop the container from starting."""

    def _boom() -> AsyncEngine:
        raise RuntimeError("no database configured")

    monkeypatch.setattr("alchymine.api.deps.get_db_engine", _boom)

    with caplog.at_level(logging.ERROR, logger="alchymine.db.pack_envelopes"):
        assert await purge_unmounted_pack_envelopes_at_startup(PracticeRegistry([])) == {}

    assert any(record.levelno >= logging.ERROR for record in caplog.records)


async def test_unmounting_then_remounting_a_directory_restores_the_pack(
    session: AsyncSession, tmp_path: Path
) -> None:
    """The full walk: mounted, cached, unmounted, purged, mounted again."""
    container = tmp_path / "packs"
    write_pack(container, "branded-pack", practices=[practice_dict("alpha")])

    mounted = build_practice_registry([container])
    assert {m.pack_id for m in mounted.list_packs()} >= {"branded-pack"}

    user = await _user(session)
    await _state(session, user.id, _envelope("branded-pack"), active_pack_ids=["branded-pack"])

    # Unmount: the directory leaves PRACTICE_PACK_DIRS.
    unmounted = build_practice_registry([])
    purged = await purge_unmounted_pack_envelopes(
        session, {m.pack_id for m in unmounted.list_packs()}
    )
    assert purged == {"branded-pack": 1}
    assert await _stored(session, user.id) is None

    # Remount: the pack loads again, and the user's opt-in still names it.
    remounted = build_practice_registry([container])
    assert remounted.get_pack("branded-pack").title == "Test Pack"
    assert (
        await purge_unmounted_pack_envelopes(session, {m.pack_id for m in remounted.list_packs()})
        == {}
    )
    state = (
        await session.execute(select(EcologyState).where(EcologyState.user_id == user.id))
    ).scalar_one()
    assert state.active_pack_ids == ["branded-pack"]

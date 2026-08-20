"""Tests for the practice-layer models and repository functions.

The load-bearing assertion in this module is the encryption one: what
the user wrote (``reflection``, ``self_check_response``,
``integration_entries.note``) has to be unreadable in the raw column
while round-tripping cleanly through the ORM. Everything the recommender
groups by stays plaintext on purpose (decision 11), and there is a test
for that too, because "encrypt everything" is the change somebody makes
later without realising it moves the recommender to a full table scan.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db import repository
from alchymine.db.models import (
    EcologyState,
    IntegrationEntry,
    JournalEntry,
    PracticeLogEntry,
    User,
)


async def _user(session: AsyncSession) -> User:
    user = User()
    session.add(user)
    await session.flush()
    return user


def _at(day: int, hour: int = 9) -> datetime:
    return datetime(2026, 8, day, hour, 0, tzinfo=UTC)


# ─── Encryption ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reflection_round_trips_through_the_model(session: AsyncSession) -> None:
    user = await _user(session)

    entry = PracticeLogEntry(
        user_id=user.id,
        pack_id="alchymine-foundations",
        practice_slug="name-the-pattern",
        primary_purpose="self-knowledge",
        purposes=["self-knowledge"],
        category="reflection",
        occurred_at=_at(14),
        day_key="2026-08-14",
        reflection="I noticed the same argument starting again.",
        self_check_response="Only what I called it, not what I did.",
    )
    session.add(entry)
    await session.flush()

    result = await session.execute(select(PracticeLogEntry).where(PracticeLogEntry.id == entry.id))
    fetched = result.scalar_one()
    assert fetched.reflection == "I noticed the same argument starting again."
    assert fetched.self_check_response == "Only what I called it, not what I did."


@pytest.mark.asyncio
async def test_reflection_is_ciphertext_in_the_raw_column(session: AsyncSession) -> None:
    """Read past the TypeDecorator: the stored bytes are not the plaintext."""
    user = await _user(session)
    plaintext = "I noticed the same argument starting again."

    entry = PracticeLogEntry(
        user_id=user.id,
        pack_id="alchymine-foundations",
        practice_slug="name-the-pattern",
        primary_purpose="self-knowledge",
        purposes=["self-knowledge"],
        category="reflection",
        occurred_at=_at(14),
        day_key="2026-08-14",
        reflection=plaintext,
        self_check_response="Only what I called it.",
    )
    session.add(entry)
    await session.flush()

    raw = await session.execute(
        text("SELECT reflection, self_check_response FROM practice_log WHERE id = :i"),
        {"i": entry.id},
    )
    raw_reflection, raw_self_check = raw.one()

    assert raw_reflection != plaintext
    assert plaintext not in raw_reflection
    assert len(raw_reflection) > len(plaintext)
    assert raw_self_check != "Only what I called it."


@pytest.mark.asyncio
async def test_recommender_columns_stay_plaintext(session: AsyncSession) -> None:
    """Decision 11. These are grouped in SQL, so they cannot be encrypted."""
    user = await _user(session)

    entry = PracticeLogEntry(
        user_id=user.id,
        pack_id="alchymine-foundations",
        practice_slug="name-the-pattern",
        primary_purpose="self-knowledge",
        purposes=["self-knowledge"],
        category="reflection",
        occurred_at=_at(14),
        day_key="2026-08-14",
    )
    session.add(entry)
    await session.flush()

    raw = await session.execute(
        text("SELECT primary_purpose, day_key, pack_id FROM practice_log WHERE id = :i"),
        {"i": entry.id},
    )
    assert raw.one() == ("self-knowledge", "2026-08-14", "alchymine-foundations")


@pytest.mark.asyncio
async def test_integration_note_is_encrypted(session: AsyncSession) -> None:
    user = await _user(session)
    note = "The reframe held for about an hour."

    entry = IntegrationEntry(user_id=user.id, purpose="reframing", note=note)
    session.add(entry)
    await session.flush()

    raw = await session.execute(
        text("SELECT note FROM integration_entries WHERE id = :i"), {"i": entry.id}
    )
    assert raw.scalar_one() != note

    fetched = await session.get(IntegrationEntry, entry.id)
    assert fetched is not None
    assert fetched.note == note


# ─── Model defaults and links ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_practice_log_defaults(session: AsyncSession) -> None:
    user = await _user(session)

    entry = PracticeLogEntry(
        user_id=user.id,
        pack_id="p",
        practice_slug="s",
        primary_purpose="steadiness",
        purposes=["steadiness"],
        category="somatic",
        occurred_at=_at(14),
        day_key="2026-08-14",
    )
    session.add(entry)
    await session.flush()

    assert len(entry.id) == 36
    assert entry.status == "completed"
    assert entry.protocol_slot is None
    assert entry.reflection is None


@pytest.mark.asyncio
async def test_ecology_state_defaults(session: AsyncSession) -> None:
    user = await _user(session)

    state = EcologyState(user_id=user.id)
    session.add(state)
    await session.flush()

    assert state.protocol_size == 5
    assert state.rotation_cursor == 0
    assert state.active_pack_ids is None


@pytest.mark.asyncio
async def test_integration_entry_links_all_three(session: AsyncSession) -> None:
    user = await _user(session)

    log = PracticeLogEntry(
        user_id=user.id,
        pack_id="p",
        practice_slug="s",
        primary_purpose="reframing",
        purposes=["reframing"],
        category="reflection",
        occurred_at=_at(14),
        day_key="2026-08-14",
    )
    intention = JournalEntry(
        user_id=user.id, title="Intention", content="Try it once", entry_type="intention"
    )
    session.add_all([log, intention])
    await session.flush()

    link = IntegrationEntry(
        user_id=user.id,
        practice_log_id=log.id,
        intention_entry_id=intention.id,
        purpose="reframing",
        capacity_delta=1,
    )
    session.add(link)
    await session.flush()

    assert link.practice_log_id == log.id
    assert link.intention_entry_id == intention.id
    assert link.reflection_entry_id is None


# ─── Repository ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_practice_log_entry_persists_the_row(session: AsyncSession) -> None:
    user = await _user(session)

    entry = await repository.create_practice_log_entry(
        session,
        user_id=user.id,
        pack_id="alchymine-foundations",
        practice_slug="name-the-pattern",
        primary_purpose="self-knowledge",
        purposes=["self-knowledge"],
        category="reflection",
        day_key="2026-08-14",
        occurred_at=_at(14),
        status="completed",
        protocol_slot="morning",
        duration_minutes=10,
        reflection="Noted.",
    )

    assert entry.id
    assert entry.status == "completed"
    assert entry.protocol_slot == "morning"
    assert entry.reflection == "Noted."


@pytest.mark.asyncio
async def test_list_practice_log_entries_is_owner_scoped(session: AsyncSession) -> None:
    """The single most important property of this table's read path."""
    owner = await _user(session)
    other = await _user(session)

    for user_id in (owner.id, other.id):
        await repository.create_practice_log_entry(
            session,
            user_id=user_id,
            pack_id="p",
            practice_slug="s",
            primary_purpose="steadiness",
            purposes=["steadiness"],
            category="attention",
            day_key="2026-08-14",
            occurred_at=_at(14),
        )

    rows, total = await repository.list_practice_log_entries(session, owner.id)
    assert total == 1
    assert [row.user_id for row in rows] == [owner.id]


@pytest.mark.asyncio
async def test_list_practice_log_entries_is_newest_first(session: AsyncSession) -> None:
    user = await _user(session)

    for day in (12, 14, 13):
        await repository.create_practice_log_entry(
            session,
            user_id=user.id,
            pack_id="p",
            practice_slug=f"s-{day}",
            primary_purpose="steadiness",
            purposes=["steadiness"],
            category="attention",
            day_key=f"2026-08-{day}",
            occurred_at=_at(day),
        )

    rows, _ = await repository.list_practice_log_entries(session, user.id)
    assert [row.day_key for row in rows] == ["2026-08-14", "2026-08-13", "2026-08-12"]


@pytest.mark.asyncio
async def test_list_practice_log_entries_filters_by_day_key_range(session: AsyncSession) -> None:
    user = await _user(session)

    for day in (10, 12, 14, 16):
        await repository.create_practice_log_entry(
            session,
            user_id=user.id,
            pack_id="p",
            practice_slug=f"s-{day}",
            primary_purpose="steadiness",
            purposes=["steadiness"],
            category="attention",
            day_key=f"2026-08-{day}",
            occurred_at=_at(day),
        )

    rows, total = await repository.list_practice_log_entries(
        session, user.id, from_day="2026-08-12", to_day="2026-08-14"
    )
    assert total == 2
    assert {row.day_key for row in rows} == {"2026-08-12", "2026-08-14"}


@pytest.mark.asyncio
async def test_list_practice_log_entries_paginates(session: AsyncSession) -> None:
    user = await _user(session)

    for day in range(10, 15):
        await repository.create_practice_log_entry(
            session,
            user_id=user.id,
            pack_id="p",
            practice_slug=f"s-{day}",
            primary_purpose="steadiness",
            purposes=["steadiness"],
            category="attention",
            day_key=f"2026-08-{day}",
            occurred_at=_at(day),
        )

    page_one, total = await repository.list_practice_log_entries(session, user.id, limit=2)
    page_two, _ = await repository.list_practice_log_entries(session, user.id, offset=2, limit=2)

    assert total == 5
    assert len(page_one) == 2
    assert len(page_two) == 2
    assert {row.id for row in page_one}.isdisjoint({row.id for row in page_two})


@pytest.mark.asyncio
async def test_get_practice_log_entry_returns_none_when_absent(session: AsyncSession) -> None:
    user = await _user(session)
    assert await repository.get_practice_log_entry(session, "no-such-id", user.id) is None


@pytest.mark.asyncio
async def test_get_practice_log_entry_hides_another_users_row(session: AsyncSession) -> None:
    owner = await _user(session)
    other = await _user(session)
    row = await repository.create_practice_log_entry(
        session,
        user_id=owner.id,
        pack_id="alchymine-foundations",
        practice_slug="name-the-pattern",
        primary_purpose="self-knowledge",
        purposes=["self-knowledge"],
        category="reflection",
        day_key="2026-08-14",
        occurred_at=_at(14),
    )

    assert await repository.get_practice_log_entry(session, row.id, owner.id) is not None
    # Another user's id yields None, indistinguishable from a missing row.
    assert await repository.get_practice_log_entry(session, row.id, other.id) is None


# ─── Ecology state ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_ecology_state_creates_with_defaults(
    session: AsyncSession,
) -> None:
    user = await _user(session)

    state = await repository.get_or_create_ecology_state(session, user.id)

    assert state.user_id == user.id
    assert state.protocol_size == 5
    assert state.rotation_cursor == 0
    assert state.active_pack_ids is None
    assert state.last_recommendation is None


@pytest.mark.asyncio
async def test_get_or_create_ecology_state_preserves_an_existing_row(
    session: AsyncSession,
) -> None:
    """The "create" half must never clobber a row that already exists.

    A second call that re-wrote the defaults would silently reset a
    user's protocol size and their rotation position on every request,
    which is the kind of bug that looks like the recommender being
    random rather than like a repository bug.
    """
    user = await _user(session)
    session.add(EcologyState(user_id=user.id, protocol_size=7, rotation_cursor=3))
    await session.flush()

    state = await repository.get_or_create_ecology_state(session, user.id)

    assert state.protocol_size == 7
    assert state.rotation_cursor == 3


@pytest.mark.asyncio
async def test_update_ecology_recommendation_writes_all_three_fields(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    envelope = {"envelope_version": 1, "day_key": "2026-08-14", "payload": {"items": []}}

    state = await repository.update_ecology_recommendation(
        session,
        user.id,
        rotation_cursor=2,
        last_recommendation=envelope,
        last_recommended_at=_at(14),
    )

    assert state.rotation_cursor == 2
    assert state.last_recommendation == envelope
    assert state.last_recommended_at is not None
    # It creates the row when there is none, so a first-ever request does
    # not need a separate write.
    assert state.protocol_size == 5


async def _state_with_a_stored_protocol(session: AsyncSession) -> str:
    """Give a fresh user a stored protocol, and return their id."""
    user = await _user(session)
    await repository.update_ecology_recommendation(
        session,
        user.id,
        rotation_cursor=1,
        last_recommendation={"envelope_version": 1, "day_key": "2026-08-14", "payload": {}},
        last_recommended_at=_at(14),
    )
    return user.id


@pytest.mark.asyncio
async def test_update_ecology_settings_creates_the_row_and_writes_both_fields(
    session: AsyncSession,
) -> None:
    user = await _user(session)

    state = await repository.update_ecology_settings(
        session, user.id, protocol_size=3, active_pack_ids=["alchymine-foundations"]
    )

    assert state.protocol_size == 3
    assert state.active_pack_ids == ["alchymine-foundations"]


@pytest.mark.asyncio
async def test_update_ecology_settings_leaves_an_omitted_field_alone(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    await repository.update_ecology_settings(
        session, user.id, protocol_size=7, active_pack_ids=["alchymine-foundations"]
    )

    state = await repository.update_ecology_settings(session, user.id, protocol_size=4)

    assert state.protocol_size == 4
    assert state.active_pack_ids == ["alchymine-foundations"]


@pytest.mark.asyncio
async def test_update_ecology_settings_can_clear_the_pack_subset(
    session: AsyncSession,
) -> None:
    """``None`` is a value here, not an absence: it means every mounted pack."""
    user = await _user(session)
    await repository.update_ecology_settings(
        session, user.id, active_pack_ids=["alchymine-foundations"]
    )

    state = await repository.update_ecology_settings(session, user.id, active_pack_ids=None)

    assert state.active_pack_ids is None


@pytest.mark.asyncio
async def test_a_size_change_clears_the_stored_protocol(session: AsyncSession) -> None:
    """``protocol_size`` is not in the pack fingerprint, so nobody else will."""
    user_id = await _state_with_a_stored_protocol(session)

    state = await repository.update_ecology_settings(session, user_id, protocol_size=3)

    assert state.last_recommendation is None
    assert state.last_recommended_at is None


@pytest.mark.asyncio
async def test_a_pack_subset_change_clears_the_stored_protocol(session: AsyncSession) -> None:
    user_id = await _state_with_a_stored_protocol(session)

    state = await repository.update_ecology_settings(
        session, user_id, active_pack_ids=["alchymine-foundations"]
    )

    assert state.last_recommendation is None


@pytest.mark.asyncio
async def test_a_settings_write_that_changes_nothing_keeps_the_stored_protocol(
    session: AsyncSession,
) -> None:
    """Saving the settings page unchanged must not reshuffle today's protocol."""
    user_id = await _state_with_a_stored_protocol(session)
    stored = await repository.get_or_create_ecology_state(session, user_id)
    envelope = stored.last_recommendation

    state = await repository.update_ecology_settings(
        session, user_id, protocol_size=5, active_pack_ids=None
    )

    assert state.last_recommendation == envelope
    assert state.last_recommended_at is not None


@pytest.mark.asyncio
async def test_update_ecology_settings_keeps_the_rotation_cursor(
    session: AsyncSession,
) -> None:
    """Clearing the protocol is not a reason to restart the purpose rotation."""
    user_id = await _state_with_a_stored_protocol(session)

    state = await repository.update_ecology_settings(session, user_id, protocol_size=6)

    assert state.rotation_cursor == 1

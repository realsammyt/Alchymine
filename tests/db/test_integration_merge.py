"""Merge semantics for one completion's integration entry.

Three properties live here, and each of them is a way the user's own
writing could be lost:

- **The row is read under a lock on the merge path.** Two saves that
  both start after the row exists would otherwise each read the same
  starting note, merge independently, and let the later flush drop the
  earlier one. The lock is a real one on PostgreSQL and compiles away on
  SQLite, so what these tests can prove is split: the clause is asserted
  against the PostgreSQL dialect, and the serialized order the lock
  produces is asserted against a live database.
- **A note that would push the entry past its total cap is refused, not
  truncated.** Cutting a sentence in half and storing the front of it is
  worse than saying the save did not land.
- **Dedup works on the save, not on the paragraph.** A replayed save is
  one note; a new note that happens to repeat something written earlier
  is still the user's writing and belongs in the entry.

Note text in these fixtures is deliberately plain and fictional. It is
also never logged: the refusal carries lengths, never content.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from alchymine.db import repository
from alchymine.db.base import Base
from alchymine.db.models import IntegrationEntry, PracticeLogEntry, User
from alchymine.db.repository import (
    NOTE_SEPARATOR,
    IntegrationNoteFull,
    merge_notes,
)

PURPOSE = "steadiness"


def _joined(*paragraphs: str) -> str:
    return NOTE_SEPARATOR.join(paragraphs)


# ─── Dedup on the save, not the paragraph ───────────────────────────────


class TestMergeDedup:
    """What counts as "the same note arriving twice"."""

    def test_the_first_note_is_stored_trimmed(self) -> None:
        assert merge_notes(None, "  a quiet one  ") == "a quiet one"

    def test_an_empty_incoming_note_leaves_the_stored_note_alone(self) -> None:
        assert merge_notes("already written", None) == "already written"
        assert merge_notes("already written", "   ") == "already written"

    def test_a_note_identical_to_the_whole_stored_note_is_stored_once(self) -> None:
        assert merge_notes("only this", "only this") == "only this"

    def test_a_replayed_note_is_stored_once(self) -> None:
        stored = _joined("first thought", "second thought")
        assert merge_notes(stored, "second thought") == stored

    def test_a_replayed_multi_paragraph_note_is_stored_once(self) -> None:
        """A save carrying two paragraphs, retried after a timeout.

        The whole save is the unit. Splitting the stored note on blank
        lines never produced this string as an element, so the replay
        used to land a second copy of both paragraphs.
        """
        arriving = _joined("what I set out to do", "what actually happened")
        stored = _joined("an earlier line", arriving)
        assert merge_notes(stored, arriving) == stored

    def test_an_inner_paragraph_repeated_is_appended_not_dropped(self) -> None:
        """The user writing the same sentence again is not a replay.

        Only the tail of the stored note can be a replay of the save
        that just arrived. A match further in is the user repeating
        themselves, which is theirs to do.
        """
        stored = _joined("held steady", "drifted off", "came back")
        assert merge_notes(stored, "drifted off") == _joined(
            "held steady", "drifted off", "came back", "drifted off"
        )

    def test_a_new_multi_paragraph_note_is_appended(self) -> None:
        stored = _joined("first thought", "second thought")
        arriving = _joined("third thought", "fourth thought")
        assert merge_notes(stored, arriving) == _joined(stored, arriving)

    def test_a_paragraph_that_only_ends_the_stored_text_is_appended(self) -> None:
        """Suffix, yes, but not a whole paragraph. Not a replay."""
        stored = "one\n\ntwothree"
        assert merge_notes(stored, "three") == _joined(stored, "three")


# ─── The total cap ──────────────────────────────────────────────────────


class TestNoteCap:
    """Refusal, never truncation. The text belongs to whoever wrote it."""

    def test_no_cap_means_no_refusal(self) -> None:
        assert merge_notes("x" * 100, "y" * 100) is not None

    def test_a_merge_that_lands_exactly_on_the_cap_is_kept(self) -> None:
        merged = merge_notes("abc", "de", total_char_cap=7)
        assert merged == _joined("abc", "de")
        assert len(merged or "") == 7

    def test_a_merge_that_would_pass_the_cap_is_refused(self) -> None:
        with pytest.raises(IntegrationNoteFull):
            merge_notes("abc", "def", total_char_cap=7)

    def test_a_first_note_longer_than_the_cap_is_refused(self) -> None:
        with pytest.raises(IntegrationNoteFull):
            merge_notes(None, "x" * 12, total_char_cap=8)

    def test_a_full_note_with_nothing_new_is_not_refused(self) -> None:
        """A save that carries no note cannot be over any cap."""
        stored = "x" * 40
        assert merge_notes(stored, None, total_char_cap=8) == stored
        assert merge_notes(stored, "  ", total_char_cap=8) == stored

    def test_a_full_note_replayed_is_not_refused(self) -> None:
        stored = _joined("x" * 30, "the tail")
        assert merge_notes(stored, "the tail", total_char_cap=8) == stored

    def test_the_refusal_does_not_carry_the_note_text(self) -> None:
        """The message travels into logs and into a 422 body."""
        secret_ish = "the thing I have not told anyone"
        with pytest.raises(IntegrationNoteFull) as caught:
            merge_notes("x" * 40, secret_ish, total_char_cap=8)

        assert secret_ish not in str(caught.value)
        assert secret_ish not in repr(caught.value)


# ─── The row lock on the merge path ─────────────────────────────────────


def _merge_path_select() -> Any:
    return repository.integration_entry_select("user-1", "log-1", for_update=True)


class TestMergePathRowLock:
    def test_the_merge_path_select_locks_the_row_on_postgresql(self) -> None:
        """Where the race is real, the read takes the row."""
        compiled = str(_merge_path_select().compile(dialect=postgresql.dialect()))
        assert "FOR UPDATE" in compiled

    def test_the_same_select_carries_no_lock_clause_on_sqlite(self) -> None:
        """Honest about the test database: SQLite compiles it away.

        Nothing is broken by that (one writer at a time is SQLite's
        whole concurrency model), but it does mean no SQLite test can
        prove the lock. That is what the dialect assertion above is for.
        """
        compiled = str(_merge_path_select().compile(dialect=sqlite.dialect()))
        assert "FOR UPDATE" not in compiled

    def test_the_unlocked_select_is_still_available_for_plain_reads(self) -> None:
        compiled = str(
            repository.integration_entry_select("user-1", "log-1").compile(
                dialect=postgresql.dialect()
            )
        )
        assert "FOR UPDATE" not in compiled

    @pytest.mark.asyncio
    async def test_every_read_inside_the_upsert_asks_for_the_lock(
        self, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both reads, not just the one on the found-existing path.

        The re-select after a lost insert race lands on the same merge,
        so it needs the same lock.
        """
        user = User()
        session.add(user)
        await session.flush()
        log = await _log_row(session, user.id)

        asked: list[bool] = []
        original = repository._get_integration_entry

        async def _spy(*args: Any, for_update: bool = False, **kwargs: Any) -> Any:
            asked.append(for_update)
            return await original(*args, for_update=for_update, **kwargs)

        monkeypatch.setattr(repository, "_get_integration_entry", _spy)

        await repository.upsert_integration_entry(
            session, user_id=user.id, practice_log_id=log.id, purpose=PURPOSE, note="first"
        )
        await repository.upsert_integration_entry(
            session, user_id=user.id, practice_log_id=log.id, purpose=PURPOSE, note="second"
        )

        assert asked, "the upsert read nothing, which cannot be right"
        assert all(asked)


# ─── Two writers, one entry ─────────────────────────────────────────────


async def _log_row(session: AsyncSession, user_id: str) -> PracticeLogEntry:
    log = PracticeLogEntry(
        user_id=user_id,
        pack_id="alchymine-foundations",
        practice_slug="find-the-floor",
        primary_purpose=PURPOSE,
        purposes=[PURPOSE],
        category="grounding",
        occurred_at=datetime(2026, 8, 14, 9, 0, tzinfo=UTC),
        day_key="2026-08-14",
    )
    session.add(log)
    await session.flush()
    return log


@pytest_asyncio.fixture
async def writers(tmp_path: Any) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """A file-backed database, so two sessions are two connections.

    The shared in-memory engine the rest of this package uses puts every
    session on one connection, which cannot show two writers at all.
    """
    url = f"sqlite+aiosqlite:///{(tmp_path / 'writers.db').as_posix()}"
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    finally:
        await engine.dispose()


class TestTwoWriters:
    @pytest.mark.asyncio
    async def test_two_interleaved_saves_keep_both_writers_paragraphs(
        self, writers: async_sessionmaker[AsyncSession]
    ) -> None:
        """The order the lock enforces, end to end.

        Writer B reads after writer A commits, which is exactly what
        ``FOR UPDATE`` buys on PostgreSQL: B blocks on A's lock rather
        than reading the pre-A note and flushing over it. Both
        paragraphs survive.

        On SQLite this is a serialization the test arranges rather than
        one the database enforces. A true concurrent interleave needs a
        PostgreSQL service in CI, which is issue #271.
        """
        async with writers() as setup:
            user = User()
            setup.add(user)
            await setup.flush()
            log = await _log_row(setup, user.id)
            user_id, log_id = user.id, log.id
            await repository.upsert_integration_entry(
                setup,
                user_id=user_id,
                practice_log_id=log_id,
                purpose=PURPOSE,
                note="what I set out to do",
            )
            await setup.commit()

        async with writers() as writer_a:
            await repository.upsert_integration_entry(
                writer_a,
                user_id=user_id,
                practice_log_id=log_id,
                purpose=PURPOSE,
                note="the self-check answer",
            )
            await writer_a.commit()

        async with writers() as writer_b:
            await repository.upsert_integration_entry(
                writer_b,
                user_id=user_id,
                practice_log_id=log_id,
                purpose=PURPOSE,
                capacity_delta=1,
                note="what actually happened",
            )
            await writer_b.commit()

        async with writers() as reader:
            rows = (
                (
                    await reader.execute(
                        select(IntegrationEntry).where(IntegrationEntry.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            note = rows[0].note or ""
            assert "what I set out to do" in note
            assert "the self-check answer" in note
            assert "what actually happened" in note
            assert rows[0].capacity_delta == 1

"""Tests for the deterministic practice context block.

The block is assembled from the practice log and the stored protocol and
handed to the coach on the ``practice`` scope. It is the only place
practice data reaches an LLM, so the properties that matter are mostly
about what it does *not* contain:

- ``reflection`` and ``self_check_response`` are encrypted columns and
  are never selected, so nothing the user wrote can appear in the block
  however long their history is.
- Nothing is emitted at all for a user with no practice history, so a
  first-time question is not padded with an empty scaffold.
- A skipped row is not a completed one. Telling the coach a user
  practiced something they declined would make every following sentence
  wrong.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.agents.growth.practice_context import build_practice_context
from alchymine.db import repository
from alchymine.db.base import Base
from alchymine.db.models import EcologyState, User

BUNDLED_PACK_ID = "alchymine-foundations"
USER_ID = "user-practice-context"


def _day(offset: int) -> str:
    """Return the UTC day *offset* days from today as ``YYYY-MM-DD``."""
    return (datetime.now(UTC).date() + timedelta(days=offset)).isoformat()


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid Fernet key, so the encrypted columns can be written."""
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        db.add(User(id=USER_ID))
        await db.flush()
        yield db
    await engine.dispose()


async def _log(
    session: AsyncSession,
    *,
    slug: str,
    purpose: str,
    day_offset: int = 0,
    status: str = "completed",
    reflection: str | None = None,
    self_check_response: str | None = None,
) -> None:
    await repository.create_practice_log_entry(
        session,
        user_id=USER_ID,
        pack_id=BUNDLED_PACK_ID,
        practice_slug=slug,
        primary_purpose=purpose,
        purposes=[purpose],
        category="somatic",
        status=status,
        occurred_at=datetime.now(UTC) + timedelta(days=day_offset),
        day_key=_day(day_offset),
        reflection=reflection,
        self_check_response=self_check_response,
    )
    await session.flush()


# ─── Nothing to say ─────────────────────────────────────────────────────


class TestEmpty:
    async def test_returns_none_without_any_practice_history(self, session: AsyncSession) -> None:
        assert await build_practice_context(session, USER_ID) is None

    async def test_returns_none_for_a_user_whose_only_rows_are_stale(
        self, session: AsyncSession
    ) -> None:
        await _log(session, slug="find-the-floor", purpose="steadiness", day_offset=-30)

        assert await build_practice_context(session, USER_ID) is None


# ─── What it says ───────────────────────────────────────────────────────


class TestContent:
    async def test_names_completed_practice_titles(self, session: AsyncSession) -> None:
        await _log(session, slug="find-the-floor", purpose="steadiness", day_offset=-1)

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "Find the Floor" in block

    async def test_counts_completions_per_purpose(self, session: AsyncSession) -> None:
        await _log(session, slug="find-the-floor", purpose="steadiness", day_offset=-1)
        await _log(session, slug="steady-return", purpose="steadiness", day_offset=-2)
        await _log(session, slug="name-the-pattern", purpose="self-knowledge", day_offset=-3)

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "steadiness 2" in block
        assert "self-knowledge 1" in block

    async def test_reports_days_practiced_not_a_streak(self, session: AsyncSession) -> None:
        await _log(session, slug="find-the-floor", purpose="steadiness", day_offset=-1)
        await _log(session, slug="steady-return", purpose="steadiness", day_offset=-1)
        await _log(session, slug="name-the-pattern", purpose="self-knowledge", day_offset=-4)

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "2 of the last 7 days" in block
        assert "streak" not in block.lower()

    async def test_skipped_rows_are_not_reported_as_completed(
        self, session: AsyncSession
    ) -> None:
        await _log(
            session,
            slug="find-the-floor",
            purpose="steadiness",
            day_offset=-1,
            status="skipped",
        )

        block = await build_practice_context(session, USER_ID)

        assert block is None or "Find the Floor" not in block

    async def test_ignores_rows_older_than_the_window(self, session: AsyncSession) -> None:
        await _log(session, slug="find-the-floor", purpose="steadiness", day_offset=-1)
        await _log(session, slug="name-the-pattern", purpose="self-knowledge", day_offset=-20)

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "Name the Pattern" not in block

    async def test_falls_back_to_the_slug_when_the_pack_is_not_mounted(
        self, session: AsyncSession
    ) -> None:
        """An unmounted pack must not take the whole block down with it."""
        await repository.create_practice_log_entry(
            session,
            user_id=USER_ID,
            pack_id="a-pack-that-was-unmounted",
            practice_slug="long-gone",
            primary_purpose="steadiness",
            purposes=["steadiness"],
            category="somatic",
            status="completed",
            occurred_at=datetime.now(UTC),
            day_key=_day(0),
        )
        await session.flush()

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "long-gone" in block


# ─── The stored protocol ────────────────────────────────────────────────


class TestStoredProtocol:
    async def _store(self, session: AsyncSession, *, day_key: str) -> None:
        session.add(
            EcologyState(
                user_id=USER_ID,
                last_recommendation={
                    "envelope_version": 1,
                    "day_key": day_key,
                    "pack_fingerprint": "abc",
                    "payload": {
                        "day_key": day_key,
                        "items": [
                            {"title": "Find the Floor", "purpose": "steadiness"},
                            {"title": "Name the Pattern", "purpose": "self-knowledge"},
                        ],
                    },
                },
            )
        )
        await session.flush()

    async def test_includes_todays_protocol(self, session: AsyncSession) -> None:
        await self._store(session, day_key=_day(0))

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "Find the Floor" in block
        assert "Name the Pattern" in block

    async def test_omits_a_stale_protocol(self, session: AsyncSession) -> None:
        await self._store(session, day_key=_day(-6))

        assert await build_practice_context(session, USER_ID) is None

    async def test_omits_a_protocol_entry_whose_pack_is_no_longer_mounted(
        self, session: AsyncSession
    ) -> None:
        """The second line of defense behind the startup envelope purge.

        The purge clears these rows at boot. If it could not run, the
        content still must not reach the coach: unmounting a pack is how
        a license is revoked.
        """
        day_key = _day(0)
        session.add(
            EcologyState(
                user_id=USER_ID,
                last_recommendation={
                    "envelope_version": 1,
                    "day_key": day_key,
                    "pack_fingerprint": "abc",
                    "payload": {
                        "day_key": day_key,
                        "items": [
                            {"pack_id": BUNDLED_PACK_ID, "title": "Find the Floor"},
                            {
                                "pack_id": "a-pack-that-was-unmounted",
                                "title": "Branded Practice Title",
                            },
                        ],
                    },
                },
            )
        )
        await session.flush()

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "Find the Floor" in block
        assert "Branded Practice Title" not in block


# ─── The data rail ──────────────────────────────────────────────────────


class TestEncryptedColumnsNeverAppear:
    """The point of the whole module. A reflection is the most private
    thing the practice layer stores, and it must not reach an LLM because
    the user asked the coach an unrelated question."""

    async def test_reflection_text_is_absent_from_the_block(self, session: AsyncSession) -> None:
        await _log(
            session,
            slug="find-the-floor",
            purpose="steadiness",
            day_offset=-1,
            reflection="I cried for twenty minutes about my brother",
        )

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "cried" not in block
        assert "brother" not in block

    async def test_self_check_text_is_absent_from_the_block(self, session: AsyncSession) -> None:
        await _log(
            session,
            slug="find-the-floor",
            purpose="steadiness",
            day_offset=-1,
            self_check_response="I only did it to avoid calling my mother",
        )

        block = await build_practice_context(session, USER_ID)

        assert block is not None
        assert "avoid calling" not in block
        assert "mother" not in block

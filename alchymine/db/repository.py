"""Async CRUD operations for Alchymine user profiles and reports.

All database access goes through this module so that:
- Encryption/decryption is handled transparently by the ORM layer
- Session lifecycle is managed consistently
- Queries are easy to test (swap in SQLite session)

Functions — Profiles
~~~~~~~~~~~~~~~~~~~~
- ``create_or_update_profile`` — write intake for a user, creating it when absent
- ``create_profile``  — create a User with intake data and optional layers
- ``get_profile``     — fetch a full User by id (eager-loads all relationships)
- ``update_layer``    — update a specific layer (identity, healing, etc.)
- ``delete_profile``  — hard-delete a User and all dependent rows
- ``list_profiles``   — paginated user list

Functions — Reports
~~~~~~~~~~~~~~~~~~~
- ``create_report``          — insert a new Report row
- ``get_report``             — fetch a Report by id
- ``list_reports_by_user``   — paginated reports for a given user
- ``update_report_status``   — change status (and optionally error)
- ``update_report_content``  — set result / html_content on completion

Functions — Journal Entries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- ``create_journal_entry``   — insert a new JournalEntry row
- ``get_journal_entry``      — fetch a JournalEntry by id
- ``list_journal_entries``   — paginated entries for a user with optional filters
- ``update_journal_entry``   — update fields on an existing entry
- ``delete_journal_entry``   — hard-delete an entry
- ``get_journal_stats``      — summary statistics for a user's journal
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from alchymine.db.models import (
    ChatMessage,
    CreativeProfile,
    EcologyState,
    FeedbackEntry,
    GeneratedImage,
    HealingProfile,
    IdentityProfile,
    IntakeData,
    IntegrationEntry,
    JournalEntry,
    MilestoneDBRecord,
    OutcomeMetricRecord,
    PerspectiveProfile,
    PracticeLogEntry,
    Report,
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


async def _ensure_user_row(session: AsyncSession, user_id: str | None) -> tuple[User, bool]:
    """Return the users row for *user_id*, inserting it when absent.

    The second element is ``True`` when this call created the row.  A
    registered account always has one already — ``/auth/register`` writes
    it and the JWT ``sub`` IS its primary key — so for those callers this
    is a plain read.
    """
    if user_id is None:
        user = User()
        session.add(user)
        await session.flush()  # generate user.id
        return user, True

    found = await session.execute(select(User).where(User.id == user_id))
    existing = found.scalar_one_or_none()
    if existing is not None:
        return existing, False

    # INSERT ... ON CONFLICT DO NOTHING rather than a bare INSERT: two
    # concurrent first-time writes would otherwise race between the SELECT
    # above and this statement, and the loser would hit the same users_pkey
    # violation this function exists to remove (#314).
    dialect_name = session.bind.dialect.name  # type: ignore[union-attr]
    insert_stmt: Any
    if dialect_name == "postgresql":
        insert_stmt = (
            pg_insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])
        )
    else:
        insert_stmt = (
            sqlite_insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=["id"])
        )
    await session.execute(insert_stmt)
    await session.flush()

    inserted = await session.execute(select(User).where(User.id == user_id))
    return inserted.scalar_one(), True


async def create_or_update_profile(
    session: AsyncSession,
    *,
    full_name: str,
    birth_date: date,
    intention: str,
    birth_time: time | None = None,
    birth_city: str | None = None,
    birth_timezone: str | None = None,
    assessment_responses: dict[str, Any] | None = None,
    family_structure: str | None = None,
    intentions: list[str] | None = None,
    user_id: str | None = None,
) -> tuple[User, bool]:
    """Write the intake profile for *user_id*, creating the user if needed.

    Returns ``(user, created)`` where *user* has all layer relationships
    loaded and *created* says whether the users row was inserted by this
    call.  When ``user_id`` is provided it is used as the primary key
    (e.g. to tie the profile to the authenticated user's JWT sub).

    The arguments are the whole intake payload, so an existing intake row
    is overwritten field for field: anything not supplied is set back to
    NULL rather than merged.  Partial edits belong on ``update_layer``.

    Only the intake row is touched.  Account columns on ``users`` (email,
    password_hash, plan, invite_code_used, created_at) and the other
    profile layers are left exactly as they were.
    """
    user, created = await _ensure_user_row(session, user_id)
    resolved_user_id = user.id

    intake_values: dict[str, Any] = {
        "full_name": full_name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_city": birth_city,
        "birth_timezone": birth_timezone,
        # Primary intention comes from the list when one was provided
        "intention": intentions[0] if intentions else intention,
        "intentions": intentions,
        "assessment_responses": assessment_responses,
        "family_structure": family_structure,
    }

    found_intake = await session.execute(
        select(IntakeData).where(IntakeData.user_id == resolved_user_id)
    )
    intake = found_intake.scalar_one_or_none()
    if intake is None:
        session.add(IntakeData(user_id=resolved_user_id, **intake_values))
    else:
        # Assign through the ORM so the EncryptedString columns keep going
        # through their type decorator.
        for key, value in intake_values.items():
            setattr(intake, key, value)
    await session.flush()

    # Expire the cached User so the reload below sees the fresh layers.
    session.expire(user)
    refreshed = await get_profile(session, resolved_user_id)
    if refreshed is None:  # pragma: no cover — the row was just flushed
        raise ValueError(f"Profile not found after write for user_id={resolved_user_id!r}")
    return refreshed, created


async def create_profile(
    session: AsyncSession,
    *,
    full_name: str,
    birth_date: date,
    intention: str,
    birth_time: time | None = None,
    birth_city: str | None = None,
    birth_timezone: str | None = None,
    assessment_responses: dict[str, Any] | None = None,
    family_structure: str | None = None,
    intentions: list[str] | None = None,
    user_id: str | None = None,
) -> User:
    """Create a user with intake data, or overwrite the intake if it exists.

    Thin wrapper over :func:`create_or_update_profile` for callers that do
    not care whether the users row was new.
    """
    user, _created = await create_or_update_profile(
        session,
        full_name=full_name,
        birth_date=birth_date,
        intention=intention,
        birth_time=birth_time,
        birth_city=birth_city,
        birth_timezone=birth_timezone,
        assessment_responses=assessment_responses,
        family_structure=family_structure,
        intentions=intentions,
        user_id=user_id,
    )
    return user


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
            f"Unknown layer {layer_name!r}. Valid layers: {', '.join(sorted(_LAYER_MAP))}"
        )

    model_cls = _LAYER_MAP[layer_name]

    # Ensure the user exists
    user_check = await session.execute(select(User).where(User.id == user_id))
    user_obj = user_check.scalar_one_or_none()
    if user_obj is None:
        raise LookupError(f"No user with id {user_id!r}")

    # Filter to valid model columns
    filtered = {
        k: v for k, v in data.items() if hasattr(model_cls, k) and k not in ("id", "user_id")
    }

    # Check if the layer row already exists.
    existing_result: Any = await session.execute(
        select(model_cls).where(model_cls.user_id == user_id)  # type: ignore[attr-defined]
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        # Row exists — plain UPDATE (safe, handles partial columns with NOT NULLs)
        for key, value in filtered.items():
            setattr(existing, key, value)
    else:
        # Row doesn't exist — use INSERT ... ON CONFLICT DO UPDATE (upsert)
        # to handle the race where another request creates the row between
        # our SELECT and INSERT.
        dialect_name = session.bind.dialect.name  # type: ignore[union-attr]
        upsert_stmt: Any
        if dialect_name == "postgresql":
            upsert_stmt = pg_insert(model_cls).values(user_id=user_id, **filtered)
            if filtered:
                upsert_stmt = upsert_stmt.on_conflict_do_update(
                    index_elements=["user_id"], set_=filtered
                )
            else:
                upsert_stmt = upsert_stmt.on_conflict_do_nothing(index_elements=["user_id"])
        else:
            upsert_stmt = sqlite_insert(model_cls).values(user_id=user_id, **filtered)
            if filtered:
                upsert_stmt = upsert_stmt.on_conflict_do_update(
                    index_elements=["user_id"], set_=filtered
                )
            else:
                upsert_stmt = upsert_stmt.on_conflict_do_nothing(index_elements=["user_id"])
        await session.execute(upsert_stmt)

    await session.flush()

    # Expire cached User so relationships are reloaded
    session.expire(user_obj)
    refreshed = await get_profile(session, user_id)
    if refreshed is None:
        raise ValueError(f"Profile not found after update_layer for user_id={user_id}")
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


# ═══════════════════════════════════════════════════════════════════════
# Report CRUD
# ═══════════════════════════════════════════════════════════════════════


async def create_report(
    session: AsyncSession,
    *,
    report_id: str,
    status: str = "pending",
    user_input: str | None = None,
    user_profile: dict[str, Any] | None = None,
    user_id: str | None = None,
    created_by_sub: str | None = None,
    report_type: str = "full",
) -> Report:
    """Insert a new report row.

    Parameters
    ----------
    session:
        Active async session.
    report_id:
        Pre-generated UUID string for the report.
    status:
        Initial status (default ``"pending"``).
    user_input:
        Free-text user request.
    user_profile:
        Optional user profile dict forwarded to orchestrator.
    user_id:
        Optional FK to the ``users`` table.
    created_by_sub:
        JWT subject of the creator — used for ownership checks on orphan
        reports (rows where ``user_id`` is ``NULL``).
    report_type:
        Report type identifier (default ``"full"``).

    Returns
    -------
    Report
        The newly created report row.
    """
    report = Report(
        id=report_id,
        status=status,
        user_input=user_input,
        user_profile=user_profile,
        user_id=user_id,
        created_by_sub=created_by_sub,
        report_type=report_type,
    )
    session.add(report)
    await session.flush()
    return report


async def get_report(session: AsyncSession, report_id: str) -> Report | None:
    """Fetch a single report by id.

    Returns ``None`` if the report does not exist.
    """
    result = await session.execute(select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()


def _report_ownership_filter(user_id: str) -> Any:
    """SQL criterion matching reports owned by *user_id*.

    A report is owned when ``user_id`` matches directly, or — for orphan
    rows created before the user row existed (``user_id IS NULL``) — when
    ``created_by_sub`` matches the JWT subject.
    """
    return or_(
        Report.user_id == user_id,
        and_(Report.user_id.is_(None), Report.created_by_sub == user_id),
    )


async def list_reports_by_user(
    session: AsyncSession,
    user_id: str,
    *,
    skip: int = 0,
    limit: int = 20,
) -> list[Report]:
    """Return a paginated list of reports owned by *user_id* (most recent first).

    Includes orphan reports (``user_id IS NULL``) whose ``created_by_sub``
    matches *user_id*.
    """
    result = await session.execute(
        select(Report)
        .where(_report_ownership_filter(user_id))
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_reports_by_user(session: AsyncSession, user_id: str) -> int:
    """Return total number of reports owned by *user_id*."""
    result = await session.execute(
        select(func.count()).select_from(Report).where(_report_ownership_filter(user_id))
    )
    return result.scalar_one()


async def update_report_status(
    session: AsyncSession,
    report_id: str,
    status: str,
    *,
    error: str | None = None,
) -> Report | None:
    """Update the status of a report (and optionally set an error message).

    Returns the updated ``Report``, or ``None`` if not found.
    """
    report = await get_report(session, report_id)
    if report is None:
        return None
    report.status = status
    if error is not None:
        report.error = error
    await session.flush()
    await session.refresh(report)
    return report


async def update_report_content(
    session: AsyncSession,
    report_id: str,
    *,
    result: dict[str, Any] | None = None,
    html_content: str | None = None,
    status: str = "complete",
) -> Report | None:
    """Set orchestrator result and/or HTML content on a report.

    Typically called when the Celery task finishes successfully.

    Returns the updated ``Report``, or ``None`` if not found.
    """
    report = await get_report(session, report_id)
    if report is None:
        return None
    report.status = status
    if result is not None:
        report.result = result
    if html_content is not None:
        report.html_content = html_content
    report.error = None
    await session.flush()
    await session.refresh(report)
    return report


# ═══════════════════════════════════════════════════════════════════════
# Journal Entry CRUD
# ═══════════════════════════════════════════════════════════════════════


async def create_journal_entry(
    session: AsyncSession,
    *,
    user_id: str,
    title: str,
    content: str,
    system: str = "general",
    entry_type: str = "reflection",
    tags: list[str] | None = None,
    mood_score: int | None = None,
) -> JournalEntry:
    """Insert a new journal entry row.

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        The owner of the entry.
    title:
        Entry title (max 200 chars).
    content:
        Entry body text — encrypted at rest.
    system:
        System this entry relates to (default ``"general"``).
    entry_type:
        Entry type (default ``"reflection"``).
    tags:
        Optional list of tag strings; stored as a JSON list.
    mood_score:
        Optional mood rating (1-10).

    Returns
    -------
    JournalEntry
        The newly created row.
    """
    entry = JournalEntry(
        user_id=user_id,
        title=title,
        content=content,
        system=system,
        entry_type=entry_type,
        tags=tags or [],
        mood_score=mood_score,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def get_journal_entry(session: AsyncSession, entry_id: str) -> JournalEntry | None:
    """Fetch a single journal entry by id.

    Returns ``None`` if the entry does not exist.
    """
    result = await session.execute(select(JournalEntry).where(JournalEntry.id == entry_id))
    return result.scalar_one_or_none()


async def get_journal_entry_for_user(
    session: AsyncSession, entry_id: str, user_id: str
) -> JournalEntry | None:
    """Fetch one of *user_id*'s journal entries by id, or ``None``.

    Ownership is filtered in SQL rather than compared by the caller, so
    another user's entry is indistinguishable from one that does not
    exist. Callers that need to distinguish the two (the journal router
    returns 404 then 403) still use :func:`get_journal_entry`; callers
    that only need "is this mine" should use this one and 404 either
    way, which is what keeps a link endpoint from becoming an existence
    oracle over somebody else's journal.
    """
    result = await session.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_journal_entries(
    session: AsyncSession,
    user_id: str,
    *,
    system: str | None = None,
    entry_type: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[JournalEntry], int]:
    """Return a paginated list of journal entries for *user_id*.

    Entries are returned in reverse chronological order (most recent first).

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        The user whose entries to list.
    system:
        Optional filter by system name.
    entry_type:
        Optional filter by entry type.
    offset:
        Number of rows to skip.
    limit:
        Maximum number of rows to return.

    Returns
    -------
    tuple[list[JournalEntry], int]
        ``(entries, total_count)`` where *total_count* is the unfiltered
        count matching the query (before pagination).
    """
    base_filter = [JournalEntry.user_id == user_id]
    if system is not None:
        base_filter.append(JournalEntry.system == system)
    if entry_type is not None:
        base_filter.append(JournalEntry.entry_type == entry_type)

    count_result = await session.execute(
        select(func.count()).select_from(JournalEntry).where(*base_filter)
    )
    total = count_result.scalar_one()

    rows_result = await session.execute(
        select(JournalEntry)
        .where(*base_filter)
        .order_by(JournalEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    entries = list(rows_result.scalars().all())
    return entries, total


async def update_journal_entry(
    session: AsyncSession,
    entry_id: str,
    **kwargs: Any,
) -> JournalEntry | None:
    """Update fields on an existing journal entry.

    Only the fields present in *kwargs* are updated.  Unknown keys are
    silently ignored.  Returns the updated entry, or ``None`` if not found.
    """
    entry = await get_journal_entry(session, entry_id)
    if entry is None:
        return None

    allowed = {"title", "content", "tags", "mood_score", "system", "entry_type"}
    for key, value in kwargs.items():
        if key in allowed:
            setattr(entry, key, value)

    await session.flush()
    await session.refresh(entry)
    return entry


async def delete_journal_entry(session: AsyncSession, entry_id: str) -> bool:
    """Delete a journal entry by id.

    Returns ``True`` if the entry was deleted, ``False`` if not found.
    """
    entry = await get_journal_entry(session, entry_id)
    if entry is None:
        return False
    await session.delete(entry)
    await session.flush()
    return True


async def get_journal_stats(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Return summary statistics for a user's journal.

    Uses SQL aggregation for counts and averages, only fetching
    individual dates for streak calculation.
    """
    base_filter = JournalEntry.user_id == user_id

    # Total count
    total_result = await session.execute(
        select(func.count()).select_from(JournalEntry).where(base_filter)
    )
    total = total_result.scalar_one()

    if total == 0:
        return {
            "total_entries": 0,
            "entries_by_system": {},
            "entries_by_type": {},
            "average_mood": None,
            "streak_days": 0,
            "tags_used": [],
        }

    # Counts by system
    system_result = await session.execute(
        select(JournalEntry.system, func.count()).where(base_filter).group_by(JournalEntry.system)
    )
    by_system: dict[str, int] = {row[0]: row[1] for row in system_result.all()}

    # Counts by type
    type_result = await session.execute(
        select(JournalEntry.entry_type, func.count())
        .where(base_filter)
        .group_by(JournalEntry.entry_type)
    )
    by_type: dict[str, int] = {row[0]: row[1] for row in type_result.all()}

    # Average mood
    mood_result = await session.execute(
        select(func.avg(JournalEntry.mood_score))
        .where(base_filter)
        .where(JournalEntry.mood_score.isnot(None))
    )
    avg_mood_raw = mood_result.scalar_one()
    avg_mood = round(float(avg_mood_raw), 2) if avg_mood_raw is not None else None

    # Tags — must fetch all since JSON arrays can't be aggregated in SQL
    tags_result = await session.execute(
        select(JournalEntry.tags).where(base_filter).where(JournalEntry.tags.isnot(None))
    )
    all_tags: set[str] = set()
    for (tags,) in tags_result.all():
        if isinstance(tags, list):
            all_tags.update(tags)

    # Streak — only fetch dates
    dates_result = await session.execute(
        select(JournalEntry.created_at).where(base_filter).order_by(JournalEntry.created_at.desc())
    )
    dates = sorted(
        {
            ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
            for (ts,) in dates_result.all()
            if ts is not None
        },
        reverse=True,
    )
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    streak = 0
    if dates and dates[0] == today:
        streak = 1
        for i in range(1, len(dates)):
            prev = datetime.strptime(dates[i - 1], "%Y-%m-%d")  # noqa: DTZ007
            curr = datetime.strptime(dates[i], "%Y-%m-%d")  # noqa: DTZ007
            if (prev - curr).days == 1:
                streak += 1
            else:
                break

    return {
        "total_entries": total,
        "entries_by_system": by_system,
        "entries_by_type": by_type,
        "average_mood": avg_mood,
        "streak_days": streak,
        "tags_used": sorted(all_tags),
    }


# ── Outcome Metrics ──────────────────────────────────────────────────────


_DERIVED_METRIC_NAMESPACE = uuid5(NAMESPACE_URL, "https://alchymine.app/outcome-metrics/derived")


def derived_metric_id(source_id: str, metric_name: str) -> str:
    """The id of the one metric row derived from row *source_id*.

    Derived rather than random, so the write that produces it can be
    replayed. A metric that stands for one event has to be updatable in
    place: without a stable id the second write mints a second
    measurement of the same thing and every count over it reads double.

    *metric_name* is part of the derivation, so one source row can carry
    several distinct metrics without them colliding.
    """
    return str(uuid5(_DERIVED_METRIC_NAMESPACE, f"{metric_name}:{source_id}"))


async def record_outcome_metric(
    session: AsyncSession,
    user_id: str,
    system: str,
    metric_name: str,
    value: float,
    period: str = "weekly",
    metric_id: str | None = None,
) -> OutcomeMetricRecord:
    """Persist an outcome metric measurement.

    Pass *metric_id* (see :func:`derived_metric_id`) when the metric
    stands for one event that can be written more than once. The write
    then updates the row instead of adding another, so the event keeps
    exactly one measurement.

    ``recorded_at`` is not touched on that path. It is when the thing
    happened, not when the last edit to it landed, and moving it would
    walk a late correction into the following day's bucket.
    """
    if metric_id is None:
        record = OutcomeMetricRecord(
            user_id=user_id,
            system=system,
            metric_name=metric_name,
            value=value,
            period=period,
        )
        session.add(record)
        await session.flush()
        return record

    dialect_name = session.bind.dialect.name  # type: ignore[union-attr]
    insert = pg_insert if dialect_name == "postgresql" else sqlite_insert
    await session.execute(
        insert(OutcomeMetricRecord)
        .values(
            id=metric_id,
            user_id=user_id,
            system=system,
            metric_name=metric_name,
            value=value,
            period=period,
        )
        .on_conflict_do_update(index_elements=["id"], set_={"value": value})
    )
    result = await session.execute(
        select(OutcomeMetricRecord)
        .where(OutcomeMetricRecord.id == metric_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def get_outcome_metrics(
    session: AsyncSession,
    user_id: str,
    system: str | None = None,
    limit: int = 100,
) -> list[OutcomeMetricRecord]:
    """Query outcome metrics for a user, optionally filtered by system."""
    stmt = select(OutcomeMetricRecord).where(OutcomeMetricRecord.user_id == user_id)
    if system:
        stmt = stmt.where(OutcomeMetricRecord.system == system)
    stmt = stmt.order_by(OutcomeMetricRecord.recorded_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Practice Log ──────────────────────────────────────────────────────────


async def create_practice_log_entry(
    session: AsyncSession,
    *,
    user_id: str,
    pack_id: str,
    practice_slug: str,
    primary_purpose: str,
    purposes: list[str],
    category: str,
    day_key: str,
    occurred_at: datetime | None = None,
    status: str = "completed",
    protocol_slot: str | None = None,
    duration_minutes: int | None = None,
    reflection: str | None = None,
    self_check_response: str | None = None,
) -> PracticeLogEntry:
    """Insert one practice-log row and return it.

    Every caller resolves *primary_purpose*, *purposes* and *category*
    from the practice registry before calling. They are denormalized
    here so a row stays readable after its pack is unmounted, and they
    are never taken from a client, because the recommender reads them.

    Parameters
    ----------
    user_id:
        The owner. Callers take this from the authenticated subject.
    pack_id, practice_slug:
        The qualified practice id, already checked against the registry.
    primary_purpose, purposes, category:
        Read off the registry definition, not the request.
    day_key:
        ``YYYY-MM-DD`` in the user's local day, stored exactly as given.
    occurred_at:
        When it happened. Defaults to now in UTC.
    status:
        ``completed`` | ``skipped`` | ``started``.
    protocol_slot:
        ``morning`` | ``day`` | ``evening`` | ``unscheduled``, or None.
    reflection, self_check_response:
        Free text, encrypted at rest.
    """
    entry = PracticeLogEntry(
        user_id=user_id,
        pack_id=pack_id,
        practice_slug=practice_slug,
        primary_purpose=primary_purpose,
        purposes=list(purposes),
        category=category,
        status=status,
        protocol_slot=protocol_slot,
        duration_minutes=duration_minutes,
        occurred_at=occurred_at or datetime.now(UTC),
        day_key=day_key,
        reflection=reflection,
        self_check_response=self_check_response,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def get_practice_log_entry(
    session: AsyncSession, entry_id: str, user_id: str
) -> PracticeLogEntry | None:
    """Fetch one of the owner's practice-log rows by id, or ``None``.

    Ownership is filtered in SQL, not left to the caller: a row that
    exists but belongs to another user is indistinguishable from one
    that does not exist, so a future by-id route cannot become an
    existence oracle.
    """
    result = await session.execute(
        select(PracticeLogEntry).where(
            PracticeLogEntry.id == entry_id, PracticeLogEntry.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_practice_log_entries(
    session: AsyncSession,
    user_id: str,
    *,
    from_day: str | None = None,
    to_day: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[PracticeLogEntry], int]:
    """Return one page of *user_id*'s practice log, newest first.

    The date range filters on ``day_key`` rather than ``occurred_at``.
    ``day_key`` is the user's local calendar day, so a range expressed
    in local days is what a caller asking for "this week" means, and the
    ``(user_id, day_key)`` index serves it directly. Both bounds are
    inclusive; either may be omitted for an open-ended range.

    Returns ``(entries, total)`` where *total* counts every row matching
    the filters before pagination.
    """
    filters = [PracticeLogEntry.user_id == user_id]
    if from_day is not None:
        filters.append(PracticeLogEntry.day_key >= from_day)
    if to_day is not None:
        filters.append(PracticeLogEntry.day_key <= to_day)
    if status is not None:
        filters.append(PracticeLogEntry.status == status)

    count_result = await session.execute(
        select(func.count()).select_from(PracticeLogEntry).where(*filters)
    )
    total = count_result.scalar_one()

    rows_result = await session.execute(
        select(PracticeLogEntry)
        .where(*filters)
        # occurred_at is the event time; id breaks ties so a page
        # boundary cannot drop or repeat a row when two events share a
        # timestamp, which same-second logging makes routine.
        .order_by(PracticeLogEntry.occurred_at.desc(), PracticeLogEntry.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows_result.scalars().all()), total


async def list_recommender_log_rows(
    session: AsyncSession, user_id: str, *, window_start_day: str
) -> list[Any]:
    """Return the plaintext practice-log columns the recommender reads.

    Five columns, none of them user-authored text. ``reflection`` and
    ``self_check_response`` are encrypted at rest and are never selected
    here, so nothing the user wrote is decrypted to build a protocol.
    That is a rail, not an optimization: the recommender has no business
    reading a reflection, and the cheapest way to guarantee it is to
    never load one.

    Two row sets in one query, because the recommender needs both:

    - every ``completed`` row *ever*, since a prerequisite is satisfied
      by a completion at any point in the past and staleness counts days
      since the last one however long ago that was;
    - every row inside the balance window whatever its status, since
      purpose shares and the decline rule are window-scoped and the
      decline rule counts skips.

    Rows are returned newest-day first purely so a truncated debug dump
    shows recent activity; the recommender itself is order-independent.
    """
    result = await session.execute(
        select(
            PracticeLogEntry.pack_id,
            PracticeLogEntry.practice_slug,
            PracticeLogEntry.primary_purpose,
            PracticeLogEntry.status,
            PracticeLogEntry.day_key,
        )
        .where(
            PracticeLogEntry.user_id == user_id,
            or_(
                PracticeLogEntry.status == "completed",
                PracticeLogEntry.day_key >= window_start_day,
            ),
        )
        .order_by(PracticeLogEntry.day_key.desc(), PracticeLogEntry.id.desc())
    )
    return list(result.all())


async def list_practice_context_rows(
    session: AsyncSession, user_id: str, *, from_day: str
) -> list[Any]:
    """Return the plaintext columns the coach context block is built from.

    Five columns, none of them user-authored text: ``pack_id``,
    ``practice_slug``, ``primary_purpose``, ``status``, ``day_key``. The
    list is written out because this docstring is the data rail's stated
    contract, and a count that drifts from the SELECT below is worse
    than no count at all. Same rail as
    :func:`list_recommender_log_rows` and for a sharper reason: this is
    the one practice query whose output reaches an LLM. ``reflection``
    and ``self_check_response`` are encrypted at rest and are not
    selected here, so a reflection cannot leak into a prompt however the
    renderer above changes.

    Bounded to ``day_key >= from_day``. The coach block summarises a
    week, and loading a user's whole history to describe seven days of
    it would grow without limit.
    """
    result = await session.execute(
        select(
            PracticeLogEntry.pack_id,
            PracticeLogEntry.practice_slug,
            PracticeLogEntry.primary_purpose,
            PracticeLogEntry.status,
            PracticeLogEntry.day_key,
        )
        .where(
            PracticeLogEntry.user_id == user_id,
            PracticeLogEntry.day_key >= from_day,
        )
        .order_by(PracticeLogEntry.day_key.desc(), PracticeLogEntry.id.desc())
    )
    return list(result.all())


async def list_journey_rows(session: AsyncSession, user_id: str, *, from_day: str) -> list[Any]:
    """Return the plaintext columns the journey chart is folded from.

    Four columns, none of them user-authored text: ``day_key``,
    ``primary_purpose``, ``status``, and the joined ``capacity_delta``.
    ``reflection``, ``self_check_response`` and the integration ``note``
    are encrypted at rest and are not selected here, so nothing the user
    wrote is decrypted to draw a chart. Same rail as
    :func:`list_recommender_log_rows`.

    The integration row is joined in rather than read from
    ``outcome_metrics``, and the reason is the day axis. The derived
    metric row is stamped ``recorded_at`` in UTC; the practice it stands
    for carries the user's *local* ``day_key``. Bucketing one series by
    UTC and the other by local day would put an evening loop in Auckland
    one column right of the practice it closed. The link row knows which
    practice it belongs to, so the practice's own day is used for both.

    The join is a LEFT OUTER: a practice without a closed loop still has
    to appear, or the chart would only show the days the user wrote
    about. At most one integration row exists per practice per user
    (``uq_integration_entries_user_practice_log``), so the join cannot
    duplicate a practice.

    Bounded to ``day_key >= from_day``. The window is capped by the
    caller; loading a user's whole history to draw ninety days of it
    would grow without limit.
    """
    result = await session.execute(
        select(
            PracticeLogEntry.day_key,
            PracticeLogEntry.primary_purpose,
            PracticeLogEntry.status,
            # Labelled, because ``row.id`` next to a practice row would
            # read as the practice's id and is the integration's. It is
            # NULL exactly when no loop was closed on that practice.
            IntegrationEntry.id.label("integration_id"),
            IntegrationEntry.capacity_delta,
        )
        .outerjoin(
            IntegrationEntry,
            and_(
                IntegrationEntry.practice_log_id == PracticeLogEntry.id,
                IntegrationEntry.user_id == PracticeLogEntry.user_id,
            ),
        )
        .where(
            PracticeLogEntry.user_id == user_id,
            PracticeLogEntry.day_key >= from_day,
        )
        .order_by(PracticeLogEntry.day_key.desc(), PracticeLogEntry.id.desc())
    )
    return list(result.all())


async def get_journey_anchors(session: AsyncSession, user_id: str) -> tuple[str | None, str | None]:
    """Return the user's first practice day and first closed-loop day.

    ``(first_practice_day, first_loop_day)``, each ``YYYY-MM-DD`` in the
    user's local day, or ``None`` where there is nothing yet.

    The one pair of facts a window cannot supply: "practicing since
    March" is the line that makes a thirty-day chart mean something, and
    it is unanswerable from thirty days of rows. Both are scalar
    aggregates over an index (``ix_practice_log_user_day``), so reading
    all of history costs one row of output each rather than all of it.
    ``day_key`` is a zero-padded ``YYYY-MM-DD`` string, so the
    lexicographic minimum is the chronological one.

    The two filter differently, on purpose.

    *first_practice_day* counts completions only, the same rule the rest
    of the series applies. The status on a log row comes from the
    client, so a user can hold a log full of ``skipped`` rows without
    ever having practiced; an unfiltered minimum would answer "March"
    for them, and the page reads exactly this field to decide whether to
    show its empty state. They would get a chart of empty columns
    captioned with a day they never practiced on.

    *first_loop_day* counts every closed loop whatever the practice's
    status. ``POST /practice/integration`` accepts a log row of any
    status and writes the derived ``practice_integration`` outcome row
    either way, so filtering here would make the journey report fewer
    loops than the dashboard for the same events. A ``started`` practice
    is also a real experience to reflect on. The pair can therefore be
    lopsided, which is safe: a user with no completion sees the empty
    state, where neither anchor is rendered.
    """
    earliest_practice = await session.execute(
        select(func.min(PracticeLogEntry.day_key)).where(
            PracticeLogEntry.user_id == user_id,
            PracticeLogEntry.status == "completed",
        )
    )
    earliest_loop = await session.execute(
        select(func.min(PracticeLogEntry.day_key))
        .select_from(IntegrationEntry)
        .join(PracticeLogEntry, PracticeLogEntry.id == IntegrationEntry.practice_log_id)
        .where(IntegrationEntry.user_id == user_id)
    )
    return earliest_practice.scalar_one(), earliest_loop.scalar_one()


# ── Ecology state ─────────────────────────────────────────────────────────


async def get_stored_recommendation(session: AsyncSession, user_id: str) -> dict[str, Any] | None:
    """Return *user_id*'s stored protocol envelope, or ``None``.

    A read that cannot write, unlike :func:`get_or_create_ecology_state`.
    The chat path calls this: asking the coach a question is not a reason
    to create recommender state for a user who has never opened the
    practice surface.
    """
    result = await session.execute(
        select(EcologyState.last_recommendation).where(EcologyState.user_id == user_id)
    )
    stored = result.scalar_one_or_none()
    return stored if isinstance(stored, dict) else None


async def get_or_create_ecology_state(session: AsyncSession, user_id: str) -> EcologyState:
    """Return *user_id*'s recommender state, creating it with defaults if absent.

    The insert is an upsert rather than a plain INSERT so two concurrent
    first requests from the same user cannot collide on the primary key.
    ``DO NOTHING`` is the right conflict action here: the row that won
    the race already holds exactly the defaults this one would have
    written, so there is nothing to reconcile.
    """
    existing = await session.execute(select(EcologyState).where(EcologyState.user_id == user_id))
    state = existing.scalar_one_or_none()
    if state is not None:
        return state

    dialect_name = session.bind.dialect.name  # type: ignore[union-attr]
    insert = pg_insert if dialect_name == "postgresql" else sqlite_insert
    await session.execute(
        insert(EcologyState)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.flush()

    created = await session.execute(select(EcologyState).where(EcologyState.user_id == user_id))
    return created.scalar_one()


async def update_ecology_recommendation(
    session: AsyncSession,
    user_id: str,
    *,
    rotation_cursor: int,
    last_recommendation: dict[str, Any],
    last_recommended_at: datetime,
) -> EcologyState:
    """Persist the outcome of one recomputation.

    ``last_recommended_at`` is written for operators reading the table.
    The stable-day comparison does *not* use it: it is a UTC instant and
    the rule compares the user's local day, which travels inside
    *last_recommendation* instead.
    """
    state = await get_or_create_ecology_state(session, user_id)
    state.rotation_cursor = rotation_cursor
    state.last_recommendation = last_recommendation
    state.last_recommended_at = last_recommended_at
    await session.flush()
    await session.refresh(state)
    return state


class Unchanged:
    """The type of :data:`UNCHANGED`. Public so callers can annotate with it."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "UNCHANGED"


UNCHANGED = Unchanged()
"""Leave a settings field as it is.

Needed because ``None`` is a real value for ``active_pack_ids``: it means
"every mounted pack". A default of ``None`` would make "do not touch it"
and "reset it to all packs" the same call.
"""


async def update_ecology_settings(
    session: AsyncSession,
    user_id: str,
    *,
    protocol_size: int | Unchanged = UNCHANGED,
    active_pack_ids: list[str] | None | Unchanged = UNCHANGED,
) -> EcologyState:
    """Write the user's recommender settings, clearing today's protocol if they moved.

    The caller validates the values. This function's own job is the part
    that is easy to get wrong: a settings change has to invalidate the
    stored protocol, or the user waits until tomorrow to see it.

    Only ``active_pack_ids`` travels in the stable-day fingerprint, so a
    change to ``protocol_size`` alone would leave the stored envelope
    replayable and the next ``/practice/today`` would answer yesterday's
    protocol at yesterday's size. Both fields therefore clear
    ``last_recommendation`` and ``last_recommended_at`` when they
    actually change. Clearing on the wider condition rather than the
    fingerprint's is deliberate: the cost is one recomputation, and the
    alternative is a rule that has to stay in step with the fingerprint
    forever.

    A write that changes nothing clears nothing, so opening the settings
    page and saving it untouched does not reshuffle the protocol under
    the user. The rotation cursor is left alone either way: it is the
    user's position in the purpose rotation, not part of the protocol
    being discarded.
    """
    state = await get_or_create_ecology_state(session, user_id)

    changed = False
    if not isinstance(protocol_size, Unchanged) and protocol_size != state.protocol_size:
        state.protocol_size = protocol_size
        changed = True
    if not isinstance(active_pack_ids, Unchanged) and active_pack_ids != state.active_pack_ids:
        # Compared against the raw column rather than a normalized read
        # of it, so a value that is not a list of strings is replaced
        # rather than mistaken for the absence of a subset.
        state.active_pack_ids = active_pack_ids
        changed = True

    if changed:
        state.last_recommendation = None
        state.last_recommended_at = None

    await session.flush()
    await session.refresh(state)
    return state


# ── Integration entries ───────────────────────────────────────────────────


NOTE_SEPARATOR = "\n\n"


class IntegrationNoteFull(Exception):
    """The entry's stored note has no room left for the incoming text.

    Raised instead of truncating. The note is the user's own writing
    about their own practice; storing the front half of a sentence under
    their name, with nothing in the record to say the rest was dropped,
    is worse than a save that plainly did not land.

    The message carries lengths only. It travels into application logs
    and into the 422 body, and note content belongs in neither.
    """

    def __init__(self, *, stored_chars: int, incoming_chars: int, cap: int) -> None:
        super().__init__(
            f"integration note would reach {stored_chars + incoming_chars} characters, "
            f"over the {cap} cap"
        )
        self.stored_chars = stored_chars
        self.incoming_chars = incoming_chars
        self.cap = cap


def merge_notes(
    existing: str | None,
    incoming: str | None,
    *,
    total_char_cap: int | None = None,
) -> str | None:
    """Fold *incoming* into *existing* without losing either.

    A completed practice offers two prompts, and each can carry a note.
    They are two pieces of the user's own writing about one practice,
    arriving in separate saves, so they are kept as separate paragraphs
    rather than one overwriting the other.

    The save is the unit of dedup, not the paragraph. *incoming* is
    skipped only when it is the whole stored note or the tail of it,
    which is exactly the shape a replayed save has: whatever the last
    accepted save appended is still on the end. Two earlier readings of
    this both came out wrong. Splitting the stored note on blank lines
    dropped a new single-paragraph note that happened to match something
    written earlier, and it never matched a replayed multi-paragraph
    save at all, because the joined string is not one of the pieces.

    *total_char_cap* bounds the merged result. ``None`` means no bound,
    for callers that have already checked or do not store the result.
    Passing it raises :class:`IntegrationNoteFull`; a save that appends
    nothing (empty, or a replay) cannot raise, however full the entry
    already is.
    """
    trimmed = incoming.strip() if incoming else ""
    if not trimmed:
        return existing

    if existing:
        if trimmed == existing or existing.endswith(f"{NOTE_SEPARATOR}{trimmed}"):
            return existing
        merged = f"{existing}{NOTE_SEPARATOR}{trimmed}"
    else:
        merged = trimmed

    if total_char_cap is not None and len(merged) > total_char_cap:
        raise IntegrationNoteFull(
            stored_chars=len(existing or ""),
            incoming_chars=len(trimmed),
            cap=total_char_cap,
        )
    return merged


def _integration_note_cap() -> int:
    """The configured ceiling on one entry's accumulated note."""
    from alchymine.config import get_settings

    return get_settings().integration_note_total_char_cap


def integration_entry_select(
    user_id: str, practice_log_id: str, *, for_update: bool = False
) -> Select[tuple[IntegrationEntry]]:
    """The statement behind every read of one completion's entry.

    Ordered and limited rather than a bare fetch. The unique key makes
    more than one row impossible going forward, but a database carrying
    duplicates from before it landed would otherwise turn every save on
    an affected practice into a 500. The earliest row wins, matching
    what the cleanup script keeps.

    *for_update* takes the row lock, and every read that leads to a
    merge asks for it. Without it, two saves arriving after the row
    exists both read the same starting note, merge separately, and the
    later flush silently drops the earlier one. Client-side queuing only
    serializes one mounted card in one tab.

    Built as a statement rather than executed here so the lock is
    assertable: SQLite compiles ``FOR UPDATE`` away, so no test against
    the test database can show it, and compiling against the PostgreSQL
    dialect is the only honest proof that production takes the lock.
    """
    statement = (
        select(IntegrationEntry)
        .where(
            IntegrationEntry.user_id == user_id,
            IntegrationEntry.practice_log_id == practice_log_id,
        )
        .order_by(IntegrationEntry.created_at.asc(), IntegrationEntry.id.asc())
        .limit(1)
        .execution_options(populate_existing=True)
    )
    return statement.with_for_update() if for_update else statement


async def _get_integration_entry(
    session: AsyncSession, user_id: str, practice_log_id: str, *, for_update: bool = False
) -> IntegrationEntry | None:
    """The caller's integration entry for one completion, or ``None``."""
    result = await session.execute(
        integration_entry_select(user_id, practice_log_id, for_update=for_update)
    )
    return result.scalars().first()


async def upsert_integration_entry(
    session: AsyncSession,
    *,
    user_id: str,
    practice_log_id: str,
    purpose: str,
    intention_entry_id: str | None = None,
    reflection_entry_id: str | None = None,
    capacity_delta: int | None = None,
    note: str | None = None,
) -> tuple[IntegrationEntry, bool]:
    """Write the integration entry for one completion. One row, always.

    Returns ``(entry, created)``, where *created* is false when the row
    was already there and this call merged into it.

    One completion is one record, keyed on ``(user_id,
    practice_log_id)``. The completed practice card offers the
    self-check and the integration reading side by side and both save
    against the same practice log row, so a plain insert per call gave
    one practice two records.

    What a second call does, and why:

    - a field it does not carry is left alone, so a save that only has
      a note cannot erase a capacity reading the user already gave;
    - notes accumulate (:func:`merge_notes`) rather than overwrite;
    - the same save replayed changes nothing.

    Both reads take the row lock (:func:`integration_entry_select`),
    because both lead to a merge: the found-existing path, and the
    re-select after a concurrent first save won the insert. The merge is
    read-modify-write in Python rather than an atomic SQL ``UPDATE``
    because ``note`` is an encrypted column. Its ciphertext is not
    concatenable or comparable in SQL, so the lock is what makes the
    read and the write one step.

    A note that would push the merged text past
    ``integration_note_total_char_cap`` raises
    :class:`IntegrationNoteFull`. Nothing is written in that case, and
    nothing already stored is touched.

    *purpose* is the practice's, read off the ``practice_log`` row by
    the caller. It is a parameter rather than a lookup here so this
    module keeps having no opinion about the practice registry, and it
    is not merged: it belongs to the practice, not to the save.

    This writes the link row only. The single derived ``outcome_metrics``
    row is a separate :func:`record_outcome_metric` call, so the two
    writes are visible as two calls at the call site rather than hidden
    inside one.
    """
    cap = _integration_note_cap()
    entry = await _get_integration_entry(session, user_id, practice_log_id, for_update=True)

    if entry is None:
        entry_id = str(uuid4())
        dialect_name = session.bind.dialect.name  # type: ignore[union-attr]
        insert = pg_insert if dialect_name == "postgresql" else sqlite_insert
        await session.execute(
            insert(IntegrationEntry)
            .values(
                id=entry_id,
                user_id=user_id,
                practice_log_id=practice_log_id,
                intention_entry_id=intention_entry_id,
                reflection_entry_id=reflection_entry_id,
                purpose=purpose,
                capacity_delta=capacity_delta,
                note=merge_notes(None, note, total_char_cap=cap),
            )
            .on_conflict_do_nothing(index_elements=["user_id", "practice_log_id"])
        )
        # DO NOTHING rather than an error, so a concurrent first save
        # from the same user is a merge instead of a 500. Whether this
        # call was the one that inserted is read off the id that came
        # back, which needs no RETURNING and no rowcount.
        stored = await _get_integration_entry(session, user_id, practice_log_id, for_update=True)
        if stored is None:  # pragma: no cover, the row was just written
            raise RuntimeError("integration entry vanished between write and read")
        if stored.id == entry_id:
            return stored, True
        entry = stored

    # The note first, so a refusal happens before anything on this row
    # is touched. A save that is rejected leaves the entry exactly as it
    # was, including the capacity reading it happened to carry.
    merged_note = merge_notes(entry.note, note, total_char_cap=cap)

    if intention_entry_id is not None:
        entry.intention_entry_id = intention_entry_id
    if reflection_entry_id is not None:
        entry.reflection_entry_id = reflection_entry_id
    if capacity_delta is not None:
        entry.capacity_delta = capacity_delta
    entry.note = merged_note

    await session.flush()
    await session.refresh(entry)
    return entry, False


# ── Milestones ────────────────────────────────────────────────────────────


async def record_milestone(
    session: AsyncSession,
    user_id: str,
    system: str,
    name: str,
    completed: bool = True,
    notes: str | None = None,
) -> MilestoneDBRecord:
    """Persist a milestone record."""
    record = MilestoneDBRecord(
        user_id=user_id,
        system=system,
        name=name,
        completed=completed,
        completed_at=datetime.now(UTC) if completed else None,
        notes=notes,
    )
    session.add(record)
    await session.flush()
    return record


async def get_milestones(
    session: AsyncSession,
    user_id: str,
    system: str | None = None,
) -> list[MilestoneDBRecord]:
    """Query milestones for a user, optionally filtered by system."""
    stmt = select(MilestoneDBRecord).where(MilestoneDBRecord.user_id == user_id)
    if system:
        stmt = stmt.where(MilestoneDBRecord.system == system)
    stmt = stmt.order_by(MilestoneDBRecord.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# Feedback CRUD
# ═══════════════════════════════════════════════════════════════════════


async def create_feedback(
    session: AsyncSession,
    *,
    message: str,
    category: str = "general",
    email: str | None = None,
    user_id: str | None = None,
    page_url: str | None = None,
) -> FeedbackEntry:
    """Insert a new feedback entry.

    Parameters
    ----------
    session:
        Active async session.
    message:
        The feedback message body.
    category:
        One of ``general | bug | feature | praise | other``.
    email:
        Optional contact email (for anonymous submissions).
    user_id:
        Optional FK to the ``users`` table.
    page_url:
        Optional URL of the page the user submitted feedback from.

    Returns
    -------
    FeedbackEntry
        The newly created row.
    """
    entry = FeedbackEntry(
        message=message,
        category=category,
        email=email,
        user_id=user_id,
        page_url=page_url,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def list_feedback(
    session: AsyncSession,
    *,
    status: str | None = None,
    category: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[FeedbackEntry], int]:
    """Return a paginated list of feedback entries (most recent first).

    Parameters
    ----------
    session:
        Active async session.
    status:
        Optional filter by status (``new | reviewed | resolved | dismissed``).
    category:
        Optional filter by category.
    offset:
        Number of rows to skip.
    limit:
        Maximum number of rows to return.

    Returns
    -------
    tuple[list[FeedbackEntry], int]
        ``(entries, total_count)`` where *total_count* is the unfiltered
        count matching the query (before pagination).
    """
    filters = []
    if status is not None:
        filters.append(FeedbackEntry.status == status)
    if category is not None:
        filters.append(FeedbackEntry.category == category)

    count_stmt = select(func.count()).select_from(FeedbackEntry)
    if filters:
        count_stmt = count_stmt.where(*filters)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    rows_stmt = (
        select(FeedbackEntry).order_by(FeedbackEntry.created_at.desc()).offset(offset).limit(limit)
    )
    if filters:
        rows_stmt = rows_stmt.where(*filters)
    rows_result = await session.execute(rows_stmt)
    entries = list(rows_result.scalars().all())
    return entries, total


async def update_feedback(
    session: AsyncSession,
    entry_id: int,
    *,
    status: str | None = None,
    admin_note: str | None = None,
) -> FeedbackEntry | None:
    """Update status and/or admin note on a feedback entry.

    Returns the updated ``FeedbackEntry``, or ``None`` if not found.
    """
    result = await session.execute(select(FeedbackEntry).where(FeedbackEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return None
    if status is not None:
        entry.status = status
    if admin_note is not None:
        entry.admin_note = admin_note
    await session.flush()
    await session.refresh(entry)
    return entry


# ═══════════════════════════════════════════════════════════════════════
# Chat Message CRUD (Growth Assistant)
# ═══════════════════════════════════════════════════════════════════════


async def save_chat_message(
    session: AsyncSession,
    *,
    user_id: str,
    role: str,
    content: str,
    system_key: str | None = None,
    refresh: bool = True,
) -> ChatMessage:
    """Persist a single chat message and return the ORM row.

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        FK to ``users.id``.
    role:
        ``"user"``, ``"assistant"``, or ``"system"``.
    content:
        Message body — encrypted at rest by the ORM column type.
    system_key:
        Optional system scope (``"intelligence" | "healing" | "wealth" |
        "creative" | "perspective"``) or ``None`` for the general coach.
    refresh:
        Read the generated columns back after the flush.  Callers that
        use ``id`` or ``created_at`` need it.  The one caller that does
        not is the assistant write on the disconnect path, and there the
        extra round trip is what fails: once the request task is being
        cancelled the refresh raises and takes the whole write with it,
        losing a reply the reader already saw.

    Returns
    -------
    ChatMessage
        The newly created row.  ``id`` and ``created_at`` are populated
        unless *refresh* was turned off.
    """
    msg = ChatMessage(
        user_id=user_id,
        role=role,
        content=content,
        system_key=system_key,
    )
    session.add(msg)
    await session.flush()
    if refresh:
        await session.refresh(msg)
    return msg


async def get_chat_history(
    session: AsyncSession,
    *,
    user_id: str,
    system_key: str | None = None,
    limit: int = 50,
) -> list[ChatMessage]:
    """Return the most recent chat history for a user, in chronological order.

    The query fetches the *latest* ``limit`` rows ordered by ``created_at``
    descending (so we always get the newest messages even when the history
    is long), then reverses the slice before returning so callers receive
    them oldest-first — the natural order for replay into an LLM context.

    When ``system_key`` is provided, only messages scoped to that system are
    returned.  When ``system_key`` is ``None``, **all** messages for the
    user are returned regardless of their scope (general history).

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        FK to ``users.id``.
    system_key:
        Optional system filter; ``None`` means "all messages".
    limit:
        Maximum number of messages to return (default 50).

    Returns
    -------
    list[ChatMessage]
        Messages in chronological (oldest-first) order.
    """
    stmt = select(ChatMessage).where(ChatMessage.user_id == user_id)
    if system_key is not None:
        stmt = stmt.where(ChatMessage.system_key == system_key)
    stmt = stmt.order_by(ChatMessage.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()  # chronological order for callers
    return rows


async def count_user_chat_messages(
    session: AsyncSession,
    *,
    user_id: str,
    system_key: str | None = None,
) -> int:
    """Return the total number of **user** messages for a user/system pair.

    Only counts ``role='user'`` rows.  Used by the history-cap guardrail
    to enforce a per-system message ceiling before accepting new input.

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        FK to ``users.id``.
    system_key:
        Optional system filter; ``None`` counts messages with ``NULL``
        system_key (general coach mode).
    """
    stmt = (
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.role == "user")
    )
    if system_key is not None:
        stmt = stmt.where(ChatMessage.system_key == system_key)
    else:
        stmt = stmt.where(ChatMessage.system_key.is_(None))
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_feedback_counts(session: AsyncSession) -> dict[str, int]:
    """Return feedback counts grouped by status.

    Returns a dict mapping each status value to its count, e.g.
    ``{"new": 5, "reviewed": 2, "resolved": 10, "dismissed": 1}``.
    Statuses with zero entries are omitted.
    """
    result = await session.execute(
        select(FeedbackEntry.status, func.count()).group_by(FeedbackEntry.status)
    )
    return {row[0]: row[1] for row in result.all()}


# ─── Generated Image CRUD ──────────────────────────────────────────────


async def create_generated_image(
    session: AsyncSession,
    *,
    user_id: str,
    prompt: str,
    file_path: str,
    mime_type: str = "image/png",
    style_preset: str | None = None,
    model: str | None = None,
) -> GeneratedImage:
    """Insert a new generated_images row.

    Parameters
    ----------
    session:
        Active async session.
    user_id:
        Owning user (FK).
    prompt:
        The exact prompt used to generate the image.
    file_path:
        Path on disk (relative to ``ART_CACHE_DIR``) where the bytes live.
    mime_type:
        IANA mime type, default ``image/png``.
    style_preset:
        Optional style preset id from ``STYLE_PRESETS``.
    model:
        Optional Gemini model id used.
    """
    image = GeneratedImage(
        user_id=user_id,
        prompt=prompt,
        file_path=file_path,
        mime_type=mime_type,
        style_preset=style_preset,
        model=model,
    )
    session.add(image)
    await session.flush()
    await session.refresh(image)
    return image


async def get_generated_image(session: AsyncSession, image_id: str) -> GeneratedImage | None:
    """Fetch a single generated_images row by id, or ``None``."""
    result = await session.execute(select(GeneratedImage).where(GeneratedImage.id == image_id))
    return result.scalar_one_or_none()


async def list_generated_images_for_user(
    session: AsyncSession,
    user_id: str,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[GeneratedImage]:
    """Return a page of a user's generated images, newest first.

    The caller is expected to strip bytes/paths before returning to
    clients — this repository helper only loads metadata from the DB.
    """
    stmt = (
        select(GeneratedImage)
        .where(GeneratedImage.user_id == user_id)
        .order_by(GeneratedImage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_generated_image(session: AsyncSession, image_id: str) -> bool:
    """Delete a generated_images row by id.

    Returns ``True`` if a row was deleted, ``False`` otherwise. The
    caller is responsible for verifying ownership before calling and
    for unlinking the corresponding file from disk.
    """
    image = await get_generated_image(session, image_id)
    if image is None:
        return False
    await session.delete(image)
    await session.flush()
    return True

"""Async CRUD operations for Alchymine user profiles and reports.

All database access goes through this module so that:
- Encryption/decryption is handled transparently by the ORM layer
- Session lifecycle is managed consistently
- Queries are easy to test (swap in SQLite session)

Functions — Profiles
~~~~~~~~~~~~~~~~~~~~
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

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from alchymine.db.models import (
    CreativeProfile,
    FeedbackEntry,
    HealingProfile,
    IdentityProfile,
    IntakeData,
    JournalEntry,
    MilestoneDBRecord,
    OutcomeMetricRecord,
    PerspectiveProfile,
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
    intentions: list[str] | None = None,
    user_id: str | None = None,
) -> User:
    """Create a new user with intake data.

    Returns the newly created ``User`` with its ``intake`` relationship
    populated.  When ``user_id`` is provided it is used as the primary key
    (e.g. to tie the profile to the authenticated user's JWT sub).
    """
    user = User(id=user_id) if user_id else User()
    session.add(user)
    await session.flush()  # generate user.id (if not already set)

    # Derive primary intention from the list when provided
    _primary = intentions[0] if intentions else intention

    intake = IntakeData(
        user_id=user.id,
        full_name=full_name,
        birth_date=birth_date,
        birth_time=birth_time,
        birth_city=birth_city,
        intention=_primary,
        intentions=intentions,
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


async def list_reports_by_user(
    session: AsyncSession,
    user_id: str,
    *,
    skip: int = 0,
    limit: int = 20,
) -> list[Report]:
    """Return a paginated list of reports for *user_id* (most recent first)."""
    result = await session.execute(
        select(Report)
        .where(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_reports_by_user(session: AsyncSession, user_id: str) -> int:
    """Return total number of reports for *user_id*."""
    result = await session.execute(
        select(func.count()).select_from(Report).where(Report.user_id == user_id)
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


async def record_outcome_metric(
    session: AsyncSession,
    user_id: str,
    system: str,
    metric_name: str,
    value: float,
    period: str = "weekly",
) -> OutcomeMetricRecord:
    """Persist an outcome metric measurement."""
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

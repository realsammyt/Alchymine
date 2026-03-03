"""Journal API endpoints — reflective journaling and progress tracking.

Provides CRUD operations for journal entries that capture user
reflections, reframes, gratitude notes, and progress observations
across all five Alchymine systems.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository

router = APIRouter()


# ── Request / Response models ───────────────────────────────────────────


class JournalEntryCreate(BaseModel):
    """Request to create a new journal entry."""

    user_id: str = Field(..., description="User identifier")
    system: str = Field(
        "general",
        description="System this entry relates to: general | healing | wealth | creative | perspective",
    )
    entry_type: str = Field(
        "reflection",
        description="Entry type: reflection | reframe | gratitude | milestone | insight",
    )
    title: str = Field(..., min_length=1, max_length=200, description="Entry title")
    content: str = Field(..., min_length=1, max_length=5000, description="Entry body text")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization")
    mood_score: int | None = Field(None, ge=1, le=10, description="Optional mood rating (1-10)")


class JournalEntryUpdate(BaseModel):
    """Request to update an existing journal entry."""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1, max_length=5000)
    tags: list[str] | None = None
    mood_score: int | None = Field(None, ge=1, le=10)


class JournalEntryResponse(BaseModel):
    """A journal entry response."""

    id: str
    user_id: str
    system: str
    entry_type: str
    title: str
    content: str
    tags: list[str]
    mood_score: int | None = None
    created_at: str
    updated_at: str


class JournalListResponse(BaseModel):
    """Paginated list of journal entries."""

    entries: list[JournalEntryResponse]
    total: int
    page: int
    per_page: int


class JournalStatsResponse(BaseModel):
    """Summary statistics for a user's journal."""

    total_entries: int
    entries_by_system: dict[str, int]
    entries_by_type: dict[str, int]
    average_mood: float | None = None
    streak_days: int = 0
    tags_used: list[str]


# ── Helpers ──────────────────────────────────────────────────────────────


def _entry_to_response(entry: Any) -> JournalEntryResponse:
    """Convert an ORM JournalEntry to a JournalEntryResponse."""
    tags = entry.tags if isinstance(entry.tags, list) else []
    created = (
        entry.created_at.isoformat()
        if hasattr(entry.created_at, "isoformat")
        else str(entry.created_at)
    )
    updated = (
        entry.updated_at.isoformat()
        if hasattr(entry.updated_at, "isoformat")
        else str(entry.updated_at)
    )
    return JournalEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        system=entry.system,
        entry_type=entry.entry_type,
        title=entry.title,
        content=entry.content,
        tags=tags,
        mood_score=entry.mood_score,
        created_at=created,
        updated_at=updated,
    )


# ── Endpoints ───────────────────────────────────────────────────────────


@router.post("/journal", status_code=201)
async def create_journal_entry(
    entry: JournalEntryCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    """Create a new journal entry.

    Supports reflections, cognitive reframes, gratitude notes,
    milestone celebrations, and system-specific insights.
    """
    if current_user["sub"] != entry.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db_entry = await repository.create_journal_entry(
        session,
        user_id=entry.user_id,
        title=entry.title,
        content=entry.content,
        system=entry.system,
        entry_type=entry.entry_type,
        tags=entry.tags,
        mood_score=entry.mood_score,
    )
    return _entry_to_response(db_entry)


@router.get("/journal/stats/{user_id}")
async def get_journal_stats(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JournalStatsResponse:
    """Get summary statistics for a user's journal.

    Returns entry counts by system and type, average mood score,
    and a list of all tags used.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    stats = await repository.get_journal_stats(session, user_id)
    return JournalStatsResponse(**stats)


@router.get("/journal/{entry_id}")
async def get_journal_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    """Retrieve a single journal entry by ID."""
    db_entry = await repository.get_journal_entry(session, entry_id)
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if current_user["sub"] != db_entry.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _entry_to_response(db_entry)


@router.put("/journal/{entry_id}")
async def update_journal_entry(
    entry_id: str,
    update: JournalEntryUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JournalEntryResponse:
    """Update an existing journal entry."""
    db_entry = await repository.get_journal_entry(session, entry_id)
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if current_user["sub"] != db_entry.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    changes: dict[str, Any] = {}
    if update.title is not None:
        changes["title"] = update.title
    if update.content is not None:
        changes["content"] = update.content
    if update.tags is not None:
        changes["tags"] = update.tags
    if update.mood_score is not None:
        changes["mood_score"] = update.mood_score

    updated = await repository.update_journal_entry(session, entry_id, **changes)
    assert updated is not None
    return _entry_to_response(updated)


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_journal_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a journal entry."""
    db_entry = await repository.get_journal_entry(session, entry_id)
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if current_user["sub"] != db_entry.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await repository.delete_journal_entry(session, entry_id)


@router.get("/journal")
async def list_journal_entries(
    user_id: str = Query(..., description="User ID to list entries for"),
    system: str | None = Query(None, description="Filter by system"),
    entry_type: str | None = Query(None, description="Filter by entry type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JournalListResponse:
    """List journal entries for a user with optional filters.

    Supports filtering by system, entry type, and pagination.
    Results are returned in reverse chronological order.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    offset = (page - 1) * per_page
    entries, total = await repository.list_journal_entries(
        session,
        user_id,
        system=system,
        entry_type=entry_type,
        offset=offset,
        limit=per_page,
    )

    return JournalListResponse(
        entries=[_entry_to_response(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
    )

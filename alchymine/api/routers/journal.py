"""Journal API endpoints — reflective journaling and progress tracking.

Provides CRUD operations for journal entries that capture user
reflections, reframes, gratitude notes, and progress observations
across all five Alchymine systems.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user

router = APIRouter()

# ── In-memory store (swap for DB later) ─────────────────────────────────

_journal_store: dict[str, dict[str, Any]] = {}
"""Module-level dict holding journal entries keyed by entry ID."""


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


# ── Endpoints ───────────────────────────────────────────────────────────


@router.post("/journal", status_code=201)
async def create_journal_entry(
    entry: JournalEntryCreate,
    current_user: dict = Depends(get_current_user),
) -> JournalEntryResponse:
    """Create a new journal entry.

    Supports reflections, cognitive reframes, gratitude notes,
    milestone celebrations, and system-specific insights.
    """
    if current_user["sub"] != entry.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    now = datetime.now(UTC).isoformat()
    entry_id = str(uuid.uuid4())

    record: dict[str, Any] = {
        "id": entry_id,
        "user_id": entry.user_id,
        "system": entry.system,
        "entry_type": entry.entry_type,
        "title": entry.title,
        "content": entry.content,
        "tags": entry.tags,
        "mood_score": entry.mood_score,
        "created_at": now,
        "updated_at": now,
    }

    _journal_store[entry_id] = record

    return JournalEntryResponse(**record)


@router.get("/journal/{entry_id}")
async def get_journal_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
) -> JournalEntryResponse:
    """Retrieve a single journal entry by ID."""
    if entry_id not in _journal_store:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    entry = _journal_store[entry_id]
    if current_user["sub"] != entry["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return JournalEntryResponse(**entry)


@router.put("/journal/{entry_id}")
async def update_journal_entry(
    entry_id: str,
    update: JournalEntryUpdate,
    current_user: dict = Depends(get_current_user),
) -> JournalEntryResponse:
    """Update an existing journal entry."""
    if entry_id not in _journal_store:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    record = _journal_store[entry_id]
    if current_user["sub"] != record["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if update.title is not None:
        record["title"] = update.title
    if update.content is not None:
        record["content"] = update.content
    if update.tags is not None:
        record["tags"] = update.tags
    if update.mood_score is not None:
        record["mood_score"] = update.mood_score

    record["updated_at"] = datetime.now(UTC).isoformat()

    return JournalEntryResponse(**record)


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_journal_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    """Delete a journal entry."""
    if entry_id not in _journal_store:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    record = _journal_store[entry_id]
    if current_user["sub"] != record["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    del _journal_store[entry_id]


@router.get("/journal")
async def list_journal_entries(
    user_id: str = Query(..., description="User ID to list entries for"),
    system: str | None = Query(None, description="Filter by system"),
    entry_type: str | None = Query(None, description="Filter by entry type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
) -> JournalListResponse:
    """List journal entries for a user with optional filters.

    Supports filtering by system, entry type, and pagination.
    Results are returned in reverse chronological order.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Filter entries belonging to the user
    user_entries = [e for e in _journal_store.values() if e["user_id"] == user_id]

    # Apply filters
    if system:
        user_entries = [e for e in user_entries if e["system"] == system]
    if entry_type:
        user_entries = [e for e in user_entries if e["entry_type"] == entry_type]

    # Sort by created_at descending
    user_entries.sort(key=lambda e: e["created_at"], reverse=True)

    total = len(user_entries)

    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    page_entries = user_entries[start:end]

    return JournalListResponse(
        entries=[JournalEntryResponse(**e) for e in page_entries],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/journal/stats/{user_id}")
async def get_journal_stats(
    user_id: str,
    current_user: dict = Depends(get_current_user),
) -> JournalStatsResponse:
    """Get summary statistics for a user's journal.

    Returns entry counts by system and type, average mood score,
    and a list of all tags used.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    user_entries = [e for e in _journal_store.values() if e["user_id"] == user_id]

    if not user_entries:
        return JournalStatsResponse(
            total_entries=0,
            entries_by_system={},
            entries_by_type={},
            average_mood=None,
            streak_days=0,
            tags_used=[],
        )

    # Count by system
    by_system: dict[str, int] = {}
    for entry in user_entries:
        sys = entry["system"]
        by_system[sys] = by_system.get(sys, 0) + 1

    # Count by type
    by_type: dict[str, int] = {}
    for entry in user_entries:
        et = entry["entry_type"]
        by_type[et] = by_type.get(et, 0) + 1

    # Average mood
    moods = [e["mood_score"] for e in user_entries if e.get("mood_score") is not None]
    avg_mood = sum(moods) / len(moods) if moods else None

    # Collect unique tags
    all_tags: set[str] = set()
    for entry in user_entries:
        all_tags.update(entry.get("tags", []))

    # Calculate streak (consecutive days with entries)
    dates = sorted({e["created_at"][:10] for e in user_entries}, reverse=True)
    streak = 0
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if dates and dates[0] == today:
        streak = 1
        for i in range(1, len(dates)):
            prev = datetime.strptime(dates[i - 1], "%Y-%m-%d")  # noqa: DTZ007
            curr = datetime.strptime(dates[i], "%Y-%m-%d")  # noqa: DTZ007
            if (prev - curr).days == 1:
                streak += 1
            else:
                break

    return JournalStatsResponse(
        total_entries=len(user_entries),
        entries_by_system=by_system,
        entries_by_type=by_type,
        average_mood=avg_mood,
        streak_days=streak,
        tags_used=sorted(all_tags),
    )

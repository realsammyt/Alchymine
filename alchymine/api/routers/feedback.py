"""Feedback API endpoints — public submission and admin management.

Endpoints:
- ``POST   /feedback``              — Public: submit feedback (no auth required).
- ``GET    /admin/feedback``        — Admin: paginated list with optional filters.
- ``PATCH  /admin/feedback/{id}``   — Admin: update status and/or admin note.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_admin
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_CATEGORIES = {"general", "bug", "feature", "praise", "other"}
_VALID_STATUSES = {"new", "reviewed", "resolved", "dismissed"}


# ── Request / Response models ────────────────────────────────────────────


class FeedbackCreate(BaseModel):
    """Request body for submitting user feedback."""

    category: str = Field(
        default="general",
        description="Feedback category: general | bug | feature | praise | other",
    )
    message: str = Field(..., min_length=10, max_length=2000, description="Feedback message")
    email: EmailStr | None = Field(default=None, description="Optional contact email")
    page_url: str | None = Field(
        default=None, description="URL of the page feedback was submitted from"
    )

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v: object) -> str:
        """Coerce unrecognised category values to 'general' instead of rejecting."""
        if isinstance(v, str) and v in _VALID_CATEGORIES:
            return v
        return "general"


class FeedbackResponse(BaseModel):
    """A single feedback entry."""

    id: int
    user_id: str | None
    email: str | None
    category: str
    message: str
    status: str
    admin_note: str | None
    page_url: str | None
    created_at: str
    updated_at: str


class FeedbackListResponse(BaseModel):
    """Paginated list of feedback entries."""

    entries: list[FeedbackResponse]
    total: int
    page: int
    per_page: int


class FeedbackPatch(BaseModel):
    """Request body for updating a feedback entry."""

    status: str | None = Field(default=None, description="New status value")
    admin_note: str | None = Field(default=None, max_length=1000, description="Internal admin note")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: object) -> str | None:
        """Reject invalid status values with a clear error message."""
        if v is None:
            return None
        if isinstance(v, str) and v in _VALID_STATUSES:
            return v
        raise ValueError(
            f"Invalid status {v!r}. Must be one of: {', '.join(sorted(_VALID_STATUSES))}"
        )


# ── Helpers ───────────────────────────────────────────────────────────────


def _entry_to_response(entry: object) -> FeedbackResponse:
    """Convert a FeedbackEntry ORM object to FeedbackResponse."""
    created = (
        entry.created_at.isoformat()  # type: ignore[union-attr]
        if hasattr(entry.created_at, "isoformat")  # type: ignore[union-attr]
        else str(entry.created_at)  # type: ignore[union-attr]
    )
    updated = (
        entry.updated_at.isoformat()  # type: ignore[union-attr]
        if hasattr(entry.updated_at, "isoformat")  # type: ignore[union-attr]
        else str(entry.updated_at)  # type: ignore[union-attr]
    )
    return FeedbackResponse(
        id=entry.id,  # type: ignore[union-attr]
        user_id=entry.user_id,  # type: ignore[union-attr]
        email=entry.email,  # type: ignore[union-attr]
        category=entry.category,  # type: ignore[union-attr]
        message=entry.message,  # type: ignore[union-attr]
        status=entry.status,  # type: ignore[union-attr]
        admin_note=entry.admin_note,  # type: ignore[union-attr]
        page_url=entry.page_url,  # type: ignore[union-attr]
        created_at=created,
        updated_at=updated,
    )


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackCreate,
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """Submit user feedback.

    No authentication required — accepts anonymous submissions.
    A notification email is sent to the admin team on a best-effort basis;
    email failure never causes this endpoint to return an error.
    """
    entry = await repository.create_feedback(
        session,
        message=body.message,
        category=body.category,
        email=str(body.email) if body.email is not None else None,
        page_url=body.page_url,
    )
    await session.commit()
    await session.refresh(entry)

    try:
        from alchymine.email import send_feedback_notification_email

        sent = await send_feedback_notification_email(
            category=entry.category,
            message=entry.message,
            email=entry.email,
            entry_id=entry.id,
        )
        if not sent:
            logger.warning("Feedback notification email not sent for entry id=%s", entry.id)
    except Exception:
        logger.warning(
            "Feedback notification email failed for entry id=%s", entry.id, exc_info=True
        )

    return _entry_to_response(entry)


@router.get("/admin/feedback")
async def list_feedback(
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status"),
    category: str | None = Query(default=None, description="Filter by category"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(get_current_admin),
) -> FeedbackListResponse:
    """List feedback entries with optional status and category filters.

    Returns results in reverse chronological order (most recent first).
    """
    offset = (page - 1) * per_page
    entries, total = await repository.list_feedback(
        session,
        status=status_filter,
        category=category,
        offset=offset,
        limit=per_page,
    )
    return FeedbackListResponse(
        entries=[_entry_to_response(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/admin/feedback/{entry_id}")
async def update_feedback(
    entry_id: int,
    body: FeedbackPatch,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(get_current_admin),
) -> FeedbackResponse:
    """Update status and/or admin note on a feedback entry."""
    entry = await repository.update_feedback(
        session,
        entry_id,
        status=body.status,
        admin_note=body.admin_note,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback entry not found",
        )
    await session.commit()
    await session.refresh(entry)
    return _entry_to_response(entry)

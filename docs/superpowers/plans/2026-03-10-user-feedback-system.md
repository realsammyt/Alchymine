# User Feedback System -- Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack user feedback system -- a form accessible from the About page and via a global floating button, a FastAPI backend that stores feedback and notifies the admin by email, and an admin panel view with filtering, status management, and admin notes.

**Architecture:** DB model + Alembic migration -> repository CRUD -> FastAPI router (POST /feedback, GET+PATCH /admin/feedback) -> email notification via Resend -> API client types/functions -> reusable FeedbackForm modal -> global FeedbackButton -> About page CTA section -> admin Feedback page -> admin nav + dashboard metrics update.

**Tech Stack:** SQLAlchemy async, Alembic, FastAPI, Pydantic v2, Resend, Next.js 15 App Router, React 18, TypeScript, Tailwind CSS

---

## File Structure

### New Files

| File                                                                       | Responsibility                                                                  |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `alchymine/db/migrations/versions/2026_03_10_0011_add_feedback_entries.py` | Alembic migration -- creates `feedback_entries` table                           |
| `alchymine/api/routers/feedback.py`                                        | FastAPI router: POST /feedback, GET /admin/feedback, PATCH /admin/feedback/{id} |
| `alchymine/web/src/components/shared/FeedbackForm.tsx`                     | Reusable modal form component                                                   |
| `alchymine/web/src/components/shared/FeedbackButton.tsx`                   | Global floating feedback trigger                                                |
| `alchymine/web/src/app/admin/feedback/page.tsx`                            | Admin feedback list page                                                        |
| `tests/api/test_feedback.py`                                               | pytest tests for feedback router                                                |

### Modified Files

| File                                             | Changes                                                                           |
| ------------------------------------------------ | --------------------------------------------------------------------------------- |
| `alchymine/db/models.py`                         | Add FeedbackEntry ORM model                                                       |
| `alchymine/db/repository.py`                     | Add feedback CRUD functions                                                       |
| `alchymine/email.py`                             | Add send_feedback_notification_email()                                            |
| `alchymine/api/main.py`                          | Import and register feedback router                                               |
| `alchymine/api/routers/__init__.py`              | Export feedback module                                                            |
| `alchymine/web/src/lib/api.ts`                   | Add FeedbackPayload type + submitFeedback(), listAdminFeedback(), patchFeedback() |
| `alchymine/web/src/app/about/page.tsx`           | Add feedback CTA section at bottom                                                |
| `alchymine/web/src/app/admin/layout.tsx`         | Add Feedback nav item to ADMIN_NAV                                                |
| `alchymine/web/src/app/admin/dashboard/page.tsx` | Add feedback metric cards                                                         |
| `alchymine/api/routers/admin.py`                 | Add feedback counts to /admin/analytics/overview                                  |
| `alchymine/web/src/app/layout.tsx`               | Mount FeedbackButton globally (authenticated users)                               |

---

## Sprint 1: Backend -- DB, API, and Email

### Task 1: FeedbackEntry DB Model + Migration

Add the `FeedbackEntry` ORM model to `alchymine/db/models.py` and create the Alembic migration.

**Steps:**

- [ ] Open `alchymine/db/models.py` and add after the `WaitlistEntry` class:

```python
# --- FeedbackEntry ────────────────────────────────────────────────────


class FeedbackEntry(Base):
    """User-submitted feedback entry.

    Status progresses: new -> reviewed -> resolved | dismissed.
    """

    __tablename__ = "feedback_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False, index=True,
        comment="general | bug | feature | praise | other"
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="new", nullable=False, index=True,
        comment="new | reviewed | resolved | dismissed"
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<FeedbackEntry id={self.id!r} category={self.category!r} status={self.status!r}>"
```

- [ ] Create `alchymine/db/migrations/versions/2026_03_10_0011_add_feedback_entries.py`:

```python
"""Add feedback_entries table for user feedback submissions.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("category", sa.String(50), server_default="general", nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("admin_note", sa.Text, nullable=True),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_feedback_entries_user_id", "feedback_entries", ["user_id"])
    op.create_index("ix_feedback_entries_category", "feedback_entries", ["category"])
    op.create_index("ix_feedback_entries_status", "feedback_entries", ["status"])
    op.create_index("ix_feedback_entries_created_at", "feedback_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_entries_created_at", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_status", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_category", table_name="feedback_entries")
    op.drop_index("ix_feedback_entries_user_id", table_name="feedback_entries")
    op.drop_table("feedback_entries")
```

- [ ] Verify migration chain is correct (down_revision matches last migration: `0010`).
- [ ] Run locally to confirm syntax:
  ```bash
  D:/Python/Python311/python.exe -c "import alchymine.db.models; print('OK')"
  ```

**Commit:** `feat(db): add FeedbackEntry model and migration 0011`

---

### Task 2: Repository CRUD Functions

Add feedback CRUD to `alchymine/db/repository.py`.

**Steps:**

- [ ] Add `FeedbackEntry` to the imports block in `repository.py`:

  ```python
  from alchymine.db.models import (
      ...
      FeedbackEntry,
      ...
  )
  ```

- [ ] Add a `# --- Feedback Entries` section at the bottom of `repository.py`:

```python
# --- Feedback Entries ─────────────────────────────────────────────────


async def create_feedback(
    session: AsyncSession,
    *,
    message: str,
    category: str = "general",
    email: str | None = None,
    user_id: str | None = None,
    page_url: str | None = None,
) -> FeedbackEntry:
    """Insert a new feedback entry and return it."""
    entry = FeedbackEntry(
        user_id=user_id,
        email=email,
        category=category,
        message=message,
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
    limit: int = 50,
) -> tuple[list[FeedbackEntry], int]:
    """Return paginated feedback entries with optional filters.

    Returns a (entries, total_count) tuple.
    """
    q = select(FeedbackEntry)
    count_q = select(func.count()).select_from(FeedbackEntry)
    if status:
        q = q.where(FeedbackEntry.status == status)
        count_q = count_q.where(FeedbackEntry.status == status)
    if category:
        q = q.where(FeedbackEntry.category == category)
        count_q = count_q.where(FeedbackEntry.category == category)
    q = q.order_by(FeedbackEntry.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(q)
    total = (await session.execute(count_q)).scalar_one()
    return list(result.scalars().all()), total


async def update_feedback(
    session: AsyncSession,
    entry_id: int,
    *,
    status: str | None = None,
    admin_note: str | None = None,
) -> FeedbackEntry | None:
    """Update status and/or admin_note on a feedback entry.

    Returns the updated entry or None if not found.
    """
    result = await session.execute(
        select(FeedbackEntry).where(FeedbackEntry.id == entry_id)
    )
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
    """Return counts of feedback entries grouped by status."""
    result = await session.execute(
        select(FeedbackEntry.status, func.count(FeedbackEntry.id))
        .group_by(FeedbackEntry.status)
    )
    rows = result.all()
    counts = {row[0]: row[1] for row in rows}
    return {
        "new": counts.get("new", 0),
        "reviewed": counts.get("reviewed", 0),
        "resolved": counts.get("resolved", 0),
        "dismissed": counts.get("dismissed", 0),
        "total": sum(counts.values()),
    }
```

- [ ] Confirm import of `FeedbackEntry` is present and no circular issues:
  ```bash
  D:/Python/Python311/python.exe -c "from alchymine.db import repository; print('OK')"
  ```

**Commit:** `feat(db): add feedback CRUD functions to repository`

---

### Task 3: Feedback API Router

Create `alchymine/api/routers/feedback.py` with public POST and admin GET+PATCH endpoints.

**Steps:**

- [ ] Create `alchymine/api/routers/feedback.py`:

```python
"""Feedback router -- submit and manage user feedback.

Endpoints:
- POST   /feedback               -- public: submit feedback (auth optional)
- GET    /admin/feedback         -- admin: list with filter + pagination
- PATCH  /admin/feedback/{id}    -- admin: update status and note
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_admin, get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import User
from alchymine.email import send_feedback_notification_email

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_CATEGORIES = {"general", "bug", "feature", "praise", "other"}
VALID_STATUSES = {"new", "reviewed", "resolved", "dismissed"}


# --- Schemas ──────────────────────────────────────────────────────────


class FeedbackCreate(BaseModel):
    """Public feedback submission payload."""

    category: str = Field("general", description="general | bug | feature | praise | other")
    message: str = Field(..., min_length=10, max_length=2000)
    email: EmailStr | None = Field(None, description="Optional contact email for anonymous users")
    page_url: str | None = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    """Single feedback entry."""

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
    """Paginated feedback list."""

    entries: list[FeedbackResponse]
    total: int
    page: int
    per_page: int


class FeedbackPatch(BaseModel):
    """Admin update payload."""

    status: str | None = Field(None, description="new | reviewed | resolved | dismissed")
    admin_note: str | None = Field(None, max_length=1000)


# --- Helpers ──────────────────────────────────────────────────────────


def _serialize(entry) -> FeedbackResponse:
    return FeedbackResponse(
        id=entry.id,
        user_id=entry.user_id,
        email=entry.email,
        category=entry.category,
        message=entry.message,
        status=entry.status,
        admin_note=entry.admin_note,
        page_url=entry.page_url,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


# --- Public endpoint ──────────────────────────────────────────────────


async def _maybe_current_user(
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Return the current user if authenticated, otherwise None."""
    try:
        from alchymine.api.auth import get_current_user as _gcu
        # Import inline to avoid circular deps at module load
        return None  # replaced below with optional dependency pattern
    except Exception:
        return None


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback",
)
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    """Accept feedback from any user (auth not required).

    If the category is invalid it is coerced to 'general'.
    """
    category = payload.category if payload.category in VALID_CATEGORIES else "general"

    entry = await repository.create_feedback(
        db,
        message=payload.message,
        category=category,
        email=str(payload.email) if payload.email else None,
        page_url=payload.page_url,
    )
    await db.commit()

    # Fire-and-forget email -- never raises
    try:
        await send_feedback_notification_email(
            category=category,
            message=payload.message,
            email=str(payload.email) if payload.email else None,
            entry_id=entry.id,
        )
    except Exception:
        logger.warning("Feedback email notification failed for entry %s", entry.id)

    return _serialize(entry)


# --- Admin endpoints ──────────────────────────────────────────────────


@router.get(
    "/admin/feedback",
    response_model=FeedbackListResponse,
    summary="List feedback entries (admin)",
)
async def list_feedback(
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(get_current_admin),
) -> FeedbackListResponse:
    """Paginated feedback list with optional status and category filters."""
    offset = (page - 1) * per_page
    entries, total = await repository.list_feedback(
        db,
        status=status_filter,
        category=category,
        offset=offset,
        limit=per_page,
    )
    return FeedbackListResponse(
        entries=[_serialize(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch(
    "/admin/feedback/{entry_id}",
    response_model=FeedbackResponse,
    summary="Update feedback status or admin note (admin)",
)
async def patch_feedback(
    entry_id: int,
    payload: FeedbackPatch,
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(get_current_admin),
) -> FeedbackResponse:
    """Update the status and/or admin note on a feedback entry."""
    if payload.status and payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    entry = await repository.update_feedback(
        db, entry_id, status=payload.status, admin_note=payload.admin_note
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    await db.commit()
    return _serialize(entry)
```

- [ ] Add `feedback` to `alchymine/api/routers/__init__.py` exports (check what pattern that file uses -- may just need to create the import in main.py).

- [ ] Register the router in `alchymine/api/main.py`. Add to imports:

  ```python
  from alchymine.api.routers import (
      ...
      feedback,
      ...
  )
  ```

  And below the other `app.include_router` calls:

  ```python
  app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
  ```

- [ ] Lint and type-check:
  ```bash
  ruff check alchymine/api/routers/feedback.py
  ruff format --check alchymine/api/routers/feedback.py
  ```

**Commit:** `feat(api): add feedback router with public POST and admin GET+PATCH`

---

### Task 4: Email Notification

Add `send_feedback_notification_email()` to `alchymine/email.py`.

**Steps:**

- [ ] Append to `alchymine/email.py` (after the last existing function):

```python
async def send_feedback_notification_email(
    *,
    category: str,
    message: str,
    email: str | None,
    entry_id: int,
) -> bool:
    """Notify the admin email address when new feedback is submitted.

    Returns True on successful delivery, False otherwise.
    Never raises.
    """
    settings = get_settings()
    admin_url = f"{settings.frontend_url}/admin/feedback"
    sender_line = f"From: {email}" if email else "Anonymous submission"

    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set -- skipping feedback notification #%s", entry_id)
        return False

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [settings.email_from],  # notify the admin address
                "subject": f"[Alchymine Feedback] New {category} submission #{entry_id}",
                "html": (
                    "<div style='font-family: sans-serif; max-width: 560px; margin: 0 auto;'>"
                    "<h2 style='color: #1a1a2e;'>New Feedback Received</h2>"
                    f"<p><strong>Category:</strong> {category}</p>"
                    f"<p><strong>{sender_line}</strong></p>"
                    f"<p style='background:#f5f5f5; padding:12px; border-radius:6px;'>{message}</p>"
                    f"<p><a href='{admin_url}' style='display:inline-block; padding:10px 20px; "
                    "background:#1a1a2e; color:#fff; text-decoration:none; border-radius:6px;'>"
                    "View in Admin Panel</a></p>"
                    "</div>"
                ),
            }
        )
        logger.info("Feedback notification sent for entry #%s", entry_id)
        return True
    except Exception as exc:
        logger.error("Failed to send feedback notification #%s: %s", entry_id, exc)
        return False
```

- [ ] Lint:
  ```bash
  ruff check alchymine/email.py
  ruff format --check alchymine/email.py
  ```

**Commit:** `feat(email): add send_feedback_notification_email()`

---

### Task 5: Write Backend Tests

Create `tests/api/test_feedback.py` covering the three endpoints.

**Steps:**

- [ ] Create `tests/api/test_feedback.py` following the existing test patterns:

```python
"""Tests for the feedback API router."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_feedback_anonymous(client: AsyncClient) -> None:
    """Anonymous users can submit feedback without authentication."""
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "bug", "message": "This is a test bug report for the system."},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "bug"
    assert data["status"] == "new"
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_submit_feedback_with_email(client: AsyncClient) -> None:
    """Feedback with optional contact email is accepted."""
    resp = await client.post(
        "/api/v1/feedback",
        json={
            "category": "feature",
            "message": "Please add dark mode to the dashboard.",
            "email": "tester@example.com",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "tester@example.com"


@pytest.mark.asyncio
async def test_submit_feedback_invalid_category_coerced(client: AsyncClient) -> None:
    """Invalid category is coerced to 'general'."""
    resp = await client.post(
        "/api/v1/feedback",
        json={"category": "notreal", "message": "Testing category coercion behavior."},
    )
    assert resp.status_code == 201
    assert resp.json()["category"] == "general"


@pytest.mark.asyncio
async def test_submit_feedback_message_too_short(client: AsyncClient) -> None:
    """Message shorter than 10 chars is rejected."""
    resp = await client.post(
        "/api/v1/feedback",
        json={"message": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_list_feedback(client: AsyncClient, admin_auth_headers: dict) -> None:
    """Admin can list all feedback entries."""
    # seed one entry
    await client.post(
        "/api/v1/feedback",
        json={"category": "praise", "message": "The app is wonderful to use."},
    )
    resp = await client.get("/api/v1/admin/feedback", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_admin_list_feedback_filter_by_status(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    """Admin can filter feedback by status."""
    resp = await client.get(
        "/api/v1/admin/feedback?status=new", headers=admin_auth_headers
    )
    assert resp.status_code == 200
    for entry in resp.json()["entries"]:
        assert entry["status"] == "new"


@pytest.mark.asyncio
async def test_admin_patch_feedback_status(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    """Admin can update feedback status and add a note."""
    create_resp = await client.post(
        "/api/v1/feedback",
        json={"category": "bug", "message": "Something broke on the intake page."},
    )
    entry_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/admin/feedback/{entry_id}",
        json={"status": "reviewed", "admin_note": "Triaged and added to backlog."},
        headers=admin_auth_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["status"] == "reviewed"
    assert data["admin_note"] == "Triaged and added to backlog."


@pytest.mark.asyncio
async def test_admin_patch_feedback_invalid_status(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    """Admin patch with invalid status returns 422."""
    create_resp = await client.post(
        "/api/v1/feedback",
        json={"category": "other", "message": "This is a general feedback message."},
    )
    entry_id = create_resp.json()["id"]
    patch_resp = await client.patch(
        f"/api/v1/admin/feedback/{entry_id}",
        json={"status": "notvalid"},
        headers=admin_auth_headers,
    )
    assert patch_resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_list_requires_auth(client: AsyncClient) -> None:
    """Unauthenticated request to admin feedback returns 401."""
    resp = await client.get("/api/v1/admin/feedback")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_patch_requires_auth(client: AsyncClient) -> None:
    """Unauthenticated patch to admin feedback returns 401."""
    resp = await client.patch("/api/v1/admin/feedback/1", json={"status": "reviewed"})
    assert resp.status_code == 401
```

- [ ] Run the new tests:
  ```bash
  CELERY_ALWAYS_EAGER=true D:/Python/Python311/python.exe -m pytest tests/api/test_feedback.py -v
  ```
- [ ] Run full lint + format check:
  ```bash
  ruff check alchymine/
  ruff format --check alchymine/
  ```

**Commit:** `test(api): add feedback router tests`

---

## Sprint 2: Frontend -- Form, Button, About Page

### Task 6: FeedbackForm Modal Component

Create the reusable modal form at `alchymine/web/src/components/shared/FeedbackForm.tsx`.

**Steps:**

- [ ] Create `alchymine/web/src/components/shared/FeedbackForm.tsx`:

```tsx
"use client";

import { useState } from "react";
import { submitFeedback } from "@/lib/api";

const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "bug", label: "Bug Report" },
  { value: "feature", label: "Feature Request" },
  { value: "praise", label: "Praise" },
  { value: "other", label: "Other" },
];

interface FeedbackFormProps {
  isOpen: boolean;
  onClose: () => void;
  pageUrl?: string;
}

export default function FeedbackForm({
  isOpen,
  onClose,
  pageUrl,
}: FeedbackFormProps) {
  const [category, setCategory] = useState("general");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await submitFeedback({
        category,
        message,
        email: email || undefined,
        page_url: pageUrl,
      });
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setSubmitted(false);
    setMessage("");
    setEmail("");
    setCategory("general");
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-surface border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {submitted ? (
          <div className="text-center py-8">
            <p className="text-2xl mb-3">Thank you</p>
            <p className="text-text/60 font-body">
              Your feedback helps improve Alchymine for everyone.
            </p>
            <button
              onClick={handleClose}
              className="mt-6 px-6 py-2 bg-primary/10 text-primary rounded-lg text-sm hover:bg-primary/20 transition-colors"
            >
              Close
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display text-lg text-text">Share Feedback</h2>
              <button
                onClick={handleClose}
                className="text-text/40 hover:text-text/80 transition-colors"
                aria-label="Close feedback form"
              >
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-text/50 mb-1 font-body uppercase tracking-wide">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-text/50 mb-1 font-body uppercase tracking-wide">
                  Message
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={4}
                  required
                  minLength={10}
                  maxLength={2000}
                  placeholder="Tell us what's on your mind..."
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder-text/30 focus:outline-none focus:border-primary/50 resize-none"
                />
              </div>

              <div>
                <label className="block text-xs text-text/50 mb-1 font-body uppercase tracking-wide">
                  Email (optional)
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="reply@example.com"
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder-text/30 focus:outline-none focus:border-primary/50"
                />
              </div>

              {error && (
                <p className="text-red-400 text-sm font-body">{error}</p>
              )}

              <button
                type="submit"
                disabled={submitting || message.length < 10}
                className="w-full py-2.5 bg-primary text-white rounded-lg text-sm font-body font-medium hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? "Sending..." : "Send Feedback"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] Lint: `npm run lint` from `alchymine/web/`
- [ ] Type-check: `npm run type-check` from `alchymine/web/`

**Commit:** `feat(web): add FeedbackForm modal component`

---

### Task 7: FeedbackButton Global Floating Trigger

Create `alchymine/web/src/components/shared/FeedbackButton.tsx`.

**Steps:**

- [ ] Create `alchymine/web/src/components/shared/FeedbackButton.tsx`:

```tsx
"use client";

import { useState } from "react";
import FeedbackForm from "./FeedbackForm";

export default function FeedbackButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-2.5 bg-surface border border-white/10 rounded-full shadow-lg text-sm font-body text-text/70 hover:text-text hover:border-white/20 transition-all hover:shadow-xl"
        aria-label="Open feedback form"
      >
        <svg
          className="w-4 h-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        Feedback
      </button>

      <FeedbackForm
        isOpen={open}
        onClose={() => setOpen(false)}
        pageUrl={
          typeof window !== "undefined" ? window.location.href : undefined
        }
      />
    </>
  );
}
```

**Commit:** `feat(web): add global FeedbackButton floating trigger`

---

### Task 8: API Client + About Page CTA + Layout Mount

Wire up the API client functions, add the About page CTA, and mount `FeedbackButton` globally.

**Steps:**

- [ ] Add feedback types and API functions to `alchymine/web/src/lib/api.ts`. Append after the last export:

```typescript
// --- Feedback ─────────────────────────────────────────────────────────

export interface FeedbackPayload {
  category?: string;
  message: string;
  email?: string;
  page_url?: string;
}

export interface FeedbackEntry {
  id: number;
  user_id: string | null;
  email: string | null;
  category: string;
  message: string;
  status: string;
  admin_note: string | null;
  page_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackListResponse {
  entries: FeedbackEntry[];
  total: number;
  page: number;
  per_page: number;
}

export async function submitFeedback(
  payload: FeedbackPayload,
): Promise<FeedbackEntry> {
  const res = await fetch(`${BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`feedback submit failed: ${res.status}`);
  return res.json();
}

export async function listAdminFeedback(
  token: string,
  params: {
    status?: string;
    category?: string;
    page?: number;
    per_page?: number;
  } = {},
): Promise<FeedbackListResponse> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.category) qs.set("category", params.category);
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  const res = await fetch(`${BASE}/admin/feedback?${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`admin feedback list failed: ${res.status}`);
  return res.json();
}

export async function patchFeedback(
  token: string,
  entryId: number,
  payload: { status?: string; admin_note?: string },
): Promise<FeedbackEntry> {
  const res = await fetch(`${BASE}/admin/feedback/${entryId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`admin feedback patch failed: ${res.status}`);
  return res.json();
}
```

- [ ] Add a CTA section to `alchymine/web/src/app/about/page.tsx` (insert before the closing `</main>` or as the last content section):

```tsx
{
  /* Feedback CTA */
}
<section className="mt-16 text-center">
  <h2 className="font-display text-2xl text-text mb-3">Help Shape Alchymine</h2>
  <p className="text-text/60 font-body max-w-md mx-auto mb-6">
    Share a bug report, a feature idea, or just let us know how the journey is
    going.
  </p>
  <FeedbackFormCTA />
</section>;
```

Create a small `FeedbackFormCTA` client component inline or as a sibling file that renders `FeedbackForm` with a button trigger (since `about/page.tsx` may be a server component, use `"use client"` wrapper or a small client component).

- [ ] Mount `FeedbackButton` in `alchymine/web/src/app/layout.tsx`. In the body (after `{children}`):

```tsx
import FeedbackButton from "@/components/shared/FeedbackButton";

// Inside <body> after {children}:
<FeedbackButton />;
```

- [ ] Type-check and lint:
  ```bash
  cd alchymine/web && npm run type-check && npm run lint
  ```

**Commit:** `feat(web): add feedback API client, About CTA, and global FeedbackButton mount`

---

## Sprint 3: Admin Panel

### Task 9: Admin Feedback Page

Create `alchymine/web/src/app/admin/feedback/page.tsx` -- list view with filtering and status management.

**Steps:**

- [ ] Create `alchymine/web/src/app/admin/feedback/page.tsx`:

```tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/hooks/useAuth";
import { listAdminFeedback, patchFeedback, FeedbackEntry } from "@/lib/api";

const STATUS_OPTIONS = ["all", "new", "reviewed", "resolved", "dismissed"];
const CATEGORY_OPTIONS = [
  "all",
  "general",
  "bug",
  "feature",
  "praise",
  "other",
];

const STATUS_BADGE: Record<string, string> = {
  new: "bg-blue-500/20 text-blue-300",
  reviewed: "bg-yellow-500/20 text-yellow-300",
  resolved: "bg-green-500/20 text-green-300",
  dismissed: "bg-white/10 text-text/40",
};

export default function AdminFeedbackPage() {
  const { token } = useAuth();
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<FeedbackEntry | null>(null);
  const [noteInput, setNoteInput] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await listAdminFeedback(token, {
        status: statusFilter !== "all" ? statusFilter : undefined,
        category: categoryFilter !== "all" ? categoryFilter : undefined,
        page,
        per_page: 25,
      });
      setEntries(data.entries);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, categoryFilter, page]);

  useEffect(() => {
    load();
  }, [load]);

  const handleStatusChange = async (
    entry: FeedbackEntry,
    newStatus: string,
  ) => {
    if (!token) return;
    setSaving(true);
    try {
      const updated = await patchFeedback(token, entry.id, {
        status: newStatus,
      });
      setEntries((prev) =>
        prev.map((e) => (e.id === updated.id ? updated : e)),
      );
      if (selected?.id === updated.id) setSelected(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNote = async () => {
    if (!token || !selected) return;
    setSaving(true);
    try {
      const updated = await patchFeedback(token, selected.id, {
        admin_note: noteInput,
      });
      setEntries((prev) =>
        prev.map((e) => (e.id === updated.id ? updated : e)),
      );
      setSelected(updated);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl text-text">Feedback</h1>
        <span className="text-sm text-text/40 font-body">{total} total</span>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-white/10 rounded-lg px-3 py-1.5 text-sm text-text"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "all" ? "All statuses" : s}
            </option>
          ))}
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => {
            setCategoryFilter(e.target.value);
            setPage(1);
          }}
          className="bg-surface border border-white/10 rounded-lg px-3 py-1.5 text-sm text-text"
        >
          {CATEGORY_OPTIONS.map((c) => (
            <option key={c} value={c}>
              {c === "all" ? "All categories" : c}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-surface border border-white/5 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-text/40 font-body">
            Loading...
          </div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-text/40 font-body">
            No feedback found.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-left">
                <th className="px-4 py-3 text-text/40 font-body font-normal">
                  Date
                </th>
                <th className="px-4 py-3 text-text/40 font-body font-normal">
                  Category
                </th>
                <th className="px-4 py-3 text-text/40 font-body font-normal">
                  Message
                </th>
                <th className="px-4 py-3 text-text/40 font-body font-normal">
                  Status
                </th>
                <th className="px-4 py-3 text-text/40 font-body font-normal">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="hover:bg-white/2 cursor-pointer"
                  onClick={() => {
                    setSelected(entry);
                    setNoteInput(entry.admin_note ?? "");
                  }}
                >
                  <td className="px-4 py-3 text-text/50 whitespace-nowrap font-body">
                    {new Date(entry.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-text/70 font-body capitalize">
                    {entry.category}
                  </td>
                  <td className="px-4 py-3 text-text max-w-xs truncate font-body">
                    {entry.message}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-body ${STATUS_BADGE[entry.status] ?? "bg-white/5 text-text/50"}`}
                    >
                      {entry.status}
                    </span>
                  </td>
                  <td
                    className="px-4 py-3"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <select
                      value={entry.status}
                      onChange={(e) =>
                        handleStatusChange(entry, e.target.value)
                      }
                      disabled={saving}
                      className="bg-black/30 border border-white/10 rounded px-2 py-1 text-xs text-text"
                    >
                      {["new", "reviewed", "resolved", "dismissed"].map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > 25 && (
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm bg-surface border border-white/10 rounded-lg disabled:opacity-40"
          >
            Prev
          </button>
          <span className="px-3 py-1 text-sm text-text/40 font-body">
            Page {page}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page * 25 >= total}
            className="px-3 py-1 text-sm bg-surface border border-white/10 rounded-lg disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-y-0 right-0 w-96 bg-surface border-l border-white/10 p-6 overflow-y-auto z-40 shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-lg">Feedback #{selected.id}</h3>
            <button
              onClick={() => setSelected(null)}
              className="text-text/40 hover:text-text"
            >
              <svg
                className="w-5 h-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          <dl className="space-y-3 text-sm font-body">
            <div>
              <dt className="text-text/40 uppercase text-xs tracking-wide">
                Category
              </dt>
              <dd className="text-text capitalize">{selected.category}</dd>
            </div>
            <div>
              <dt className="text-text/40 uppercase text-xs tracking-wide">
                Email
              </dt>
              <dd className="text-text">{selected.email ?? "Anonymous"}</dd>
            </div>
            <div>
              <dt className="text-text/40 uppercase text-xs tracking-wide">
                Message
              </dt>
              <dd className="text-text/80 whitespace-pre-wrap">
                {selected.message}
              </dd>
            </div>
            {selected.page_url && (
              <div>
                <dt className="text-text/40 uppercase text-xs tracking-wide">
                  Page
                </dt>
                <dd className="text-text/60 text-xs break-all">
                  {selected.page_url}
                </dd>
              </div>
            )}
            <div>
              <dt className="text-text/40 uppercase text-xs tracking-wide mb-1">
                Admin Note
              </dt>
              <textarea
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                rows={3}
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-text resize-none"
                placeholder="Add an internal note..."
              />
              <button
                onClick={handleSaveNote}
                disabled={saving}
                className="mt-2 px-4 py-1.5 bg-primary/10 text-primary text-sm rounded-lg hover:bg-primary/20 disabled:opacity-40 transition-colors"
              >
                {saving ? "Saving..." : "Save Note"}
              </button>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}
```

- [ ] Add `Feedback` to the `ADMIN_NAV` array in `alchymine/web/src/app/admin/layout.tsx`:

```typescript
// In the ADMIN_NAV array, add after Waitlist:
{ name: "Feedback", href: "/admin/feedback", icon: "chat" },
```

Add a `case "chat":` to the `AdminIcon` switch:

```tsx
case "chat":
  return (
    <svg
      className={base}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
```

- [ ] Lint and type-check:
  ```bash
  cd alchymine/web && npm run type-check && npm run lint
  ```

**Commit:** `feat(web): add admin feedback page with filtering and status management`

---

### Task 10: Dashboard Metrics Update

Expose feedback counts in the admin analytics endpoint and show metric cards on the dashboard.

**Steps:**

- [ ] In `alchymine/api/routers/admin.py`, add to the analytics overview endpoint. Import `FeedbackEntry`:

  ```python
  from alchymine.db.models import AdminAuditLog, FeedbackEntry, InviteCode, JournalEntry, Report, User, WaitlistEntry
  ```

  Inside the `GET /admin/analytics/overview` handler, add a feedback count query alongside the existing queries:

  ```python
  feedback_new_count = (
      await db.execute(
          select(func.count(FeedbackEntry.id)).where(FeedbackEntry.status == "new")
      )
  ).scalar_one()
  feedback_total_count = (
      await db.execute(select(func.count(FeedbackEntry.id)))
  ).scalar_one()
  ```

  Include `feedback_new` and `feedback_total` in the response dict.

- [ ] In `alchymine/web/src/app/admin/dashboard/page.tsx`, add feedback metric cards after the existing stat cards. Fetch the analytics data and surface `feedback_new` and `feedback_total` alongside existing metrics.

- [ ] Lint, type-check, and run tests:
  ```bash
  ruff check alchymine/api/routers/admin.py
  ruff format --check alchymine/api/routers/admin.py
  cd alchymine/web && npm run type-check && npm run lint
  CELERY_ALWAYS_EAGER=true D:/Python/Python311/python.exe -m pytest tests/api/ -v
  ```

**Commit:** `feat(admin): add feedback metrics to analytics overview and dashboard`

---

## Final Validation

Run the complete local pre-push checklist before opening a PR:

```bash
# Python checks
ruff check alchymine/
ruff format --check alchymine/
mypy alchymine/
CELERY_ALWAYS_EAGER=true D:/Python/Python311/python.exe -m pytest tests/ -v

# Frontend checks
cd alchymine/web && npm run type-check && npm run lint && npm run build
```

Expected outcomes:

- [ ] `ruff check` exits 0
- [ ] `ruff format --check` exits 0
- [ ] `mypy` exits 0
- [ ] All pytest tests pass (including 10 new feedback tests)
- [ ] `npm run type-check` exits 0
- [ ] `npm run build` succeeds

**Final PR commit:** `feat: add full-stack user feedback system`

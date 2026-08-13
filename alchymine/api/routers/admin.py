"""Admin router — user management, invite codes, and analytics endpoints.

Endpoints:
- ``GET    /admin/users``                    — Paginated user list.
- ``GET    /admin/users/{user_id}``          — User detail with profile presence flags.
- ``PATCH  /admin/users/{user_id}/status``   — Enable/disable a user account.
- ``PATCH  /admin/users/{user_id}/admin``    — Grant or revoke admin privileges.
- ``GET    /admin/invite-codes``             — Paginated invite code list.
- ``POST   /admin/invite-codes``             — Create a single invite code.
- ``POST   /admin/invite-codes/bulk``        — Bulk-create N invite codes.
- ``PATCH  /admin/invite-codes/{code_id}``   — Update an invite code.
- ``DELETE /admin/invite-codes/{code_id}``   — Hard-delete an unused invite code.
- ``GET    /admin/analytics/overview``       — Aggregate platform stats.
- ``GET    /admin/analytics/users``          — Daily new-user counts.
- ``GET    /admin/usage``                    — Spend, gate state, and top spenders.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Case, asc, case, desc, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload

from alchymine.api.auth import get_current_admin
from alchymine.api.deps import get_db_session
from alchymine.config import get_settings
from alchymine.db.models import (
    AdminAuditLog,
    FeedbackEntry,
    InviteCode,
    JournalEntry,
    Report,
    UsageRecord,
    User,
    WaitlistEntry,
)
from alchymine.db.usage_counters import (
    GLOBAL_SCOPE,
    METER_LLM_CALLS,
    current_month_key,
    current_period_key,
    get_count,
)
from alchymine.email import send_invitation_email
from alchymine.llm.ledger import UNATTRIBUTED_SCOPE
from alchymine.safety.audit import AuditEventType
from alchymine.safety.audit import log_event as safety_log_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")

# ─── Database Session Dependency ──────────────────────────────────────────
# Uses the centralized get_db_session from alchymine.api.deps.
# Alias kept for backward compatibility with tests that import get_db.
get_db = get_db_session


# ─── Audit Log Helper ─────────────────────────────────────────────────────


async def _audit(
    db: AsyncSession,
    admin_id: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """Write an audit log entry to the DB and the in-memory safety audit log.

    The DB-backed AdminAuditLog provides persistent, queryable admin audit
    history.  The safety audit module's in-memory log provides a unified
    view of all safety-relevant events (admin actions included) for real-time
    monitoring and stats.
    """
    db.add(
        AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
    await db.flush()

    # Mirror to safety audit log for unified monitoring
    safety_log_event(
        event_type=AuditEventType.FINANCIAL_DATA_ACCESS,
        system="admin",
        summary=f"Admin action: {action}",
        user_id=admin_id,
        metadata={
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            **(detail or {}),
        },
    )


# ─── Pydantic Schemas ────────────────────────────────────────────────────


class AdminUserResponse(BaseModel):
    """Summary user record returned from paginated list."""

    id: str
    email: str | None
    is_admin: bool
    is_active: bool
    created_at: str
    last_login_at: str | None
    invite_code_used: str | None


class AdminUserDetailResponse(AdminUserResponse):
    """Detailed user record including profile presence flags."""

    version: str
    updated_at: str
    has_intake: bool
    has_identity: bool
    has_healing: bool
    has_wealth: bool
    has_creative: bool
    has_perspective: bool


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users."""

    users: list[AdminUserResponse]
    total: int
    page: int
    per_page: int


class StatusUpdateRequest(BaseModel):
    """Request body for enabling or disabling a user account."""

    is_active: bool


class AdminToggleRequest(BaseModel):
    """Request body for granting or revoking admin privileges."""

    is_admin: bool


class CreateInviteCodeRequest(BaseModel):
    """Request body for creating a single invite code."""

    code: str | None = None  # Auto-generate if not provided
    max_uses: int = Field(default=1, ge=1, le=10000)
    expires_at: str | None = None  # ISO 8601
    note: str | None = Field(default=None, max_length=255)


class BulkCreateInviteCodesRequest(BaseModel):
    """Request body for bulk-creating invite codes."""

    count: int = Field(..., ge=1, le=100)
    max_uses: int = Field(default=1, ge=1, le=10000)
    expires_at: str | None = None
    note: str | None = Field(default=None, max_length=255)


class InviteCodeResponse(BaseModel):
    """Invite code record."""

    id: int
    code: str
    created_by: str | None
    max_uses: int
    uses_count: int
    expires_at: str | None
    is_active: bool
    note: str | None
    created_at: str
    updated_at: str


class PaginatedInviteCodesResponse(BaseModel):
    """Paginated list of invite codes."""

    codes: list[InviteCodeResponse]
    total: int
    page: int
    per_page: int


class UpdateInviteCodeRequest(BaseModel):
    """Request body for updating an invite code."""

    is_active: bool | None = None
    max_uses: int | None = Field(default=None, ge=1)
    expires_at: str | None = None
    note: str | None = Field(default=None, max_length=255)


class AnalyticsOverviewResponse(BaseModel):
    """Aggregate platform statistics."""

    total_users: int
    active_users: int
    admin_users: int
    new_users_today: int
    new_users_week: int
    new_users_month: int
    total_invite_codes: int
    active_invite_codes: int
    total_reports: int
    total_journal_entries: int
    feedback_new: int
    feedback_total: int


class DailyUserCount(BaseModel):
    """New-user count for a single calendar date."""

    date: str
    count: int


class UserAnalyticsResponse(BaseModel):
    """Daily new-user counts over a period."""

    daily_counts: list[DailyUserCount]
    period_days: int


class InviteUserRequest(BaseModel):
    """Request body for inviting one or more users by email."""

    emails: list[EmailStr] = Field(..., min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=255)
    expires_in_days: int = Field(default=7, ge=1, le=90)


class InviteUserResult(BaseModel):
    """Result for a single email invitation."""

    email: str
    invite_code: str
    email_sent: bool


class InviteUsersResponse(BaseModel):
    """Response containing results for all invited emails."""

    results: list[InviteUserResult]
    total_invited: int
    total_emails_sent: int


class WaitlistEntryResponse(BaseModel):
    """Single waitlist entry record."""

    id: int
    email: str
    status: str
    invite_code_id: int | None
    notes: str | None
    created_at: str
    updated_at: str


class PaginatedWaitlistResponse(BaseModel):
    """Paginated list of waitlist entries."""

    entries: list[WaitlistEntryResponse]
    total: int
    page: int
    per_page: int


class InviteWaitlistRequest(BaseModel):
    """Request body for inviting selected waitlist entries."""

    entry_ids: list[int] = Field(..., min_length=1)
    expires_in_days: int = Field(default=7, ge=1, le=90)


class WaitlistInviteResult(BaseModel):
    """Result for a single waitlist entry invitation."""

    entry_id: int
    email: str
    invite_code: str
    email_sent: bool


class InviteWaitlistResponse(BaseModel):
    """Response for waitlist invite action."""

    results: list[WaitlistInviteResult]
    total_invited: int
    total_emails_sent: int
    total_skipped: int


class UsageSurfaceRow(BaseModel):
    """What one product surface cost inside a window."""

    surface: str
    calls: int
    cost_micros: int
    cost_cents: int


class UsageModelRow(BaseModel):
    """What one model cost inside a window, with the tokens behind it."""

    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    cost_micros: int


class UsageSurfaceBreakdown(BaseModel):
    """The per-surface rollup, for both windows."""

    today: list[UsageSurfaceRow]
    month: list[UsageSurfaceRow]


class UsageModelBreakdown(BaseModel):
    """The per-model rollup, for both windows."""

    today: list[UsageModelRow]
    month: list[UsageModelRow]


class UsageTodayBlock(BaseModel):
    """The day: what it cost, and how close the two breakers are to tripping."""

    period_key: str
    spend_micros: int
    spend_cents: int
    ceiling_micros: int
    # Negative when the day went past its ceiling. Reported rather than
    # clamped: an overshoot is bounded by concurrency, not by one call, and
    # hiding it behind a floor of zero would make the two look identical.
    remaining_micros: int
    llm_calls: int
    llm_call_ceiling: int
    record_count: int
    # The denominator matters. A count with nothing to compare it against
    # cannot answer the question section 6.2 asks: is the estimated share
    # more than a few percent, and does the disconnect path need a look.
    estimated_record_count: int


class UsageMonthBlock(BaseModel):
    """The month against the budget. Nothing here stops anything."""

    month_key: str
    spend_micros: int
    spend_cents: int
    budget_micros: int
    remaining_micros: int
    pct_of_budget: float


class UsageTopUserRow(BaseModel):
    """One account's month-to-date spend, against what its plan funds."""

    user_id: str
    email: str | None
    plan: str
    calls: int
    cost_micros: int
    cost_cents: int
    allowance_cents: int
    pct_of_allowance: float


class AdminUsageResponse(BaseModel):
    """Spend and gate state, for the human who decides what to do about it."""

    as_of: str
    today: UsageTodayBlock
    month: UsageMonthBlock
    by_surface: UsageSurfaceBreakdown
    by_model: UsageModelBreakdown
    top_users: list[UsageTopUserRow]


# ─── Helpers ─────────────────────────────────────────────────────────────


def _invite_code_response(code: InviteCode) -> InviteCodeResponse:
    """Convert an InviteCode ORM object to its response schema."""
    return InviteCodeResponse(
        id=code.id,
        code=code.code,
        created_by=code.created_by,
        max_uses=code.max_uses,
        uses_count=code.uses_count,
        expires_at=str(code.expires_at) if code.expires_at is not None else None,
        is_active=code.is_active,
        note=code.note,
        created_at=str(code.created_at),
        updated_at=str(code.updated_at),
    )


def _waitlist_entry_response(entry: WaitlistEntry) -> WaitlistEntryResponse:
    """Convert a WaitlistEntry ORM object to its response schema."""
    return WaitlistEntryResponse(
        id=entry.id,
        email=entry.email,
        status=entry.status,
        invite_code_id=entry.invite_code_id,
        notes=entry.notes,
        created_at=str(entry.created_at),
        updated_at=str(entry.updated_at),
    )


def _parse_expires_at(value: str | None) -> datetime | None:
    """Parse an ISO 8601 expires_at string into a timezone-aware datetime."""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid expires_at format: {value!r}. Expected ISO 8601.",
        ) from exc


# ─── User Management Endpoints ───────────────────────────────────────────


@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    search: str = Query(default=""),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PaginatedUsersResponse:
    """Return a paginated list of users with optional filtering and sorting."""
    query = select(User)

    if search:
        query = query.where(User.email.ilike(f"%{search}%"))  # type: ignore[union-attr]

    if active_only:
        query = query.where(User.is_active.is_(True))  # type: ignore[union-attr]

    # Total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Sorting — validate against allowlist to prevent attribute injection
    _ALLOWED_SORT_COLUMNS = {"created_at", "email", "is_admin", "is_active", "last_login_at"}
    if sort_by not in _ALLOWED_SORT_COLUMNS:
        sort_by = "created_at"
    sort_col = getattr(User, sort_by, User.created_at)
    order_fn = desc if sort_order.lower() == "desc" else asc
    query = query.order_by(order_fn(sort_col))

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedUsersResponse(
        users=[
            AdminUserResponse(
                id=u.id,
                email=u.email,
                is_admin=u.is_admin,
                is_active=u.is_active,
                created_at=str(u.created_at),
                last_login_at=str(u.last_login_at) if u.last_login_at is not None else None,
                invite_code_used=u.invite_code_used,
            )
            for u in users
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminUserDetailResponse:
    """Return detailed information for a single user including profile presence flags."""
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.intake),
            selectinload(User.identity),
            selectinload(User.healing),
            selectinload(User.wealth),
            selectinload(User.creative),
            selectinload(User.perspective),
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return AdminUserDetailResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=str(user.created_at),
        last_login_at=str(user.last_login_at) if user.last_login_at is not None else None,
        invite_code_used=user.invite_code_used,
        version=user.version,
        updated_at=str(user.updated_at),
        has_intake=user.intake is not None,
        has_identity=user.identity is not None,
        has_healing=user.healing is not None,
        has_wealth=user.wealth is not None,
        has_creative=user.creative is not None,
        has_perspective=user.perspective is not None,
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: str,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserResponse:
    """Enable or disable a user account.

    An admin cannot disable their own account.
    """
    if user_id == admin.id and not body.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot disable your own account.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    previous_status = user.is_active
    user.is_active = body.is_active

    await _audit(
        db,
        admin_id=admin.id,
        action="update_user_status",
        target_type="user",
        target_id=user_id,
        detail={"previous": previous_status, "new": body.is_active},
    )
    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=str(user.created_at),
        last_login_at=str(user.last_login_at) if user.last_login_at is not None else None,
        invite_code_used=user.invite_code_used,
    )


@router.patch("/users/{user_id}/admin", response_model=AdminUserResponse)
async def update_user_admin(
    user_id: str,
    body: AdminToggleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AdminUserResponse:
    """Grant or revoke admin privileges for a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    previous_admin = user.is_admin
    user.is_admin = body.is_admin

    await _audit(
        db,
        admin_id=admin.id,
        action="update_user_admin",
        target_type="user",
        target_id=user_id,
        detail={"previous": previous_admin, "new": body.is_admin},
    )
    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=str(user.created_at),
        last_login_at=str(user.last_login_at) if user.last_login_at is not None else None,
        invite_code_used=user.invite_code_used,
    )


# ─── Invite by Email ─────────────────────────────────────────────────────


@router.post("/invite", response_model=InviteUsersResponse, status_code=status.HTTP_201_CREATED)
async def invite_users_by_email(
    body: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> InviteUsersResponse:
    """Invite one or more users by email.

    For each email address:
    1. Creates a single-use invite code (expires after ``expires_in_days``).
    2. Sends an invitation email with a registration link (fire-and-forget).

    The invite code is always created and returned, even if the email service
    is unavailable — the admin can share the code manually in that case.
    """
    expires_at = datetime.now(UTC) + timedelta(days=body.expires_in_days)
    results: list[InviteUserResult] = []
    emails_sent = 0

    for email in body.emails:
        code_value = secrets.token_urlsafe(16)
        invite_note = f"Invited: {email}"
        if body.note:
            invite_note = f"Invited: {email} — {body.note}"

        invite = InviteCode(
            code=code_value,
            created_by=admin.id,
            max_uses=1,
            expires_at=expires_at,
            note=invite_note,
        )
        db.add(invite)
        await db.flush()

        # Send inline so the admin gets immediate feedback on delivery status.
        sent = await send_invitation_email(
            email, code_value, invited_by=admin.email, expires_at=expires_at
        )
        if sent:
            emails_sent += 1

        results.append(InviteUserResult(email=email, invite_code=code_value, email_sent=sent))

    await _audit(
        db,
        admin_id=admin.id,
        action="invite_users_by_email",
        target_type="invite_code",
        target_id=None,
        detail={
            "emails": [str(e) for e in body.emails],
            "count": len(body.emails),
            "emails_sent": emails_sent,
        },
    )
    await db.commit()

    return InviteUsersResponse(
        results=results,
        total_invited=len(results),
        total_emails_sent=emails_sent,
    )


# ─── Invite Code Endpoints ────────────────────────────────────────────────


@router.get("/invite-codes", response_model=PaginatedInviteCodesResponse)
async def list_invite_codes(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=200),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PaginatedInviteCodesResponse:
    """Return a paginated list of invite codes."""
    query = select(InviteCode)

    if active_only:
        query = query.where(InviteCode.is_active.is_(True))  # type: ignore[union-attr]

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(desc(InviteCode.created_at))
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    codes = result.scalars().all()

    return PaginatedInviteCodesResponse(
        codes=[_invite_code_response(c) for c in codes],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/invite-codes", response_model=InviteCodeResponse, status_code=status.HTTP_201_CREATED
)
async def create_invite_code(
    body: CreateInviteCodeRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> InviteCodeResponse:
    """Create a single invite code.

    If ``code`` is not provided, a secure random code is generated automatically.
    """
    code_value = body.code if body.code is not None else secrets.token_urlsafe(16)
    expires_at = _parse_expires_at(body.expires_at)

    invite = InviteCode(
        code=code_value,
        created_by=admin.id,
        max_uses=body.max_uses,
        expires_at=expires_at,
        note=body.note,
    )
    db.add(invite)
    await db.flush()

    await _audit(
        db,
        admin_id=admin.id,
        action="create_invite_code",
        target_type="invite_code",
        target_id=str(invite.id),
        detail={"code": code_value, "max_uses": body.max_uses},
    )
    await db.commit()
    await db.refresh(invite)

    return _invite_code_response(invite)


@router.post(
    "/invite-codes/bulk",
    response_model=list[InviteCodeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_invite_codes(
    body: BulkCreateInviteCodesRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[InviteCodeResponse]:
    """Bulk-create N invite codes with auto-generated values."""
    expires_at = _parse_expires_at(body.expires_at)
    created: list[InviteCode] = []

    for _ in range(body.count):
        invite = InviteCode(
            code=secrets.token_urlsafe(16),
            created_by=admin.id,
            max_uses=body.max_uses,
            expires_at=expires_at,
            note=body.note,
        )
        db.add(invite)
        created.append(invite)

    await db.flush()

    await _audit(
        db,
        admin_id=admin.id,
        action="bulk_create_invite_codes",
        target_type="invite_code",
        target_id=None,
        detail={"count": body.count, "max_uses": body.max_uses},
    )
    await db.commit()

    for invite in created:
        await db.refresh(invite)

    return [_invite_code_response(c) for c in created]


@router.patch("/invite-codes/{code_id}", response_model=InviteCodeResponse)
async def update_invite_code(
    code_id: int,
    body: UpdateInviteCodeRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> InviteCodeResponse:
    """Update an invite code's properties."""
    result = await db.execute(select(InviteCode).where(InviteCode.id == code_id))
    invite = result.scalar_one_or_none()

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )

    changes: dict = {}

    if body.is_active is not None:
        changes["is_active"] = {"previous": invite.is_active, "new": body.is_active}
        invite.is_active = body.is_active

    if body.max_uses is not None:
        changes["max_uses"] = {"previous": invite.max_uses, "new": body.max_uses}
        invite.max_uses = body.max_uses

    if body.expires_at is not None:
        expires_dt = _parse_expires_at(body.expires_at)
        changes["expires_at"] = {"new": body.expires_at}
        invite.expires_at = expires_dt

    if body.note is not None:
        changes["note"] = {"previous": invite.note, "new": body.note}
        invite.note = body.note

    await _audit(
        db,
        admin_id=admin.id,
        action="update_invite_code",
        target_type="invite_code",
        target_id=str(code_id),
        detail=changes,
    )
    await db.commit()
    await db.refresh(invite)

    return _invite_code_response(invite)


@router.delete("/invite-codes/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite_code(
    code_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> None:
    """Hard-delete an invite code.

    Only codes that have never been used (``uses_count == 0``) may be deleted.
    """
    result = await db.execute(select(InviteCode).where(InviteCode.id == code_id))
    invite = result.scalar_one_or_none()

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite code not found",
        )

    if invite.uses_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an invite code that has been used.",
        )

    await _audit(
        db,
        admin_id=admin.id,
        action="delete_invite_code",
        target_type="invite_code",
        target_id=str(code_id),
        detail={"code": invite.code},
    )
    await db.delete(invite)
    await db.commit()


# ─── Analytics Endpoints ──────────────────────────────────────────────────


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AnalyticsOverviewResponse:
    """Return aggregate platform statistics."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    active_users = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))  # type: ignore[union-attr]
    ).scalar_one()
    admin_users = (
        await db.execute(select(func.count()).select_from(User).where(User.is_admin.is_(True)))  # type: ignore[union-attr]
    ).scalar_one()

    new_users_today = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= today_start)
        )
    ).scalar_one()
    new_users_week = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= week_start)
        )
    ).scalar_one()
    new_users_month = (
        await db.execute(
            select(func.count()).select_from(User).where(User.created_at >= month_start)
        )
    ).scalar_one()

    total_invite_codes = (
        await db.execute(select(func.count()).select_from(InviteCode))
    ).scalar_one()
    active_invite_codes = (
        await db.execute(
            select(func.count()).select_from(InviteCode).where(InviteCode.is_active.is_(True))  # type: ignore[union-attr]
        )
    ).scalar_one()

    total_reports = (await db.execute(select(func.count()).select_from(Report))).scalar_one()
    total_journal_entries = (
        await db.execute(select(func.count()).select_from(JournalEntry))
    ).scalar_one()

    feedback_new_count = (
        await db.execute(select(func.count(FeedbackEntry.id)).where(FeedbackEntry.status == "new"))
    ).scalar_one()
    feedback_total_count = (await db.execute(select(func.count(FeedbackEntry.id)))).scalar_one()

    return AnalyticsOverviewResponse(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        new_users_today=new_users_today,
        new_users_week=new_users_week,
        new_users_month=new_users_month,
        total_invite_codes=total_invite_codes,
        active_invite_codes=active_invite_codes,
        total_reports=total_reports,
        total_journal_entries=total_journal_entries,
        feedback_new=feedback_new_count,
        feedback_total=feedback_total_count,
    )


@router.get("/analytics/users", response_model=UserAnalyticsResponse)
async def analytics_users(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> UserAnalyticsResponse:
    """Return daily new-user counts over the past N days."""
    now = datetime.now(UTC)
    period_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Fetch all users created within the period
    result = await db.execute(
        select(User.created_at).where(User.created_at >= period_start).order_by(User.created_at)
    )
    timestamps = result.scalars().all()

    # Aggregate into date buckets
    counts: dict[str, int] = {}
    for ts in timestamps:
        if ts is not None:
            if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            date_key = ts.strftime("%Y-%m-%d")
            counts[date_key] = counts.get(date_key, 0) + 1

    # Build ordered list covering every day in the period
    daily_counts: list[DailyUserCount] = []
    for i in range(days):
        day = period_start + timedelta(days=i)
        date_key = day.strftime("%Y-%m-%d")
        daily_counts.append(DailyUserCount(date=date_key, count=counts.get(date_key, 0)))

    return UserAnalyticsResponse(daily_counts=daily_counts, period_days=days)


# ─── Usage and Spend ──────────────────────────────────────────────────────
#
# Nothing on this router is mounted at a bare "/{param}", so no
# parameterized sibling can shadow "/usage". Keep it that way: a catch-all
# added above this line would swallow the route silently, and FastAPI
# matches in registration order without warning about it.


def _spend_cents(micros: int) -> int:
    """Convert micro-dollars to cents, rounding up.

    Once, at the aggregate, never per call. Per-call cents would round a
    half-cent chat turn up to a whole one, a 96% over-count, which at the
    allowance level tells users they are out of budget at roughly half
    their real usage. Ceiling here satisfies the never-under-count rail
    without distorting the per-call number.
    """
    return -(-micros // 10_000)


def _surface_or_unattributed() -> Case[str]:
    """``usage_records.surface``, except that unattributed spend gets its own.

    A relabel rather than an extra row, so the breakdown still sums to the
    window total. Design section 5.5 wants that number visible rather than
    buried inside whichever surface happened to lose its attribution; which
    surface it came from is already in the WARNING the ledger logged when
    it wrote the row.
    """
    return case(
        (UsageRecord.user_id.is_(None), literal(UNATTRIBUTED_SCOPE)),
        else_=UsageRecord.surface,
    )


async def _window_totals(
    db: AsyncSession, window: InstrumentedAttribute[str], key: str
) -> tuple[int, int, int]:
    """Return ``(record_count, cost_micros, estimated_count)`` for one window."""
    row = (
        await db.execute(
            select(
                func.count(UsageRecord.id),
                func.coalesce(func.sum(UsageRecord.cost_micros), 0),
                func.coalesce(func.sum(case((UsageRecord.estimated.is_(True), 1), else_=0)), 0),
            ).where(window == key)
        )
    ).one()
    return int(row[0]), int(row[1]), int(row[2])


async def _by_surface(
    db: AsyncSession, window: InstrumentedAttribute[str], key: str
) -> list[UsageSurfaceRow]:
    """Roll one window up by surface, costliest first."""
    surface = _surface_or_unattributed().label("surface")
    result = await db.execute(
        select(
            surface,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.cost_micros), 0),
        )
        .where(window == key)
        .group_by(surface)
    )
    rows = [
        UsageSurfaceRow(
            surface=str(name),
            calls=int(calls),
            cost_micros=int(micros),
            cost_cents=_spend_cents(int(micros)),
        )
        for name, calls, micros in result
    ]
    if not any(row.surface == UNATTRIBUTED_SCOPE for row in rows):
        # Always present, even at zero. A missing row reads as "we do not
        # measure this"; a zero reads as "there was none", which is the
        # thing an operator actually wants to know.
        rows.append(
            UsageSurfaceRow(surface=UNATTRIBUTED_SCOPE, calls=0, cost_micros=0, cost_cents=0)
        )
    rows.sort(key=lambda row: row.cost_micros, reverse=True)
    return rows


async def _by_model(db: AsyncSession, window: InstrumentedAttribute[str], key: str) -> list[UsageModelRow]:
    """Roll one window up by model id, costliest first.

    Both cache fields are reported, not just reads: slice 5's acceptance
    criterion is read off this block, and a cache write bills at 1.25x.
    """
    result = await db.execute(
        select(
            UsageRecord.model,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cache_read_input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cache_creation_input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cost_micros), 0),
        )
        .where(window == key)
        .group_by(UsageRecord.model)
        .order_by(desc(func.coalesce(func.sum(UsageRecord.cost_micros), 0)))
    )
    return [
        UsageModelRow(
            model=str(model),
            calls=int(calls),
            input_tokens=int(tokens_in),
            output_tokens=int(tokens_out),
            cache_read_input_tokens=int(cache_read),
            cache_creation_input_tokens=int(cache_write),
            cost_micros=int(micros),
        )
        for model, calls, tokens_in, tokens_out, cache_read, cache_write, micros in result
    ]


async def _top_users(db: AsyncSession, month_key: str, top: int) -> list[UsageTopUserRow]:
    """The costliest accounts this month, against what their plans fund.

    This is the view that answers the question the roadmap says validates
    the Pro price: what does a p95 active user actually cost.

    Monthly only, because the allowance it is measured against is monthly.
    The inner join is what keeps unattributed spend out: those rows have no
    user, and they are already visible as their own row in ``by_surface``.
    """
    settings = get_settings()
    total_micros = func.coalesce(func.sum(UsageRecord.cost_micros), 0)
    result = await db.execute(
        select(UsageRecord.user_id, User.email, User.plan, func.count(UsageRecord.id), total_micros)
        .join(User, User.id == UsageRecord.user_id)
        .where(UsageRecord.month_key == month_key)
        .group_by(UsageRecord.user_id, User.email, User.plan)
        .order_by(desc(total_micros))
        .limit(top)
    )

    rows: list[UsageTopUserRow] = []
    for user_id, email, plan, calls, micros in result:
        allowance_cents = settings.allowance_cents_for(str(plan))
        allowance_micros = allowance_cents * 10_000
        rows.append(
            UsageTopUserRow(
                user_id=str(user_id),
                email=email,
                plan=str(plan),
                calls=int(calls),
                cost_micros=int(micros),
                cost_cents=_spend_cents(int(micros)),
                allowance_cents=allowance_cents,
                # free has an allowance of zero by design, so this guard is
                # a real case rather than defensive noise.
                pct_of_allowance=(
                    round(int(micros) * 100 / allowance_micros, 1) if allowance_micros else 0.0
                ),
            )
        )
    return rows


@router.get("/usage", response_model=AdminUsageResponse)
async def admin_usage(
    top: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> AdminUsageResponse:
    """Return what the paid surfaces have cost, and how close the gates are.

    Two sources, and the split is the point. Gate numbers — call counts and
    ceilings — come from ``usage_counters``, which answers "are we blocked".
    Every dollar comes from ``usage_records``, which answers "what did it
    cost". Reading spend off the counters would work today and drift the
    moment a counter is reset or a meter is renamed.

    Two windows: ``today`` carries the daily ceiling that can actually block
    a call, ``month`` carries the budget that deliberately cannot. There is
    no automatic monthly kill switch (design section 7.1); crossing 80% logs
    at ERROR from the ledger's write path, so the alert does not wait for
    somebody to open this page.
    """
    settings = get_settings()
    period_key = current_period_key()
    month_key = current_month_key()

    today_records, today_micros, today_estimated = await _window_totals(
        db, UsageRecord.period_key, period_key
    )
    _, month_micros, _ = await _window_totals(db, UsageRecord.month_key, month_key)

    ceiling_micros = settings.daily_global_spend_ceiling_micros()
    budget_micros = settings.monthly_llm_spend_budget_micros()

    return AdminUsageResponse(
        as_of=datetime.now(UTC).isoformat(),
        today=UsageTodayBlock(
            period_key=period_key,
            spend_micros=today_micros,
            spend_cents=_spend_cents(today_micros),
            ceiling_micros=ceiling_micros,
            remaining_micros=ceiling_micros - today_micros,
            llm_calls=await get_count(
                scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS, period_key=period_key
            ),
            llm_call_ceiling=settings.global_daily_llm_call_ceiling,
            record_count=today_records,
            estimated_record_count=today_estimated,
        ),
        month=UsageMonthBlock(
            month_key=month_key,
            spend_micros=month_micros,
            spend_cents=_spend_cents(month_micros),
            budget_micros=budget_micros,
            remaining_micros=budget_micros - month_micros,
            pct_of_budget=(round(month_micros * 100 / budget_micros, 1) if budget_micros else 0.0),
        ),
        by_surface=UsageSurfaceBreakdown(
            today=await _by_surface(db, UsageRecord.period_key, period_key),
            month=await _by_surface(db, UsageRecord.month_key, month_key),
        ),
        by_model=UsageModelBreakdown(
            today=await _by_model(db, UsageRecord.period_key, period_key),
            month=await _by_model(db, UsageRecord.month_key, month_key),
        ),
        top_users=await _top_users(db, month_key, top),
    )


# ─── Waitlist Admin Endpoints ─────────────────────────────────────────────


@router.get("/waitlist", response_model=PaginatedWaitlistResponse)
async def list_waitlist(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PaginatedWaitlistResponse:
    """Return a paginated list of waitlist entries with optional status filter."""
    query = select(WaitlistEntry)

    if status_filter is not None:
        query = query.where(WaitlistEntry.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(desc(WaitlistEntry.created_at))
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    entries = result.scalars().all()

    return PaginatedWaitlistResponse(
        entries=[_waitlist_entry_response(e) for e in entries],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/waitlist/invite", response_model=InviteWaitlistResponse, status_code=status.HTTP_201_CREATED
)
async def invite_waitlist_entries(
    body: InviteWaitlistRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> InviteWaitlistResponse:
    """Invite selected waitlist entries by their IDs.

    For each pending entry:
    1. Creates a single-use invite code (expires after ``expires_in_days``).
    2. Sends an invitation email (fire-and-forget with status feedback).
    3. Updates the waitlist entry status to ``invited``.

    Non-pending entries are skipped.
    """
    expires_at = datetime.now(UTC) + timedelta(days=body.expires_in_days)

    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.id.in_(body.entry_ids)))
    entries = result.scalars().all()

    results: list[WaitlistInviteResult] = []
    emails_sent = 0
    skipped = 0

    for entry in entries:
        if entry.status != "pending":
            skipped += 1
            continue

        code_value = secrets.token_urlsafe(16)
        invite = InviteCode(
            code=code_value,
            created_by=admin.id,
            max_uses=1,
            expires_at=expires_at,
            note=f"Waitlist invite: {entry.email}",
        )
        db.add(invite)
        await db.flush()

        entry.invite_code_id = invite.id
        entry.status = "invited"

        sent = await send_invitation_email(
            entry.email, code_value, invited_by=admin.email, expires_at=expires_at
        )
        if sent:
            emails_sent += 1

        results.append(
            WaitlistInviteResult(
                entry_id=entry.id,
                email=entry.email,
                invite_code=code_value,
                email_sent=sent,
            )
        )

    await _audit(
        db,
        admin_id=admin.id,
        action="invite_waitlist_entries",
        target_type="waitlist_entry",
        target_id=None,
        detail={
            "entry_ids": body.entry_ids,
            "invited": len(results),
            "skipped": skipped,
            "emails_sent": emails_sent,
        },
    )
    await db.commit()

    return InviteWaitlistResponse(
        results=results,
        total_invited=len(results),
        total_emails_sent=emails_sent,
        total_skipped=skipped,
    )


@router.delete("/waitlist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_waitlist_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> None:
    """Remove a waitlist entry.

    Returns 204 on success, 404 if the entry does not exist.
    """
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found",
        )

    await _audit(
        db,
        admin_id=admin.id,
        action="delete_waitlist_entry",
        target_type="waitlist_entry",
        target_id=str(entry_id),
        detail={"email": entry.email, "status": entry.status},
    )
    await db.delete(entry)
    await db.commit()

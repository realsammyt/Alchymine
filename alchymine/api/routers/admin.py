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
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from alchymine.api.auth import get_current_admin
from alchymine.db.base import Base, get_async_engine, get_async_session_factory
from alchymine.db.models import AdminAuditLog, InviteCode, JournalEntry, Report, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")

# ─── Database Session Dependency ──────────────────────────────────────────

_engine = None
_session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session.

    Lazily creates the engine and session factory on first call,
    and creates all tables (for development / testing convenience).
    """
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is None:
        _engine = get_async_engine()
        _session_factory = get_async_session_factory(_engine)
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with _session_factory() as session:
        yield session


# ─── Audit Log Helper ─────────────────────────────────────────────────────


async def _audit(
    db: AsyncSession,
    admin_id: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> None:
    """Write an audit log entry and flush (without committing)."""
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


class DailyUserCount(BaseModel):
    """New-user count for a single calendar date."""

    date: str
    count: int


class UserAnalyticsResponse(BaseModel):
    """Daily new-user counts over a period."""

    daily_counts: list[DailyUserCount]
    period_days: int


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

    # Sorting
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

"""Authentication router — register, login, refresh, logout, password reset, and user info endpoints.

Endpoints:
- ``POST /auth/register``        — Create a new user and return tokens (+ set httpOnly cookies).
- ``POST /auth/login``           — Authenticate and return tokens (+ set httpOnly cookies).
- ``POST /auth/logout``          — Clear auth cookies.
- ``POST /auth/refresh``         — Exchange a refresh token for a new access token.
- ``GET  /auth/me``              — Return current user info (protected).
- ``POST /auth/forgot-password`` — Request a password reset token.
- ``POST /auth/reset-password``  — Reset password using a valid token.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from alchymine.api.deps import get_db_session
from alchymine.config import get_settings
from alchymine.db.models import InviteCode, User, WaitlistEntry
from alchymine.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

# ─── Pydantic Schemas ────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    promo_code: str = Field(..., description="Invitation code required for signup")


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request body for token refresh.

    ``refresh_token`` is optional when a ``refresh_token`` httpOnly cookie is
    present on the request — the endpoint will fall back to reading the cookie.
    """

    refresh_token: str | None = None


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class ForgotPasswordRequest(BaseModel):
    """Request body for password reset request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for password reset."""

    token: str
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class WaitlistRequest(BaseModel):
    """Request body for public waitlist signup."""

    email: EmailStr


class WaitlistResponse(BaseModel):
    """Response for waitlist signup."""

    message: str
    already_registered: bool


class UserResponse(BaseModel):
    """Response containing user information."""

    id: str
    email: str
    version: str
    created_at: str
    is_admin: bool = False


# ─── Database Session Dependency ──────────────────────────────────────────
# Uses the centralized get_db_session from alchymine.api.deps.
# Alias kept for backward compatibility with tests that import get_db.
get_db = get_db_session


# ─── Cookie helpers ───────────────────────────────────────────────────────

_ACCESS_TOKEN_MAX_AGE = 1800  # 30 minutes
_REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Attach httpOnly auth cookies to *response* (in addition to the JSON body)."""
    settings = get_settings()
    secure = settings.environment != "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=_ACCESS_TOKEN_MAX_AGE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=_REFRESH_TOKEN_MAX_AGE,
        path="/api/v1/auth/refresh",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Remove auth cookies from the client."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")


# ─── Endpoints ────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user.

    Creates the user in the database, hashes the password, and returns
    an access token + refresh token pair.

    Returns 403 if the promo code is invalid.
    Returns 409 if the email is already registered.
    """
    # Validate invite code from DB (atomic: validate + increment in one UPDATE)
    result = await db.execute(
        update(InviteCode)
        .where(
            InviteCode.code == body.promo_code,
            InviteCode.is_active.is_(True),
            InviteCode.uses_count < InviteCode.max_uses,
            or_(InviteCode.expires_at.is_(None), InviteCode.expires_at > func.now()),
        )
        .values(uses_count=InviteCode.uses_count + 1)
        .returning(InviteCode)
    )
    invite_code_row = result.scalar_one_or_none()
    if invite_code_row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid, expired, or fully used invitation code",
        )

    # Check for existing user
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        invite_code_used=invite_code_row.code,
    )
    db.add(user)

    logger.info(
        "Invite code '%s' used by %s (%d/%d uses)",
        invite_code_row.code,
        body.email,
        invite_code_row.uses_count,
        invite_code_row.max_uses,
    )

    await db.commit()
    await db.refresh(user)

    # Best-effort: mark the waitlist entry as registered if the invite code matches
    try:
        waitlist_result = await db.execute(
            select(WaitlistEntry).where(WaitlistEntry.email == body.email)
        )
        waitlist_entry = waitlist_result.scalar_one_or_none()
        if waitlist_entry is not None and waitlist_entry.status != "registered":
            waitlist_entry.status = "registered"
            await db.commit()
    except Exception:
        logger.exception(
            "Failed to update waitlist status for %s — registration continues", body.email
        )

    # Generate tokens
    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return tokens.

    Validates email + password against the database and returns
    an access token + refresh token pair.

    Returns 401 if credentials are invalid.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user.last_login_at = datetime.now(UTC)
    await db.commit()

    # Generate tokens
    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """Clear auth cookies to log the user out.

    This removes the httpOnly access and refresh token cookies from the
    client.  Callers using header-based auth should also discard their
    locally stored tokens.
    """
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a refresh token for a new access token.

    Accepts the refresh token from either the JSON body or the ``refresh_token``
    httpOnly cookie.  Validates the token, verifies the user still exists, checks
    that the token was issued after the last password change, and returns a new
    access + refresh token pair (also setting fresh cookies).

    Returns 401 if the refresh token is invalid, the user no longer exists, or
    the token predates the most recent password change.
    """
    raw_refresh = body.refresh_token or request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required",
        )

    payload = decode_token(raw_refresh)

    # Ensure it is a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Verify user still exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    # Reject tokens issued before (or at the same second as) the last
    # password change.  JWT ``iat`` is an integer epoch, so we truncate
    # ``password_changed_at`` to whole seconds for a fair comparison.
    # Using ``<=`` means tokens minted in the same calendar second as
    # the change are also revoked — the user must log in again, which
    # is the safe default.
    if user.password_changed_at is not None:
        token_iat = payload.get("iat")
        changed_at = user.password_changed_at
        if changed_at.tzinfo is None:
            changed_at = changed_at.replace(tzinfo=UTC)
        changed_at_truncated = changed_at.replace(microsecond=0)
        if token_iat is None or datetime.fromtimestamp(token_iat, tz=UTC) <= changed_at_truncated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked — please log in again",
            )

    # Issue new tokens
    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    _set_auth_cookies(response, access_token, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Return the current authenticated user's information.

    Requires a valid access token in the Authorization header.
    """
    user_id = current_user.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user.id,
        email=user.email or "",
        version=user.version,
        created_at=str(user.created_at),
        is_admin=user.is_admin,
    )


# ─── Password Reset ──────────────────────────────────────────────────────

RESET_TOKEN_EXPIRE_MINUTES = 60


def _hash_reset_token(token: str) -> str:
    """Hash a reset token for storage (prevents DB leak → account takeover)."""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Request a password reset.

    Always returns a success message regardless of whether the email exists
    (prevents email enumeration). If the email exists, a reset token is
    generated and logged server-side.

    In production, integrate an email service to deliver the reset link.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is not None:
        # Generate a secure token
        raw_token = secrets.token_urlsafe(32)
        user.password_reset_token = _hash_reset_token(raw_token)
        user.password_reset_expires = datetime.now(UTC) + timedelta(
            minutes=RESET_TOKEN_EXPIRE_MINUTES,
        )
        await db.commit()

        # Send the reset email (fire-and-forget via BackgroundTasks)
        background_tasks.add_task(send_password_reset_email, body.email, raw_token)

    return MessageResponse(
        message="If an account exists with that email, password reset instructions have been sent.",
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset a password using a valid reset token.

    Validates the token, checks expiry, and updates the password.
    The token is single-use and cleared after a successful reset.
    """
    token_hash = _hash_reset_token(body.token)

    result = await db.execute(select(User).where(User.password_reset_token == token_hash))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Compare expiry — handle both tz-aware and naive datetimes (SQLite returns naive)
    now = datetime.now(UTC)
    expires = user.password_reset_expires
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires is None or expires < now:
        # Clear the expired token
        user.password_reset_token = None
        user.password_reset_expires = None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password, record the change timestamp (invalidates existing refresh tokens),
    # and clear the one-time reset token.
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = datetime.now(UTC)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()

    return MessageResponse(message="Password has been reset successfully.")


# ─── Waitlist ─────────────────────────────────────────────────────────────


@router.post("/waitlist", response_model=WaitlistResponse)
async def join_waitlist(
    body: WaitlistRequest,
    db: AsyncSession = Depends(get_db),
) -> WaitlistResponse:
    """Add an email to the public waitlist.

    Idempotent — always returns 200 to avoid email enumeration.
    Returns ``already_registered: true`` when the email is already on the list.
    """
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == body.email))
    existing = result.scalar_one_or_none()

    if existing is not None:
        return WaitlistResponse(
            message="You're already on the waitlist.",
            already_registered=True,
        )

    entry = WaitlistEntry(email=body.email)
    db.add(entry)
    await db.commit()

    logger.info("New waitlist signup: %s", body.email)

    return WaitlistResponse(
        message="You're on the waitlist — we'll be in touch.",
        already_registered=False,
    )

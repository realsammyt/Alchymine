"""JWT authentication utilities for Alchymine API.

Provides password hashing, JWT token creation/validation, and a FastAPI
dependency for extracting the current user from a bearer token.

Configuration via environment variables:
- ``JWT_SECRET_KEY``             — HMAC signing key (required in production)
- ``JWT_ALGORITHM``              — JWT algorithm (default: HS256)
- ``ACCESS_TOKEN_EXPIRE_MINUTES``— Access token lifetime (default: 30)
- ``REFRESH_TOKEN_EXPIRE_DAYS``  — Refresh token lifetime (default: 7)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.deps import get_db_session
from alchymine.config import get_settings
from alchymine.db.models import User

# ─── Configuration ────────────────────────────────────────────────────────
# Convenience aliases so existing call-sites (and tests that import these
# names) continue to work without changes.

_settings = get_settings()
JWT_SECRET_KEY: str = _settings.jwt_secret_key
JWT_ALGORITHM: str = _settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES: int = _settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS: int = _settings.refresh_token_expire_days

# ─── Password Hashing ────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Parameters
    ----------
    password:
        The plaintext password to hash.

    Returns
    -------
    str
        The bcrypt hash string.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Parameters
    ----------
    plain:
        The plaintext password to verify.
    hashed:
        The bcrypt hash to verify against.

    Returns
    -------
    bool
        True if the password matches the hash.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ─── JWT Token Creation ──────────────────────────────────────────────────


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    data:
        Claims to encode in the token. Must include ``sub`` for the user ID.
    expires_delta:
        Optional custom expiration. Defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns
    -------
    str
        The encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed JWT refresh token with a longer lifetime.

    Parameters
    ----------
    data:
        Claims to encode in the token. Must include ``sub`` for the user ID.

    Returns
    -------
    str
        The encoded JWT string.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Parameters
    ----------
    token:
        The encoded JWT string.

    Returns
    -------
    dict
        The decoded token payload.

    Raises
    ------
    HTTPException
        If the token is expired, malformed, or invalid.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ─── FastAPI Dependencies ─────────────────────────────────────────────────


async def get_current_user(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
) -> dict:
    """FastAPI dependency that extracts the current user from a bearer token or cookie.

    Checks the ``Authorization: Bearer`` header first. If absent, falls back to
    reading the ``access_token`` httpOnly cookie so cookie-based auth works
    transparently alongside legacy header-based clients.

    Parameters
    ----------
    request:
        The incoming HTTP request (used to read cookies).
    bearer_token:
        The JWT bearer token extracted from the Authorization header, or None.

    Returns
    -------
    dict
        The decoded token payload containing at least ``sub`` (user ID).

    Raises
    ------
    HTTPException
        If no valid token is found in either the header or cookie.
    """
    token = bearer_token or request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ─── Admin Dependency ─────────────────────────────────────────────────────


async def get_current_admin(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """FastAPI dependency that requires the current user to be an active admin.

    Re-reads the User from the database on every request to ensure admin
    status hasn't been revoked since the JWT was issued.

    Returns the full User ORM object.

    Raises
    ------
    HTTPException
        401 if not authenticated, 403 if not an active admin.
    """
    payload = await get_current_user(request, bearer_token)
    user_id = payload.get("sub")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user


# ─── Entitlement Dependency ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Account:
    """An immutable snapshot of what this account is entitled to, right now.

    Frozen because the gates downstream read it several times per request
    (entitlement, then allowance, then the response envelope) and every read
    has to agree.
    """

    user_id: str
    email: str | None
    plan: str
    plan_status: str
    is_admin: bool
    plan_period_end: datetime | None
    trial_ends_at: datetime | None

    @property
    def effective_plan(self) -> str:
        """The plan actually in force right now.

        A lapsed window degrades to 'free' rather than keeping paid access,
        so a cancelled subscriber stops costing money at the period end
        instead of at their next token refresh.
        """
        if self.plan_period_end is None:
            return self.plan

        period_end = self.plan_period_end
        if period_end.tzinfo is None:
            # SQLite hands back naive datetimes. Everything we write is UTC.
            period_end = period_end.replace(tzinfo=UTC)

        return "free" if period_end <= datetime.now(UTC) else self.plan


async def get_current_account(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> Account:
    """FastAPI dependency returning the caller's entitlement snapshot.

    The DB-backed sibling of :func:`get_current_admin`, minus the admin
    requirement. ``get_current_user`` stays JWT-only and never touches the
    database, which is why there is nowhere on it to hang an entitlement.

    The plan is read from Postgres on every gated request, never from the
    token. Access tokens live 30 minutes and refresh tokens 7 days, so a plan
    claim baked into a JWT would hand a cancelled subscriber a week of
    inference we are paying for.

    There is deliberately no Redis cache here. A 30 to 60 second read-through
    cache is worth adding once Stripe webhooks exist to invalidate it; until
    then one SELECT per gated request is the affordable, correct answer.

    Raises
    ------
    HTTPException
        401 if the token is missing, invalid, or names a user that no longer
        exists; 403 if the account is disabled.
    """
    payload = await get_current_user(request, bearer_token)
    user_id = payload.get("sub")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Slice 2 sets the attribution ContextVars here, from the resolved user id
    # and request.state.request_id, so the LLM egress sites can name who a
    # paid call belongs to.

    return Account(
        user_id=user.id,
        email=user.email,
        plan=user.plan,
        plan_status=user.plan_status,
        is_admin=user.is_admin,
        plan_period_end=user.plan_period_end,
        trial_ends_at=user.trial_ends_at,
    )

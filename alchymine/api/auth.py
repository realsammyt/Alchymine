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

import os
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# ─── Configuration ────────────────────────────────────────────────────────

JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ─── Password Hashing ────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
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


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """FastAPI dependency that extracts the current user from a bearer token.

    Parameters
    ----------
    token:
        The JWT bearer token extracted from the Authorization header.

    Returns
    -------
    dict
        The decoded token payload containing at least ``sub`` (user ID).

    Raises
    ------
    HTTPException
        If the token is missing, expired, or invalid.
    """
    payload = decode_token(token)
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

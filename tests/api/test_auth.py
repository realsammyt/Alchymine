"""Tests for JWT authentication — registration, login, token management, and protected endpoints.

Uses an in-memory SQLite database so no external services are needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alchymine.api.auth import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from alchymine.api.main import app
from alchymine.api.routers.auth import get_db
from alchymine.db.base import Base

# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _override_db():
    """Override the DB dependency with an in-memory SQLite database for every test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """Return a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    """Register a test user and return the response data including tokens."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepassword123",
            "promo_code": "alchyours",
        },
    )
    assert response.status_code == 201
    return response.json()


# ─── Password Hashing Tests ──────────────────────────────────────────────


class TestPasswordHashing:
    """Tests for hash_password and verify_password utilities."""

    def test_hash_password_returns_bcrypt_hash(self):
        """hash_password should return a bcrypt-formatted hash string."""
        hashed = hash_password("my-secret")
        assert hashed.startswith("$2")
        assert len(hashed) > 50

    def test_verify_password_correct(self):
        """verify_password should return True for a matching password."""
        hashed = hash_password("correct-password")
        assert verify_password("correct-password", hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for a wrong password."""
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_password_unique_salts(self):
        """Two calls to hash_password with the same input should produce different hashes."""
        hash1 = hash_password("same-password")
        hash2 = hash_password("same-password")
        assert hash1 != hash2


# ─── Token Tests ──────────────────────────────────────────────────────────


class TestTokens:
    """Tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        """create_access_token should return a valid JWT with 'access' type."""
        token = create_access_token({"sub": "user-123", "email": "a@b.com"})
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self):
        """create_refresh_token should return a valid JWT with 'refresh' type."""
        token = create_refresh_token({"sub": "user-123", "email": "a@b.com"})
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_access_token_custom_expiry(self):
        """create_access_token should respect a custom expires_delta."""
        token = create_access_token(
            {"sub": "user-123"},
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        # Should expire within ~5 minutes from now (with 10s tolerance)
        delta = exp - now
        assert timedelta(minutes=4, seconds=50) < delta < timedelta(minutes=5, seconds=10)

    def test_decode_token_valid(self):
        """decode_token should return the payload for a valid token."""
        token = create_access_token({"sub": "user-456"})
        payload = decode_token(token)
        assert payload["sub"] == "user-456"

    def test_decode_token_expired(self):
        """decode_token should raise HTTPException for an expired token."""
        token = create_access_token(
            {"sub": "user-123"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_token_invalid(self):
        """decode_token should raise HTTPException for a garbage token."""
        with pytest.raises(Exception) as exc_info:
            decode_token("not.a.valid.jwt")
        assert exc_info.value.status_code == 401

    def test_decode_token_wrong_secret(self):
        """decode_token should reject a token signed with a different secret."""
        token = jwt.encode(
            {"sub": "user-123", "exp": datetime.now(UTC) + timedelta(hours=1)},
            "different-secret",
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(Exception) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401


# ─── Registration Tests ──────────────────────────────────────────────────


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, client: TestClient):
        """Registering a new user should return 201 with access and refresh tokens."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "password123", "promo_code": "alchyours"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient):
        """Registering with an already-used email should return 409."""
        payload = {"email": "dup@example.com", "password": "password123", "promo_code": "alchyours"}
        response1 = client.post("/api/v1/auth/register", json=payload)
        assert response1.status_code == 201

        response2 = client.post("/api/v1/auth/register", json=payload)
        assert response2.status_code == 409
        assert "already registered" in response2.json()["detail"].lower()

    def test_register_short_password(self, client: TestClient):
        """Registering with a password shorter than 8 characters should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "abc", "promo_code": "alchyours"},
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Registering with an invalid email should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123", "promo_code": "alchyours"},
        )
        assert response.status_code == 422

    def test_register_missing_fields(self, client: TestClient):
        """Registering with missing fields should return 422."""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422

    def test_register_invalid_promo_code(self, client: TestClient):
        """Registering with a wrong promo code should return 403."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "promo@example.com",
                "password": "password123",
                "promo_code": "wrongcode",
            },
        )
        assert response.status_code == 403
        assert "invalid" in response.json()["detail"].lower()

    def test_register_missing_promo_code(self, client: TestClient):
        """Registering without a promo code should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "nopromo@example.com", "password": "password123"},
        )
        assert response.status_code == 422


# ─── Login Tests ──────────────────────────────────────────────────────────


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client: TestClient, registered_user: dict):
        """Logging in with correct credentials should return tokens."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, registered_user: dict):
        """Logging in with the wrong password should return 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Logging in with an unregistered email should return 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert response.status_code == 401


# ─── Protected Endpoint Tests ─────────────────────────────────────────────


class TestProtectedEndpoint:
    """Tests for GET /api/v1/auth/me (requires authentication)."""

    def test_me_with_valid_token(self, client: TestClient, registered_user: dict):
        """GET /me with a valid token should return user info."""
        token = registered_user["access_token"]
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "version" in data

    def test_me_without_token(self, client: TestClient):
        """GET /me without a token should return 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token(self, client: TestClient):
        """GET /me with a garbage token should return 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert response.status_code == 401

    def test_me_with_refresh_token_rejected(self, client: TestClient, registered_user: dict):
        """GET /me with a refresh token (instead of access token) should return 401."""
        refresh_token = registered_user["refresh_token"]
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 401
        assert "token type" in response.json()["detail"].lower()

    def test_me_with_expired_token(self, client: TestClient, registered_user: dict):
        """GET /me with an expired token should return 401."""
        # Decode the original token to get the user's sub claim
        original = decode_token(registered_user["access_token"])
        # Create a token that already expired
        expired_token = create_access_token(
            {"sub": original["sub"], "email": original.get("email")},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401


# ─── Refresh Token Tests ─────────────────────────────────────────────────


class TestRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    def test_refresh_success(self, client: TestClient, registered_user: dict):
        """Refreshing with a valid refresh token should return new tokens."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_rejected(self, client: TestClient, registered_user: dict):
        """Using an access token as a refresh token should be rejected."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["access_token"]},
        )
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Refreshing with a garbage token should return 401."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401

    def test_refresh_new_token_works(self, client: TestClient, registered_user: dict):
        """The new access token from a refresh should work on protected endpoints."""
        # Refresh
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert refresh_resp.status_code == 200
        new_access = refresh_resp.json()["access_token"]

        # Use the new access token
        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "test@example.com"

    def test_refresh_with_missing_token_rejected(self, client: TestClient):
        """Refreshing without a token in body or cookie should return 401."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={},
        )
        assert response.status_code == 401


# ─── Cookie Tests ─────────────────────────────────────────────────────────


class TestAuthCookies:
    """Tests that login and register set httpOnly auth cookies."""

    def test_login_sets_cookies(self, client: TestClient, registered_user: dict):
        """Login should set access_token and refresh_token cookies."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_register_sets_cookies(self, client: TestClient):
        """Register should set access_token and refresh_token cookies."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie@example.com",
                "password": "password123",
                "promo_code": "alchyours",
            },
        )
        assert response.status_code == 201
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_me_with_cookie_auth(self, client: TestClient, registered_user: dict):
        """GET /me should accept the access_token cookie instead of Bearer header."""
        # Log in to obtain cookies
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert login_resp.status_code == 200
        cookie_value = login_resp.cookies["access_token"]

        # Use cookie instead of Authorization header
        response = client.get(
            "/api/v1/auth/me",
            cookies={"access_token": cookie_value},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_logout_clears_cookies(self, client: TestClient, registered_user: dict):
        """POST /auth/logout should clear auth cookies."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully."


# ─── Forgot Password Tests ──────────────────────────────────────────────


class TestForgotPassword:
    """Tests for POST /api/v1/auth/forgot-password."""

    def test_forgot_password_existing_email(self, client: TestClient, registered_user: dict):
        """Requesting a reset for an existing email should return 200 with a message."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_forgot_password_nonexistent_email(self, client: TestClient):
        """Requesting a reset for a non-existent email should still return 200 (no enumeration)."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_forgot_password_invalid_email(self, client: TestClient):
        """Requesting a reset with an invalid email should return 422."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422


# ─── Reset Password Tests ───────────────────────────────────────────────


class TestResetPassword:
    """Tests for POST /api/v1/auth/reset-password."""

    def test_reset_password_invalid_token(self, client: TestClient):
        """Resetting with a bad token should return 400."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "bad-token", "new_password": "newpassword123"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_reset_password_short_password(self, client: TestClient):
        """Resetting with a password shorter than 8 characters should return 422."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token", "new_password": "abc"},
        )
        assert response.status_code == 422

    def test_forgot_then_reset_flow(self, client: TestClient, registered_user: dict):
        """Full flow: forgot → set known token in DB → reset → login with new password."""
        import secrets

        from sqlalchemy import select

        from alchymine.api.routers.auth import _hash_reset_token, get_db
        from alchymine.db.models import User

        # Step 1: Request reset (creates a token in the DB)
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200

        # Step 2: Generate a known token and inject it into the DB
        # (we can't intercept the server-logged token)
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_reset_token(raw_token)

        # Use the overridden get_db dependency to access the same in-memory DB
        import asyncio

        async def _set_token() -> None:
            async for db in app.dependency_overrides[get_db]():
                result = await db.execute(select(User).where(User.email == "test@example.com"))
                user = result.scalar_one()
                user.password_reset_token = token_hash
                user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
                await db.commit()

        asyncio.run(_set_token())

        # Step 3: Reset the password
        reset_resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "brand-new-password"},
        )
        assert reset_resp.status_code == 200

        # Step 4: Login with the new password
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "brand-new-password"},
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

        # Step 5: Old password no longer works
        old_login = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert old_login.status_code == 401

        # Step 6: Token is single-use — reusing it fails
        reuse_resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "another-password"},
        )
        assert reuse_resp.status_code == 400


# ─── Token Revocation Tests ──────────────────────────────────────────────


class TestTokenRevocationOnPasswordReset:
    """Tests that refresh tokens issued before a password reset are invalidated."""

    def test_refresh_token_revoked_after_password_reset(
        self, client: TestClient, registered_user: dict
    ):
        """A refresh token obtained before a password reset should be rejected."""
        import asyncio
        import secrets

        from sqlalchemy import select

        from alchymine.api.routers.auth import _hash_reset_token, get_db
        from alchymine.db.models import User

        old_refresh_token = registered_user["refresh_token"]

        # Verify the old refresh token works before the reset
        pre_reset_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert pre_reset_resp.status_code == 200

        # Trigger a password reset via the forgot/reset flow
        client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_reset_token(raw_token)

        async def _set_reset_token() -> None:
            async for db in app.dependency_overrides[get_db]():
                result = await db.execute(select(User).where(User.email == "test@example.com"))
                user = result.scalar_one()
                user.password_reset_token = token_hash
                user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
                await db.commit()

        asyncio.run(_set_reset_token())

        reset_resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "brand-new-password-2"},
        )
        assert reset_resp.status_code == 200

        # The old refresh token should now be rejected
        post_reset_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert post_reset_resp.status_code == 401
        assert "revoked" in post_reset_resp.json()["detail"].lower()

    def test_new_refresh_token_works_after_password_reset(
        self, client: TestClient, registered_user: dict
    ):
        """A refresh token issued after a password reset should be accepted."""
        import asyncio
        import secrets

        from sqlalchemy import select

        from alchymine.api.routers.auth import _hash_reset_token, get_db
        from alchymine.db.models import User

        client.post("/api/v1/auth/forgot-password", json={"email": "test@example.com"})

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_reset_token(raw_token)

        async def _set_reset_token() -> None:
            async for db in app.dependency_overrides[get_db]():
                result = await db.execute(select(User).where(User.email == "test@example.com"))
                user = result.scalar_one()
                user.password_reset_token = token_hash
                user.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)
                await db.commit()

        asyncio.run(_set_reset_token())

        client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "post-reset-password"},
        )

        # Wait so the new login token's ``iat`` (integer seconds) falls
        # strictly after the password_changed_at second.
        import time

        time.sleep(1.1)

        # Log in with the new password to get a fresh refresh token
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "post-reset-password"},
        )
        assert login_resp.status_code == 200
        new_refresh_token = login_resp.json()["refresh_token"]

        # New refresh token should work
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.json()


# ─── Password Reset Email Tests ─────────────────────────────────────────


class TestPasswordResetEmail:
    """Tests that the forgot-password endpoint integrates with the email service."""

    def test_forgot_password_calls_email_service(
        self, client: TestClient, registered_user: dict
    ):
        """Requesting a reset for an existing email should schedule the email task."""
        from unittest.mock import AsyncMock, patch

        mock_send = AsyncMock(return_value=True)
        with patch("alchymine.api.routers.auth.send_password_reset_email", mock_send):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert response.status_code == 200
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "test@example.com"
        # Second arg is the raw token string
        assert isinstance(call_args[0][1], str)
        assert len(call_args[0][1]) > 0

    def test_forgot_password_nonexistent_email_no_email_sent(self, client: TestClient):
        """Requesting a reset for a non-existent email should NOT call the email service."""
        from unittest.mock import AsyncMock, patch

        mock_send = AsyncMock(return_value=True)
        with patch("alchymine.api.routers.auth.send_password_reset_email", mock_send):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "nobody@example.com"},
            )
        assert response.status_code == 200
        mock_send.assert_not_called()

    def test_forgot_password_email_failure_still_returns_success(
        self, client: TestClient, registered_user: dict
    ):
        """Even if the email service fails, the endpoint should still return 200."""
        from unittest.mock import AsyncMock, patch

        mock_send = AsyncMock(return_value=False)
        with patch("alchymine.api.routers.auth.send_password_reset_email", mock_send):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert response.status_code == 200
        assert "message" in response.json()
        mock_send.assert_called_once()

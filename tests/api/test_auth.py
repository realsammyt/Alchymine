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
        json={"email": "test@example.com", "password": "securepassword123"},
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
            json={"email": "new@example.com", "password": "password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient):
        """Registering with an already-used email should return 409."""
        payload = {"email": "dup@example.com", "password": "password123"}
        response1 = client.post("/api/v1/auth/register", json=payload)
        assert response1.status_code == 201

        response2 = client.post("/api/v1/auth/register", json=payload)
        assert response2.status_code == 409
        assert "already registered" in response2.json()["detail"].lower()

    def test_register_short_password(self, client: TestClient):
        """Registering with a password shorter than 8 characters should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "abc"},
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Registering with an invalid email should return 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 422

    def test_register_missing_fields(self, client: TestClient):
        """Registering with missing fields should return 422."""
        response = client.post("/api/v1/auth/register", json={})
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

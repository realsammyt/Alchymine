"""Tests for the public waitlist and admin waitlist management endpoints.

Uses an in-memory SQLite database and overrides the DB dependency so no
external services are needed.  Admin endpoints also override
``get_current_admin``.  The ``_audit`` helper is patched to a no-op to
avoid SQLite's BigInteger autoincrement limitation (same pattern as
test_admin.py).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alchymine.api.auth import get_current_admin
from alchymine.api.main import app
from alchymine.api.routers import admin as admin_module
from alchymine.api.routers import auth as auth_module
from alchymine.db.base import Base
from alchymine.db.models import User, WaitlistEntry

# ─── Helpers ──────────────────────────────────────────────────────────────


def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


def _make_admin(session_factory) -> User:
    async def _create() -> User:
        async with session_factory() as session:
            user = User(
                id="admin-wl-1",
                email="admin@waitlist-test.com",
                is_admin=True,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return _run(_create())


# ─── Shared DB fixture ─────────────────────────────────────────────────────


@pytest.fixture()
def db_session_factory():
    """Create a shared in-memory SQLite engine + session factory."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run(_init())
    return factory


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_audit():
    """Patch the admin router's _audit helper to a no-op."""
    with patch.object(admin_module, "_audit", new=AsyncMock(return_value=None)):
        yield


@pytest.fixture()
def auth_client(db_session_factory):
    """TestClient with the auth router's DB overridden (no admin auth)."""

    async def _get_test_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[auth_module.get_db] = _get_test_db
    yield TestClient(app)
    app.dependency_overrides.pop(auth_module.get_db, None)


@pytest.fixture()
def admin_client(db_session_factory):
    """TestClient with both the admin router's DB and admin auth overridden."""

    async def _get_test_db():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[admin_module.get_db] = _get_test_db

    admin_user = _make_admin(db_session_factory)
    app.dependency_overrides[get_current_admin] = lambda: admin_user

    yield TestClient(app)

    app.dependency_overrides.pop(admin_module.get_db, None)
    app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture()
def seeded_waitlist_entry(db_session_factory) -> WaitlistEntry:
    """Insert a pending WaitlistEntry and return it."""

    async def _create():
        async with db_session_factory() as session:
            entry = WaitlistEntry(email="seeded@example.com", status="pending")
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return entry

    return _run(_create())


# ─── Public Waitlist Endpoint Tests ───────────────────────────────────────


class TestJoinWaitlist:
    """Tests for POST /api/v1/auth/waitlist."""

    def test_new_email_returns_200(self, auth_client: TestClient):
        """A new email should be added and return 200."""
        response = auth_client.post(
            "/api/v1/auth/waitlist",
            json={"email": "new@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["already_registered"] is False
        assert "waitlist" in data["message"].lower()

    def test_new_email_stored_in_db(self, auth_client: TestClient, db_session_factory):
        """A new signup should create a WaitlistEntry row in the database."""
        auth_client.post(
            "/api/v1/auth/waitlist",
            json={"email": "stored@example.com"},
        )

        async def _check():
            async with db_session_factory() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(WaitlistEntry).where(WaitlistEntry.email == "stored@example.com")
                )
                return result.scalar_one_or_none()

        entry = _run(_check())
        assert entry is not None
        assert entry.status == "pending"

    def test_duplicate_email_returns_200_already_registered(self, auth_client: TestClient):
        """A duplicate signup should return 200 with already_registered=True."""
        auth_client.post("/api/v1/auth/waitlist", json={"email": "dup@example.com"})
        response = auth_client.post("/api/v1/auth/waitlist", json={"email": "dup@example.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["already_registered"] is True

    def test_invalid_email_returns_422(self, auth_client: TestClient):
        """An invalid email address should return 422 validation error."""
        response = auth_client.post(
            "/api/v1/auth/waitlist",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422

    def test_missing_email_returns_422(self, auth_client: TestClient):
        """Omitting the email field should return 422."""
        response = auth_client.post("/api/v1/auth/waitlist", json={})
        assert response.status_code == 422


# ─── Admin Waitlist List Endpoint Tests ───────────────────────────────────


class TestListWaitlist:
    """Tests for GET /api/v1/admin/waitlist."""

    def test_returns_200(self, admin_client: TestClient):
        """Admin waitlist list should return 200."""
        response = admin_client.get("/api/v1/admin/waitlist")
        assert response.status_code == 200

    def test_paginated_structure(self, admin_client: TestClient):
        """Response should include entries, total, page, per_page."""
        response = admin_client.get("/api/v1/admin/waitlist")
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["entries"], list)

    def test_includes_seeded_entry(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry
    ):
        """A seeded entry should appear in the list."""
        response = admin_client.get("/api/v1/admin/waitlist")
        data = response.json()
        emails = [e["email"] for e in data["entries"]]
        assert seeded_waitlist_entry.email in emails

    def test_status_filter(self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry):
        """Filtering by status=pending should return only pending entries."""
        response = admin_client.get("/api/v1/admin/waitlist?status=pending")
        data = response.json()
        assert all(e["status"] == "pending" for e in data["entries"])

    def test_status_filter_no_match(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry
    ):
        """Filtering by status=registered should return 0 entries when none exist."""
        response = admin_client.get("/api/v1/admin/waitlist?status=registered")
        data = response.json()
        assert data["total"] == 0

    def test_pagination_defaults(self, admin_client: TestClient):
        """Default page=1, per_page=50 should be reflected in response."""
        response = admin_client.get("/api/v1/admin/waitlist")
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 50


# ─── Admin Waitlist Invite Endpoint Tests ─────────────────────────────────


class TestInviteWaitlistEntries:
    """Tests for POST /api/v1/admin/waitlist/invite."""

    def test_invite_pending_entry_returns_201(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry
    ):
        """Inviting a pending entry should return 201."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            response = admin_client.post(
                "/api/v1/admin/waitlist/invite",
                json={"entry_ids": [seeded_waitlist_entry.id], "expires_in_days": 7},
            )
        assert response.status_code == 201

    def test_invite_creates_invite_code_and_updates_status(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry, db_session_factory
    ):
        """Inviting should create an InviteCode and set status to invited."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            response = admin_client.post(
                "/api/v1/admin/waitlist/invite",
                json={"entry_ids": [seeded_waitlist_entry.id]},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_invited"] == 1
        assert data["total_emails_sent"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["entry_id"] == seeded_waitlist_entry.id
        assert len(data["results"][0]["invite_code"]) > 8

    def test_invite_skips_non_pending_entries(
        self, admin_client: TestClient, db_session_factory
    ):
        """Non-pending entries should be skipped and counted in total_skipped."""

        async def _create_invited():
            async with db_session_factory() as session:
                entry = WaitlistEntry(email="already-invited@example.com", status="invited")
                session.add(entry)
                await session.commit()
                await session.refresh(entry)
                return entry

        invited_entry = _run(_create_invited())

        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            response = admin_client.post(
                "/api/v1/admin/waitlist/invite",
                json={"entry_ids": [invited_entry.id]},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_invited"] == 0
        assert data["total_skipped"] == 1

    def test_invite_email_failure_still_returns_201(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry
    ):
        """Email failure should not block the response — code is still created."""
        with patch.object(
            admin_module, "send_invitation_email", new=AsyncMock(return_value=False)
        ):
            response = admin_client.post(
                "/api/v1/admin/waitlist/invite",
                json={"entry_ids": [seeded_waitlist_entry.id]},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_emails_sent"] == 0
        assert data["results"][0]["email_sent"] is False

    def test_invite_empty_entry_ids_returns_422(self, admin_client: TestClient):
        """Providing an empty entry_ids list should return 422."""
        response = admin_client.post(
            "/api/v1/admin/waitlist/invite",
            json={"entry_ids": []},
        )
        assert response.status_code == 422


# ─── Admin Waitlist Delete Endpoint Tests ─────────────────────────────────


class TestDeleteWaitlistEntry:
    """Tests for DELETE /api/v1/admin/waitlist/{entry_id}."""

    def test_delete_existing_entry_returns_204(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry
    ):
        """Deleting an existing entry should return 204."""
        response = admin_client.delete(
            f"/api/v1/admin/waitlist/{seeded_waitlist_entry.id}"
        )
        assert response.status_code == 204

    def test_delete_removes_entry_from_list(
        self, admin_client: TestClient, seeded_waitlist_entry: WaitlistEntry
    ):
        """After deletion the entry should not appear in the list."""
        admin_client.delete(f"/api/v1/admin/waitlist/{seeded_waitlist_entry.id}")
        response = admin_client.get("/api/v1/admin/waitlist")
        emails = [e["email"] for e in response.json()["entries"]]
        assert seeded_waitlist_entry.email not in emails

    def test_delete_nonexistent_entry_returns_404(self, admin_client: TestClient):
        """Deleting a non-existent entry should return 404."""
        response = admin_client.delete("/api/v1/admin/waitlist/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

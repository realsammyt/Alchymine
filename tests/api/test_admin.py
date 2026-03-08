"""Tests for admin panel API endpoints.

Uses an in-memory SQLite database and overrides both ``get_current_admin``
and the admin router's ``get_db`` so no external services are needed.

The ``_audit`` helper in the admin router writes to ``AdminAuditLog`` which
uses a ``BigInteger`` primary key.  SQLite only supports autoincrement for a
column declared as exactly ``INTEGER PRIMARY KEY``; ``BIGINT`` disables that
and produces a NOT NULL violation.  We patch ``_audit`` to a no-op in all
tests so the write-path tests exercise the real business logic without
tripping over this SQLite limitation (production runs PostgreSQL which
handles BigInteger autoincrement correctly).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alchymine.api.auth import get_current_admin
from alchymine.api.main import app
from alchymine.api.routers import admin as admin_module
from alchymine.db.base import Base
from alchymine.db.models import InviteCode, User

# ─── Helpers ──────────────────────────────────────────────────────────────


def _make_real_admin(session_factory) -> User:
    """Insert and return a real admin User row via a synchronous helper.

    We run this with asyncio so we can use the same in-memory engine that the
    test overrides point to.
    """
    import asyncio

    async def _create() -> User:
        async with session_factory() as session:
            user = User(
                id="admin-1",
                email="admin@test.com",
                is_admin=True,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return asyncio.run(_create())


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_audit():
    """Patch the admin router's _audit helper to a no-op async function.

    AdminAuditLog uses BigInteger PK which SQLite only supports as autoincrement
    when declared as INTEGER (not BIGINT).  Production runs PostgreSQL; this
    patch lets the test DB stay SQLite without schema changes.
    """
    with patch.object(admin_module, "_audit", new=AsyncMock(return_value=None)):
        yield


@pytest.fixture(autouse=True)
def _override_admin_db():
    """Override the admin router's get_db with an in-memory SQLite session.

    Also seeds the schema and yields a (engine, session_factory) pair so
    other fixtures can insert test data into the same database.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    import asyncio

    async def _init_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init_schema())

    async def _get_test_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[admin_module.get_db] = _get_test_db

    # Expose session_factory on the fixture value so other fixtures can use it
    _override_admin_db.session_factory = session_factory  # type: ignore[attr-defined]

    yield session_factory

    app.dependency_overrides.pop(admin_module.get_db, None)


@pytest.fixture(autouse=True)
def _override_admin_auth(_override_admin_db):
    """Override get_current_admin to return a real User row from the test DB."""
    session_factory = _override_admin_db
    admin_user = _make_real_admin(session_factory)
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    yield admin_user
    app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def client() -> TestClient:
    """Return a synchronous TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def seeded_invite_code(_override_admin_db) -> InviteCode:
    """Insert an unused InviteCode and return it."""
    import asyncio

    session_factory = _override_admin_db

    async def _create():
        async with session_factory() as session:
            code = InviteCode(
                code="TEST-CODE-123",
                created_by="admin-1",
                max_uses=5,
            )
            session.add(code)
            await session.commit()
            await session.refresh(code)
            return code

    return asyncio.run(_create())


# ─── Analytics ────────────────────────────────────────────────────────────


class TestAnalyticsOverview:
    """Tests for GET /api/v1/admin/analytics/overview."""

    def test_analytics_overview_returns_200(self, client: TestClient):
        """Overview endpoint should return 200 with all expected keys."""
        response = client.get("/api/v1/admin/analytics/overview")
        assert response.status_code == 200

    def test_analytics_overview_has_expected_keys(self, client: TestClient):
        """Response should contain all aggregate statistic fields."""
        response = client.get("/api/v1/admin/analytics/overview")
        data = response.json()
        expected_keys = {
            "total_users",
            "active_users",
            "admin_users",
            "new_users_today",
            "new_users_week",
            "new_users_month",
            "total_invite_codes",
            "active_invite_codes",
            "total_reports",
            "total_journal_entries",
        }
        assert expected_keys.issubset(data.keys())

    def test_analytics_overview_counts_seeded_user(self, client: TestClient):
        """total_users should reflect the seeded admin user."""
        response = client.get("/api/v1/admin/analytics/overview")
        data = response.json()
        # The admin fixture inserts one user into the test DB
        assert data["total_users"] >= 1
        assert data["admin_users"] >= 1


class TestAnalyticsUsers:
    """Tests for GET /api/v1/admin/analytics/users."""

    def test_analytics_users_returns_200(self, client: TestClient):
        """Analytics users endpoint should return 200."""
        response = client.get("/api/v1/admin/analytics/users")
        assert response.status_code == 200

    def test_analytics_users_has_daily_counts(self, client: TestClient):
        """Response should contain daily_counts list and period_days."""
        response = client.get("/api/v1/admin/analytics/users")
        data = response.json()
        assert "daily_counts" in data
        assert "period_days" in data
        assert isinstance(data["daily_counts"], list)

    def test_analytics_users_default_period_is_30_days(self, client: TestClient):
        """Default period should be 30 days producing 30 daily count entries."""
        response = client.get("/api/v1/admin/analytics/users")
        data = response.json()
        assert data["period_days"] == 30
        assert len(data["daily_counts"]) == 30

    def test_analytics_users_custom_period(self, client: TestClient):
        """Custom days=7 should return 7 daily count entries."""
        response = client.get("/api/v1/admin/analytics/users?days=7")
        data = response.json()
        assert data["period_days"] == 7
        assert len(data["daily_counts"]) == 7


# ─── User Management ──────────────────────────────────────────────────────


class TestListUsers:
    """Tests for GET /api/v1/admin/users."""

    def test_list_users_returns_200(self, client: TestClient):
        """List users endpoint should return 200."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 200

    def test_list_users_paginated_structure(self, client: TestClient):
        """Response should have users, total, page, and per_page fields."""
        response = client.get("/api/v1/admin/users")
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["users"], list)

    def test_list_users_includes_seeded_admin(self, client: TestClient):
        """The seeded admin user should appear in the list."""
        response = client.get("/api/v1/admin/users")
        data = response.json()
        assert data["total"] >= 1
        ids = [u["id"] for u in data["users"]]
        assert "admin-1" in ids

    def test_list_users_default_pagination(self, client: TestClient):
        """Default page=1, per_page=20 should be reflected in the response."""
        response = client.get("/api/v1/admin/users")
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 20

    def test_list_users_sort_invalid_column_defaults_safely(self, client: TestClient):
        """An invalid sort_by column should fall back to created_at, not leak model attributes."""
        response = client.get("/api/v1/admin/users?sort_by=password_hash")
        assert response.status_code == 200
        # Should still return users (fell back to created_at), not error or expose password_hash
        data = response.json()
        assert "users" in data


class TestListUsersWithSearch:
    """Tests for GET /api/v1/admin/users?search=..."""

    def test_search_matches_email(self, client: TestClient):
        """Search by admin email substring should return matching users."""
        response = client.get("/api/v1/admin/users?search=admin@test")
        data = response.json()
        assert data["total"] >= 1
        assert all("admin" in (u["email"] or "") for u in data["users"])

    def test_search_no_match_returns_empty(self, client: TestClient):
        """Search that matches nothing should return an empty users list."""
        response = client.get("/api/v1/admin/users?search=zzz-no-match-zzz")
        data = response.json()
        assert data["total"] == 0
        assert data["users"] == []


class TestGetUserDetail:
    """Tests for GET /api/v1/admin/users/{user_id}."""

    def test_get_existing_user_returns_200(self, client: TestClient):
        """Requesting the seeded admin user should return 200."""
        response = client.get("/api/v1/admin/users/admin-1")
        assert response.status_code == 200

    def test_get_existing_user_detail_fields(self, client: TestClient):
        """Detail response should include profile-presence flags."""
        response = client.get("/api/v1/admin/users/admin-1")
        data = response.json()
        assert data["id"] == "admin-1"
        assert data["email"] == "admin@test.com"
        assert data["is_admin"] is True
        for flag in ("has_intake", "has_identity", "has_healing", "has_wealth", "has_creative", "has_perspective"):
            assert flag in data

    def test_get_nonexistent_user_returns_404(self, client: TestClient):
        """Requesting an unknown user ID should return 404."""
        response = client.get("/api/v1/admin/users/does-not-exist")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ─── Invite Codes ─────────────────────────────────────────────────────────


class TestCreateInviteCode:
    """Tests for POST /api/v1/admin/invite-codes."""

    def test_create_invite_code_returns_201(self, client: TestClient):
        """Creating an invite code should return 201."""
        response = client.post(
            "/api/v1/admin/invite-codes",
            json={"code": "MY-CODE-001", "max_uses": 3},
        )
        assert response.status_code == 201

    def test_create_invite_code_response_fields(self, client: TestClient):
        """Response should include id, code, and usage tracking fields."""
        response = client.post(
            "/api/v1/admin/invite-codes",
            json={"code": "MY-CODE-002", "max_uses": 1},
        )
        data = response.json()
        assert data["code"] == "MY-CODE-002"
        assert data["max_uses"] == 1
        assert data["uses_count"] == 0
        assert "id" in data
        assert "created_at" in data

    def test_create_invite_code_auto_generate(self, client: TestClient):
        """Omitting the code field should auto-generate a non-empty code."""
        response = client.post(
            "/api/v1/admin/invite-codes",
            json={"max_uses": 1},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"]  # non-empty string
        assert len(data["code"]) > 8


class TestBulkCreateInviteCodes:
    """Tests for POST /api/v1/admin/invite-codes/bulk."""

    def test_bulk_create_returns_201(self, client: TestClient):
        """Bulk create should return 201."""
        response = client.post(
            "/api/v1/admin/invite-codes/bulk",
            json={"count": 3, "max_uses": 1},
        )
        assert response.status_code == 201

    def test_bulk_create_correct_count(self, client: TestClient):
        """Bulk create with count=3 should return exactly 3 codes."""
        response = client.post(
            "/api/v1/admin/invite-codes/bulk",
            json={"count": 3, "max_uses": 1},
        )
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_bulk_create_codes_are_unique(self, client: TestClient):
        """All bulk-created codes should have unique values."""
        response = client.post(
            "/api/v1/admin/invite-codes/bulk",
            json={"count": 5, "max_uses": 2},
        )
        codes = [item["code"] for item in response.json()]
        assert len(set(codes)) == 5

    def test_bulk_create_with_note(self, client: TestClient):
        """Bulk create with a note should apply the note to all codes."""
        response = client.post(
            "/api/v1/admin/invite-codes/bulk",
            json={"count": 2, "max_uses": 1, "note": "test batch"},
        )
        data = response.json()
        assert all(item["note"] == "test batch" for item in data)


class TestListInviteCodes:
    """Tests for GET /api/v1/admin/invite-codes."""

    def test_list_invite_codes_returns_200(self, client: TestClient):
        """List invite codes should return 200."""
        response = client.get("/api/v1/admin/invite-codes")
        assert response.status_code == 200

    def test_list_invite_codes_paginated_structure(self, client: TestClient):
        """Response should have codes, total, page, per_page."""
        response = client.get("/api/v1/admin/invite-codes")
        data = response.json()
        assert "codes" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_list_invite_codes_includes_seeded_code(
        self, client: TestClient, seeded_invite_code: InviteCode
    ):
        """The seeded invite code should appear in the list."""
        response = client.get("/api/v1/admin/invite-codes")
        data = response.json()
        assert data["total"] >= 1
        found_codes = [c["code"] for c in data["codes"]]
        assert seeded_invite_code.code in found_codes


class TestDeleteInviteCode:
    """Tests for DELETE /api/v1/admin/invite-codes/{code_id}."""

    def test_delete_unused_code_returns_204(
        self, client: TestClient, seeded_invite_code: InviteCode
    ):
        """Deleting an unused invite code should return 204."""
        response = client.delete(f"/api/v1/admin/invite-codes/{seeded_invite_code.id}")
        assert response.status_code == 204

    def test_delete_removes_code_from_list(
        self, client: TestClient, seeded_invite_code: InviteCode
    ):
        """After deletion, the code should not appear in the list."""
        client.delete(f"/api/v1/admin/invite-codes/{seeded_invite_code.id}")
        response = client.get("/api/v1/admin/invite-codes")
        codes = [c["code"] for c in response.json()["codes"]]
        assert seeded_invite_code.code not in codes

    def test_delete_nonexistent_code_returns_404(self, client: TestClient):
        """Deleting a non-existent code ID should return 404."""
        response = client.delete("/api/v1/admin/invite-codes/99999")
        assert response.status_code == 404


# ─── Auth Guard ───────────────────────────────────────────────────────────


# ─── Invite by Email ─────────────────────────────────────────────────────


class TestInviteByEmail:
    """Tests for POST /api/v1/admin/invite."""

    def test_invite_single_email_returns_201(self, client: TestClient):
        """Inviting a single email should return 201 with results."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            response = client.post(
                "/api/v1/admin/invite",
                json={"emails": ["newuser@example.com"]},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_invited"] == 1
        assert data["total_emails_sent"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["email"] == "newuser@example.com"
        assert data["results"][0]["email_sent"] is True
        assert len(data["results"][0]["invite_code"]) > 8

    def test_invite_multiple_emails(self, client: TestClient):
        """Inviting multiple emails should create one invite code per email."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            response = client.post(
                "/api/v1/admin/invite",
                json={
                    "emails": ["a@example.com", "b@example.com", "c@example.com"],
                    "note": "batch test",
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_invited"] == 3
        assert data["total_emails_sent"] == 3
        # All invite codes should be unique
        codes = [r["invite_code"] for r in data["results"]]
        assert len(set(codes)) == 3

    def test_invite_creates_invite_codes_in_db(self, client: TestClient):
        """Invite codes should be visible in the invite codes list after creation."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            invite_resp = client.post(
                "/api/v1/admin/invite",
                json={"emails": ["dbcheck@example.com"]},
            )
        assert invite_resp.status_code == 201
        code = invite_resp.json()["results"][0]["invite_code"]

        # Verify the code appears in the invite codes list
        list_resp = client.get("/api/v1/admin/invite-codes")
        all_codes = [c["code"] for c in list_resp.json()["codes"]]
        assert code in all_codes

    def test_invite_code_note_contains_email(self, client: TestClient):
        """The created invite code's note should reference the invited email."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            invite_resp = client.post(
                "/api/v1/admin/invite",
                json={"emails": ["noted@example.com"], "note": "VIP"},
            )
        code_value = invite_resp.json()["results"][0]["invite_code"]

        list_resp = client.get("/api/v1/admin/invite-codes")
        matching = [c for c in list_resp.json()["codes"] if c["code"] == code_value]
        assert len(matching) == 1
        assert "noted@example.com" in matching[0]["note"]
        assert "VIP" in matching[0]["note"]

    def test_invite_email_failure_still_creates_code(self, client: TestClient):
        """If email sending fails, the invite code should still be created."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=False)):
            response = client.post(
                "/api/v1/admin/invite",
                json={"emails": ["noemail@example.com"]},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["total_invited"] == 1
        assert data["total_emails_sent"] == 0
        assert data["results"][0]["email_sent"] is False
        # Code should still exist
        assert len(data["results"][0]["invite_code"]) > 8

    def test_invite_invalid_email_returns_422(self, client: TestClient):
        """Providing an invalid email should return 422."""
        response = client.post(
            "/api/v1/admin/invite",
            json={"emails": ["not-an-email"]},
        )
        assert response.status_code == 422

    def test_invite_empty_emails_returns_422(self, client: TestClient):
        """Providing an empty emails list should return 422."""
        response = client.post(
            "/api/v1/admin/invite",
            json={"emails": []},
        )
        assert response.status_code == 422

    def test_invite_with_custom_expiry(self, client: TestClient):
        """Inviting with a custom expiry should create codes that expire accordingly."""
        with patch.object(admin_module, "send_invitation_email", new=AsyncMock(return_value=True)):
            response = client.post(
                "/api/v1/admin/invite",
                json={"emails": ["expiry@example.com"], "expires_in_days": 30},
            )
        assert response.status_code == 201
        code_value = response.json()["results"][0]["invite_code"]

        list_resp = client.get("/api/v1/admin/invite-codes")
        matching = [c for c in list_resp.json()["codes"] if c["code"] == code_value]
        assert len(matching) == 1
        assert matching[0]["expires_at"] is not None

    def test_invite_calls_email_service_with_correct_args(self, client: TestClient):
        """The email service should be called with the correct email and invite code."""
        mock_send = AsyncMock(return_value=True)
        with patch.object(admin_module, "send_invitation_email", new=mock_send):
            response = client.post(
                "/api/v1/admin/invite",
                json={"emails": ["verify@example.com"]},
            )
        assert response.status_code == 201
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "verify@example.com"
        assert isinstance(call_args[0][1], str)  # invite code
        assert call_args[1]["invited_by"] == "admin@test.com"


class TestAdminAuthGuard:
    """Verify that admin endpoints reject unauthenticated/non-admin callers."""

    def test_endpoints_require_admin(self):
        """Removing the admin override should cause admin endpoints to return 401 or 403."""
        # Temporarily remove the admin override installed by autouse fixture
        app.dependency_overrides.pop(get_current_admin, None)
        try:
            # Use a fresh client with no auth headers
            test_client = TestClient(app, raise_server_exceptions=False)
            response = test_client.get("/api/v1/admin/users")
            assert response.status_code in (401, 403)
        finally:
            # Restore will be handled by the autouse fixture on next test
            pass

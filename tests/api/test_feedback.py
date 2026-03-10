"""Tests for the feedback API router.

Covers public submission (POST /api/v1/feedback) and admin management
endpoints (GET /api/v1/admin/feedback, PATCH /api/v1/admin/feedback/{id}).

Uses an in-memory SQLite database and overrides both ``get_db_session`` and
``get_current_admin`` so no external services are needed.

Email notification is patched to a no-op to prevent real SMTP calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — ensure all models are registered
from alchymine.api.auth import get_current_admin
from alchymine.api.deps import get_db_session
from alchymine.api.main import app
from alchymine.db.base import Base
from alchymine.db.models import User

# ── Helpers ────────────────────────────────────────────────────────────────


def _build_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )


async def _init_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _make_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _make_admin_user(session_factory) -> User:
    """Insert a real admin User row into the test DB."""

    async def _create() -> User:
        async with session_factory() as session:
            user = User(
                id="admin-test-1",
                email="admin@feedback.test",
                is_admin=True,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return asyncio.run(_create())


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def _db_session_factory():
    """Create an in-memory SQLite engine, seed the schema, and yield the factory."""
    engine = _build_engine()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_init_schema(engine))
    loop.close()

    factory = _make_session_factory(engine)
    return factory, engine


@pytest.fixture
def client(_db_session_factory) -> TestClient:
    """TestClient with get_db_session overridden to use an in-memory SQLite DB.

    get_current_admin is also overridden to return a real admin User row so
    admin endpoints work without JWT validation.
    """
    factory, engine = _db_session_factory
    admin_user = _make_admin_user(factory)

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_current_admin] = lambda: admin_user

    tc = TestClient(app)
    yield tc

    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_admin, None)


# ── POST /api/v1/feedback ──────────────────────────────────────────────────


class TestSubmitFeedback:
    """Tests for POST /api/v1/feedback (public, no auth required)."""

    def test_submit_feedback_anonymous(self, client: TestClient) -> None:
        """Anonymous submission with category + message should return 201."""
        with patch(
            "alchymine.email.send_feedback_notification_email", new=AsyncMock(return_value=True)
        ):
            response = client.post(
                "/api/v1/feedback",
                json={"category": "bug", "message": "Something is broken on the home page."},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "bug"
        assert data["message"] == "Something is broken on the home page."
        assert data["status"] == "new"
        assert data["email"] is None
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_submit_feedback_with_email(self, client: TestClient) -> None:
        """Submission with optional email should persist and return the email."""
        with patch(
            "alchymine.email.send_feedback_notification_email", new=AsyncMock(return_value=True)
        ):
            response = client.post(
                "/api/v1/feedback",
                json={
                    "category": "feature",
                    "message": "Please add dark mode to the dashboard.",
                    "email": "user@example.com",
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["category"] == "feature"

    def test_submit_feedback_invalid_category_coerced(self, client: TestClient) -> None:
        """An unrecognised category value should be coerced to 'general'."""
        with patch(
            "alchymine.email.send_feedback_notification_email", new=AsyncMock(return_value=True)
        ):
            response = client.post(
                "/api/v1/feedback",
                json={
                    "category": "totally-invalid-category",
                    "message": "This is my feedback message.",
                },
            )
        assert response.status_code == 201
        assert response.json()["category"] == "general"

    def test_submit_feedback_message_too_short(self, client: TestClient) -> None:
        """A message shorter than 10 characters should return 422."""
        response = client.post(
            "/api/v1/feedback",
            json={"category": "general", "message": "Short"},
        )
        assert response.status_code == 422


# ── GET /api/v1/admin/feedback ─────────────────────────────────────────────


class TestAdminListFeedback:
    """Tests for GET /api/v1/admin/feedback."""

    def _seed_entry(
        self, client: TestClient, *, message: str = "Test feedback entry here.", **kwargs
    ) -> dict:
        """Submit a feedback entry and return the response dict."""
        payload = {"category": "general", "message": message, **kwargs}
        with patch(
            "alchymine.email.send_feedback_notification_email", new=AsyncMock(return_value=True)
        ):
            resp = client.post("/api/v1/feedback", json=payload)
        assert resp.status_code == 201
        return resp.json()

    def test_admin_list_feedback(self, client: TestClient) -> None:
        """Admin can list feedback; seeded entry should appear in the response."""
        self._seed_entry(client, message="Admin list test entry here.")
        response = client.get("/api/v1/admin/feedback")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert data["total"] >= 1
        assert isinstance(data["entries"], list)

    def test_admin_list_feedback_filter_by_status(self, client: TestClient) -> None:
        """Filtering by status=new should return only entries with that status."""
        self._seed_entry(client, message="Status filter test entry here.")
        response = client.get("/api/v1/admin/feedback?status=new")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for entry in data["entries"]:
            assert entry["status"] == "new"


# ── PATCH /api/v1/admin/feedback/{id} ─────────────────────────────────────


class TestAdminPatchFeedback:
    """Tests for PATCH /api/v1/admin/feedback/{entry_id}."""

    def _seed_entry(self, client: TestClient) -> int:
        """Submit a feedback entry and return its id."""
        with patch(
            "alchymine.email.send_feedback_notification_email", new=AsyncMock(return_value=True)
        ):
            resp = client.post(
                "/api/v1/feedback",
                json={"category": "general", "message": "Patch test feedback entry here."},
            )
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_admin_patch_feedback_status(self, client: TestClient) -> None:
        """Admin can update status and add an admin_note; changes persist in response."""
        entry_id = self._seed_entry(client)
        response = client.patch(
            f"/api/v1/admin/feedback/{entry_id}",
            json={"status": "reviewed", "admin_note": "Acknowledged and logged."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reviewed"
        assert data["admin_note"] == "Acknowledged and logged."
        assert data["id"] == entry_id

    def test_admin_patch_feedback_invalid_status(self, client: TestClient) -> None:
        """PATCH with an invalid status value should return 422."""
        entry_id = self._seed_entry(client)
        response = client.patch(
            f"/api/v1/admin/feedback/{entry_id}",
            json={"status": "not-a-real-status"},
        )
        assert response.status_code == 422


# ── Auth guards ────────────────────────────────────────────────────────────


class TestAdminAuthGuards:
    """Admin endpoints must reject unauthenticated callers."""

    def test_admin_list_requires_auth(self, _db_session_factory) -> None:
        """GET /admin/feedback without auth should return 401."""
        factory, engine = _db_session_factory

        async def _override_db() -> AsyncGenerator[AsyncSession, None]:
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db_session] = _override_db
        app.dependency_overrides.pop(get_current_admin, None)
        try:
            tc = TestClient(app, raise_server_exceptions=False)
            response = tc.get("/api/v1/admin/feedback")
            assert response.status_code in (401, 403)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

    def test_admin_patch_requires_auth(self, _db_session_factory) -> None:
        """PATCH /admin/feedback/{id} without auth should return 401."""
        factory, engine = _db_session_factory

        async def _override_db() -> AsyncGenerator[AsyncSession, None]:
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db_session] = _override_db
        app.dependency_overrides.pop(get_current_admin, None)
        try:
            tc = TestClient(app, raise_server_exceptions=False)
            response = tc.patch("/api/v1/admin/feedback/1", json={"status": "reviewed"})
            assert response.status_code in (401, 403)
        finally:
            app.dependency_overrides.pop(get_db_session, None)

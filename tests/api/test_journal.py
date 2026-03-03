"""Tests for Journal API endpoints.

Covers:
- CRUD operations for journal entries
- Listing with filters and pagination
- Journal statistics
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import alchymine.db.models  # noqa: F401
from alchymine.api.deps import get_db_session
from alchymine.api.main import app
from alchymine.db.base import Base


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a valid Fernet key is available for encryption in tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient wired to an in-memory SQLite engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create tables synchronously before entering the async context
    loop = asyncio.new_event_loop()
    loop.run_until_complete(_create_tables(engine))

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_get_db_session
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.pop(get_db_session, None)

    loop.run_until_complete(engine.dispose())
    loop.close()


async def _create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class TestJournalCreate:
    """POST /api/v1/journal"""

    def test_create_entry_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "title": "My first reflection",
                "content": "Today I started my journey.",
            },
        )
        assert response.status_code == 201

    def test_create_entry_returns_data(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "system": "healing",
                "entry_type": "gratitude",
                "title": "Grateful for progress",
                "content": "I completed my first breathwork session.",
                "tags": ["breathwork", "progress"],
                "mood_score": 8,
            },
        )
        data = response.json()
        assert data["user_id"] == "user-1"
        assert data["system"] == "healing"
        assert data["entry_type"] == "gratitude"
        assert data["title"] == "Grateful for progress"
        assert data["mood_score"] == 8
        assert "id" in data
        assert "created_at" in data

    def test_create_entry_defaults(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "title": "Quick note",
                "content": "A general reflection.",
            },
        )
        data = response.json()
        assert data["system"] == "general"
        assert data["entry_type"] == "reflection"
        assert data["mood_score"] is None
        assert data["tags"] == []


class TestJournalRead:
    """GET /api/v1/journal/{entry_id}"""

    def test_get_entry(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "title": "Test entry",
                "content": "Content here.",
            },
        )
        entry_id = create_resp.json()["id"]
        response = client.get(f"/api/v1/journal/{entry_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test entry"

    def test_get_nonexistent_entry(self, client: TestClient) -> None:
        response = client.get("/api/v1/journal/nonexistent-id")
        assert response.status_code == 404


class TestJournalUpdate:
    """PUT /api/v1/journal/{entry_id}"""

    def test_update_entry(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "title": "Original title",
                "content": "Original content.",
            },
        )
        entry_id = create_resp.json()["id"]

        response = client.put(
            f"/api/v1/journal/{entry_id}",
            json={"title": "Updated title", "mood_score": 9},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated title"
        assert data["mood_score"] == 9
        assert data["content"] == "Original content."

    def test_update_nonexistent_entry(self, client: TestClient) -> None:
        response = client.put(
            "/api/v1/journal/nonexistent-id",
            json={"title": "Won't work"},
        )
        assert response.status_code == 404


class TestJournalDelete:
    """DELETE /api/v1/journal/{entry_id}"""

    def test_delete_entry(self, client: TestClient) -> None:
        create_resp = client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "title": "To delete",
                "content": "Will be removed.",
            },
        )
        entry_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/journal/{entry_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/api/v1/journal/{entry_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_entry(self, client: TestClient) -> None:
        response = client.delete("/api/v1/journal/nonexistent-id")
        assert response.status_code == 404


class TestJournalList:
    """GET /api/v1/journal"""

    def test_list_entries(self, client: TestClient) -> None:
        for i in range(3):
            client.post(
                "/api/v1/journal",
                json={
                    "user_id": "user-1",
                    "title": f"Entry {i}",
                    "content": f"Content {i}",
                },
            )

        response = client.get("/api/v1/journal?user_id=user-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["entries"]) == 3

    def test_list_filters_by_system(self, client: TestClient) -> None:
        client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "system": "healing",
                "title": "Healing note",
                "content": "Healing content.",
            },
        )
        client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "system": "wealth",
                "title": "Wealth note",
                "content": "Wealth content.",
            },
        )

        response = client.get("/api/v1/journal?user_id=user-1&system=healing")
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["system"] == "healing"

    def test_list_filters_by_entry_type(self, client: TestClient) -> None:
        client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "entry_type": "reframe",
                "title": "Reframe",
                "content": "A cognitive reframe.",
            },
        )
        client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "entry_type": "gratitude",
                "title": "Gratitude",
                "content": "Thankful for today.",
            },
        )

        response = client.get("/api/v1/journal?user_id=user-1&entry_type=reframe")
        data = response.json()
        assert data["total"] == 1
        assert data["entries"][0]["entry_type"] == "reframe"

    def test_list_pagination(self, client: TestClient) -> None:
        for i in range(5):
            client.post(
                "/api/v1/journal",
                json={
                    "user_id": "user-1",
                    "title": f"Entry {i}",
                    "content": f"Content {i}",
                },
            )

        response = client.get("/api/v1/journal?user_id=user-1&page=1&per_page=2")
        data = response.json()
        assert data["total"] == 5
        assert len(data["entries"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2

    def test_list_denied_for_other_user(self, client: TestClient) -> None:
        """Authenticated user cannot list another user's journal entries."""
        client.post(
            "/api/v1/journal",
            json={
                "user_id": "user-1",
                "title": "User 1 only",
                "content": "Content.",
            },
        )

        response = client.get("/api/v1/journal?user_id=user-2")
        assert response.status_code == 403


class TestJournalStats:
    """GET /api/v1/journal/stats/{user_id}"""

    def test_stats_empty_user(self, client: TestClient) -> None:
        response = client.get("/api/v1/journal/stats/user-1")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 0
        assert data["average_mood"] is None

    def test_stats_with_entries(self, client: TestClient) -> None:
        for system, mood in [("healing", 7), ("wealth", 8), ("healing", 9)]:
            client.post(
                "/api/v1/journal",
                json={
                    "user_id": "user-1",
                    "system": system,
                    "title": f"{system} entry",
                    "content": "Content.",
                    "mood_score": mood,
                    "tags": [system, "progress"],
                },
            )

        response = client.get("/api/v1/journal/stats/user-1")
        data = response.json()
        assert data["total_entries"] == 3
        assert data["entries_by_system"]["healing"] == 2
        assert data["entries_by_system"]["wealth"] == 1
        assert data["average_mood"] == 8.0
        assert "healing" in data["tags_used"]
        assert "progress" in data["tags_used"]

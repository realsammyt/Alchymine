"""Tests for the profile CRUD API router.

Uses an in-memory SQLite database via ``app.dependency_overrides`` to inject
a test session into all endpoints that depend on ``get_db_session``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Import all models so Base.metadata is populated
import alchymine.db.models  # noqa: F401
from alchymine.api.deps import get_db_session
from alchymine.db.base import Base

# ─── Test fixtures ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a valid Fernet key is available for encryption in tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an in-memory SQLite async engine with schema."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return a session factory bound to the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with DB dependency overridden."""
    from alchymine.api.main import app

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Helpers ───────────────────────────────────────────────────────────

_VALID_PROFILE = {
    "full_name": "Maria Elena Vasquez",
    "birth_date": "1992-03-15",
    "intention": "family",
}

_FULL_PROFILE = {
    "full_name": "Maria Elena Vasquez",
    "birth_date": "1992-03-15",
    "birth_time": "14:14:00",
    "birth_city": "Mexico City",
    "intention": "family",
    "assessment_responses": {"big_five_1": 4, "big_five_2": 2},
    "family_structure": "single parent",
}


# ─── POST /api/v1/profile — Create ────────────────────────────────────


@pytest.mark.asyncio
async def test_create_profile_minimal(client: AsyncClient) -> None:
    """POST with only required fields returns 201 with profile data."""
    resp = await client.post("/api/v1/profile", json=_VALID_PROFILE)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["version"] == "2.0"
    assert data["intake"]["full_name"] == "Maria Elena Vasquez"
    assert data["intake"]["birth_date"] == "1992-03-15"
    assert data["intake"]["intention"] == "family"


@pytest.mark.asyncio
async def test_create_profile_full(client: AsyncClient) -> None:
    """POST with all fields populates intake completely."""
    resp = await client.post("/api/v1/profile", json=_FULL_PROFILE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["intake"]["birth_time"] == "14:14:00"
    assert data["intake"]["birth_city"] == "Mexico City"
    assert data["intake"]["assessment_responses"]["big_five_1"] == 4
    assert data["intake"]["family_structure"] == "single parent"


@pytest.mark.asyncio
async def test_create_profile_validation_missing_name(client: AsyncClient) -> None:
    """POST without full_name returns 422 validation error."""
    resp = await client.post(
        "/api/v1/profile",
        json={
            "birth_date": "1992-03-15",
            "intention": "family",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_validation_missing_birth_date(client: AsyncClient) -> None:
    """POST without birth_date returns 422 validation error."""
    resp = await client.post(
        "/api/v1/profile",
        json={
            "full_name": "Test User",
            "intention": "career",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_validation_short_name(client: AsyncClient) -> None:
    """POST with name shorter than 2 chars returns 422."""
    resp = await client.post(
        "/api/v1/profile",
        json={
            "full_name": "X",
            "birth_date": "1992-03-15",
            "intention": "career",
        },
    )
    assert resp.status_code == 422


# ─── GET /api/v1/profile/{user_id} — Read ─────────────────────────────


@pytest.mark.asyncio
async def test_get_profile_found(client: AsyncClient) -> None:
    """GET returns the created profile."""
    create_resp = await client.post("/api/v1/profile", json=_VALID_PROFILE)
    user_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/profile/{user_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == user_id
    assert data["intake"]["full_name"] == "Maria Elena Vasquez"


@pytest.mark.asyncio
async def test_get_profile_not_found(client: AsyncClient) -> None:
    """GET for non-existent user returns 404."""
    resp = await client.get("/api/v1/profile/nonexistent-uuid")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ─── GET /api/v1/profiles — List ──────────────────────────────────────


@pytest.mark.asyncio
async def test_list_profiles_empty(client: AsyncClient) -> None:
    """GET /profiles returns empty list when no profiles exist."""
    resp = await client.get("/api/v1/profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["profiles"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_list_profiles_populated(client: AsyncClient) -> None:
    """GET /profiles returns all created profiles."""
    for i in range(3):
        await client.post(
            "/api/v1/profile",
            json={
                "full_name": f"User {i}",
                "birth_date": "2000-01-01",
                "intention": "career",
            },
        )

    resp = await client.get("/api/v1/profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["profiles"]) == 3


@pytest.mark.asyncio
async def test_list_profiles_pagination(client: AsyncClient) -> None:
    """GET /profiles with offset and limit paginates correctly."""
    for i in range(5):
        await client.post(
            "/api/v1/profile",
            json={
                "full_name": f"User {i}",
                "birth_date": "2000-01-01",
                "intention": "career",
            },
        )

    resp = await client.get("/api/v1/profiles?offset=2&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["offset"] == 2
    assert data["limit"] == 2


# ─── PUT /api/v1/profile/{user_id}/{layer} — Update Layer ─────────────


@pytest.mark.asyncio
async def test_update_layer_identity(client: AsyncClient) -> None:
    """PUT creates an identity layer on an existing profile."""
    create_resp = await client.post("/api/v1/profile", json=_VALID_PROFILE)
    user_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/profile/{user_id}/identity",
        json={
            "data": {
                "numerology": {"life_path": 7, "expression": 3},
                "astrology": {"sun_sign": "Pisces"},
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["identity"] is not None
    assert data["identity"]["numerology"]["life_path"] == 7
    assert data["identity"]["astrology"]["sun_sign"] == "Pisces"


@pytest.mark.asyncio
async def test_update_layer_healing(client: AsyncClient) -> None:
    """PUT creates a healing layer on an existing profile."""
    create_resp = await client.post("/api/v1/profile", json=_VALID_PROFILE)
    user_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/profile/{user_id}/healing",
        json={
            "data": {
                "selected_modalities": [{"modality": "breathwork"}],
                "max_difficulty": "developing",
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["healing"] is not None
    assert data["healing"]["max_difficulty"] == "developing"


@pytest.mark.asyncio
async def test_update_layer_invalid_layer_name(client: AsyncClient) -> None:
    """PUT with unknown layer name returns 422."""
    create_resp = await client.post("/api/v1/profile", json=_VALID_PROFILE)
    user_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/profile/{user_id}/nonexistent",
        json={"data": {"foo": "bar"}},
    )
    assert resp.status_code == 422
    assert "Unknown layer" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_layer_user_not_found(client: AsyncClient) -> None:
    """PUT for non-existent user returns 404."""
    resp = await client.put(
        "/api/v1/profile/fake-uuid/identity",
        json={"data": {"numerology": {"life_path": 1}}},
    )
    assert resp.status_code == 404
    assert "No user" in resp.json()["detail"]


# ─── DELETE /api/v1/profile/{user_id} — Delete ────────────────────────


@pytest.mark.asyncio
async def test_delete_profile_success(client: AsyncClient) -> None:
    """DELETE removes the profile and returns confirmation."""
    create_resp = await client.post("/api/v1/profile", json=_VALID_PROFILE)
    user_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/profile/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Profile deleted"

    # Verify deleted
    get_resp = await client.get(f"/api/v1/profile/{user_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile_not_found(client: AsyncClient) -> None:
    """DELETE for non-existent user returns 404."""
    resp = await client.delete("/api/v1/profile/nonexistent-uuid")
    assert resp.status_code == 404


# ─── Full lifecycle ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_crud_lifecycle(client: AsyncClient) -> None:
    """End-to-end: create, read, update layer, list, delete."""
    # 1. Create
    create_resp = await client.post("/api/v1/profile", json=_FULL_PROFILE)
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # 2. Read
    get_resp = await client.get(f"/api/v1/profile/{user_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["intake"]["full_name"] == "Maria Elena Vasquez"

    # 3. Update identity layer
    put_resp = await client.put(
        f"/api/v1/profile/{user_id}/identity",
        json={
            "data": {
                "numerology": {"life_path": 3, "expression": 6},
                "astrology": {"sun_sign": "Pisces", "moon_sign": "Scorpio"},
            }
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["identity"]["numerology"]["life_path"] == 3

    # 4. Update healing layer
    put_resp2 = await client.put(
        f"/api/v1/profile/{user_id}/healing",
        json={
            "data": {
                "selected_modalities": [{"modality": "breathwork"}],
                "max_difficulty": "developing",
            }
        },
    )
    assert put_resp2.status_code == 200

    # 5. List — should contain 1 profile
    list_resp = await client.get("/api/v1/profiles")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1

    # 6. Delete
    del_resp = await client.delete(f"/api/v1/profile/{user_id}")
    assert del_resp.status_code == 200

    # 7. List — should be empty
    list_resp2 = await client.get("/api/v1/profiles")
    assert list_resp2.status_code == 200
    assert list_resp2.json()["count"] == 0


# ─── Reports endpoint still works with DB ─────────────────────────────


@pytest.mark.asyncio
async def test_reports_post_with_db(client: AsyncClient) -> None:
    """POST /reports creates a report in the database."""
    resp = await client.post(
        "/api/v1/reports",
        json={
            "intake": {
                "full_name": "Maria Elena Vasquez",
                "birth_date": "1992-03-15",
                "intention": "family",
            },
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert "id" in data


@pytest.mark.asyncio
async def test_reports_get_not_found_with_db(client: AsyncClient) -> None:
    """GET /reports/{id} for non-existent ID returns 404."""
    resp = await client.get("/api/v1/reports/nonexistent-id")
    assert resp.status_code == 404

"""Tests for health check endpoint."""

from __future__ import annotations

import os

os.environ.setdefault("CELERY_ALWAYS_EAGER", "true")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import alchymine.db.models  # noqa: F401,E402
from alchymine.api.deps import get_db_session, set_db_engine  # noqa: E402
from alchymine.api.main import app  # noqa: E402
from alchymine.db.base import Base  # noqa: E402
from alchymine.workers.tasks import _set_task_engine  # noqa: E402


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a valid Fernet key is available."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine and initialise the schema."""
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


@pytest.fixture
def client(engine) -> TestClient:
    """Provide a TestClient wired to the in-memory SQLite engine."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_session
    set_db_engine(engine)
    _set_task_engine(engine)

    yield TestClient(app)

    app.dependency_overrides.clear()
    set_db_engine(None)
    _set_task_engine(None)


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    # 200 when DB+Redis are available, 503 when degraded (e.g. test env)
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "alchymine-api"
    assert "version" in data


def test_numerology_endpoint_exists(client: TestClient) -> None:
    response = client.get("/api/v1/numerology/John%20Smith?birth_date=1990-03-15")
    # May return 501 (not implemented) or 200 -- but not 404
    assert response.status_code in (200, 501)


def test_astrology_endpoint_exists(client: TestClient) -> None:
    response = client.get("/api/v1/astrology/1992-03-15")
    assert response.status_code == 200
    data = response.json()
    assert data["sun_sign"] == "Pisces"


def test_reports_post_returns_202(client: TestClient) -> None:
    response = client.post(
        "/api/v1/reports",
        json={
            "intake": {
                "full_name": "Maria Elena Vasquez",
                "birth_date": "1992-03-15",
                "intention": "family",
            },
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "id" in data


def test_reports_get_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/reports/nonexistent-id")
    assert response.status_code == 404

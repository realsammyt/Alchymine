"""Tests for the per-user daily cap on POST /art/generate.

Image generation is the one endpoint where a single logged-in user can
run up a bill on their own, so it carries a per-user daily cap on top of
the global breaker. Exhausting it is a normal state, not a failure: the
response has to tell the client both *what* happened and *when* to come
back, in a form it can render without printing an error.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session, set_db_engine
from alchymine.api.main import app
from alchymine.api.routers.generative_art import _gemini_dependency
from alchymine.db.base import Base
from alchymine.db.models import User
from alchymine.db.usage_counters import METER_ART_GENERATIONS, get_count
from alchymine.llm.gemini import GeminiImageResult

TEST_USER_ID = "user-1"
OTHER_USER_ID = "user-cap-other"


def _image() -> GeminiImageResult:
    return GeminiImageResult(
        image_bytes=b"\x89PNG\r\n\x1a\n",
        mime_type="image/png",
        prompt="a serene forest",
        model="gemini-test",
        generated_at=datetime.now(UTC),
    )


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient where the route and the cost meter share one SQLite DB.

    Both must point at the same engine: the route reads the user through
    the injected session while the meter opens its own session from the
    ``deps`` singleton, exactly as they do in production.
    """
    monkeypatch.setenv("ART_CACHE_DIR", str(tmp_path))

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _setup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            session.add(User(id=TEST_USER_ID, email="cap@example.com", is_active=True))
            session.add(User(id=OTHER_USER_ID, email="other@example.com", is_active=True))
            await session.commit()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_setup())

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    gemini = MagicMock()
    gemini.is_available = True
    gemini.generate_image = AsyncMock(side_effect=lambda _prompt: _image())

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[_gemini_dependency] = lambda: gemini
    set_db_engine(engine)

    tc = TestClient(app)
    tc.gemini = gemini  # type: ignore[attr-defined] — handy for call assertions
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(_gemini_dependency, None)
        set_db_engine(None)
        loop.run_until_complete(engine.dispose())
        loop.close()


def _as_user(user_id: str) -> None:
    async def _current() -> dict:
        return {"sub": user_id, "email": f"{user_id}@example.com"}

    app.dependency_overrides[get_current_user] = _current


class TestDailyCap:
    def test_allows_generations_up_to_the_cap(self, client: TestClient) -> None:
        from alchymine.config import get_settings

        cap = get_settings().daily_art_generations_per_user
        for _ in range(cap):
            assert client.post("/api/v1/art/generate", json={}).status_code == 201

    def test_blocks_the_generation_past_the_cap(self, client: TestClient) -> None:
        from alchymine.config import get_settings

        cap = get_settings().daily_art_generations_per_user
        for _ in range(cap):
            client.post("/api/v1/art/generate", json={})

        response = client.post("/api/v1/art/generate", json={})
        assert response.status_code == 429

    def test_capped_response_is_machine_readable(self, client: TestClient) -> None:
        from alchymine.config import get_settings

        for _ in range(get_settings().daily_art_generations_per_user):
            client.post("/api/v1/art/generate", json={})

        detail = client.post("/api/v1/art/generate", json={}).json()["detail"]
        assert detail["code"] == "daily_art_cap_reached"
        assert datetime.fromisoformat(detail["retry_at"]) > datetime.now(UTC)
        # Shown to a person, so it follows the house copy rules.
        assert "—" not in detail["message"]
        for banned in ("delve", "leverage", "robust", "seamless", "utilize", "ensure"):
            assert banned not in detail["message"].lower()

    def test_capped_request_never_reaches_gemini(self, client: TestClient) -> None:
        from alchymine.config import get_settings

        cap = get_settings().daily_art_generations_per_user
        for _ in range(cap):
            client.post("/api/v1/art/generate", json={})
        calls_before = client.gemini.generate_image.call_count  # type: ignore[attr-defined]

        client.post("/api/v1/art/generate", json={})

        assert client.gemini.generate_image.call_count == calls_before  # type: ignore[attr-defined]

    def test_cap_is_per_user(self, client: TestClient) -> None:
        from alchymine.config import get_settings

        cap = get_settings().daily_art_generations_per_user
        for _ in range(cap):
            client.post("/api/v1/art/generate", json={})
        assert client.post("/api/v1/art/generate", json={}).status_code == 429

        _as_user(OTHER_USER_ID)
        try:
            # A different user starts with a full allowance.
            assert client.post("/api/v1/art/generate", json={}).status_code == 201
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_cap_resets_on_the_next_utc_day(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from alchymine.config import get_settings

        cap = get_settings().daily_art_generations_per_user
        for _ in range(cap):
            client.post("/api/v1/art/generate", json={})
        assert client.post("/api/v1/art/generate", json={}).status_code == 429

        monkeypatch.setattr(
            "alchymine.db.usage_counters.current_period_key",
            lambda *_args, **_kwargs: "2099-01-01",
        )
        assert client.post("/api/v1/art/generate", json={}).status_code == 201

    def test_unavailable_gemini_does_not_spend_the_allowance(
        self, client: TestClient
    ) -> None:
        """A 204 costs nothing, so it must not burn one of the day's three."""
        client.gemini.is_available = False  # type: ignore[attr-defined]

        assert client.post("/api/v1/art/generate", json={}).status_code == 204

        counted = asyncio.run(
            get_count(scope=TEST_USER_ID, meter=METER_ART_GENERATIONS)
        )
        assert counted == 0

"""Tests for how a tripped cost breaker reaches the user.

The breaker itself is tested in ``tests/llm/test_cost_breaker.py``. What
matters here is the surface: every cost-bearing route must turn a tripped
breaker into a clear "temporarily unavailable, try again later" state.
Never a raw 500, never a swallowed error, never canned text passed off as
a real answer.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import alchymine.db.models  # noqa: F401 — register models with metadata
from alchymine.api.deps import get_db_session
from alchymine.api.main import app
from alchymine.api.routers.generative_art import _gemini_dependency
from alchymine.db.base import Base
from alchymine.db.models import User
from alchymine.db.usage_counters import CostCeilingExceeded

TEST_USER_ID = "user-1"


def _tripped() -> CostCeilingExceeded:
    return CostCeilingExceeded(
        meter="llm_calls",
        scope="global",
        retry_at=datetime.now(UTC) + timedelta(hours=2),
    )


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
def client() -> TestClient:
    """TestClient wired to an in-memory SQLite DB with the test user seeded."""
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
            session.add(User(id=TEST_USER_ID, email="breaker@example.com", is_active=True))
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

    app.dependency_overrides[get_db_session] = _override_session
    tc = TestClient(app)
    try:
        yield tc
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        loop.run_until_complete(engine.dispose())
        loop.close()


class TestArtRouteSurface:
    def test_tripped_breaker_returns_service_unavailable(self, client: TestClient) -> None:
        gemini = MagicMock()
        gemini.is_available = True
        gemini.generate_image = AsyncMock(side_effect=_tripped())
        app.dependency_overrides[_gemini_dependency] = lambda: gemini
        try:
            response = client.post("/api/v1/art/generate", json={})
        finally:
            app.dependency_overrides.pop(_gemini_dependency, None)

        assert response.status_code == 503

    def test_tripped_breaker_body_is_machine_readable(self, client: TestClient) -> None:
        gemini = MagicMock()
        gemini.is_available = True
        gemini.generate_image = AsyncMock(side_effect=_tripped())
        app.dependency_overrides[_gemini_dependency] = lambda: gemini
        try:
            response = client.post("/api/v1/art/generate", json={})
        finally:
            app.dependency_overrides.pop(_gemini_dependency, None)

        detail = response.json()["detail"]
        assert detail["code"] == "llm_temporarily_unavailable"
        # Shape, not just presence: the client parses this to show a countdown.
        retry_at = datetime.fromisoformat(detail["retry_at"])
        assert retry_at.tzinfo is not None
        assert retry_at > datetime.now(UTC)
        # The message is shown to a person, so it must read like one wrote it.
        assert "—" not in detail["message"]
        assert "try again later" in detail["message"].lower()

    def test_tripped_breaker_is_not_a_raw_500(self, client: TestClient) -> None:
        """The generic error middleware must not get to claim this one."""
        gemini = MagicMock()
        gemini.is_available = True
        gemini.generate_image = AsyncMock(side_effect=_tripped())
        app.dependency_overrides[_gemini_dependency] = lambda: gemini
        try:
            response = client.post("/api/v1/art/generate", json={})
        finally:
            app.dependency_overrides.pop(_gemini_dependency, None)

        assert response.status_code != 500
        assert "An unexpected error occurred" not in response.text


class TestDegradedLedgerSurface:
    """A ledger that cannot record spend blocks the next paid call.

    It reaches the user through the machinery a tripped breaker already
    uses: a 503 with a machine-readable code, not a 500 and not a silent
    success that spends money nobody can account for.
    """

    def _art_call(self, client: TestClient, *, degraded: bool):  # noqa: ANN202
        """POST the art route through the real charge_paid_call guard.

        Both counter paths — the per-user art cap in the router and the
        global call breaker in the guard — are stubbed to healthy. That
        matters: an unreachable counter fails closed on its own and returns
        the same 503, so without the stubs this would pass whether or not
        the degraded-ledger block exists.
        """
        from unittest.mock import patch

        from alchymine.db.usage_counters import clear_ledger_degraded, mark_ledger_degraded
        from alchymine.llm.cost_guard import charge_paid_call

        async def _generate(prompt: str) -> None:
            await charge_paid_call()
            return None

        gemini = MagicMock()
        gemini.is_available = True
        gemini.generate_image = _generate
        app.dependency_overrides[_gemini_dependency] = lambda: gemini

        clear_ledger_degraded()
        if degraded:
            mark_ledger_degraded("insert failed")
        consume = AsyncMock(return_value=1)
        try:
            with (
                patch("alchymine.llm.cost_guard.consume", consume),
                patch("alchymine.api.routers.generative_art.consume", AsyncMock(return_value=1)),
                patch("alchymine.api.routers.generative_art.refund", AsyncMock()),
            ):
                response = client.post("/api/v1/art/generate", json={})
        finally:
            clear_ledger_degraded()
            app.dependency_overrides.pop(_gemini_dependency, None)
        return response, consume

    def test_a_healthy_ledger_lets_the_call_through(self, client: TestClient) -> None:
        """The control. Without it, an unrelated 503 would look like a pass."""
        response, consume = self._art_call(client, degraded=False)

        assert response.status_code != 503
        assert consume.await_count == 1

    def test_a_degraded_ledger_renders_as_the_existing_503(self, client: TestClient) -> None:
        response, consume = self._art_call(client, degraded=True)

        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "llm_temporarily_unavailable"
        # Blocked means not attempted: the call meter is never touched.
        assert consume.await_count == 0

    def test_the_503_body_leaks_no_internal_detail(self, client: TestClient) -> None:
        response, _ = self._art_call(client, degraded=True)

        for leak in ("Traceback", "CostCeilingExceeded", "meter_unavailable", "ledger"):
            assert leak not in response.text


class TestChatStreamSurface:
    def test_tripped_breaker_emits_an_unavailable_frame(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The SSE stream already started, so the state ships as an error frame."""

        async def _blocked(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            raise _tripped()
            yield ""  # pragma: no cover — makes this an async generator

        monkeypatch.setattr(
            "alchymine.api.routers.chat.LLMClient.stream_generate",
            _blocked,
        )

        with client.stream("POST", "/api/v1/chat", json={"message": "hello there"}) as response:
            body = "".join(response.iter_text())

        assert "event: error" in body
        assert "try again later" in body.lower()
        # The generic "Streaming failed" catch-all must not swallow this.
        assert "Streaming failed" not in body

    def test_unavailable_frame_carries_no_internal_detail(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _blocked(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            raise _tripped()
            yield ""  # pragma: no cover

        monkeypatch.setattr(
            "alchymine.api.routers.chat.LLMClient.stream_generate",
            _blocked,
        )

        with client.stream("POST", "/api/v1/chat", json={"message": "hello there"}) as response:
            body = "".join(response.iter_text())

        for leak in ("Traceback", "CostCeilingExceeded", "llm_calls", "global"):
            assert leak not in body

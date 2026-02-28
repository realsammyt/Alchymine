"""Tests for HTML report export endpoint and renderer.

Covers:
- HTML renderer produces valid HTML
- GET /reports/{id}/html endpoint
- HTML content structure
"""

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
from alchymine.db import repository  # noqa: E402
from alchymine.db.base import Base  # noqa: E402
from alchymine.engine.reports.html_renderer import render_report_html  # noqa: E402
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


def _seed_report(engine, report_id: str, status: str, result: dict | None = None) -> None:
    """Seed a report row into the test database."""
    import asyncio

    from alchymine.db.base import get_async_session_factory

    async def _seed():
        factory = get_async_session_factory(engine)
        async with factory() as session:
            await repository.create_report(
                session,
                report_id=report_id,
                status=status,
                user_input="test",
            )
            if result is not None or status in ("complete", "failed"):
                await repository.update_report_content(
                    session,
                    report_id,
                    result=result,
                    status=status,
                )
            await session.commit()

    try:
        asyncio.get_running_loop()
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, _seed()).result()
    except RuntimeError:
        asyncio.run(_seed())


@pytest.fixture
def sample_report_data() -> dict:
    """A completed report dict for the HTML renderer (render_report_html)."""
    return {
        "report_id": "test-report-123",
        "status": "complete",
        "created_at": "2026-02-28T12:00:00+00:00",
        "updated_at": "2026-02-28T12:01:00+00:00",
        "result": {
            "profile_summary": {
                "identity": {
                    "numerology": {
                        "life_path": 7,
                        "expression": 3,
                        "soul_urge": 5,
                        "personality": 8,
                        "personal_year": 4,
                        "maturity": 1,
                        "is_master_number": False,
                    },
                    "astrology": {
                        "sun_sign": "Pisces",
                        "moon_sign": "Leo",
                        "rising_sign": "Virgo",
                        "mercury_retrograde": True,
                        "venus_retrograde": False,
                    },
                    "archetype": {
                        "primary": "sage",
                        "secondary": "explorer",
                        "shadow": "Detachment",
                        "light_qualities": ["Wisdom", "Insight", "Analysis"],
                        "shadow_qualities": ["Isolation", "Overthinking"],
                    },
                    "personality": {
                        "big_five": {
                            "openness": 85,
                            "conscientiousness": 70,
                            "extraversion": 35,
                            "agreeableness": 65,
                            "neuroticism": 30,
                        },
                        "attachment_style": "secure",
                        "enneagram_type": 5,
                        "enneagram_wing": 4,
                    },
                    "strengths_map": [
                        "Analytical Thinking",
                        "Creative Vision",
                        "Deep Focus",
                    ],
                },
            },
            "quality_passed": True,
        },
    }


@pytest.fixture
def sample_result_data(sample_report_data: dict) -> dict:
    """The result dict portion for seeding into DB."""
    return sample_report_data["result"]


class TestHtmlRenderer:
    """Tests for alchymine.engine.reports.html_renderer."""

    def test_render_returns_string(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert isinstance(result, str)

    def test_render_is_html(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "</html>" in result

    def test_render_contains_report_id(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "test-report-123" in result

    def test_render_contains_numerology(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "Life Path" in result
        assert "Expression" in result
        assert "Soul Urge" in result

    def test_render_contains_astrology(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "Pisces" in result
        assert "Leo" in result
        assert "Mercury Retrograde" in result

    def test_render_contains_archetype(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "Sage" in result
        assert "Explorer" in result
        assert "Detachment" in result

    def test_render_contains_personality(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "Openness" in result
        assert "Conscientiousness" in result

    def test_render_contains_strengths(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "Analytical Thinking" in result
        assert "Deep Focus" in result

    def test_render_contains_print_button(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "window.print()" in result

    def test_render_contains_footer(self, sample_report_data: dict) -> None:
        result = render_report_html(sample_report_data)
        assert "CC-BY-NC-SA 4.0" in result
        assert "deterministic" in result.lower()

    def test_render_empty_report(self) -> None:
        result = render_report_html({"report_id": "empty", "status": "complete"})
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result


class TestHtmlExportEndpoint:
    """Tests for GET /api/v1/reports/{report_id}/html"""

    def test_html_export_returns_200(
        self, client: TestClient, engine, sample_result_data: dict
    ) -> None:
        _seed_report(engine, "test-123", "complete", sample_result_data)
        response = client.get("/api/v1/reports/test-123/html")
        assert response.status_code == 200

    def test_html_export_content_type(
        self, client: TestClient, engine, sample_result_data: dict
    ) -> None:
        _seed_report(engine, "test-123", "complete", sample_result_data)
        response = client.get("/api/v1/reports/test-123/html")
        assert "text/html" in response.headers["content-type"]

    def test_html_export_contains_html(
        self, client: TestClient, engine, sample_result_data: dict
    ) -> None:
        _seed_report(engine, "test-123", "complete", sample_result_data)
        response = client.get("/api/v1/reports/test-123/html")
        assert "<!DOCTYPE html>" in response.text
        assert "Alchymine Report" in response.text

    def test_html_export_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/reports/nonexistent/html")
        assert response.status_code == 404

    def test_html_export_still_generating(self, client: TestClient, engine) -> None:
        _seed_report(engine, "generating-id", "generating")
        response = client.get("/api/v1/reports/generating-id/html")
        assert response.status_code == 202

    def test_html_export_pending(self, client: TestClient, engine) -> None:
        _seed_report(engine, "pending-id", "pending")
        response = client.get("/api/v1/reports/pending-id/html")
        assert response.status_code == 202

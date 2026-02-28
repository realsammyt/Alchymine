"""Tests for PDF report generation and download.

Covers:
- PDFRenderer with mocked Playwright (no real browser required)
- Financial disclaimer injection
- Evidence metadata footer injection
- GET /api/v1/reports/{report_id}/pdf endpoint
- Celery generate_pdf_report task in eager mode
- PlaywrightNotAvailableError handling
"""

from __future__ import annotations

import os
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

# Enable Celery eager mode before any Celery imports
os.environ["CELERY_ALWAYS_EAGER"] = "true"

import importlib  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import alchymine.db.models  # noqa: F401, E402
import alchymine.workers.celery_app as celery_app_mod  # noqa: E402

importlib.reload(celery_app_mod)

from alchymine.api.deps import get_db_session, set_db_engine  # noqa: E402
from alchymine.api.main import app  # noqa: E402
from alchymine.db import repository  # noqa: E402
from alchymine.db.base import Base  # noqa: E402
from alchymine.engine.reports.pdf_renderer import (  # noqa: E402
    PDFRenderer,
    PlaywrightNotAvailableError,
    inject_evidence_footer,
    inject_financial_disclaimer,
)
from alchymine.workers.tasks import _set_task_engine, pdf_store  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Ensure a valid Fernet key is available."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ALCHYMINE_ENCRYPTION_KEY", key)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Wire up the task engine so Celery tasks use this DB
    _set_task_engine(eng)

    yield eng

    _set_task_engine(None)

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
def client(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session():
        async with factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_session
    set_db_engine(engine)
    _set_task_engine(engine)
    yield TestClient(app)
    app.dependency_overrides.clear()
    set_db_engine(None)
    _set_task_engine(None)


@pytest.fixture(autouse=True)
def _clear_pdf_store():
    pdf_store.clear()


@pytest.fixture
def sample_report_result():
    return {
        "profile_summary": {
            "identity": {
                "numerology": {
                    "life_path": 7, "expression": 3, "soul_urge": 5,
                    "personality": 8, "personal_year": 4, "maturity": 1,
                    "is_master_number": False,
                },
                "astrology": {
                    "sun_sign": "Pisces", "moon_sign": "Leo",
                    "rising_sign": "Virgo",
                },
                "archetype": {
                    "primary": "sage", "secondary": "explorer",
                    "shadow": "Detachment",
                },
                "personality": {
                    "big_five": {
                        "openness": 85, "conscientiousness": 70,
                        "extraversion": 35, "agreeableness": 65,
                        "neuroticism": 30,
                    },
                    "attachment_style": "secure",
                    "enneagram_type": 5, "enneagram_wing": 4,
                },
                "strengths_map": ["Analytical Thinking", "Creative Vision", "Deep Focus"],
            },
        },
        "coordinator_results": [],
        "quality_passed": True,
    }


@pytest.fixture
def wealth_report_result(sample_report_result):
    data = dict(sample_report_result)
    data["coordinator_results"] = [
        {"system": "wealth", "status": "complete", "data": {"net_worth": 100000}},
    ]
    return data


@pytest.fixture
def fake_pdf_bytes():
    return b"%PDF-1.4 fake pdf content for testing"


def _build_playwright_mocks(pdf_bytes, capture_fn=None):
    mock_page = AsyncMock()
    if capture_fn is not None:
        mock_page.set_content = AsyncMock(side_effect=capture_fn)
    else:
        mock_page.set_content = AsyncMock()
    mock_page.pdf = AsyncMock(return_value=pdf_bytes)

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_pw = AsyncMock()
    mock_pw.chromium = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return MagicMock(return_value=mock_cm), mock_page


def _patch_pw(mock_fn):
    fake = ModuleType("playwright")
    fake_async = ModuleType("playwright.async_api")
    fake_async.async_playwright = mock_fn  # type: ignore[attr-defined]
    return patch.dict(sys.modules, {"playwright": fake, "playwright.async_api": fake_async})


async def _seed_report(session, rid, result):
    await repository.create_report(session, report_id=rid, status="complete", user_input="test")
    await repository.update_report_content(session, rid, result=result, status="complete")
    await session.commit()


# ── Financial disclaimer tests ────────────────────────────────────────


class TestFinancialDisclaimerInjection:
    def test_injects_before_body_close(self):
        html = "<html><body><p>Hello</p></body></html>"
        result = inject_financial_disclaimer(html)
        assert "Financial Disclaimer" in result
        assert result.index("Financial Disclaimer") < result.index("</body>")

    def test_injects_when_no_body_tag(self):
        assert "Financial Disclaimer" in inject_financial_disclaimer("<html><p>Hi</p></html>")

    def test_disclaimer_contains_required_text(self):
        result = inject_financial_disclaimer("<html><body></body></html>")
        assert "educational and informational purposes" in result
        assert "does not constitute financial advice" in result
        assert "qualified financial advisor" in result

    def test_original_content_preserved(self):
        result = inject_financial_disclaimer("<html><body><p>My Report</p></body></html>")
        assert "<p>My Report</p>" in result


# ── Evidence footer tests ─────────────────────────────────────────────


class TestEvidenceFooterInjection:
    def test_injects_before_body_close(self):
        result = inject_evidence_footer("<html><body><p>Hello</p></body></html>")
        assert "deterministic algorithms" in result
        assert result.index("deterministic") < result.index("</body>")

    def test_injects_when_no_body_tag(self):
        assert "CC-BY-NC-SA 4.0" in inject_evidence_footer("<html><p>Hi</p></html>")

    def test_footer_contains_attribution(self):
        result = inject_evidence_footer("<html><body></body></html>")
        assert "Alchymine" in result
        assert "Evidence ratings" in result


# ── PDFRenderer tests ─────────────────────────────────────────────────


class TestPDFRenderer:
    @pytest.mark.asyncio
    async def test_render_pdf_returns_bytes(self, fake_pdf_bytes):
        fn, _ = _build_playwright_mocks(fake_pdf_bytes)
        with _patch_pw(fn):
            result = await PDFRenderer().render_pdf("<html><body>Test</body></html>")
        assert result == fake_pdf_bytes

    @pytest.mark.asyncio
    async def test_render_pdf_with_financial_disclaimer(self, fake_pdf_bytes):
        captured = []
        fn, _ = _build_playwright_mocks(fake_pdf_bytes, lambda h, **kw: captured.append(h))
        with _patch_pw(fn):
            await PDFRenderer().render_pdf("<html><body>R</body></html>", is_wealth_report=True)
        assert len(captured) == 1
        assert "Financial Disclaimer" in captured[0]

    @pytest.mark.asyncio
    async def test_render_pdf_with_evidence_footer(self, fake_pdf_bytes):
        captured = []
        fn, _ = _build_playwright_mocks(fake_pdf_bytes, lambda h, **kw: captured.append(h))
        with _patch_pw(fn):
            await PDFRenderer().render_pdf("<html><body>R</body></html>")
        assert len(captured) == 1
        assert "deterministic algorithms" in captured[0]

    @pytest.mark.asyncio
    async def test_render_pdf_writes_to_file(self, fake_pdf_bytes, tmp_path):
        out = str(tmp_path / "test.pdf")
        fn, _ = _build_playwright_mocks(fake_pdf_bytes)
        with _patch_pw(fn):
            result = await PDFRenderer().render_pdf("<html><body>T</body></html>", output_path=out)
        assert result == fake_pdf_bytes
        from pathlib import Path
        assert Path(out).read_bytes() == fake_pdf_bytes

    @pytest.mark.asyncio
    async def test_render_pdf_playwright_not_installed(self):
        with patch.dict(sys.modules, {"playwright": None, "playwright.async_api": None}):
            with pytest.raises(PlaywrightNotAvailableError, match="not installed"):
                await PDFRenderer().render_pdf("<html><body>T</body></html>")


# ── PDF endpoint tests ────────────────────────────────────────────────


class TestPdfEndpoint:
    @pytest.mark.asyncio
    async def test_pdf_returns_200(self, client, session, sample_report_result, fake_pdf_bytes):
        await _seed_report(session, "pdf-123", sample_report_result)
        pdf_store["pdf-123"] = fake_pdf_bytes
        resp = client.get("/api/v1/reports/pdf-123/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_pdf_attachment_header(self, client, session, sample_report_result, fake_pdf_bytes):
        await _seed_report(session, "pdf-123", sample_report_result)
        pdf_store["pdf-123"] = fake_pdf_bytes
        resp = client.get("/api/v1/reports/pdf-123/pdf")
        assert "attachment" in resp.headers["content-disposition"]
        assert "pdf-123" in resp.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_pdf_returns_bytes(self, client, session, sample_report_result, fake_pdf_bytes):
        await _seed_report(session, "pdf-123", sample_report_result)
        pdf_store["pdf-123"] = fake_pdf_bytes
        assert client.get("/api/v1/reports/pdf-123/pdf").content == fake_pdf_bytes

    def test_pdf_404_missing_report(self, client):
        resp = client.get("/api/v1/reports/nonexistent/pdf")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pdf_404_incomplete(self, client, session):
        await repository.create_report(session, report_id="gen-id", status="generating", user_input="t")
        await session.commit()
        resp = client.get("/api/v1/reports/gen-id/pdf")
        assert resp.status_code == 404
        assert "not complete" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pdf_404_not_generated(self, client, session, sample_report_result):
        await _seed_report(session, "pdf-123", sample_report_result)
        resp = client.get("/api/v1/reports/pdf-123/pdf")
        assert resp.status_code == 404
        assert "not been generated" in resp.json()["detail"].lower()


# ── Celery PDF task tests ─────────────────────────────────────────────


class TestGeneratePdfReportTask:
    def test_task_fails_missing(self):
        from alchymine.workers.tasks import generate_pdf_report

        async def ret_none(rid):
            return None

        with patch("alchymine.workers.tasks._db_get_report", side_effect=ret_none):
            result = generate_pdf_report("no-id")
        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()

    def test_task_fails_incomplete(self):
        from alchymine.workers.tasks import generate_pdf_report

        rpt = MagicMock(status="processing")

        async def ret(rid):
            return rpt

        with patch("alchymine.workers.tasks._db_get_report", side_effect=ret):
            result = generate_pdf_report("inc-id")
        assert result["status"] == "failed"
        assert "not complete" in result["error"].lower()

    def test_task_success(self, sample_report_result, fake_pdf_bytes):
        from alchymine.workers.tasks import generate_pdf_report

        rpt = MagicMock(id="pdf-123", status="complete", result=sample_report_result)
        rpt.created_at.isoformat.return_value = "2026-02-28T12:00:00+00:00"

        async def ret(rid):
            return rpt

        async def render(*a, **kw):
            return fake_pdf_bytes

        with (
            patch("alchymine.workers.tasks._db_get_report", side_effect=ret),
            patch("alchymine.engine.reports.pdf_renderer.PDFRenderer") as cls,
        ):
            cls.return_value.render_pdf = render
            result = generate_pdf_report("pdf-123")

        assert result["status"] == "complete"
        assert result["size_bytes"] == len(fake_pdf_bytes)
        assert pdf_store["pdf-123"] == fake_pdf_bytes

    def test_task_detects_wealth(self, wealth_report_result, fake_pdf_bytes):
        from alchymine.workers.tasks import generate_pdf_report

        rpt = MagicMock(id="w-1", status="complete", result=wealth_report_result)
        rpt.created_at.isoformat.return_value = "2026-02-28T12:00:00+00:00"
        kw_cap = {}

        async def ret(rid):
            return rpt

        async def render(*a, **kw):
            kw_cap.update(kw)
            return fake_pdf_bytes

        with (
            patch("alchymine.workers.tasks._db_get_report", side_effect=ret),
            patch("alchymine.engine.reports.pdf_renderer.PDFRenderer") as cls,
        ):
            cls.return_value.render_pdf = render
            result = generate_pdf_report("w-1")

        assert result["status"] == "complete"
        assert kw_cap.get("is_wealth_report") is True

    def test_task_handles_error(self, sample_report_result):
        from alchymine.workers.tasks import generate_pdf_report

        rpt = MagicMock(id="pdf-123", status="complete", result=sample_report_result)
        rpt.created_at.isoformat.return_value = "2026-02-28T12:00:00+00:00"

        async def ret(rid):
            return rpt

        async def render(*a, **kw):
            raise PlaywrightNotAvailableError("Playwright not installed")

        with (
            patch("alchymine.workers.tasks._db_get_report", side_effect=ret),
            patch("alchymine.engine.reports.pdf_renderer.PDFRenderer") as cls,
        ):
            cls.return_value.render_pdf = render
            result = generate_pdf_report("pdf-123")

        assert result["status"] == "failed"
        assert "not installed" in result["error"].lower()

"""Tests for HTML report export endpoint and renderer.

Covers:
- HTML renderer produces valid HTML
- GET /reports/{id}/html endpoint
- HTML content structure
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app
from alchymine.engine.reports.html_renderer import render_report_html
from alchymine.workers.tasks import report_store


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_store() -> None:
    """Clear report store between tests."""
    report_store.clear()


@pytest.fixture
def sample_report_data() -> dict:
    """A completed report with identity layer data."""
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

    def test_html_export_returns_200(self, client: TestClient, sample_report_data: dict) -> None:
        report_store["test-123"] = sample_report_data
        response = client.get("/api/v1/reports/test-123/html")
        assert response.status_code == 200

    def test_html_export_content_type(self, client: TestClient, sample_report_data: dict) -> None:
        report_store["test-123"] = sample_report_data
        response = client.get("/api/v1/reports/test-123/html")
        assert "text/html" in response.headers["content-type"]

    def test_html_export_contains_html(self, client: TestClient, sample_report_data: dict) -> None:
        report_store["test-123"] = sample_report_data
        response = client.get("/api/v1/reports/test-123/html")
        assert "<!DOCTYPE html>" in response.text
        assert "Alchymine Report" in response.text

    def test_html_export_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/reports/nonexistent/html")
        assert response.status_code == 404

    def test_html_export_still_processing(self, client: TestClient) -> None:
        report_store["processing-id"] = {
            "report_id": "processing-id",
            "status": "processing",
            "created_at": "2026-02-28T12:00:00+00:00",
        }
        response = client.get("/api/v1/reports/processing-id/html")
        assert response.status_code == 202

    def test_html_export_queued(self, client: TestClient) -> None:
        report_store["queued-id"] = {
            "report_id": "queued-id",
            "status": "queued",
            "created_at": "2026-02-28T12:00:00+00:00",
        }
        response = client.get("/api/v1/reports/queued-id/html")
        assert response.status_code == 202

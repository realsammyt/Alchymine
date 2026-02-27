"""Tests for Biorhythm API endpoints.

Covers:
- POST /api/v1/biorhythm/calculate — single-day calculation
- POST /api/v1/biorhythm/range — multi-day range
- POST /api/v1/biorhythm/compatibility — two-person comparison
- Response schema validation
- Evidence rating and methodology disclosure
- Error handling for invalid input
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/biorhythm/calculate — single day
# ═══════════════════════════════════════════════════════════════════════════


class TestBiorhythmCalculateEndpoint:
    """Tests for POST /api/v1/biorhythm/calculate."""

    def test_calculate_returns_200(self, client: TestClient) -> None:
        """POST /biorhythm/calculate returns 200 with valid input."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        assert response.status_code == 200

    def test_calculate_has_result_field(self, client: TestClient) -> None:
        """Response wraps the calculation in a 'result' field."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert "result" in data

    def test_calculate_result_has_cycle_values(self, client: TestClient) -> None:
        """Result includes physical, emotional, intellectual sine values."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        result = response.json()["result"]
        for field in ["physical", "emotional", "intellectual"]:
            assert field in result
            assert -1.0 <= result[field] <= 1.0

    def test_calculate_result_has_percentages(self, client: TestClient) -> None:
        """Result includes percentage values (0-100)."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        result = response.json()["result"]
        for field in ["physical_percentage", "emotional_percentage", "intellectual_percentage"]:
            assert field in result
            assert 0 <= result[field] <= 100

    def test_calculate_result_has_critical_flags(self, client: TestClient) -> None:
        """Result includes critical-day boolean flags."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        result = response.json()["result"]
        for field in ["is_physical_critical", "is_emotional_critical", "is_intellectual_critical"]:
            assert field in result
            assert isinstance(result[field], bool)

    def test_calculate_result_has_days_alive(self, client: TestClient) -> None:
        """Result includes days_alive count."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        result = response.json()["result"]
        assert result["days_alive"] == 12402

    def test_calculate_includes_evidence_rating(self, client: TestClient) -> None:
        """Response includes evidence_rating = 'LOW'."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert data["evidence_rating"] == "LOW"

    def test_calculate_includes_methodology_note(self, client: TestClient) -> None:
        """Response includes methodology disclosure string."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert "methodology_note" in data
        assert "not supported by scientific consensus" in data["methodology_note"]

    def test_calculate_target_before_birth_returns_400(self, client: TestClient) -> None:
        """Target date before birth date returns 400."""
        response = client.post(
            "/api/v1/biorhythm/calculate",
            json={
                "birth_date": "2026-02-27",
                "target_date": "1992-03-15",
            },
        )
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/biorhythm/range — multi-day range
# ═══════════════════════════════════════════════════════════════════════════


class TestBiorhythmRangeEndpoint:
    """Tests for POST /api/v1/biorhythm/range."""

    def test_range_returns_200(self, client: TestClient) -> None:
        """POST /biorhythm/range returns 200 with valid input."""
        response = client.post(
            "/api/v1/biorhythm/range",
            json={
                "birth_date": "1992-03-15",
                "start_date": "2026-02-27",
                "days": 7,
            },
        )
        assert response.status_code == 200

    def test_range_returns_correct_number_of_results(self, client: TestClient) -> None:
        """Response contains exactly the requested number of results."""
        response = client.post(
            "/api/v1/biorhythm/range",
            json={
                "birth_date": "1992-03-15",
                "start_date": "2026-02-27",
                "days": 7,
            },
        )
        data = response.json()
        assert len(data["results"]) == 7
        assert data["days_requested"] == 7

    def test_range_default_days_30(self, client: TestClient) -> None:
        """Default days value is 30."""
        response = client.post(
            "/api/v1/biorhythm/range",
            json={
                "birth_date": "1992-03-15",
                "start_date": "2026-02-27",
            },
        )
        data = response.json()
        assert len(data["results"]) == 30
        assert data["days_requested"] == 30

    def test_range_includes_evidence_rating(self, client: TestClient) -> None:
        """Range response includes evidence_rating."""
        response = client.post(
            "/api/v1/biorhythm/range",
            json={
                "birth_date": "1992-03-15",
                "start_date": "2026-02-27",
                "days": 3,
            },
        )
        data = response.json()
        assert data["evidence_rating"] == "LOW"

    def test_range_exceeding_365_returns_422(self, client: TestClient) -> None:
        """Days > 365 returns 422 validation error."""
        response = client.post(
            "/api/v1/biorhythm/range",
            json={
                "birth_date": "1992-03-15",
                "start_date": "2026-02-27",
                "days": 400,
            },
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/biorhythm/compatibility — two-person comparison
# ═══════════════════════════════════════════════════════════════════════════


class TestBiorhythmCompatibilityEndpoint:
    """Tests for POST /api/v1/biorhythm/compatibility."""

    def test_compatibility_returns_200(self, client: TestClient) -> None:
        """POST /biorhythm/compatibility returns 200 with valid input."""
        response = client.post(
            "/api/v1/biorhythm/compatibility",
            json={
                "birth_date_a": "1992-03-15",
                "birth_date_b": "1990-07-04",
                "target_date": "2026-02-27",
            },
        )
        assert response.status_code == 200

    def test_compatibility_has_both_persons(self, client: TestClient) -> None:
        """Response includes biorhythm results for both persons."""
        response = client.post(
            "/api/v1/biorhythm/compatibility",
            json={
                "birth_date_a": "1992-03-15",
                "birth_date_b": "1990-07-04",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert "person_a" in data
        assert "person_b" in data
        assert "physical" in data["person_a"]
        assert "physical" in data["person_b"]

    def test_compatibility_has_similarity_scores(self, client: TestClient) -> None:
        """Response includes similarity scores for each cycle."""
        response = client.post(
            "/api/v1/biorhythm/compatibility",
            json={
                "birth_date_a": "1992-03-15",
                "birth_date_b": "1990-07-04",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        for field in ["physical_similarity", "emotional_similarity", "intellectual_similarity"]:
            assert field in data
            assert isinstance(data[field], (int, float))

    def test_compatibility_has_overall_sync(self, client: TestClient) -> None:
        """Response includes overall_sync percentage."""
        response = client.post(
            "/api/v1/biorhythm/compatibility",
            json={
                "birth_date_a": "1992-03-15",
                "birth_date_b": "1990-07-04",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert "overall_sync" in data
        assert isinstance(data["overall_sync"], (int, float))

    def test_identical_birthdays_high_sync(self, client: TestClient) -> None:
        """Identical birth dates produce 100% sync."""
        response = client.post(
            "/api/v1/biorhythm/compatibility",
            json={
                "birth_date_a": "1992-03-15",
                "birth_date_b": "1992-03-15",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert data["overall_sync"] == 100.0

    def test_compatibility_includes_evidence_rating(self, client: TestClient) -> None:
        """Compatibility response includes evidence_rating."""
        response = client.post(
            "/api/v1/biorhythm/compatibility",
            json={
                "birth_date_a": "1992-03-15",
                "birth_date_b": "1990-07-04",
                "target_date": "2026-02-27",
            },
        )
        data = response.json()
        assert data["evidence_rating"] == "LOW"

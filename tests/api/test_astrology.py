"""Tests for Astrology API endpoints.

Covers:
- GET /api/v1/astrology/{birth_date} with valid date
- Optional query params (birth_time, birth_city)
- Response schema validation
- Known sun sign values
- Error handling for invalid dates
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/astrology/{birth_date} — basic requests
# ═══════════════════════════════════════════════════════════════════════════


class TestAstrologyGetEndpoint:
    """Tests for GET /api/v1/astrology/{birth_date}."""

    def test_get_astrology_returns_200(self, client: TestClient) -> None:
        """GET /astrology/{birth_date} returns 200 with valid date."""
        response = client.get("/api/v1/astrology/1992-03-15")
        assert response.status_code == 200

    def test_get_astrology_pisces(self, client: TestClient) -> None:
        """March 15 produces Pisces sun sign."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert data["sun_sign"] == "Pisces"

    def test_get_astrology_cancer(self, client: TestClient) -> None:
        """July 4 produces Cancer sun sign."""
        response = client.get("/api/v1/astrology/1990-07-04")
        data = response.json()
        assert data["sun_sign"] == "Cancer"

    def test_get_astrology_capricorn_december(self, client: TestClient) -> None:
        """December 25 produces Capricorn sun sign."""
        response = client.get("/api/v1/astrology/1985-12-25")
        data = response.json()
        assert data["sun_sign"] == "Capricorn"

    def test_get_astrology_capricorn_january(self, client: TestClient) -> None:
        """January 1 produces Capricorn sun sign."""
        response = client.get("/api/v1/astrology/2000-01-01")
        data = response.json()
        assert data["sun_sign"] == "Capricorn"

    def test_get_astrology_birth_date_in_response(self, client: TestClient) -> None:
        """Response includes the birth_date that was requested."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert data["birth_date"] == "1992-03-15"


# ═══════════════════════════════════════════════════════════════════════════
# Optional query parameters
# ═══════════════════════════════════════════════════════════════════════════


class TestAstrologyQueryParams:
    """Tests for optional birth_time and birth_city parameters."""

    def test_with_birth_time(self, client: TestClient) -> None:
        """Providing birth_time returns 200 (may include calculation_note)."""
        response = client.get(
            "/api/v1/astrology/1992-03-15",
            params={"birth_time": "14:14:00"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sun_sign"] == "Pisces"

    def test_with_birth_city(self, client: TestClient) -> None:
        """Providing birth_city returns 200."""
        response = client.get(
            "/api/v1/astrology/1992-03-15",
            params={"birth_city": "Mexico City"},
        )
        assert response.status_code == 200

    def test_with_both_time_and_city(self, client: TestClient) -> None:
        """Providing both birth_time and birth_city returns 200."""
        response = client.get(
            "/api/v1/astrology/1992-03-15",
            params={"birth_time": "14:14:00", "birth_city": "Mexico City"},
        )
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Response schema validation
# ═══════════════════════════════════════════════════════════════════════════


class TestAstrologyResponseSchema:
    """Validate the shape and types of the astrology response."""

    def test_response_has_all_required_fields(self, client: TestClient) -> None:
        """Response includes all AstrologyResponse fields."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        required_fields = {
            "sun_sign",
            "sun_degree",
            "moon_sign",
            "moon_degree",
            "birth_date",
        }
        assert required_fields.issubset(set(data.keys()))

    def test_response_has_optional_fields(self, client: TestClient) -> None:
        """Response includes optional fields (may be null)."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert "rising_sign" in data
        assert "rising_degree" in data
        assert "mercury_retrograde" in data
        assert "venus_retrograde" in data
        assert "calculation_note" in data

    def test_sun_degree_is_numeric(self, client: TestClient) -> None:
        """sun_degree is a float."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert isinstance(data["sun_degree"], (int, float))

    def test_moon_degree_is_numeric(self, client: TestClient) -> None:
        """moon_degree is a float."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert isinstance(data["moon_degree"], (int, float))

    def test_retrograde_fields_are_bool(self, client: TestClient) -> None:
        """mercury_retrograde and venus_retrograde are booleans."""
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert isinstance(data["mercury_retrograde"], bool)
        assert isinstance(data["venus_retrograde"], bool)

    def test_sun_sign_is_valid_zodiac(self, client: TestClient) -> None:
        """sun_sign is one of the 12 zodiac signs."""
        valid_signs = {
            "Aries",
            "Taurus",
            "Gemini",
            "Cancer",
            "Leo",
            "Virgo",
            "Libra",
            "Scorpio",
            "Sagittarius",
            "Capricorn",
            "Aquarius",
            "Pisces",
        }
        response = client.get("/api/v1/astrology/1992-03-15")
        data = response.json()
        assert data["sun_sign"] in valid_signs


# ═══════════════════════════════════════════════════════════════════════════
# Error handling
# ═══════════════════════════════════════════════════════════════════════════


class TestAstrologyErrors:
    """Tests for error cases."""

    def test_invalid_date_format_returns_422(self, client: TestClient) -> None:
        """Invalid date format returns 422."""
        response = client.get("/api/v1/astrology/not-a-date")
        assert response.status_code == 422

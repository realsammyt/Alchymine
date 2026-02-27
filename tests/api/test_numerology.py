"""Tests for Numerology API endpoints.

Covers:
- GET /api/v1/numerology/{name} with valid name
- GET /api/v1/numerology/{name} with birth_date query param
- GET /api/v1/numerology/{name} with system=chaldean
- POST /api/v1/numerology with request body
- Response schema validation
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
# GET /api/v1/numerology/{name} — basic requests
# ═══════════════════════════════════════════════════════════════════════════


class TestNumerologyGetEndpoint:
    """Tests for GET /api/v1/numerology/{name}."""

    def test_get_numerology_returns_200(self, client: TestClient) -> None:
        """GET /numerology/{name} returns 200 with a valid name."""
        response = client.get("/api/v1/numerology/John%20Smith")
        assert response.status_code == 200

    def test_get_numerology_with_birth_date(self, client: TestClient) -> None:
        """GET /numerology/{name}?birth_date= returns correct life path."""
        response = client.get(
            "/api/v1/numerology/John%20Smith",
            params={"birth_date": "1990-03-15"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["life_path"] == 1
        assert data["birth_date"] == "1990-03-15"

    def test_get_numerology_default_birth_date(self, client: TestClient) -> None:
        """Without birth_date, defaults to 2000-01-01."""
        response = client.get("/api/v1/numerology/John%20Smith")
        assert response.status_code == 200
        data = response.json()
        assert data["birth_date"] == "2000-01-01"

    def test_get_numerology_name_in_response(self, client: TestClient) -> None:
        """Response includes the name that was used for the calculation."""
        response = client.get("/api/v1/numerology/Maria%20Elena%20Vasquez")
        data = response.json()
        assert data["name_used"] == "Maria Elena Vasquez"

    def test_get_numerology_system_default_pythagorean(self, client: TestClient) -> None:
        """Default system is pythagorean."""
        response = client.get("/api/v1/numerology/John%20Smith")
        data = response.json()
        assert data["system"] == "pythagorean"
        assert data["chaldean_name"] is None

    def test_get_numerology_system_chaldean(self, client: TestClient) -> None:
        """System=chaldean includes chaldean_name value."""
        response = client.get(
            "/api/v1/numerology/John%20Smith",
            params={"birth_date": "1990-03-15", "system": "chaldean"},
        )
        data = response.json()
        assert data["system"] == "chaldean"
        assert data["chaldean_name"] == 8


# ═══════════════════════════════════════════════════════════════════════════
# Response Schema Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestNumerologyResponseSchema:
    """Validate the shape and types of the numerology response."""

    def test_response_has_all_required_fields(self, client: TestClient) -> None:
        """Response includes all NumerologyResponse fields."""
        response = client.get(
            "/api/v1/numerology/Maria%20Elena%20Vasquez",
            params={"birth_date": "1992-03-15"},
        )
        data = response.json()
        required_fields = {
            "life_path", "expression", "soul_urge", "personality",
            "personal_year", "personal_month", "maturity",
            "is_master_number", "chaldean_name", "system",
            "name_used", "birth_date",
        }
        assert required_fields.issubset(set(data.keys()))

    def test_integer_fields_are_integers(self, client: TestClient) -> None:
        """Numerological numbers are integers."""
        response = client.get(
            "/api/v1/numerology/John%20Smith",
            params={"birth_date": "1990-03-15"},
        )
        data = response.json()
        for field in ["life_path", "expression", "soul_urge", "personality",
                      "personal_year", "personal_month", "maturity"]:
            assert isinstance(data[field], int), f"{field} should be int"

    def test_is_master_number_is_bool(self, client: TestClient) -> None:
        """is_master_number is a boolean."""
        response = client.get("/api/v1/numerology/John%20Smith")
        data = response.json()
        assert isinstance(data["is_master_number"], bool)

    def test_known_values_maria(self, client: TestClient) -> None:
        """Verify hand-checked numerology values for Maria Elena Vasquez."""
        response = client.get(
            "/api/v1/numerology/Maria%20Elena%20Vasquez",
            params={"birth_date": "1992-03-15"},
        )
        data = response.json()
        assert data["life_path"] == 3
        assert data["expression"] == 1
        assert data["soul_urge"] == 4
        assert data["personality"] == 6
        assert data["maturity"] == 4

    def test_known_values_john(self, client: TestClient) -> None:
        """Verify hand-checked numerology values for John Smith."""
        response = client.get(
            "/api/v1/numerology/John%20Smith",
            params={"birth_date": "1990-03-15"},
        )
        data = response.json()
        assert data["life_path"] == 1
        assert data["expression"] == 8
        assert data["soul_urge"] == 6
        assert data["personality"] == 11


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/numerology — body requests
# ═══════════════════════════════════════════════════════════════════════════


class TestNumerologyPostEndpoint:
    """Tests for POST /api/v1/numerology."""

    def test_post_numerology_returns_200(self, client: TestClient) -> None:
        """POST /numerology returns 200 with valid body."""
        response = client.post(
            "/api/v1/numerology",
            json={
                "full_name": "John Smith",
                "birth_date": "1990-03-15",
            },
        )
        assert response.status_code == 200

    def test_post_numerology_matches_get(self, client: TestClient) -> None:
        """POST and GET return the same results for the same input."""
        get_resp = client.get(
            "/api/v1/numerology/John%20Smith",
            params={"birth_date": "1990-03-15"},
        )
        post_resp = client.post(
            "/api/v1/numerology",
            json={
                "full_name": "John Smith",
                "birth_date": "1990-03-15",
            },
        )
        assert get_resp.json() == post_resp.json()

    def test_post_with_chaldean_system(self, client: TestClient) -> None:
        """POST with system=chaldean includes chaldean_name."""
        response = client.post(
            "/api/v1/numerology",
            json={
                "full_name": "John Smith",
                "birth_date": "1990-03-15",
                "system": "chaldean",
            },
        )
        data = response.json()
        assert data["system"] == "chaldean"
        assert data["chaldean_name"] is not None

    def test_post_missing_full_name_returns_422(self, client: TestClient) -> None:
        """Missing required field returns 422 validation error."""
        response = client.post(
            "/api/v1/numerology",
            json={"birth_date": "1990-03-15"},
        )
        assert response.status_code == 422

    def test_post_missing_birth_date_returns_422(self, client: TestClient) -> None:
        """Missing birth_date in POST body returns 422."""
        response = client.post(
            "/api/v1/numerology",
            json={"full_name": "John Smith"},
        )
        assert response.status_code == 422

    def test_post_name_too_short_returns_422(self, client: TestClient) -> None:
        """Name shorter than 2 characters returns 422 validation error."""
        response = client.post(
            "/api/v1/numerology",
            json={
                "full_name": "A",
                "birth_date": "1990-01-01",
            },
        )
        assert response.status_code == 422

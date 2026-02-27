"""Tests for Wealth and Compatibility API endpoints.

At least 8 tests covering:
- POST /wealth/profile returns valid response
- POST /wealth/plan returns valid plan
- POST /wealth/levers returns ordered levers
- POST /compatibility returns score and breakdown
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# Wealth Profile Endpoint
# ═══════════════════════════════════════════════════════════════════════════


class TestWealthProfileEndpoint:
    """Tests for POST /api/v1/wealth/profile."""

    def test_wealth_profile_returns_200(self, client: TestClient) -> None:
        """POST /wealth/profile returns 200 with valid input."""
        response = client.post(
            "/api/v1/wealth/profile",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "conservative",
            },
        )
        assert response.status_code == 200

    def test_wealth_profile_returns_archetype(self, client: TestClient) -> None:
        """Response includes wealth archetype name and description."""
        response = client.post(
            "/api/v1/wealth/profile",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "conservative",
            },
        )
        data = response.json()
        assert data["wealth_archetype"] == "The Builder"
        assert len(data["description"]) > 0
        assert len(data["primary_levers"]) > 0
        assert len(data["strengths"]) > 0
        assert len(data["blind_spots"]) > 0
        assert len(data["recommended_actions"]) > 0

    def test_wealth_profile_includes_scores(self, client: TestClient) -> None:
        """Response includes transparency scores for all 8 archetypes."""
        response = client.post(
            "/api/v1/wealth/profile",
            json={
                "life_path": 7,
                "archetype_primary": "sage",
                "risk_tolerance": "moderate",
            },
        )
        data = response.json()
        assert "scores" in data
        assert len(data["scores"]) == 8

    def test_wealth_profile_invalid_life_path(self, client: TestClient) -> None:
        """Invalid life path returns 422 validation error."""
        response = client.post(
            "/api/v1/wealth/profile",
            json={
                "life_path": 99,
                "archetype_primary": "sage",
                "risk_tolerance": "moderate",
            },
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Wealth Plan Endpoint
# ═══════════════════════════════════════════════════════════════════════════


class TestWealthPlanEndpoint:
    """Tests for POST /api/v1/wealth/plan."""

    def test_wealth_plan_returns_200(self, client: TestClient) -> None:
        """POST /wealth/plan returns 200 with valid input."""
        response = client.post(
            "/api/v1/wealth/plan",
            json={
                "life_path": 3,
                "archetype_primary": "creator",
                "risk_tolerance": "aggressive",
                "intention": "money",
            },
        )
        assert response.status_code == 200

    def test_wealth_plan_has_3_phases(self, client: TestClient) -> None:
        """Plan response includes exactly 3 phases."""
        response = client.post(
            "/api/v1/wealth/plan",
            json={
                "life_path": 3,
                "archetype_primary": "creator",
                "risk_tolerance": "moderate",
                "intention": "career",
            },
        )
        data = response.json()
        assert len(data["phases"]) == 3
        assert data["phases"][0]["name"] == "Foundation"
        assert data["phases"][1]["name"] == "Building"
        assert data["phases"][2]["name"] == "Acceleration"

    def test_wealth_plan_with_context(self, client: TestClient) -> None:
        """Plan works with optional wealth context."""
        response = client.post(
            "/api/v1/wealth/plan",
            json={
                "life_path": 6,
                "archetype_primary": "caregiver",
                "risk_tolerance": "conservative",
                "intention": "family",
                "wealth_context": {
                    "income_range": "$50k-$75k",
                    "has_investments": False,
                    "has_business": False,
                    "dependents": 2,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["daily_habits"]) > 0
        assert len(data["weekly_reviews"]) > 0


# ═══════════════════════════════════════════════════════════════════════════
# Wealth Levers Endpoint
# ═══════════════════════════════════════════════════════════════════════════


class TestWealthLeversEndpoint:
    """Tests for POST /api/v1/wealth/levers."""

    def test_levers_returns_200(self, client: TestClient) -> None:
        """POST /wealth/levers returns 200 with 5 levers."""
        response = client.post(
            "/api/v1/wealth/levers",
            json={
                "life_path": 1,
                "risk_tolerance": "moderate",
                "intention": "money",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["levers"]) == 5
        assert set(data["levers"]) == {"EARN", "KEEP", "GROW", "PROTECT", "TRANSFER"}


# ═══════════════════════════════════════════════════════════════════════════
# Compatibility Endpoint
# ═══════════════════════════════════════════════════════════════════════════


class TestCompatibilityEndpoint:
    """Tests for POST /api/v1/compatibility."""

    def test_compatibility_returns_200(self, client: TestClient) -> None:
        """POST /compatibility returns 200 with valid profiles."""
        response = client.post(
            "/api/v1/compatibility",
            json={
                "profile_a": {
                    "life_path": 3,
                    "archetype_primary": "creator",
                    "big_five": {
                        "openness": 80.0,
                        "conscientiousness": 55.0,
                        "extraversion": 70.0,
                        "agreeableness": 65.0,
                        "neuroticism": 40.0,
                    },
                },
                "profile_b": {
                    "life_path": 7,
                    "archetype_primary": "sage",
                    "big_five": {
                        "openness": 75.0,
                        "conscientiousness": 70.0,
                        "extraversion": 40.0,
                        "agreeableness": 60.0,
                        "neuroticism": 45.0,
                    },
                },
            },
        )
        assert response.status_code == 200

    def test_compatibility_score_in_range(self, client: TestClient) -> None:
        """Overall compatibility score is between 0 and 100."""
        response = client.post(
            "/api/v1/compatibility",
            json={
                "profile_a": {
                    "life_path": 1,
                    "archetype_primary": "hero",
                    "big_five": {
                        "openness": 50.0,
                        "conscientiousness": 50.0,
                        "extraversion": 50.0,
                        "agreeableness": 50.0,
                        "neuroticism": 50.0,
                    },
                },
                "profile_b": {
                    "life_path": 5,
                    "archetype_primary": "explorer",
                    "big_five": {
                        "openness": 90.0,
                        "conscientiousness": 30.0,
                        "extraversion": 80.0,
                        "agreeableness": 40.0,
                        "neuroticism": 60.0,
                    },
                },
            },
        )
        data = response.json()
        assert 0 <= data["overall_score"] <= 100
        assert 0 <= data["breakdown"]["life_path_score"] <= 100
        assert 0 <= data["breakdown"]["archetype_score"] <= 100
        assert 0 <= data["breakdown"]["big_five_score"] <= 100

    def test_compatibility_includes_summary(self, client: TestClient) -> None:
        """Response includes a human-readable summary string."""
        response = client.post(
            "/api/v1/compatibility",
            json={
                "profile_a": {
                    "life_path": 6,
                    "archetype_primary": "lover",
                    "big_five": {
                        "openness": 65.0,
                        "conscientiousness": 70.0,
                        "extraversion": 55.0,
                        "agreeableness": 85.0,
                        "neuroticism": 30.0,
                    },
                },
                "profile_b": {
                    "life_path": 2,
                    "archetype_primary": "caregiver",
                    "big_five": {
                        "openness": 60.0,
                        "conscientiousness": 75.0,
                        "extraversion": 50.0,
                        "agreeableness": 80.0,
                        "neuroticism": 35.0,
                    },
                },
            },
        )
        data = response.json()
        assert isinstance(data["summary"], str)
        assert len(data["summary"]) > 20

    def test_identical_profiles_high_score(self, client: TestClient) -> None:
        """Identical profiles produce a high compatibility score."""
        profile = {
            "life_path": 3,
            "archetype_primary": "creator",
            "big_five": {
                "openness": 70.0,
                "conscientiousness": 60.0,
                "extraversion": 65.0,
                "agreeableness": 55.0,
                "neuroticism": 45.0,
            },
        }
        response = client.post(
            "/api/v1/compatibility",
            json={"profile_a": profile, "profile_b": profile},
        )
        data = response.json()
        # Identical profiles: Big Five = 100, same archetype = 80, same LP = 80
        assert data["overall_score"] >= 80
        assert data["breakdown"]["big_five_score"] == 100.0

"""Tests for GET /api/v1/healing/spiral-route endpoint (Task 6.1).

Validates that the healing-specific spiral route endpoint returns
the correct structure with healing rank, score, reason, and
recommended modalities.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.auth import get_current_user
from alchymine.api.main import app


async def _test_current_user() -> dict:
    return {"sub": "test-user", "email": "test@example.com"}


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = _test_current_user
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


class TestHealingSpiralRoute:
    """Tests for GET /api/v1/healing/spiral-route"""

    def test_returns_200_with_defaults(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route")
        assert response.status_code == 200

    def test_returns_healing_rank_and_score(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        assert "healing_rank" in data
        assert "healing_score" in data
        assert 1 <= data["healing_rank"] <= 5
        assert 0 <= data["healing_score"] <= 100

    def test_health_intention_gives_healing_top_rank(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        # With health intention, healing should be primary
        assert data["healing_rank"] == 1
        assert data["primary_system"] == "healing"

    def test_returns_recommended_modalities(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        assert "recommended_modalities" in data
        assert len(data["recommended_modalities"]) > 0
        # Each modality should have required fields
        for mod in data["recommended_modalities"]:
            assert "modality" in mod
            assert "category" in mod
            assert "description" in mod
            assert "evidence_level" in mod

    def test_returns_for_you_today(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        assert "for_you_today" in data
        assert len(data["for_you_today"]) > 10

    def test_returns_healing_reason(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        assert "healing_reason" in data
        assert len(data["healing_reason"]) > 10

    def test_returns_healing_entry_action(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        assert "healing_entry_action" in data
        assert len(data["healing_entry_action"]) > 5

    def test_money_intention_gives_lower_healing_rank(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=money")
        data = response.json()
        # With money intention, healing should not be primary
        assert data["healing_rank"] > 1
        assert data["primary_system"] == "wealth"

    def test_with_personality_params(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/healing/spiral-route"
            "?intention=career"
            "&personality_neuroticism=90"
            "&personality_openness=30"
        )
        data = response.json()
        assert response.status_code == 200
        # High neuroticism should boost healing, verify it's scored
        assert data["healing_score"] > 0
        assert 1 <= data["healing_rank"] <= 5

        # Compare with low neuroticism — healing score should be higher
        response_low = client.get(
            "/api/v1/healing/spiral-route"
            "?intention=career"
            "&personality_neuroticism=10"
            "&personality_openness=30"
        )
        data_low = response_low.json()
        assert data["healing_score"] >= data_low["healing_score"]

    def test_with_life_path(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/healing/spiral-route?intention=career&life_path=6"
        )
        data = response.json()
        assert response.status_code == 200
        # LP 6 (Nurturer) boosts healing
        assert "healing_rank" in data

    def test_evidence_level_metadata(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        assert data["evidence_level"] == "strong"
        assert data["calculation_type"] == "deterministic"

    def test_primary_rank_gives_deeper_modalities(self, client: TestClient) -> None:
        """When healing is primary, recommended modalities include consciousness_journey."""
        response = client.get("/api/v1/healing/spiral-route?intention=health")
        data = response.json()
        modality_names = [m["modality"] for m in data["recommended_modalities"]]
        # Primary tier includes consciousness_journey
        assert "consciousness_journey" in modality_names

    def test_lower_rank_gives_foundational_modalities(self, client: TestClient) -> None:
        """When healing ranks low, recommended modalities focus on basics."""
        response = client.get("/api/v1/healing/spiral-route?intention=money")
        data = response.json()
        modality_names = [m["modality"] for m in data["recommended_modalities"]]
        # Lower tier should include basics like breathwork, sleep, nature
        assert "breathwork" in modality_names

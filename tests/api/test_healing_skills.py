"""Tests for healing skills API endpoints.

Covers:
- GET /api/v1/healing/skills — list all skills
- GET /api/v1/healing/skills?modality=<name> — filter by modality
- GET /api/v1/healing/skills/{skill_id} — get single skill
- GET /api/v1/healing/skills/{skill_id} — 404 for unknown skill
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/healing/skills
# ═══════════════════════════════════════════════════════════════════════════


class TestListSkills:
    def test_list_all_skills_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        assert response.status_code == 200

    def test_list_all_skills_returns_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        data = response.json()
        assert isinstance(data, list)

    def test_list_all_skills_has_15_items(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        data = response.json()
        assert len(data) >= 15

    def test_skill_has_required_fields(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        skill = response.json()[0]
        assert "id" in skill
        assert "modality" in skill
        assert "title" in skill
        assert "duration_minutes" in skill
        assert "difficulty" in skill
        assert "instructions" in skill
        assert "contraindications" in skill
        assert "traditions" in skill
        assert "evidence_level" in skill
        assert "tags" in skill

    def test_filter_by_modality_breathwork(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills", params={"modality": "breathwork"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for skill in data:
            assert skill["modality"] == "breathwork"

    def test_filter_by_unknown_modality_returns_empty(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/healing/skills", params={"modality": "nonexistent_modality"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_filter_by_modality_coherence_meditation(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/healing/skills", params={"modality": "coherence_meditation"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["modality"] == "coherence_meditation"


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/healing/skills/{skill_id}
# ═══════════════════════════════════════════════════════════════════════════


class TestGetSkill:
    def test_get_existing_skill_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills/bw_001")
        assert response.status_code == 200

    def test_get_existing_skill_returns_correct_data(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills/bw_001")
        data = response.json()
        assert data["id"] == "bw_001"
        assert data["modality"] == "breathwork"
        assert data["title"] == "Box Breathing Baseline"
        assert isinstance(data["instructions"], list)
        assert len(data["instructions"]) >= 1

    def test_get_nonexistent_skill_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills/does_not_exist")
        assert response.status_code == 404

    def test_get_404_has_detail_field(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills/does_not_exist")
        data = response.json()
        assert "detail" in data

    def test_get_each_seed_skill(self, client: TestClient) -> None:
        seed_ids = [
            "bw_001",
            "coherence_001",
            "language_001",
            "resilience_001",
            "consciousness_001",
            "sound_001",
            "somatic_001",
            "sleep_001",
            "nature_001",
            "pni_001",
            "grief_001",
            "water_001",
            "community_001",
            "expressive_001",
            "inquiry_001",
        ]
        for skill_id in seed_ids:
            response = client.get(f"/api/v1/healing/skills/{skill_id}")
            assert response.status_code == 200, (
                f"Expected 200 for skill '{skill_id}', got {response.status_code}"
            )

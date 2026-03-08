"""Tests for Creative Forge API endpoints.

Covers:
- POST /creative/assessment — Guilford divergent thinking scoring
- POST /creative/style — style fingerprint generation
- POST /creative/projects — project suggestions
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# POST /creative/assessment
# ═══════════════════════════════════════════════════════════════════════════


class TestGuilfordAssessment:
    """Tests for POST /api/v1/creative/assessment."""

    def _component_level_responses(self) -> dict:
        return {
            "responses": {
                "fluency": 75,
                "flexibility": 60,
                "originality": 85,
                "elaboration": 50,
                "sensitivity": 70,
                "redefinition": 55,
            }
        }

    def _question_level_responses(self) -> dict:
        return {
            "responses": {
                "guil_flu1": 80,
                "guil_flu2": 70,
                "guil_flu3": 75,
                "guil_flex1": 60,
                "guil_flex2": 55,
                "guil_flex3": 65,
                "guil_orig1": 90,
                "guil_orig2": 80,
                "guil_orig3": 85,
                "guil_elab1": 50,
                "guil_elab2": 45,
                "guil_elab3": 55,
                "guil_sens1": 70,
                "guil_sens2": 65,
                "guil_sens3": 75,
                "guil_redef1": 50,
                "guil_redef2": 55,
                "guil_redef3": 60,
            }
        }

    def test_assessment_returns_200_component_level(self, client: TestClient) -> None:
        """POST /creative/assessment returns 200 with component-level scores."""
        response = client.post(
            "/api/v1/creative/assessment",
            json=self._component_level_responses(),
        )
        assert response.status_code == 200

    def test_assessment_returns_all_components(self, client: TestClient) -> None:
        """Response includes all six Guilford components."""
        response = client.post(
            "/api/v1/creative/assessment",
            json=self._component_level_responses(),
        )
        data = response.json()
        assert "fluency" in data
        assert "flexibility" in data
        assert "originality" in data
        assert "elaboration" in data
        assert "sensitivity" in data
        assert "redefinition" in data

    def test_assessment_component_scores_match(self, client: TestClient) -> None:
        """Component-level scores are preserved in the response."""
        response = client.post(
            "/api/v1/creative/assessment",
            json=self._component_level_responses(),
        )
        data = response.json()
        assert data["fluency"] == 75.0
        assert data["originality"] == 85.0

    def test_assessment_question_level_returns_200(self, client: TestClient) -> None:
        """POST /creative/assessment returns 200 with question-level scores."""
        response = client.post(
            "/api/v1/creative/assessment",
            json=self._question_level_responses(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fluency"] == 75.0  # avg of 80, 70, 75

    def test_assessment_scores_clamped(self, client: TestClient) -> None:
        """Scores exceeding 100 are clamped."""
        response = client.post(
            "/api/v1/creative/assessment",
            json={
                "responses": {
                    "fluency": 150,
                    "flexibility": 60,
                    "originality": 85,
                    "elaboration": 50,
                    "sensitivity": 70,
                    "redefinition": 55,
                }
            },
        )
        data = response.json()
        assert data["fluency"] == 100.0


# ═══════════════════════════════════════════════════════════════════════════
# POST /creative/style
# ═══════════════════════════════════════════════════════════════════════════


class TestStyleFingerprint:
    """Tests for POST /api/v1/creative/style."""

    def _style_payload(self, **overrides) -> dict:
        base = {
            "guilford_scores": {
                "fluency": 80,
                "flexibility": 65,
                "originality": 90,
                "elaboration": 50,
                "sensitivity": 70,
                "redefinition": 55,
            },
            "creative_dna": {
                "structure_vs_improvisation": 0.7,
                "collaboration_vs_solitude": 0.3,
                "convergent_vs_divergent": 0.8,
                "primary_sensory_mode": "visual",
                "creative_peak": "morning",
            },
        }
        base.update(overrides)
        return base

    def test_style_returns_200(self, client: TestClient) -> None:
        """POST /creative/style returns 200 with valid input."""
        response = client.post("/api/v1/creative/style", json=self._style_payload())
        assert response.status_code == 200

    def test_style_contains_summary(self, client: TestClient) -> None:
        """Response includes guilford_summary and dna_summary."""
        response = client.post("/api/v1/creative/style", json=self._style_payload())
        data = response.json()
        assert "guilford_summary" in data
        assert "dna_summary" in data
        assert "dominant_components" in data
        assert "creative_style" in data
        assert "overall_score" in data

    def test_style_includes_strengths(self, client: TestClient) -> None:
        """Response includes strengths and growth areas."""
        response = client.post("/api/v1/creative/style", json=self._style_payload())
        data = response.json()
        assert isinstance(data["strengths"], list)
        assert len(data["strengths"]) > 0
        assert isinstance(data["growth_areas"], list)
        assert len(data["growth_areas"]) > 0

    def test_style_includes_mediums(self, client: TestClient) -> None:
        """Response includes recommended creative mediums."""
        response = client.post("/api/v1/creative/style", json=self._style_payload())
        data = response.json()
        assert isinstance(data["recommended_mediums"], list)
        assert len(data["recommended_mediums"]) > 0

    def test_style_dominant_components_top3(self, client: TestClient) -> None:
        """Dominant components returns top 3 Guilford components."""
        response = client.post("/api/v1/creative/style", json=self._style_payload())
        data = response.json()
        dominant = data["dominant_components"]
        assert len(dominant) == 3
        # With scores 90, 80, 70, 65, 55, 50 — top 3 should be originality, fluency, sensitivity
        assert dominant[0] == "originality"
        assert dominant[1] == "fluency"


# ═══════════════════════════════════════════════════════════════════════════
# POST /creative/projects
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectSuggestions:
    """Tests for POST /api/v1/creative/projects."""

    def test_projects_returns_200(self, client: TestClient) -> None:
        """POST /creative/projects returns 200 with valid input."""
        response = client.post(
            "/api/v1/creative/projects",
            json={
                "orientation": "Expressive Artist",
                "strengths": ["fluency", "originality"],
                "skill_level": "beginner",
            },
        )
        assert response.status_code == 200

    def test_projects_returns_list(self, client: TestClient) -> None:
        """Response contains a list of projects."""
        response = client.post(
            "/api/v1/creative/projects",
            json={
                "orientation": "Expressive Artist",
                "strengths": ["fluency"],
                "skill_level": "beginner",
            },
        )
        data = response.json()
        assert isinstance(data["projects"], list)
        assert data["total"] > 0
        assert data["orientation"] == "Expressive Artist"

    def test_project_has_required_fields(self, client: TestClient) -> None:
        """Each project has title, description, type, medium, skill_level."""
        response = client.post(
            "/api/v1/creative/projects",
            json={
                "orientation": "Pioneer Creator",
                "strengths": ["elaboration"],
                "skill_level": "intermediate",
            },
        )
        data = response.json()
        assert data["total"] > 0
        project = data["projects"][0]
        assert "title" in project
        assert "description" in project
        assert "type" in project
        assert "medium" in project
        assert "skill_level" in project

"""Tests for Healing API endpoints.

Covers:
- GET /healing/modalities — list all, filter by category, filter by evidence_level
- POST /healing/match — match modalities for a user profile
- GET /healing/breathwork/{intention} — get breathwork pattern
- POST /healing/crisis/detect — detect crisis in text
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# GET /healing/modalities
# ═══════════════════════════════════════════════════════════════════════════


class TestListModalities:
    """Tests for GET /api/v1/healing/modalities."""

    def test_list_all_modalities_returns_200(self, client: TestClient) -> None:
        """GET /healing/modalities returns 200 with all 15 modalities."""
        response = client.get("/api/v1/healing/modalities")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["modalities"]) == 15

    def test_modality_has_required_fields(self, client: TestClient) -> None:
        """Each modality has all expected fields."""
        response = client.get("/api/v1/healing/modalities")
        data = response.json()
        modality = data["modalities"][0]
        assert "name" in modality
        assert "skill_trigger" in modality
        assert "category" in modality
        assert "description" in modality
        assert "contraindications" in modality
        assert "min_difficulty" in modality
        assert "traditions" in modality
        assert "evidence_level" in modality

    def test_filter_by_category(self, client: TestClient) -> None:
        """Filter by category returns only matching modalities."""
        response = client.get("/api/v1/healing/modalities", params={"category": "somatic"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        for mod in data["modalities"]:
            assert mod["category"] == "somatic"

    def test_filter_by_evidence_level(self, client: TestClient) -> None:
        """Filter by evidence_level returns only matching modalities."""
        response = client.get(
            "/api/v1/healing/modalities", params={"evidence_level": "strong"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        for mod in data["modalities"]:
            assert mod["evidence_level"] == "strong"

    def test_filter_by_category_and_evidence(self, client: TestClient) -> None:
        """Combined category + evidence_level filter works."""
        response = client.get(
            "/api/v1/healing/modalities",
            params={"category": "somatic", "evidence_level": "strong"},
        )
        assert response.status_code == 200
        data = response.json()
        for mod in data["modalities"]:
            assert mod["category"] == "somatic"
            assert mod["evidence_level"] == "strong"

    def test_invalid_category_returns_400(self, client: TestClient) -> None:
        """Invalid category returns 400."""
        response = client.get(
            "/api/v1/healing/modalities", params={"category": "nonexistent"}
        )
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# POST /healing/match
# ═══════════════════════════════════════════════════════════════════════════


class TestMatchModalities:
    """Tests for POST /api/v1/healing/match."""

    def _match_payload(self, **overrides) -> dict:
        base = {
            "archetype_primary": "creator",
            "big_five": {
                "openness": 80.0,
                "conscientiousness": 55.0,
                "extraversion": 70.0,
                "agreeableness": 65.0,
                "neuroticism": 40.0,
            },
            "intention": "health",
            "max_difficulty": "foundation",
            "top_n": 5,
        }
        base.update(overrides)
        return base

    def test_match_returns_200(self, client: TestClient) -> None:
        """POST /healing/match returns 200 with valid input."""
        response = client.post("/api/v1/healing/match", json=self._match_payload())
        assert response.status_code == 200

    def test_match_returns_correct_count(self, client: TestClient) -> None:
        """Response contains at most top_n matches."""
        response = client.post("/api/v1/healing/match", json=self._match_payload(top_n=3))
        data = response.json()
        assert data["total"] <= 3
        assert len(data["matches"]) == data["total"]

    def test_match_includes_preference_score(self, client: TestClient) -> None:
        """Each match includes a preference_score between 0 and 1."""
        response = client.post("/api/v1/healing/match", json=self._match_payload())
        data = response.json()
        for match in data["matches"]:
            assert 0 <= match["preference_score"] <= 1
            assert "modality" in match
            assert "skill_trigger" in match

    def test_match_with_contraindications(self, client: TestClient) -> None:
        """Contraindications filter out matching modalities."""
        response = client.post(
            "/api/v1/healing/match",
            json=self._match_payload(
                contraindications=["severe asthma"],
                max_difficulty="advanced",
                top_n=15,
            ),
        )
        data = response.json()
        # Breathwork should be excluded (contraindicated for severe asthma)
        modality_names = [m["modality"] for m in data["matches"]]
        assert "breathwork" not in modality_names


# ═══════════════════════════════════════════════════════════════════════════
# GET /healing/breathwork/{intention}
# ═══════════════════════════════════════════════════════════════════════════


class TestBreathwork:
    """Tests for GET /api/v1/healing/breathwork/{intention}."""

    def test_breathwork_calm_returns_200(self, client: TestClient) -> None:
        """GET /healing/breathwork/calm returns 200."""
        response = client.get("/api/v1/healing/breathwork/calm")
        assert response.status_code == 200

    def test_breathwork_returns_pattern_fields(self, client: TestClient) -> None:
        """Response includes all breathwork pattern fields."""
        response = client.get("/api/v1/healing/breathwork/focus")
        data = response.json()
        assert "name" in data
        assert "inhale_seconds" in data
        assert "hold_seconds" in data
        assert "exhale_seconds" in data
        assert "hold_empty_seconds" in data
        assert "cycles" in data
        assert "difficulty" in data
        assert "description" in data

    def test_breathwork_with_difficulty(self, client: TestClient) -> None:
        """Difficulty query param filters available patterns."""
        response = client.get(
            "/api/v1/healing/breathwork/energy",
            params={"difficulty": "foundation"},
        )
        data = response.json()
        assert data["difficulty"] == "foundation"


# ═══════════════════════════════════════════════════════════════════════════
# POST /healing/crisis/detect
# ═══════════════════════════════════════════════════════════════════════════


class TestCrisisDetect:
    """Tests for POST /api/v1/healing/crisis/detect."""

    def test_no_crisis_detected(self, client: TestClient) -> None:
        """Neutral text returns no crisis detected."""
        response = client.post(
            "/api/v1/healing/crisis/detect",
            json={"text": "I had a great day today and feel wonderful."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["crisis_detected"] is False
        assert data["severity"] is None
        assert data["matched_keywords"] == []

    def test_crisis_detected_emergency(self, client: TestClient) -> None:
        """Emergency-level keywords trigger crisis detection."""
        response = client.post(
            "/api/v1/healing/crisis/detect",
            json={"text": "I want to end my life and have been thinking about suicide."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["crisis_detected"] is True
        assert data["severity"] == "emergency"
        assert len(data["matched_keywords"]) > 0
        assert len(data["resources"]) > 0
        assert len(data["disclaimers"]) > 0

    def test_crisis_detected_high(self, client: TestClient) -> None:
        """High-severity keywords trigger appropriate detection."""
        response = client.post(
            "/api/v1/healing/crisis/detect",
            json={"text": "I am experiencing domestic violence at home."},
        )
        data = response.json()
        assert data["crisis_detected"] is True
        assert data["severity"] == "high"

    def test_crisis_resources_include_hotlines(self, client: TestClient) -> None:
        """Crisis resources include standard hotline numbers."""
        response = client.post(
            "/api/v1/healing/crisis/detect",
            json={"text": "I feel hopeless and can't go on anymore."},
        )
        data = response.json()
        assert data["crisis_detected"] is True
        resource_names = [r["name"] for r in data["resources"]]
        assert "988 Suicide & Crisis Lifeline" in resource_names

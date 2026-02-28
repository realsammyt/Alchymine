"""Tests for the cross-system integration API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestArchetypeCreativeEndpoint:
    """POST /api/v1/integration/archetype-creative"""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/archetype-creative", json={"archetype": "Creator"})
        assert resp.status_code == 200

    def test_returns_insight(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/archetype-creative", json={"archetype": "Explorer"})
        data = resp.json()
        assert "insight" in data
        assert "action" in data
        assert data["source_system"] == "intelligence"
        assert data["target_system"] == "creative"


class TestShadowBlockEndpoint:
    """POST /api/v1/integration/shadow-block"""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/shadow-block", json={"shadow_archetype": "Creator"})
        assert resp.status_code == 200

    def test_returns_block_insight(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/shadow-block", json={"shadow_archetype": "Sage"})
        data = resp.json()
        assert "analysis_paralysis" in data["insight"].lower()


class TestCycleTimingEndpoint:
    """POST /api/v1/integration/cycle-timing"""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/cycle-timing", json={"personal_year": 1})
        assert resp.status_code == 200

    def test_validates_range(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/cycle-timing", json={"personal_year": 0})
        assert resp.status_code == 422


class TestWealthCreativeEndpoint:
    """POST /api/v1/integration/wealth-creative"""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/wealth-creative",
            json={"wealth_archetype": "Builder", "creative_style": "generative"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bridge_type"] == "wealth_creative_alignment"


class TestHealingPerspectiveEndpoint:
    """POST /api/v1/integration/healing-perspective"""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/healing-perspective",
            json={"healing_modality": "breathwork", "kegan_stage": 3},
        )
        assert resp.status_code == 200

    def test_validates_kegan_range(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/healing-perspective",
            json={"healing_modality": "breathwork", "kegan_stage": 6},
        )
        assert resp.status_code == 422


class TestCoherenceEndpoint:
    """POST /api/v1/integration/coherence"""

    def test_returns_200(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/coherence",
            json={"active_recommendations": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["coherence_score"] == 1.0

    def test_detects_conflicts(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/coherence",
            json={
                "active_recommendations": [
                    {"system": "healing", "action": "Rest and slow down"},
                    {"system": "wealth", "action": "Launch and expand now"},
                ]
            },
        )
        data = resp.json()
        assert len(data["conflicts"]) > 0


class TestSynthesizeEndpoint:
    """POST /api/v1/integration/synthesize"""

    def test_empty_profile(self, client: TestClient) -> None:
        resp = client.post("/api/v1/integration/synthesize", json={})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_full_profile(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/synthesize",
            json={
                "numerology": {"personal_year": 5},
                "archetype": {"primary": "Creator", "shadow": "Sage"},
                "wealth_archetype": "Builder",
                "creative_style": "generative",
                "kegan_stage": 3,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5
        bridge_types = [d["bridge_type"] for d in data]
        assert "archetype_to_creative" in bridge_types
        assert "shadow_to_block" in bridge_types
        assert "cycle_to_timing" in bridge_types

    def test_partial_profile(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/integration/synthesize",
            json={"archetype": {"primary": "Hero"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

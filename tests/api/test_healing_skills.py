"""Tests for the public healing skills API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app
from alchymine.engine.healing.modalities import MODALITY_REGISTRY


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── GET /api/v1/healing/skills ─────────────────────────────────────────


class TestListHealingSkills:
    def test_returns_200_and_15_skills(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 15

    def test_skill_payload_has_required_fields(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        assert response.status_code == 200
        skill = response.json()[0]
        for field in (
            "name",
            "modality",
            "title",
            "description",
            "steps",
            "evidence_rating",
            "contraindications",
            "duration_minutes",
        ):
            assert field in skill, f"missing {field}"
        assert isinstance(skill["steps"], list)
        assert len(skill["steps"]) >= 1

    def test_filter_by_modality(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills", params={"modality": "breathwork"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for skill in data:
            assert skill["modality"] == "breathwork"

    def test_unknown_modality_returns_empty_list(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/healing/skills",
            params={"modality": "definitely-not-a-modality"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_every_modality_represented(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills")
        modalities = {s["modality"] for s in response.json()}
        assert modalities == set(MODALITY_REGISTRY.keys())


# ── GET /api/v1/healing/skills/{name} ──────────────────────────────────


class TestGetHealingSkill:
    def test_returns_skill_when_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills/breathwork-box-breathing")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "breathwork-box-breathing"
        assert data["modality"] == "breathwork"
        assert data["evidence_rating"] in {"A", "B", "C", "D"}

    def test_returns_404_when_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/skills/no-such-skill")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ── Auth: endpoints are public reference data ─────────────────────────


def test_list_endpoint_does_not_require_auth() -> None:
    """Skills are open reference data — must work even when the auth
    override fixture is bypassed by clearing dependency overrides.
    """
    app.dependency_overrides.clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/healing/skills")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    finally:
        # conftest's autouse fixtures will re-install overrides next test.
        pass

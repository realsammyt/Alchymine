"""Tests for the public healing skills API endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app
from alchymine.config import get_settings
from alchymine.engine.healing.modalities import MODALITY_REGISTRY
from alchymine.engine.healing.skills import EXTERNAL_DIR_ENV_VAR, set_skill_registry


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_skill_registry() -> object:
    """Keep the process-global skill registry from leaking between tests."""
    set_skill_registry(None)
    yield
    set_skill_registry(None)


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
            "license",
            "attribution",
            "source_url",
            "bundled",
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


# ── A configured external directory that cannot be used ───────────────


class TestExternalDirFailsLoudly:
    """Issue #265, gap 2. The old wrapper logged a warning and served a
    quietly smaller catalogue, so a typo in the mount path shipped less
    product with no operator signal.
    """

    def test_unusable_external_dir_does_not_silently_shrink_the_catalogue(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        typo = tmp_path / "typo-in-this-path"
        monkeypatch.setenv(EXTERNAL_DIR_ENV_VAR, str(typo))
        get_settings.cache_clear()
        try:
            with caplog.at_level(logging.ERROR):
                response = TestClient(app).get("/api/v1/healing/skills")
        finally:
            get_settings.cache_clear()
            set_skill_registry(None)

        # The request fails rather than returning a shorter list.
        assert response.status_code == 500

        # The operator gets the path and the variable that pointed at it.
        errors = " ".join(r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR)
        assert str(typo) in errors
        assert EXTERNAL_DIR_ENV_VAR in errors

        # The user does not get a traceback or the server's filesystem layout.
        body = response.json()
        assert str(typo) not in body["detail"]
        assert EXTERNAL_DIR_ENV_VAR not in body["detail"]

    def test_bundled_only_is_unaffected_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(EXTERNAL_DIR_ENV_VAR, raising=False)
        get_settings.cache_clear()
        try:
            response = TestClient(app).get("/api/v1/healing/skills")
            assert response.status_code == 200
            assert len(response.json()) == 15
        finally:
            get_settings.cache_clear()
            set_skill_registry(None)


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

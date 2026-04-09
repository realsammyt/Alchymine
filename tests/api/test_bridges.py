"""Tests for the public cross-system bridges API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app

EXPECTED_IDS = {"XS-01", "XS-02", "XS-03", "XS-04", "XS-05", "XS-06", "XS-07"}
REQUIRED_FIELDS = (
    "id",
    "name",
    "source_system",
    "target_system",
    "description",
    "insight_keys",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────
# GET /api/v1/bridges
# ─────────────────────────────────────────────────────────────────────────


class TestListBridges:
    def test_list_all_bridges(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 7

    def test_list_bridges_structure(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges")
        assert response.status_code == 200
        for bridge in response.json():
            for field in REQUIRED_FIELDS:
                assert field in bridge, f"missing {field} in {bridge}"
            assert isinstance(bridge["insight_keys"], list)
            assert len(bridge["insight_keys"]) >= 1

    def test_all_bridge_ids_present(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges")
        ids = {b["id"] for b in response.json()}
        assert ids == EXPECTED_IDS

    def test_list_returns_stable_order(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges")
        ids = [b["id"] for b in response.json()]
        assert ids == sorted(ids)
        assert ids[0] == "XS-01"
        assert ids[-1] == "XS-07"

    def test_filter_by_source_system(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges", params={"source": "healing"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        for b in data:
            assert b["source_system"] == "healing"
        # XS-01 (healing→perspective) and XS-06 (healing→creative)
        assert {b["id"] for b in data} == {"XS-01", "XS-06"}

    def test_filter_by_target_system(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges", params={"target": "wealth"})
        assert response.status_code == 200
        data = response.json()
        for b in data:
            assert b["target_system"] == "wealth"
        # XS-05 (perspective→wealth)
        assert {b["id"] for b in data} == {"XS-05"}

    def test_filter_by_both(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/bridges",
            params={"source": "intelligence", "target": "perspective"},
        )
        assert response.status_code == 200
        data = response.json()
        # XS-07 (intelligence→perspective)
        assert len(data) == 1
        assert data[0]["id"] == "XS-07"

    def test_filter_unknown_source_returns_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges", params={"source": "definitely-not-real"})
        assert response.status_code == 200
        assert response.json() == []

    def test_filter_unknown_target_returns_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges", params={"target": "definitely-not-real"})
        assert response.status_code == 200
        assert response.json() == []

    def test_filter_combo_with_no_matches_returns_empty(self, client: TestClient) -> None:
        # healing→healing doesn't exist
        response = client.get(
            "/api/v1/bridges",
            params={"source": "healing", "target": "healing"},
        )
        assert response.status_code == 200
        assert response.json() == []


# ─────────────────────────────────────────────────────────────────────────
# GET /api/v1/bridges/{bridge_id}
# ─────────────────────────────────────────────────────────────────────────


class TestGetSingleBridge:
    def test_get_single_bridge(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges/XS-01")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "XS-01"
        assert data["source_system"] == "healing"
        assert data["target_system"] == "perspective"
        for field in REQUIRED_FIELDS:
            assert field in data

    def test_get_unknown_bridge(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges/XS-99")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_bridge_with_garbage_id(self, client: TestClient) -> None:
        response = client.get("/api/v1/bridges/not-a-bridge")
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────
# Auth: endpoints are public reference data
# ─────────────────────────────────────────────────────────────────────────


def test_list_endpoint_is_public() -> None:
    """Bridges are open reference data — must work even when the auth
    override fixture is bypassed by clearing dependency overrides.
    """
    app.dependency_overrides.clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/bridges")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
            assert len(response.json()) == 7
    finally:
        # conftest's autouse fixtures will re-install overrides next test.
        pass


def test_get_endpoint_is_public() -> None:
    app.dependency_overrides.clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/bridges/XS-02")
            assert response.status_code == 200
            assert response.json()["id"] == "XS-02"
    finally:
        pass

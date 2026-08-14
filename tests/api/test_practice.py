"""Tests for the practice read endpoints.

Auth is required on every route (decision 27 gates on identity, not on
plan), so the first test here removes the global override from
``tests/api/conftest.py`` to prove the dependency is actually wired.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from alchymine.api.auth import get_current_user
from alchymine.api.main import app

BUNDLED_PACK_ID = "alchymine-foundations"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def anonymous_client() -> Iterator[TestClient]:
    """A client with the test auth override removed."""
    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        yield TestClient(app)
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


class TestAuth:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/practices",
            "/api/v1/practices/packs",
            f"/api/v1/practices/{BUNDLED_PACK_ID}/name-the-pattern",
        ],
    )
    def test_routes_require_auth(self, anonymous_client: TestClient, path: str) -> None:
        assert anonymous_client.get(path).status_code == 401


class TestListPractices:
    def test_returns_the_bundled_pack(self, client: TestClient) -> None:
        response = client.get("/api/v1/practices")
        assert response.status_code == 200

        items = response.json()
        assert len(items) == 10
        assert {item["pack_id"] for item in items} == {BUNDLED_PACK_ID}

    def test_item_shape(self, client: TestClient) -> None:
        item = client.get("/api/v1/practices").json()[0]
        assert item["pack_id"] == BUNDLED_PACK_ID
        assert "progression_depth" in item
        practice = item["practice"]
        assert practice["slug"]
        assert len(practice["daily_prompts"]) == 3
        assert practice["self_check"]["question"].endswith("?")

    def test_filter_by_purpose(self, client: TestClient) -> None:
        items = client.get("/api/v1/practices", params={"purpose": "steadiness"}).json()
        assert len(items) == 2
        for item in items:
            assert "steadiness" in item["practice"]["purposes"]

    def test_filter_by_category(self, client: TestClient) -> None:
        items = client.get("/api/v1/practices", params={"category": "reflection"}).json()
        assert items
        for item in items:
            assert item["practice"]["category"] == "reflection"

    def test_filter_by_pack_id(self, client: TestClient) -> None:
        items = client.get("/api/v1/practices", params={"pack_id": BUNDLED_PACK_ID}).json()
        assert len(items) == 10

    def test_filters_combine(self, client: TestClient) -> None:
        items = client.get(
            "/api/v1/practices",
            params={"purpose": "expression", "category": "relational"},
        ).json()
        assert len(items) == 1
        assert items[0]["practice"]["category"] == "relational"

    def test_unknown_filter_value_returns_an_empty_list(self, client: TestClient) -> None:
        assert client.get("/api/v1/practices", params={"purpose": "levitation"}).json() == []
        assert client.get("/api/v1/practices", params={"pack_id": "nope"}).json() == []


class TestGetPractice:
    def test_returns_one_practice(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/practices/{BUNDLED_PACK_ID}/name-the-pattern")
        assert response.status_code == 200

        body = response.json()
        assert body["pack_id"] == BUNDLED_PACK_ID
        assert body["practice"]["slug"] == "name-the-pattern"
        assert body["progression_depth"] == 0

    def test_unknown_slug_is_404(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/practices/{BUNDLED_PACK_ID}/not-a-practice")
        assert response.status_code == 404
        assert "not-a-practice" in response.json()["detail"]

    def test_unknown_pack_is_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/practices/no-such-pack/name-the-pattern")
        assert response.status_code == 404
        assert "no-such-pack" in response.json()["detail"]


class TestListPacks:
    def test_surfaces_license_and_attribution(self, client: TestClient) -> None:
        response = client.get("/api/v1/practices/packs")
        assert response.status_code == 200

        packs = response.json()
        assert len(packs) == 1

        pack = packs[0]
        assert pack["manifest"]["pack_id"] == BUNDLED_PACK_ID
        assert pack["manifest"]["license"] == "CC-BY-NC-SA-4.0"
        assert pack["manifest"]["attribution"] == "Alchymine Contributors"
        assert pack["manifest"]["bundled"] is True
        assert pack["practice_count"] == 10

    def test_packs_route_is_not_shadowed_by_the_detail_route(
        self, client: TestClient
    ) -> None:
        """`/practices/packs` is a literal route and must win over the pattern."""
        body = client.get("/api/v1/practices/packs").json()
        assert isinstance(body, list)
        assert "manifest" in body[0]

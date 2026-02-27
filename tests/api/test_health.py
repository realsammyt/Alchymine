"""Tests for health check endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "alchymine-api"
    assert "version" in data


def test_numerology_endpoint_exists(client: TestClient) -> None:
    response = client.get("/api/v1/numerology/John%20Smith?birth_date=1990-03-15")
    # May return 501 (not implemented) or 200 — but not 404
    assert response.status_code in (200, 501)


def test_astrology_endpoint_exists(client: TestClient) -> None:
    response = client.get("/api/v1/astrology/1992-03-15")
    assert response.status_code == 200
    data = response.json()
    assert data["sun_sign"] == "Pisces"


def test_reports_post_returns_202(client: TestClient) -> None:
    response = client.post(
        "/api/v1/reports",
        json={
            "intake": {
                "full_name": "Maria Elena Vasquez",
                "birth_date": "1992-03-15",
                "intention": "family",
            },
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert "id" in data


def test_reports_get_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/reports/nonexistent-id")
    assert response.status_code == 404

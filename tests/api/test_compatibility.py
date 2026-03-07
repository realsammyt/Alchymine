"""Tests for the compatibility API endpoint.

All calculations are deterministic — same inputs always produce the same output.
Uses the global auth override from conftest.py (get_current_user is mocked).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _profile(
    life_path: int = 3,
    archetype: str = "creator",
    big_five: dict | None = None,
) -> dict:
    """Build a minimal profile input dict."""
    return {
        "life_path": life_path,
        "archetype_primary": archetype,
        "big_five": big_five
        or {
            "openness": 75.0,
            "conscientiousness": 55.0,
            "extraversion": 60.0,
            "agreeableness": 80.0,
            "neuroticism": 45.0,
        },
    }


def _compat_payload(profile_a: dict | None = None, profile_b: dict | None = None) -> dict:
    return {
        "profile_a": profile_a or _profile(),
        "profile_b": profile_b or _profile(life_path=7, archetype="sage"),
    }


class TestCompatibilityEndpoint:
    """Tests for POST /api/v1/compatibility."""

    def test_returns_200_with_valid_input(self, client: TestClient) -> None:
        """Endpoint returns 200 for a valid compatibility request."""
        response = client.post("/api/v1/compatibility", json=_compat_payload())
        assert response.status_code == 200

    def test_response_has_expected_fields(self, client: TestClient) -> None:
        """Response contains overall_score, breakdown, and summary."""
        data = client.post("/api/v1/compatibility", json=_compat_payload()).json()
        assert "overall_score" in data
        assert "breakdown" in data
        assert "summary" in data
        breakdown = data["breakdown"]
        assert "life_path_score" in breakdown
        assert "archetype_score" in breakdown
        assert "big_five_score" in breakdown

    def test_score_in_valid_range(self, client: TestClient) -> None:
        """Overall score and all breakdown scores are 0-100."""
        data = client.post("/api/v1/compatibility", json=_compat_payload()).json()
        assert 0 <= data["overall_score"] <= 100
        for key in ("life_path_score", "archetype_score", "big_five_score"):
            assert 0 <= data["breakdown"][key] <= 100

    def test_deterministic_same_input_same_output(self, client: TestClient) -> None:
        """Same inputs always produce identical output (no randomness)."""
        payload = _compat_payload()
        r1 = client.post("/api/v1/compatibility", json=payload).json()
        r2 = client.post("/api/v1/compatibility", json=payload).json()
        assert r1 == r2

    def test_different_inputs_different_scores(self, client: TestClient) -> None:
        """Different profile pairs produce different overall scores."""
        payload_a = _compat_payload(
            profile_a=_profile(life_path=1, archetype="hero"),
            profile_b=_profile(life_path=5, archetype="explorer"),
        )
        payload_b = _compat_payload(
            profile_a=_profile(life_path=4, archetype="ruler"),
            profile_b=_profile(life_path=9, archetype="rebel"),
        )
        score_a = client.post("/api/v1/compatibility", json=payload_a).json()["overall_score"]
        score_b = client.post("/api/v1/compatibility", json=payload_b).json()["overall_score"]
        assert score_a != score_b

    def test_missing_required_field_returns_422(self, client: TestClient) -> None:
        """Missing a required field returns 422."""
        response = client.post(
            "/api/v1/compatibility",
            json={"profile_a": _profile()},
        )
        assert response.status_code == 422

    def test_invalid_life_path_returns_422(self, client: TestClient) -> None:
        """Life path outside 1-33 returns 422."""
        payload = _compat_payload(
            profile_a=_profile(life_path=0),
        )
        response = client.post("/api/v1/compatibility", json=payload)
        assert response.status_code == 422

    def test_invalid_archetype_returns_422(self, client: TestClient) -> None:
        """An invalid archetype string returns 422."""
        payload = _compat_payload(
            profile_a=_profile(archetype="nonexistent"),
        )
        response = client.post("/api/v1/compatibility", json=payload)
        assert response.status_code == 422

    def test_identical_profiles_high_score(self, client: TestClient) -> None:
        """Two identical profiles should have a high compatibility score."""
        profile = _profile(life_path=3, archetype="creator")
        payload = _compat_payload(profile_a=profile, profile_b=profile)
        data = client.post("/api/v1/compatibility", json=payload).json()
        # Identical profiles: life_path=(3,3)=80, archetype same=80, big_five=100
        assert data["overall_score"] >= 80

    def test_synergy_pair_high_archetype_score(self, client: TestClient) -> None:
        """A known synergy archetype pair gets a high archetype score."""
        payload = _compat_payload(
            profile_a=_profile(archetype="creator"),
            profile_b=_profile(archetype="sage"),
        )
        data = client.post("/api/v1/compatibility", json=payload).json()
        assert data["breakdown"]["archetype_score"] == 85.0

    def test_tension_pair_low_archetype_score(self, client: TestClient) -> None:
        """A known tension archetype pair gets a low archetype score."""
        payload = _compat_payload(
            profile_a=_profile(archetype="ruler"),
            profile_b=_profile(archetype="rebel"),
        )
        data = client.post("/api/v1/compatibility", json=payload).json()
        assert data["breakdown"]["archetype_score"] == 40.0

    def test_master_number_bonus(self, client: TestClient) -> None:
        """Both master numbers get a +10 bonus on life path score."""
        # LP 11 reduces to 2, LP 22 reduces to 4 -> base (2,4)=80, +10=90
        payload = _compat_payload(
            profile_a=_profile(life_path=11),
            profile_b=_profile(life_path=22),
        )
        data = client.post("/api/v1/compatibility", json=payload).json()
        assert data["breakdown"]["life_path_score"] == 90.0

    def test_summary_contains_level(self, client: TestClient) -> None:
        """Summary string contains a compatibility level descriptor."""
        data = client.post("/api/v1/compatibility", json=_compat_payload()).json()
        summary = data["summary"]
        assert any(
            level in summary
            for level in ("Exceptional", "Strong", "Moderate", "Challenging", "Complex")
        )

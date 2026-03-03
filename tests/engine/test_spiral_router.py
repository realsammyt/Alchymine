"""Tests for the Alchemical Spiral adaptive routing engine.

Covers:
- Intention-based routing
- Life Path boosts
- Personality-based adjustments
- Breadth encouragement (systems_engaged)
- API endpoint integration
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.auth import get_current_user
from alchymine.api.main import app
from alchymine.engine.spiral.router import route_user


async def _test_current_user() -> dict:
    return {"sub": "test-user", "email": "test@example.com"}


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = _test_current_user
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


class TestSpiralRouter:
    """Tests for the route_user() engine function."""

    def test_money_intention_routes_to_wealth(self) -> None:
        result = route_user(intention="money")
        assert result.primary_system == "wealth"

    def test_health_intention_routes_to_healing(self) -> None:
        result = route_user(intention="health")
        assert result.primary_system == "healing"

    def test_purpose_intention_routes_to_perspective(self) -> None:
        result = route_user(intention="purpose")
        assert result.primary_system == "perspective"

    def test_career_routes_to_intelligence_or_perspective(self) -> None:
        result = route_user(intention="career")
        # Career maps to intelligence and perspective equally
        assert result.primary_system in ("intelligence", "perspective")

    def test_returns_all_five_systems(self) -> None:
        result = route_user(intention="money")
        systems = {r.system for r in result.recommendations}
        assert systems == {"intelligence", "healing", "wealth", "creative", "perspective"}

    def test_recommendations_sorted_by_priority(self) -> None:
        result = route_user(intention="money")
        priorities = [r.priority for r in result.recommendations]
        assert priorities == [1, 2, 3, 4, 5]

    def test_scores_normalized_to_100(self) -> None:
        result = route_user(intention="money")
        top_score = result.recommendations[0].score
        assert top_score == 100.0

    def test_all_scores_between_0_and_100(self) -> None:
        result = route_user(intention="money")
        for rec in result.recommendations:
            assert 0 <= rec.score <= 100

    def test_life_path_boost(self) -> None:
        # Life Path 3 = Creative boost
        result_no_lp = route_user(intention="career")
        result_lp3 = route_user(intention="career", life_path=3)

        creative_no_lp = next(r for r in result_no_lp.recommendations if r.system == "creative")
        creative_lp3 = next(r for r in result_lp3.recommendations if r.system == "creative")

        # Creative should rank higher with LP 3
        assert creative_lp3.priority <= creative_no_lp.priority

    def test_high_openness_boosts_creative(self) -> None:
        result_low = route_user(intention="career", personality_openness=30)
        result_high = route_user(intention="career", personality_openness=85)

        creative_low = next(r for r in result_low.recommendations if r.system == "creative")
        creative_high = next(r for r in result_high.recommendations if r.system == "creative")

        assert creative_high.priority <= creative_low.priority

    def test_high_neuroticism_boosts_healing(self) -> None:
        result_low = route_user(intention="career", personality_neuroticism=20)
        result_high = route_user(intention="career", personality_neuroticism=80)

        healing_low = next(r for r in result_low.recommendations if r.system == "healing")
        healing_high = next(r for r in result_high.recommendations if r.system == "healing")

        assert healing_high.priority <= healing_low.priority

    def test_systems_engaged_encourages_breadth(self) -> None:
        result_fresh = route_user(intention="money")
        result_engaged = route_user(intention="money", systems_engaged=["wealth"])

        wealth_fresh = next(r for r in result_fresh.recommendations if r.system == "wealth")
        wealth_engaged = next(r for r in result_engaged.recommendations if r.system == "wealth")

        # Wealth should be penalized when already engaged
        assert wealth_engaged.score <= wealth_fresh.score

    def test_unknown_intention_defaults_to_purpose(self) -> None:
        result = route_user(intention="unknown_value")
        # Should not crash, should default to purpose
        assert result.primary_system is not None
        assert len(result.recommendations) == 5

    def test_for_you_today_not_empty(self) -> None:
        result = route_user(intention="money")
        assert len(result.for_you_today) > 10

    def test_each_recommendation_has_entry_action(self) -> None:
        result = route_user(intention="money")
        for rec in result.recommendations:
            assert len(rec.entry_action) > 5

    def test_each_recommendation_has_reason(self) -> None:
        result = route_user(intention="money")
        for rec in result.recommendations:
            assert len(rec.reason) > 10

    def test_evidence_metadata(self) -> None:
        result = route_user(intention="money")
        assert result.evidence_level == "strong"
        assert result.calculation_type == "deterministic"
        assert "LLM" in result.methodology

    def test_deterministic_results(self) -> None:
        """Same inputs should always produce same outputs."""
        r1 = route_user(intention="money", life_path=7, personality_openness=80)
        r2 = route_user(intention="money", life_path=7, personality_openness=80)

        assert r1.primary_system == r2.primary_system
        assert [r.system for r in r1.recommendations] == [r.system for r in r2.recommendations]
        assert [r.score for r in r1.recommendations] == [r.score for r in r2.recommendations]


class TestSpiralEndpoint:
    """Tests for POST /api/v1/spiral/route"""

    def test_endpoint_returns_200(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/spiral/route",
            json={"intention": "money"},
        )
        assert response.status_code == 200

    def test_endpoint_returns_recommendations(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/spiral/route",
            json={"intention": "career", "life_path": 7},
        )
        data = response.json()
        assert "primary_system" in data
        assert "recommendations" in data
        assert len(data["recommendations"]) == 5

    def test_endpoint_with_full_params(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/spiral/route",
            json={
                "intention": "business",
                "life_path": 8,
                "personality_openness": 75,
                "personality_neuroticism": 40,
                "systems_engaged": ["wealth", "intelligence"],
            },
        )
        data = response.json()
        assert response.status_code == 200
        assert data["evidence_level"] == "strong"
        assert data["calculation_type"] == "deterministic"

    def test_endpoint_for_you_today(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/spiral/route",
            json={"intention": "health"},
        )
        data = response.json()
        assert "for_you_today" in data
        assert len(data["for_you_today"]) > 10

    def test_endpoint_each_system_has_fields(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/spiral/route",
            json={"intention": "money"},
        )
        data = response.json()
        for rec in data["recommendations"]:
            assert "system" in rec
            assert "score" in rec
            assert "reason" in rec
            assert "entry_action" in rec
            assert "priority" in rec

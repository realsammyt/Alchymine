"""Tests for Perspective Prism API endpoints.

Covers:
- POST /perspective/frameworks/pros-cons — pros/cons analysis
- POST /perspective/frameworks/weighted-matrix — weighted decision matrix
- POST /perspective/biases/detect — cognitive bias detection
- POST /perspective/kegan/assess — Kegan stage assessment
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# POST /perspective/frameworks/pros-cons
# ═══════════════════════════════════════════════════════════════════════════


class TestProsConsAnalysis:
    """Tests for POST /api/v1/perspective/frameworks/pros-cons."""

    def test_pros_cons_returns_200(self, client: TestClient) -> None:
        """POST /perspective/frameworks/pros-cons returns 200."""
        response = client.post(
            "/api/v1/perspective/frameworks/pros-cons",
            json={
                "decision": "Accept the job offer",
                "factors": {
                    "pros": ["Higher salary", "Better location", "Growth opportunity"],
                    "cons": ["Longer commute", "Less vacation"],
                },
            },
        )
        assert response.status_code == 200

    def test_pros_cons_balance_score(self, client: TestClient) -> None:
        """Balance score is between -1 and +1."""
        response = client.post(
            "/api/v1/perspective/frameworks/pros-cons",
            json={
                "decision": "Accept the job offer",
                "factors": {
                    "pros": ["Higher salary", "Better location", "Growth opportunity"],
                    "cons": ["Longer commute"],
                },
            },
        )
        data = response.json()
        assert -1 <= data["balance_score"] <= 1
        assert data["pro_count"] == 3
        assert data["con_count"] == 1
        # balance_score = (3-1)/4 = 0.5, which is > 0.15 but not > 0.5
        assert data["assessment"] == "Moderately favourable"

    def test_pros_cons_includes_methodology(self, client: TestClient) -> None:
        """Response includes methodology attribution."""
        response = client.post(
            "/api/v1/perspective/frameworks/pros-cons",
            json={
                "decision": "Move to a new city",
                "factors": {"pros": ["Adventure"], "cons": ["Cost"]},
            },
        )
        data = response.json()
        assert "methodology" in data
        assert len(data["methodology"]) > 20

    def test_pros_cons_empty_decision_returns_422(self, client: TestClient) -> None:
        """Empty decision string returns 422."""
        response = client.post(
            "/api/v1/perspective/frameworks/pros-cons",
            json={
                "decision": "",
                "factors": {"pros": ["Good"], "cons": []},
            },
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# POST /perspective/frameworks/weighted-matrix
# ═══════════════════════════════════════════════════════════════════════════


class TestWeightedMatrix:
    """Tests for POST /api/v1/perspective/frameworks/weighted-matrix."""

    def _matrix_payload(self) -> dict:
        return {
            "options": ["Option A", "Option B"],
            "criteria": [
                {
                    "name": "Cost",
                    "weight": 0.4,
                    "scores": {"Option A": 8, "Option B": 5},
                },
                {
                    "name": "Quality",
                    "weight": 0.6,
                    "scores": {"Option A": 6, "Option B": 9},
                },
            ],
        }

    def test_weighted_matrix_returns_200(self, client: TestClient) -> None:
        """POST /perspective/frameworks/weighted-matrix returns 200."""
        response = client.post(
            "/api/v1/perspective/frameworks/weighted-matrix",
            json=self._matrix_payload(),
        )
        assert response.status_code == 200

    def test_weighted_matrix_ranks_options(self, client: TestClient) -> None:
        """Response includes ranked options sorted by weighted score."""
        response = client.post(
            "/api/v1/perspective/frameworks/weighted-matrix",
            json=self._matrix_payload(),
        )
        data = response.json()
        ranked = data["ranked_options"]
        assert len(ranked) == 2
        # Option B: 5*0.4 + 9*0.6 = 2+5.4 = 7.4; Option A: 8*0.4 + 6*0.6 = 3.2+3.6 = 6.8
        assert ranked[0]["option"] == "Option B"
        assert ranked[0]["weighted_score"] > ranked[1]["weighted_score"]

    def test_weighted_matrix_includes_breakdown(self, client: TestClient) -> None:
        """Response includes criteria breakdown."""
        response = client.post(
            "/api/v1/perspective/frameworks/weighted-matrix",
            json=self._matrix_payload(),
        )
        data = response.json()
        assert len(data["criteria_breakdown"]) == 2
        assert "methodology" in data

    def test_weighted_matrix_empty_options_returns_422(self, client: TestClient) -> None:
        """Empty options list returns 422."""
        response = client.post(
            "/api/v1/perspective/frameworks/weighted-matrix",
            json={
                "options": [],
                "criteria": [{"name": "Cost", "weight": 1, "scores": {}}],
            },
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# POST /perspective/biases/detect
# ═══════════════════════════════════════════════════════════════════════════


class TestBiasDetection:
    """Tests for POST /api/v1/perspective/biases/detect."""

    def test_no_biases_detected(self, client: TestClient) -> None:
        """Neutral text returns no biases."""
        response = client.post(
            "/api/v1/perspective/biases/detect",
            json={"text": "The data shows a clear trend in the quarterly results."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["biases_detected"] == []

    def test_confirmation_bias_detected(self, client: TestClient) -> None:
        """Text with confirmation bias keywords is detected."""
        response = client.post(
            "/api/v1/perspective/biases/detect",
            json={"text": "I knew it all along, this proves my point exactly as I expected."},
        )
        data = response.json()
        assert data["total"] > 0
        bias_types = [b["bias_type"] for b in data["biases_detected"]]
        assert "confirmation_bias" in bias_types

    def test_sunk_cost_detected(self, client: TestClient) -> None:
        """Text with sunk cost keywords is detected."""
        response = client.post(
            "/api/v1/perspective/biases/detect",
            json={
                "text": "I've already invested too much time, can't give up now after all the effort."
            },
        )
        data = response.json()
        bias_types = [b["bias_type"] for b in data["biases_detected"]]
        assert "sunk_cost_fallacy" in bias_types

    def test_bias_includes_strategies(self, client: TestClient) -> None:
        """Detected biases include debiasing strategies."""
        response = client.post(
            "/api/v1/perspective/biases/detect",
            json={"text": "I knew it, this proves my point."},
        )
        data = response.json()
        assert data["total"] > 0
        bias = data["biases_detected"][0]
        assert "strategies" in bias
        assert len(bias["strategies"]) > 0
        assert "reframe" in bias

    def test_bias_includes_disclaimer(self, client: TestClient) -> None:
        """Response includes reflective aid disclaimer."""
        response = client.post(
            "/api/v1/perspective/biases/detect",
            json={"text": "Everyone is doing it, it must be right."},
        )
        data = response.json()
        assert "disclaimer" in data
        assert "reflective aid" in data["disclaimer"]


# ═══════════════════════════════════════════════════════════════════════════
# POST /perspective/kegan/assess
# ═══════════════════════════════════════════════════════════════════════════


class TestKeganAssessment:
    """Tests for POST /api/v1/perspective/kegan/assess."""

    def test_kegan_returns_200(self, client: TestClient) -> None:
        """POST /perspective/kegan/assess returns 200."""
        response = client.post(
            "/api/v1/perspective/kegan/assess",
            json={
                "responses": {
                    "self_awareness": 4,
                    "perspective_taking": 4,
                    "relationship_to_authority": 4.5,
                    "conflict_tolerance": 4,
                    "systems_thinking": 3.5,
                }
            },
        )
        assert response.status_code == 200

    def test_kegan_self_authoring(self, client: TestClient) -> None:
        """Responses near stage 4 produce self-authoring result."""
        response = client.post(
            "/api/v1/perspective/kegan/assess",
            json={
                "responses": {
                    "self_awareness": 4,
                    "perspective_taking": 4,
                    "relationship_to_authority": 4.5,
                    "conflict_tolerance": 4,
                    "systems_thinking": 3.5,
                }
            },
        )
        data = response.json()
        assert data["stage"] == "self-authoring"
        assert data["stage_number"] == 4
        assert data["name"] == "Self-Authoring"

    def test_kegan_includes_growth(self, client: TestClient) -> None:
        """Response includes growth practices and encouragement."""
        response = client.post(
            "/api/v1/perspective/kegan/assess",
            json={
                "responses": {
                    "self_awareness": 3,
                    "perspective_taking": 3,
                    "conflict_tolerance": 2.5,
                }
            },
        )
        data = response.json()
        assert "growth_practices" in data
        assert len(data["growth_practices"]) > 0
        assert "supportive_environments" in data
        assert "encouragement" in data

    def test_kegan_insufficient_dimensions_returns_400(self, client: TestClient) -> None:
        """Fewer than 2 dimensions returns 400."""
        response = client.post(
            "/api/v1/perspective/kegan/assess",
            json={"responses": {"self_awareness": 3}},
        )
        assert response.status_code == 400

    def test_kegan_out_of_range_returns_400(self, client: TestClient) -> None:
        """Scores outside 1-5 range return 400."""
        response = client.post(
            "/api/v1/perspective/kegan/assess",
            json={
                "responses": {
                    "self_awareness": 10,
                    "perspective_taking": 3,
                }
            },
        )
        assert response.status_code == 400

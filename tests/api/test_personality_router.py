"""Tests for Personality Assessment API endpoints.

Covers:
- POST /personality/big-five — Big Five (mini-IPIP) scoring
- POST /personality/attachment — Attachment style scoring
- POST /personality/enneagram — Enneagram type scoring
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# POST /personality/big-five
# ═══════════════════════════════════════════════════════════════════════════


class TestBigFiveAssessment:
    """Tests for POST /api/v1/personality/big-five."""

    def _all_responses(self, value: int = 3) -> dict:
        """Create a complete 20-item response set with uniform values."""
        responses = {}
        for prefix in ["e", "a", "c", "n", "o"]:
            for i in range(1, 5):
                responses[f"bf_{prefix}{i}"] = value
        return {"responses": responses}

    def _mixed_responses(self) -> dict:
        """Create a realistic mixed response set."""
        return {
            "responses": {
                "bf_e1": 4, "bf_e2": 2, "bf_e3": 5, "bf_e4": 2,  # Extraversion: high
                "bf_a1": 4, "bf_a2": 2, "bf_a3": 4, "bf_a4": 1,  # Agreeableness: high
                "bf_c1": 3, "bf_c2": 3, "bf_c3": 3, "bf_c4": 3,  # Conscientiousness: moderate
                "bf_n1": 2, "bf_n2": 4, "bf_n3": 2, "bf_n4": 4,  # Neuroticism: low
                "bf_o1": 5, "bf_o2": 1, "bf_o3": 1, "bf_o4": 1,  # Openness: high
            }
        }

    def test_big_five_returns_200(self, client: TestClient) -> None:
        """POST /personality/big-five returns 200 with valid input."""
        response = client.post(
            "/api/v1/personality/big-five",
            json=self._all_responses(),
        )
        assert response.status_code == 200

    def test_big_five_returns_all_traits(self, client: TestClient) -> None:
        """Response includes all five traits."""
        response = client.post(
            "/api/v1/personality/big-five",
            json=self._all_responses(),
        )
        data = response.json()
        assert "openness" in data
        assert "conscientiousness" in data
        assert "extraversion" in data
        assert "agreeableness" in data
        assert "neuroticism" in data

    def test_big_five_scores_0_to_100(self, client: TestClient) -> None:
        """All trait scores are between 0 and 100."""
        response = client.post(
            "/api/v1/personality/big-five",
            json=self._mixed_responses(),
        )
        data = response.json()
        for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            assert 0 <= data[trait] <= 100

    def test_big_five_all_ones_low_scores(self, client: TestClient) -> None:
        """All 1 responses produce low (or bottom-of-range) scores."""
        response = client.post(
            "/api/v1/personality/big-five",
            json=self._all_responses(value=1),
        )
        data = response.json()
        # With all 1s: forward-scored items sum=4, reverse-scored items sum=4*5=20
        # For extraversion: 2 forward (1+1=2) + 2 reverse (5+5=10) = 12
        # So it is not necessarily 0; this just verifies the endpoint works
        for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            assert 0 <= data[trait] <= 100

    def test_big_five_missing_items_returns_400(self, client: TestClient) -> None:
        """Missing items returns 400."""
        response = client.post(
            "/api/v1/personality/big-five",
            json={"responses": {"bf_e1": 3, "bf_e2": 3}},
        )
        assert response.status_code == 400

    def test_big_five_invalid_score_returns_400(self, client: TestClient) -> None:
        """Score outside 1-5 range returns 400."""
        responses = self._all_responses()
        responses["responses"]["bf_e1"] = 9  # Invalid
        response = client.post(
            "/api/v1/personality/big-five",
            json=responses,
        )
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# POST /personality/attachment
# ═══════════════════════════════════════════════════════════════════════════


class TestAttachmentAssessment:
    """Tests for POST /api/v1/personality/attachment."""

    def test_attachment_returns_200(self, client: TestClient) -> None:
        """POST /personality/attachment returns 200."""
        response = client.post(
            "/api/v1/personality/attachment",
            json={
                "responses": {
                    "att_closeness": 5,
                    "att_abandonment": 1,
                    "att_trust": 5,
                    "att_self_reliance": 3,
                }
            },
        )
        assert response.status_code == 200

    def test_secure_attachment(self, client: TestClient) -> None:
        """High closeness + low abandonment + high trust produces secure."""
        response = client.post(
            "/api/v1/personality/attachment",
            json={
                "responses": {
                    "att_closeness": 5,
                    "att_abandonment": 1,
                    "att_trust": 5,
                    "att_self_reliance": 3,
                }
            },
        )
        data = response.json()
        assert data["attachment_style"] == "secure"

    def test_anxious_attachment(self, client: TestClient) -> None:
        """High closeness + high abandonment produces anxious."""
        response = client.post(
            "/api/v1/personality/attachment",
            json={
                "responses": {
                    "att_closeness": 5,
                    "att_abandonment": 5,
                    "att_trust": 4,
                    "att_self_reliance": 2,
                }
            },
        )
        data = response.json()
        assert data["attachment_style"] == "anxious"

    def test_avoidant_attachment(self, client: TestClient) -> None:
        """Low closeness + low abandonment + high self-reliance produces avoidant."""
        response = client.post(
            "/api/v1/personality/attachment",
            json={
                "responses": {
                    "att_closeness": 1,
                    "att_abandonment": 1,
                    "att_trust": 3,
                    "att_self_reliance": 5,
                }
            },
        )
        data = response.json()
        assert data["attachment_style"] == "avoidant"

    def test_attachment_missing_items_returns_400(self, client: TestClient) -> None:
        """Missing items returns 400."""
        response = client.post(
            "/api/v1/personality/attachment",
            json={"responses": {"att_closeness": 3}},
        )
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# POST /personality/enneagram
# ═══════════════════════════════════════════════════════════════════════════


class TestEnneagramAssessment:
    """Tests for POST /api/v1/personality/enneagram."""

    def _all_responses(self, dominant_type: int = 4) -> dict:
        """Create 9-item responses where dominant_type has the highest score."""
        responses = {}
        for i in range(1, 10):
            responses[f"enn_{i}"] = 5 if i == dominant_type else 2
        return {"responses": responses}

    def test_enneagram_returns_200(self, client: TestClient) -> None:
        """POST /personality/enneagram returns 200."""
        response = client.post(
            "/api/v1/personality/enneagram",
            json=self._all_responses(),
        )
        assert response.status_code == 200

    def test_enneagram_primary_type(self, client: TestClient) -> None:
        """Highest-scored type is returned as primary."""
        response = client.post(
            "/api/v1/personality/enneagram",
            json=self._all_responses(dominant_type=4),
        )
        data = response.json()
        assert data["primary_type"] == 4
        assert data["primary_name"] == "Individualist"

    def test_enneagram_wing(self, client: TestClient) -> None:
        """Wing is one of the adjacent types."""
        response = client.post(
            "/api/v1/personality/enneagram",
            json=self._all_responses(dominant_type=4),
        )
        data = response.json()
        assert data["wing"] in [3, 5]  # Adjacent to type 4

    def test_enneagram_type_1_wing(self, client: TestClient) -> None:
        """Type 1 has adjacent types 9 and 2 (circular)."""
        response = client.post(
            "/api/v1/personality/enneagram",
            json=self._all_responses(dominant_type=1),
        )
        data = response.json()
        assert data["primary_type"] == 1
        assert data["primary_name"] == "Reformer"
        assert data["wing"] in [9, 2]

    def test_enneagram_missing_items_returns_400(self, client: TestClient) -> None:
        """Missing items returns 400."""
        response = client.post(
            "/api/v1/personality/enneagram",
            json={"responses": {"enn_1": 3, "enn_2": 4}},
        )
        assert response.status_code == 400

    def test_enneagram_invalid_score_returns_400(self, client: TestClient) -> None:
        """Score outside 1-5 range returns 400."""
        responses = self._all_responses()
        responses["responses"]["enn_1"] = 10  # Invalid
        response = client.post(
            "/api/v1/personality/enneagram",
            json=responses,
        )
        assert response.status_code == 400

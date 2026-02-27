"""Tests for evidence metadata and CSV export features.

Covers:
- Evidence metadata (evidence_level, calculation_type, methodology) on all system responses
- CSV export endpoint for wealth plans
- CSV export content structure
"""

from __future__ import annotations

import csv
import io

import pytest
from fastapi.testclient import TestClient

from alchymine.api.main import app
from alchymine.engine.wealth.export import plan_to_csv
from alchymine.engine.wealth.plan import ActivationPlan, PlanPhase


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# Evidence Metadata Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestEvidenceMetadata:
    """All system API responses should include evidence metadata."""

    def test_numerology_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.get("/api/v1/numerology/John%20Doe?birth_date=1990-01-15")
        data = response.json()
        assert data["evidence_level"] == "traditional"
        assert data["calculation_type"] == "deterministic"
        assert "methodology" in data
        assert len(data["methodology"]) > 10

    def test_astrology_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.get("/api/v1/astrology/1990-01-15")
        data = response.json()
        assert data["evidence_level"] == "traditional"
        assert data["calculation_type"] == "deterministic"
        assert "methodology" in data

    def test_wealth_profile_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/profile",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "conservative",
            },
        )
        data = response.json()
        assert data["evidence_level"] == "strong"
        assert data["calculation_type"] == "deterministic"
        assert "methodology" in data
        assert "LLM" in data["methodology"]

    def test_wealth_plan_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/plan",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "moderate",
                "intention": "money",
            },
        )
        data = response.json()
        assert data["evidence_level"] == "strong"
        assert data["calculation_type"] == "deterministic"
        assert "methodology" in data

    def test_healing_match_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/healing/match",
            json={
                "archetype_primary": "sage",
                "big_five": {
                    "openness": 80,
                    "conscientiousness": 70,
                    "extraversion": 40,
                    "agreeableness": 60,
                    "neuroticism": 30,
                },
                "intention": "health",
            },
        )
        data = response.json()
        assert data["evidence_level"] == "moderate"
        assert data["calculation_type"] == "hybrid"
        assert "methodology" in data

    def test_breathwork_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.get("/api/v1/healing/breathwork/calm")
        data = response.json()
        assert data["evidence_level"] == "moderate"
        assert data["calculation_type"] == "deterministic"
        assert "methodology" in data

    def test_guilford_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/creative/assessment",
            json={
                "responses": {
                    "fluency": 75,
                    "flexibility": 60,
                    "originality": 80,
                    "elaboration": 65,
                    "sensitivity": 70,
                    "redefinition": 55,
                },
            },
        )
        data = response.json()
        assert data["evidence_level"] == "strong"
        assert data["calculation_type"] == "deterministic"

    def test_bias_detect_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/perspective/biases/detect",
            json={"text": "I always knew this would work because it confirms my theory."},
        )
        data = response.json()
        assert data["evidence_level"] == "moderate"
        assert data["calculation_type"] == "deterministic"

    def test_kegan_has_evidence_metadata(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/perspective/kegan/assess",
            json={
                "responses": {
                    "self_awareness": 4,
                    "perspective_taking": 3,
                    "relationship_to_authority": 4,
                    "conflict_tolerance": 3,
                    "systems_thinking": 4,
                },
            },
        )
        data = response.json()
        assert data["evidence_level"] == "strong"
        assert data["calculation_type"] == "ai-assisted"
        assert "methodology" in data


# ═══════════════════════════════════════════════════════════════════════════
# CSV Export Module Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCsvExportModule:
    """Tests for alchymine.engine.wealth.export.plan_to_csv."""

    @pytest.fixture
    def sample_plan(self) -> ActivationPlan:
        from alchymine.engine.profile import WealthLever

        return ActivationPlan(
            wealth_archetype="The Builder",
            phases=(
                PlanPhase(
                    name="Foundation",
                    days=(1, 30),
                    focus_lever=WealthLever.EARN,
                    actions=("Action 1", "Action 2"),
                    milestones=("Milestone 1",),
                ),
                PlanPhase(
                    name="Building",
                    days=(31, 60),
                    focus_lever=WealthLever.KEEP,
                    actions=("Action 3",),
                    milestones=("Milestone 2",),
                ),
                PlanPhase(
                    name="Acceleration",
                    days=(61, 90),
                    focus_lever=WealthLever.GROW,
                    actions=("Action 4",),
                    milestones=("Milestone 3",),
                ),
            ),
            daily_habits=("Habit 1", "Habit 2"),
            weekly_reviews=("Review 1",),
        )

    def test_returns_string(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        assert isinstance(result, str)

    def test_contains_archetype(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        assert "The Builder" in result

    def test_contains_disclaimer(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        assert "not financial advice" in result.lower()

    def test_is_valid_csv(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) > 10  # Should have many rows

    def test_contains_all_phases(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        assert "Foundation" in result
        assert "Building" in result
        assert "Acceleration" in result

    def test_contains_actions(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        assert "Action 1" in result
        assert "Action 4" in result

    def test_contains_daily_habits(self, sample_plan: ActivationPlan) -> None:
        result = plan_to_csv(sample_plan)
        assert "Habit 1" in result
        assert "Habit 2" in result

    def test_contains_status_column(self, sample_plan: ActivationPlan) -> None:
        """Expanded action items have an empty Status column for user tracking."""
        result = plan_to_csv(sample_plan)
        assert "Status" in result


# ═══════════════════════════════════════════════════════════════════════════
# CSV Export Endpoint Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCsvExportEndpoint:
    """Tests for POST /api/v1/wealth/plan/export."""

    def test_csv_export_returns_200(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/plan/export",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "moderate",
                "intention": "money",
            },
        )
        assert response.status_code == 200

    def test_csv_export_content_type(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/plan/export",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "moderate",
                "intention": "money",
            },
        )
        assert "text/csv" in response.headers["content-type"]

    def test_csv_export_has_content_disposition(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/plan/export",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "moderate",
                "intention": "money",
            },
        )
        assert "attachment" in response.headers.get("content-disposition", "")
        assert ".csv" in response.headers.get("content-disposition", "")

    def test_csv_export_body_is_valid_csv(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/plan/export",
            json={
                "life_path": 7,
                "archetype_primary": "sage",
                "risk_tolerance": "conservative",
                "intention": "purpose",
            },
        )
        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)
        assert len(rows) > 10

    def test_csv_export_includes_disclaimer(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/wealth/plan/export",
            json={
                "life_path": 4,
                "archetype_primary": "ruler",
                "risk_tolerance": "moderate",
                "intention": "money",
            },
        )
        assert "not financial advice" in response.text.lower()

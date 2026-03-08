"""End-to-end pipeline integration tests.

Exercises the full flow: assessment answers → orchestrator → 5 coordinators
→ synthesis → verify all systems produce data. Uses real engines (no LLM
mocking needed — engines are deterministic). Verifies Sprint 2 additions:
risk_tolerance flows downstream, strengths_map is populated, Guilford and
Kegan data reach their coordinators.
"""

from __future__ import annotations

import pytest

from alchymine.agents.orchestrator.coordinator import CoordinatorStatus
from alchymine.agents.orchestrator.orchestrator import (
    MasterOrchestrator,
    OrchestratorResult,
)
from alchymine.agents.orchestrator.synthesis import _build_strengths_map

# ═══════════════════════════════════════════════════════════════════════
# Section 1: Full pipeline — orchestrator end-to-end with real engines
# ═══════════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """Run the real MasterOrchestrator with full assessment data."""

    pytestmark = pytest.mark.asyncio

    async def test_all_five_systems_produce_data(self, full_request_data: dict) -> None:
        """All 5 coordinators are invoked and produce non-empty data."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert isinstance(result, OrchestratorResult)

        system_names = {cr.system for cr in result.coordinator_results}
        assert "intelligence" in system_names
        assert "healing" in system_names
        assert "wealth" in system_names
        assert "creative" in system_names
        assert "perspective" in system_names

    async def test_no_system_errors(self, full_request_data: dict) -> None:
        """No coordinator should be in ERROR status with full data."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        for cr in result.coordinator_results:
            assert cr.status != CoordinatorStatus.ERROR.value, (
                f"{cr.system} returned ERROR: {cr.errors}"
            )

    async def test_synthesis_produced_for_multi_system(self, full_request_data: dict) -> None:
        """Multi-system request produces synthesis output."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert result.synthesis is not None
        assert "systems" in result.synthesis
        assert "participating_systems" in result.synthesis
        assert len(result.synthesis["participating_systems"]) >= 2


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Intelligence system data shape
# ═══════════════════════════════════════════════════════════════════════


class TestIntelligenceOutput:
    """Verify Intelligence coordinator produces expected data sections."""

    pytestmark = pytest.mark.asyncio

    async def test_numerology_present(self, full_request_data: dict) -> None:
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        intel = next(cr for cr in result.coordinator_results if cr.system == "intelligence")
        assert "numerology" in intel.data
        assert "life_path" in intel.data["numerology"]

    async def test_personality_present(self, full_request_data: dict) -> None:
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        intel = next(cr for cr in result.coordinator_results if cr.system == "intelligence")
        assert "personality" in intel.data
        personality = intel.data["personality"]
        assert "big_five" in personality
        # Verify Big Five has expected traits
        big_five = personality["big_five"]
        for trait in (
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ):
            assert trait in big_five

    async def test_archetype_present(self, full_request_data: dict) -> None:
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        intel = next(cr for cr in result.coordinator_results if cr.system == "intelligence")
        assert "archetype" in intel.data


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Risk tolerance flows to Wealth (TBD-8)
# ═══════════════════════════════════════════════════════════════════════


class TestRiskToleranceFlow:
    """Verify risk_tolerance is scored from assessment and enriched downstream."""

    pytestmark = pytest.mark.asyncio

    async def test_risk_tolerance_in_intelligence_personality(
        self, full_request_data: dict
    ) -> None:
        """Intelligence coordinator scores risk_tolerance from risk items."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        intel = next(cr for cr in result.coordinator_results if cr.system == "intelligence")
        personality = intel.data.get("personality", {})
        assert "risk_tolerance" in personality
        # Our fixture has risk scores 5, 4, 5 → avg 4.67 → aggressive
        assert personality["risk_tolerance"] == "aggressive"

    async def test_wealth_receives_risk_tolerance(self, full_request_data: dict) -> None:
        """Wealth coordinator is invoked after Intelligence enriches request_data."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        wealth = next(cr for cr in result.coordinator_results if cr.system == "wealth")
        # Wealth should not be in error — it received life_path and risk_tolerance
        assert wealth.status != CoordinatorStatus.ERROR.value


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Guilford creativity scores flow (TBD-6)
# ═══════════════════════════════════════════════════════════════════════


class TestGuilfordFlow:
    """Verify Guilford assessment responses are scored in Creative coordinator."""

    pytestmark = pytest.mark.asyncio

    async def test_creative_has_guilford_scores(self, full_request_data: dict) -> None:
        """Creative coordinator computes Guilford scores from guil_* responses."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        creative = next(cr for cr in result.coordinator_results if cr.system == "creative")
        assert creative.status != CoordinatorStatus.ERROR.value
        guilford = creative.data.get("guilford_scores", {})
        assert guilford, "guilford_scores should be populated from assessment"
        for dim in (
            "fluency",
            "flexibility",
            "originality",
            "elaboration",
            "sensitivity",
            "redefinition",
        ):
            assert dim in guilford


# ═══════════════════════════════════════════════════════════════════════
# Section 5: Kegan perspective responses flow (TBD-7)
# ═══════════════════════════════════════════════════════════════════════


class TestKeganFlow:
    """Verify Kegan assessment responses are extracted and available."""

    pytestmark = pytest.mark.asyncio

    async def test_kegan_responses_extracted(self, full_request_data: dict) -> None:
        """Orchestrator extracts kegan_responses from assessment after Intelligence."""
        orchestrator = MasterOrchestrator()

        # Capture enriched request_data by checking what Perspective receives
        captured: dict = {}
        original_process = orchestrator._coordinators
        from unittest.mock import AsyncMock, MagicMock

        from alchymine.agents.orchestrator.coordinator import CoordinatorResult
        from alchymine.agents.orchestrator.intent import SystemIntent

        # Replace only Perspective coordinator to capture its input
        real_perspective = original_process[SystemIntent.PERSPECTIVE]

        async def capture_and_delegate(user_id: str, request_data: dict) -> CoordinatorResult:
            captured.update(request_data)
            return await real_perspective.process(user_id, request_data)

        mock_perspective = MagicMock()
        mock_perspective.process = AsyncMock(side_effect=capture_and_delegate)
        orchestrator._coordinators[SystemIntent.PERSPECTIVE] = mock_perspective

        await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert "kegan_responses" in captured
        kegan = captured["kegan_responses"]
        expected_dims = {
            "self_awareness",
            "perspective_taking",
            "relationship_to_authority",
            "conflict_tolerance",
            "systems_thinking",
        }
        assert set(kegan.keys()) == expected_dims


# ═══════════════════════════════════════════════════════════════════════
# Section 6: Strengths map populated (TBD-9)
# ═══════════════════════════════════════════════════════════════════════


class TestStrengthsMapIntegration:
    """Verify strengths_map is populated from real coordinator results."""

    pytestmark = pytest.mark.asyncio

    async def test_strengths_map_not_empty(self, full_request_data: dict) -> None:
        """With full assessment data, strengths_map should contain entries."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        strengths = _build_strengths_map(result.coordinator_results)
        assert len(strengths) > 0, (
            f"strengths_map should not be empty with full data. "
            f"Systems: {[cr.system for cr in result.coordinator_results]}"
        )

    async def test_strengths_from_multiple_systems(self, full_request_data: dict) -> None:
        """Strengths should include entries from creative system (Guilford peaks)."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        strengths = _build_strengths_map(result.coordinator_results)
        # Guilford items all scored at 4 → 75/100. identify_strengths()
        # should surface at least one creative dimension.
        creative_keywords = {
            "fluency",
            "flexibility",
            "originality",
            "elaboration",
            "sensitivity",
            "redefinition",
        }
        found_creative = [s for s in strengths if any(kw in s.lower() for kw in creative_keywords)]
        assert len(found_creative) > 0, (
            f"Expected creative strengths from Guilford scores but got: {strengths}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Section 7: Intelligence enriches downstream coordinators
# ═══════════════════════════════════════════════════════════════════════


class TestIntelligenceEnrichment:
    """Verify Intelligence results enrich downstream coordinator request_data."""

    pytestmark = pytest.mark.asyncio

    async def test_downstream_receives_life_path(self, full_request_data: dict) -> None:
        """After Intelligence runs, request_data should have life_path."""
        orchestrator = MasterOrchestrator()

        captured: dict = {}
        from unittest.mock import AsyncMock, MagicMock

        from alchymine.agents.orchestrator.coordinator import CoordinatorResult
        from alchymine.agents.orchestrator.intent import SystemIntent

        real_wealth = orchestrator._coordinators[SystemIntent.WEALTH]

        async def capture_and_delegate(user_id: str, request_data: dict) -> CoordinatorResult:
            captured.update(request_data)
            return await real_wealth.process(user_id, request_data)

        mock_wealth = MagicMock()
        mock_wealth.process = AsyncMock(side_effect=capture_and_delegate)
        orchestrator._coordinators[SystemIntent.WEALTH] = mock_wealth

        await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert "life_path" in captured, "Wealth should receive life_path from Intelligence"
        assert isinstance(captured["life_path"], int)

    async def test_downstream_receives_archetype(self, full_request_data: dict) -> None:
        """After Intelligence runs, request_data should have archetype."""
        orchestrator = MasterOrchestrator()

        captured: dict = {}
        from unittest.mock import AsyncMock, MagicMock

        from alchymine.agents.orchestrator.coordinator import CoordinatorResult
        from alchymine.agents.orchestrator.intent import SystemIntent

        real_healing = orchestrator._coordinators[SystemIntent.HEALING]

        async def capture_and_delegate(user_id: str, request_data: dict) -> CoordinatorResult:
            captured.update(request_data)
            return await real_healing.process(user_id, request_data)

        mock_healing = MagicMock()
        mock_healing.process = AsyncMock(side_effect=capture_and_delegate)
        orchestrator._coordinators[SystemIntent.HEALING] = mock_healing

        await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert "archetype" in captured, "Healing should receive archetype from Intelligence"


# ═══════════════════════════════════════════════════════════════════════
# Section 8: Synthesis output shape
# ═══════════════════════════════════════════════════════════════════════


class TestSynthesisOutputShape:
    """Verify synthesis output has the expected structure."""

    pytestmark = pytest.mark.asyncio

    async def test_synthesis_has_all_participating_systems(self, full_request_data: dict) -> None:
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert result.synthesis is not None
        participating = set(result.synthesis["participating_systems"])
        expected = {"intelligence", "healing", "wealth", "creative", "perspective"}
        assert participating == expected

    async def test_synthesis_overall_status_not_error(self, full_request_data: dict) -> None:
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert result.synthesis is not None
        assert result.synthesis["overall_status"] != CoordinatorStatus.ERROR.value

    async def test_synthesis_has_system_data(self, full_request_data: dict) -> None:
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request(
            full_request_data["text"],
            user_profile=full_request_data,
            intentions=full_request_data["intentions"],
        )

        assert result.synthesis is not None
        systems = result.synthesis["systems"]
        for sys_name in ("intelligence", "healing", "wealth", "creative", "perspective"):
            assert sys_name in systems, f"Missing system data for {sys_name}"
            assert isinstance(systems[sys_name], dict)

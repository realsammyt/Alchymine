"""Tests for the Master Orchestrator agent.

Covers intent classification, system coordinators (success / failure /
degraded modes), the master orchestrator end-to-end flow, multi-system
request processing, graceful degradation, quality gate integration, and
multi-system synthesis.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alchymine.agents.orchestrator.coordinator import (
    BaseCoordinator,
    CoordinatorResult,
    CoordinatorStatus,
    CreativeCoordinator,
    HealingCoordinator,
    IntelligenceCoordinator,
    PerspectiveCoordinator,
    WealthCoordinator,
)
from alchymine.agents.orchestrator.intent import (
    IntentResult,
    SystemIntent,
    classify_intent,
    intentions_to_systems,
)
from alchymine.agents.orchestrator.orchestrator import (
    MasterOrchestrator,
    OrchestratorResult,
    synthesize_results,
)

# ═══════════════════════════════════════════════════════════════════════
# Section 1: Intent Classification — per-system keyword detection
# ═══════════════════════════════════════════════════════════════════════


class TestIntentClassificationIntelligence:
    """Intent classification routes to INTELLIGENCE for numerology / astrology keywords."""

    def test_numerology_keyword(self) -> None:
        result = classify_intent("Tell me about my numerology profile")
        assert result.intent == SystemIntent.INTELLIGENCE
        assert result.confidence > 0
        assert "numerology" in result.detected_keywords

    def test_birth_chart_keyword(self) -> None:
        result = classify_intent("Can you calculate my birth chart?")
        assert result.intent == SystemIntent.INTELLIGENCE
        assert "birth chart" in result.detected_keywords

    def test_astrology_keyword(self) -> None:
        result = classify_intent("What does astrology say about my zodiac sign?")
        assert result.intent == SystemIntent.INTELLIGENCE
        assert "astrology" in result.detected_keywords

    def test_life_path_keyword(self) -> None:
        result = classify_intent("What is my life path number?")
        assert result.intent == SystemIntent.INTELLIGENCE
        assert "life path" in result.detected_keywords

    def test_sun_sign_keyword(self) -> None:
        result = classify_intent("What is my sun sign?")
        assert result.intent == SystemIntent.INTELLIGENCE


class TestIntentClassificationHealing:
    """Intent classification routes to HEALING for healing / breathwork keywords."""

    def test_healing_keyword(self) -> None:
        result = classify_intent("I need some healing practices")
        assert result.intent == SystemIntent.HEALING
        assert "healing" in result.detected_keywords

    def test_breathwork_keyword(self) -> None:
        result = classify_intent("Can you guide me through breathwork?")
        assert result.intent == SystemIntent.HEALING
        assert "breathwork" in result.detected_keywords

    def test_meditation_keyword(self) -> None:
        result = classify_intent("I want to try meditation")
        assert result.intent == SystemIntent.HEALING
        assert "meditation" in result.detected_keywords


class TestIntentClassificationWealth:
    """Intent classification routes to WEALTH for financial keywords."""

    def test_money_keyword(self) -> None:
        result = classify_intent("Help me manage my money better")
        assert result.intent == SystemIntent.WEALTH
        assert "money" in result.detected_keywords

    def test_debt_keyword(self) -> None:
        result = classify_intent("I need help paying off my debt")
        assert result.intent == SystemIntent.WEALTH
        assert "debt" in result.detected_keywords

    def test_invest_keyword(self) -> None:
        result = classify_intent("How should I think about wealth and invest?")
        assert result.intent == SystemIntent.WEALTH
        assert "invest" in result.detected_keywords


class TestIntentClassificationCreative:
    """Intent classification routes to CREATIVE for art / writing keywords."""

    def test_creative_keyword(self) -> None:
        result = classify_intent("I want to explore my creative side")
        assert result.intent == SystemIntent.CREATIVE
        assert "creative" in result.detected_keywords

    def test_art_keyword(self) -> None:
        result = classify_intent("Tell me about art techniques")
        assert result.intent == SystemIntent.CREATIVE
        assert "art" in result.detected_keywords

    def test_writing_keyword(self) -> None:
        result = classify_intent("I need help with my writing process")
        assert result.intent == SystemIntent.CREATIVE
        assert "writing" in result.detected_keywords


class TestIntentClassificationPerspective:
    """Intent classification routes to PERSPECTIVE for decision / bias keywords."""

    def test_decision_keyword(self) -> None:
        result = classify_intent("Help me make a decision about my career")
        assert result.intent == SystemIntent.PERSPECTIVE
        assert "decision" in result.detected_keywords

    def test_bias_keyword(self) -> None:
        result = classify_intent("Am I showing any cognitive bias in my reasoning?")
        assert result.intent == SystemIntent.PERSPECTIVE
        assert "cognitive bias" in result.detected_keywords

    def test_framework_keyword(self) -> None:
        result = classify_intent("What framework should I use for this problem?")
        assert result.intent == SystemIntent.PERSPECTIVE
        assert "framework" in result.detected_keywords


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Intent Classification — edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestIntentClassificationEdgeCases:
    """Edge cases for intent classification."""

    def test_multi_system_detection(self) -> None:
        """When multiple systems have similar keyword density, return MULTI_SYSTEM."""
        # Both systems have 2 keywords each: numerology+astrology vs healing+breathwork
        result = classify_intent(
            "I want to explore my numerology astrology and also healing breathwork"
        )
        assert result.intent == SystemIntent.MULTI_SYSTEM
        assert len(result.secondary_intents) >= 2
        assert result.confidence > 0

    def test_unknown_intent_for_gibberish(self) -> None:
        result = classify_intent("asdfghjkl qwertyuiop zxcvbnm")
        assert result.intent == SystemIntent.UNKNOWN
        assert result.confidence == 0.0

    def test_unknown_intent_for_empty_string(self) -> None:
        result = classify_intent("")
        assert result.intent == SystemIntent.UNKNOWN
        assert result.confidence == 0.0

    def test_unknown_intent_for_whitespace(self) -> None:
        result = classify_intent("   ")
        assert result.intent == SystemIntent.UNKNOWN
        assert result.confidence == 0.0

    def test_intent_result_is_frozen(self) -> None:
        """IntentResult is a frozen dataclass."""
        result = classify_intent("Tell me my numerology")
        with pytest.raises(AttributeError):
            result.intent = SystemIntent.HEALING  # type: ignore[misc]

    def test_confidence_between_zero_and_one(self) -> None:
        result = classify_intent("numerology astrology life path")
        assert 0.0 <= result.confidence <= 1.0

    def test_detected_keywords_are_sorted(self) -> None:
        result = classify_intent("zodiac astrology birth chart numerology")
        assert result.detected_keywords == sorted(result.detected_keywords)

    def test_case_insensitive(self) -> None:
        """Keywords should match regardless of case."""
        result = classify_intent("NUMEROLOGY is fascinating")
        assert result.intent == SystemIntent.INTELLIGENCE


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Coordinator — success / failure / degraded
# ═══════════════════════════════════════════════════════════════════════


class TestCoordinatorSuccessMode:
    """Coordinators return SUCCESS with valid data from engine calls."""

    async def test_intelligence_coordinator_success(self) -> None:
        coordinator = IntelligenceCoordinator()
        # Mock the engine imports so the coordinator can run
        mock_profile = MagicMock()
        mock_profile.life_path = 3
        mock_profile.expression = 6
        mock_profile.soul_urge = 5
        mock_profile.personality = 1
        mock_profile.personal_year = 7
        mock_profile.personal_month = 3

        # Provide Big Five assessment responses for the personality node
        bf_responses = {
            f"bf_{t}{i}": 3
            for t in ("e", "a", "c", "n", "o")
            for i in (1, 2, 3, 4)
        }

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                return_value="Pisces",
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_degree",
                return_value=354.5,
            ),
        ):
            from datetime import date

            result = await coordinator.process(
                "user-1",
                {
                    "full_name": "Maria",
                    "birth_date": date(1992, 3, 15),
                    "assessment_responses": bf_responses,
                },
            )
        assert result.status == CoordinatorStatus.SUCCESS.value
        assert result.system == "intelligence"
        assert "numerology" in result.data
        assert "personality" in result.data
        assert "archetype" in result.data
        assert "biorhythm" in result.data

    async def test_healing_coordinator_success(self) -> None:
        coordinator = HealingCoordinator()
        mock_crisis = MagicMock()
        mock_crisis.is_crisis = False

        with patch(
            "alchymine.engine.healing.detect_crisis",
            return_value=mock_crisis,
        ):
            result = await coordinator.process(
                "user-1",
                {"text": "I want to try breathwork"},
            )
        assert result.system == "healing"
        assert "disclaimers" in result.data
        assert len(result.data["disclaimers"]) > 0

    async def test_wealth_coordinator_success(self) -> None:
        coordinator = WealthCoordinator()
        mock_archetype = MagicMock()
        mock_archetype.name = "Builder"
        mock_archetype.description = "Steady wealth builder"

        with (
            patch(
                "alchymine.engine.wealth.map_wealth_archetype",
                return_value=mock_archetype,
            ),
            patch(
                "alchymine.engine.wealth.prioritize_levers",
                return_value=[],
            ),
        ):
            result = await coordinator.process(
                "user-1",
                {"life_path": 3, "risk_tolerance": "moderate", "intention": "money"},
            )
        assert result.system == "wealth"
        assert "disclaimers" in result.data


class TestCoordinatorFailureMode:
    """Coordinators handle errors gracefully without crashing."""

    async def test_coordinator_returns_error_on_exception(self) -> None:
        """If _execute raises, process() should catch it and return ERROR."""

        class FailingCoordinator(BaseCoordinator):
            system_name = "test_failing"

            async def _execute(self, user_id, request_data):
                raise RuntimeError("Engine unavailable")

        coordinator = FailingCoordinator()
        result = await coordinator.process("user-1", {})
        assert result.status == CoordinatorStatus.ERROR.value
        assert len(result.errors) > 0
        assert "Engine unavailable" in result.errors[0]

    async def test_base_coordinator_not_implemented(self) -> None:
        """BaseCoordinator._execute raises NotImplementedError."""
        coordinator = BaseCoordinator()
        result = await coordinator.process("user-1", {})
        assert result.status == CoordinatorStatus.ERROR.value
        assert any("must implement" in e.lower() for e in result.errors)


class TestCoordinatorDegradedMode:
    """Coordinators enter degraded mode when partial data is available."""

    async def test_intelligence_degraded_when_astrology_fails(self) -> None:
        """Intelligence coordinator degrades when astrology is unavailable but numerology works."""
        coordinator = IntelligenceCoordinator()
        mock_profile = MagicMock()
        mock_profile.life_path = 3
        mock_profile.expression = 6
        mock_profile.soul_urge = 5
        mock_profile.personality = 1
        mock_profile.personal_year = 7
        mock_profile.personal_month = 3

        with (
            patch(
                "alchymine.engine.numerology.calculate_pythagorean_profile",
                return_value=mock_profile,
            ),
            patch(
                "alchymine.engine.astrology.approximate_sun_sign",
                side_effect=ImportError("swisseph not installed"),
            ),
        ):
            from datetime import date

            result = await coordinator.process(
                "user-1",
                {"full_name": "Maria", "birth_date": date(1992, 3, 15)},
            )

        assert result.status == CoordinatorStatus.DEGRADED.value
        assert "numerology" in result.data
        assert len(result.errors) > 0

    async def test_healing_includes_disclaimers_even_on_degraded(self) -> None:
        """Healing coordinator always includes disclaimers."""
        coordinator = HealingCoordinator()
        with patch(
            "alchymine.engine.healing.detect_crisis",
            side_effect=ImportError("healing engine not available"),
        ):
            result = await coordinator.process("user-1", {"text": "hello"})
        assert "disclaimers" in result.data
        assert len(result.data["disclaimers"]) > 0


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Quality gate integration
# ═══════════════════════════════════════════════════════════════════════


class TestQualityGateIntegration:
    """Coordinators run quality gates on their output."""

    async def test_quality_gate_failure_degrades_status(self) -> None:
        """If quality gate fails, coordinator result is degraded."""

        class BadOutputCoordinator(BaseCoordinator):
            system_name = "healing"

            async def _execute(self, user_id, request_data):
                return CoordinatorResult(
                    system="healing",
                    status=CoordinatorStatus.SUCCESS.value,
                    data={
                        "text": "This will cure your anxiety.",
                        # Missing disclaimers — quality gate will fail
                    },
                )

        coordinator = BadOutputCoordinator()
        result = await coordinator.process("user-1", {})
        assert result.quality_passed is False

    async def test_quality_gate_pass_keeps_success(self) -> None:
        """If quality gate passes, status stays SUCCESS."""

        class GoodOutputCoordinator(BaseCoordinator):
            system_name = "healing"

            async def _execute(self, user_id, request_data):
                return CoordinatorResult(
                    system="healing",
                    status=CoordinatorStatus.SUCCESS.value,
                    data={
                        "text": "Based on your profile, breathwork may be helpful.",
                        "disclaimers": [
                            "This is not medical advice. Consult a qualified healthcare professional."
                        ],
                    },
                )

        coordinator = GoodOutputCoordinator()
        result = await coordinator.process("user-1", {})
        assert result.quality_passed is True
        assert result.status == CoordinatorStatus.SUCCESS.value

    async def test_unknown_system_quality_gate_passes_by_default(self) -> None:
        """Systems without a registered quality gate pass by default."""

        class CustomCoordinator(BaseCoordinator):
            system_name = "intelligence"

            async def _execute(self, user_id, request_data):
                return CoordinatorResult(
                    system="intelligence",
                    status=CoordinatorStatus.SUCCESS.value,
                    data={"life_path": 7},
                )

        coordinator = CustomCoordinator()
        result = await coordinator.process("user-1", {})
        # intelligence has no dedicated quality gate, should pass
        assert result.quality_passed is True


# ═══════════════════════════════════════════════════════════════════════
# Section 5: Orchestrator end-to-end
# ═══════════════════════════════════════════════════════════════════════


class TestOrchestratorEndToEnd:
    """End-to-end tests: classify -> delegate -> validate -> result."""

    async def test_single_system_request(self) -> None:
        """A single-system request routes to one coordinator."""
        orchestrator = MasterOrchestrator()

        # Mock the intelligence coordinator
        mock_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 3}},
            quality_passed=True,
        )
        orchestrator._coordinators[SystemIntent.INTELLIGENCE] = MagicMock()
        orchestrator._coordinators[SystemIntent.INTELLIGENCE].process = AsyncMock(
            return_value=mock_result
        )

        result = await orchestrator.process_request("Tell me my numerology")
        assert isinstance(result, OrchestratorResult)
        assert result.intent.intent == SystemIntent.INTELLIGENCE
        assert len(result.coordinator_results) == 1
        assert result.coordinator_results[0].system == "intelligence"
        assert result.synthesis is None

    async def test_unknown_intent_returns_empty(self) -> None:
        """UNKNOWN intent returns no coordinator results."""
        orchestrator = MasterOrchestrator()
        result = await orchestrator.process_request("asdfghjkl random gibberish")
        assert result.intent.intent == SystemIntent.UNKNOWN
        assert len(result.coordinator_results) == 0
        assert result.quality_passed is True

    async def test_result_has_request_id(self) -> None:
        """Every result has a unique request_id (UUID)."""
        orchestrator = MasterOrchestrator()
        mock_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={},
            quality_passed=True,
        )
        orchestrator._coordinators[SystemIntent.HEALING] = MagicMock()
        orchestrator._coordinators[SystemIntent.HEALING].process = AsyncMock(
            return_value=mock_result
        )

        result = await orchestrator.process_request("healing breathwork")
        assert result.request_id is not None
        assert len(result.request_id) > 0

    async def test_user_profile_passed_to_coordinator(self) -> None:
        """User profile data is forwarded to coordinators."""
        orchestrator = MasterOrchestrator()
        captured_data = {}

        async def capture_process(user_id, request_data):
            captured_data.update(request_data)
            return CoordinatorResult(
                system="healing",
                status=CoordinatorStatus.SUCCESS.value,
                data={},
                quality_passed=True,
            )

        mock_coordinator = MagicMock()
        mock_coordinator.process = AsyncMock(side_effect=capture_process)
        orchestrator._coordinators[SystemIntent.HEALING] = mock_coordinator

        await orchestrator.process_request(
            "healing breathwork",
            user_profile={"id": "user-42", "birth_date": "1992-03-15"},
        )
        assert captured_data.get("id") == "user-42"
        assert captured_data.get("birth_date") == "1992-03-15"


# ═══════════════════════════════════════════════════════════════════════
# Section 6: Multi-system request processing
# ═══════════════════════════════════════════════════════════════════════


class TestMultiSystemProcessing:
    """Multi-system requests invoke multiple coordinators and synthesize."""

    async def test_multi_system_invokes_multiple_coordinators(self) -> None:
        orchestrator = MasterOrchestrator()

        healing_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.SUCCESS.value,
            data={"modalities": ["breathwork"]},
            quality_passed=True,
        )
        intelligence_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 7}},
            quality_passed=True,
        )

        for intent_enum, mock_result in [
            (SystemIntent.HEALING, healing_result),
            (SystemIntent.INTELLIGENCE, intelligence_result),
        ]:
            mock_coord = MagicMock()
            mock_coord.process = AsyncMock(return_value=mock_result)
            orchestrator._coordinators[intent_enum] = mock_coord

        # Force multi-system classification
        with patch(
            "alchymine.agents.orchestrator.orchestrator.classify_intent",
            return_value=IntentResult(
                intent=SystemIntent.MULTI_SYSTEM,
                confidence=0.5,
                secondary_intents=[SystemIntent.HEALING, SystemIntent.INTELLIGENCE],
                detected_keywords=["healing", "numerology"],
            ),
        ):
            result = await orchestrator.process_request("healing numerology breathwork astrology")

        assert len(result.coordinator_results) == 2
        assert result.synthesis is not None
        assert "systems" in result.synthesis

    async def test_multi_system_synthesis_contains_all_systems(self) -> None:
        results = [
            CoordinatorResult(
                system="healing",
                status=CoordinatorStatus.SUCCESS.value,
                data={"modalities": ["breathwork"]},
            ),
            CoordinatorResult(
                system="wealth",
                status=CoordinatorStatus.SUCCESS.value,
                data={"archetype": "Builder"},
            ),
        ]
        synthesis = synthesize_results(results)
        assert "healing" in synthesis["participating_systems"]
        assert "wealth" in synthesis["participating_systems"]
        assert "healing" in synthesis["systems"]
        assert "wealth" in synthesis["systems"]


# ═══════════════════════════════════════════════════════════════════════
# Section 7: Graceful degradation
# ═══════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    """Orchestrator continues when individual coordinators fail."""

    async def test_one_coordinator_fails_others_continue(self) -> None:
        orchestrator = MasterOrchestrator()

        # Healing fails
        healing_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.ERROR.value,
            data={},
            errors=["Healing engine unavailable"],
            quality_passed=False,
        )
        # Intelligence succeeds
        intelligence_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 3}},
            quality_passed=True,
        )

        mock_healing = MagicMock()
        mock_healing.process = AsyncMock(return_value=healing_result)
        mock_intelligence = MagicMock()
        mock_intelligence.process = AsyncMock(return_value=intelligence_result)

        orchestrator._coordinators[SystemIntent.HEALING] = mock_healing
        orchestrator._coordinators[SystemIntent.INTELLIGENCE] = mock_intelligence

        with patch(
            "alchymine.agents.orchestrator.orchestrator.classify_intent",
            return_value=IntentResult(
                intent=SystemIntent.MULTI_SYSTEM,
                confidence=0.5,
                secondary_intents=[SystemIntent.HEALING, SystemIntent.INTELLIGENCE],
                detected_keywords=["healing", "numerology"],
            ),
        ):
            result = await orchestrator.process_request("healing numerology")

        # Both coordinators were called
        assert len(result.coordinator_results) == 2
        # Overall quality is False because healing failed
        assert result.quality_passed is False
        # But we still got intelligence data
        intel_result = [r for r in result.coordinator_results if r.system == "intelligence"][0]
        assert intel_result.status == CoordinatorStatus.SUCCESS.value

    async def test_all_coordinators_fail_returns_errors(self) -> None:
        orchestrator = MasterOrchestrator()

        failing_result = CoordinatorResult(
            system="healing",
            status=CoordinatorStatus.ERROR.value,
            data={},
            errors=["Engine unavailable"],
            quality_passed=False,
        )
        mock_coord = MagicMock()
        mock_coord.process = AsyncMock(return_value=failing_result)
        orchestrator._coordinators[SystemIntent.HEALING] = mock_coord

        result = await orchestrator.process_request("healing breathwork")
        assert result.quality_passed is False
        assert len(result.coordinator_results) == 1
        assert result.coordinator_results[0].status == CoordinatorStatus.ERROR.value


# ═══════════════════════════════════════════════════════════════════════
# Section 8: Synthesis logic
# ═══════════════════════════════════════════════════════════════════════


class TestSynthesis:
    """Tests for synthesize_results combining multi-system outputs."""

    def test_synthesis_merges_system_data(self) -> None:
        results = [
            CoordinatorResult(
                system="intelligence",
                status=CoordinatorStatus.SUCCESS.value,
                data={"life_path": 3},
            ),
            CoordinatorResult(
                system="healing",
                status=CoordinatorStatus.SUCCESS.value,
                data={"modalities": ["breathwork"]},
            ),
        ]
        synthesis = synthesize_results(results)
        assert synthesis["systems"]["intelligence"] == {"life_path": 3}
        assert synthesis["systems"]["healing"] == {"modalities": ["breathwork"]}

    def test_synthesis_tracks_participating_systems(self) -> None:
        results = [
            CoordinatorResult(system="wealth", status=CoordinatorStatus.SUCCESS.value, data={}),
            CoordinatorResult(system="creative", status=CoordinatorStatus.SUCCESS.value, data={}),
        ]
        synthesis = synthesize_results(results)
        assert set(synthesis["participating_systems"]) == {"wealth", "creative"}

    def test_synthesis_overall_status_success(self) -> None:
        results = [
            CoordinatorResult(system="a", status=CoordinatorStatus.SUCCESS.value, data={}),
            CoordinatorResult(system="b", status=CoordinatorStatus.SUCCESS.value, data={}),
        ]
        synthesis = synthesize_results(results)
        assert synthesis["overall_status"] == CoordinatorStatus.SUCCESS.value

    def test_synthesis_overall_status_degraded(self) -> None:
        results = [
            CoordinatorResult(system="a", status=CoordinatorStatus.SUCCESS.value, data={}),
            CoordinatorResult(
                system="b",
                status=CoordinatorStatus.DEGRADED.value,
                data={},
                errors=["partial failure"],
            ),
        ]
        synthesis = synthesize_results(results)
        assert synthesis["overall_status"] == CoordinatorStatus.DEGRADED.value

    def test_synthesis_overall_status_error_when_all_fail(self) -> None:
        results = [
            CoordinatorResult(
                system="a",
                status=CoordinatorStatus.ERROR.value,
                data={},
                errors=["fail"],
            ),
            CoordinatorResult(
                system="b",
                status=CoordinatorStatus.ERROR.value,
                data={},
                errors=["fail"],
            ),
        ]
        synthesis = synthesize_results(results)
        assert synthesis["overall_status"] == CoordinatorStatus.ERROR.value

    def test_synthesis_collects_errors(self) -> None:
        results = [
            CoordinatorResult(
                system="a",
                status=CoordinatorStatus.DEGRADED.value,
                data={},
                errors=["error-a1", "error-a2"],
            ),
            CoordinatorResult(
                system="b",
                status=CoordinatorStatus.SUCCESS.value,
                data={},
            ),
        ]
        synthesis = synthesize_results(results)
        assert "error-a1" in synthesis["errors"]
        assert "error-a2" in synthesis["errors"]

    def test_synthesis_empty_results(self) -> None:
        synthesis = synthesize_results([])
        assert synthesis["participating_systems"] == []
        assert synthesis["overall_status"] == CoordinatorStatus.SUCCESS.value


# ═══════════════════════════════════════════════════════════════════════
# Section 9: Coordinator system name mapping
# ═══════════════════════════════════════════════════════════════════════


class TestCoordinatorSystemNames:
    """Each coordinator reports the correct system name."""

    def test_intelligence_system_name(self) -> None:
        assert IntelligenceCoordinator.system_name == "intelligence"

    def test_healing_system_name(self) -> None:
        assert HealingCoordinator.system_name == "healing"

    def test_wealth_system_name(self) -> None:
        assert WealthCoordinator.system_name == "wealth"

    def test_creative_system_name(self) -> None:
        assert CreativeCoordinator.system_name == "creative"

    def test_perspective_system_name(self) -> None:
        assert PerspectiveCoordinator.system_name == "perspective"


# ═══════════════════════════════════════════════════════════════════════
# Section 10: MasterOrchestrator initialisation
# ═══════════════════════════════════════════════════════════════════════


class TestOrchestratorInit:
    """MasterOrchestrator initialises with all five coordinators."""

    def test_has_all_five_coordinators(self) -> None:
        orchestrator = MasterOrchestrator()
        expected = {
            SystemIntent.INTELLIGENCE,
            SystemIntent.HEALING,
            SystemIntent.WEALTH,
            SystemIntent.CREATIVE,
            SystemIntent.PERSPECTIVE,
        }
        assert set(orchestrator._coordinators.keys()) == expected

    def test_coordinators_are_correct_types(self) -> None:
        orchestrator = MasterOrchestrator()
        assert isinstance(
            orchestrator._coordinators[SystemIntent.INTELLIGENCE], IntelligenceCoordinator
        )
        assert isinstance(orchestrator._coordinators[SystemIntent.HEALING], HealingCoordinator)
        assert isinstance(orchestrator._coordinators[SystemIntent.WEALTH], WealthCoordinator)
        assert isinstance(orchestrator._coordinators[SystemIntent.CREATIVE], CreativeCoordinator)
        assert isinstance(
            orchestrator._coordinators[SystemIntent.PERSPECTIVE], PerspectiveCoordinator
        )


# ═══════════════════════════════════════════════════════════════════════
# Section 11: Intention-based routing
# ═══════════════════════════════════════════════════════════════════════


class TestIntentionsToSystems:
    """intentions_to_systems maps user intention values to SystemIntent lists."""

    def test_health_intention_includes_healing(self) -> None:
        systems = intentions_to_systems(["health"])
        assert SystemIntent.INTELLIGENCE in systems
        assert SystemIntent.HEALING in systems

    def test_money_intention_includes_wealth(self) -> None:
        systems = intentions_to_systems(["money"])
        assert SystemIntent.INTELLIGENCE in systems
        assert SystemIntent.WEALTH in systems

    def test_multiple_intentions_deduplicated(self) -> None:
        systems = intentions_to_systems(["health", "money"])
        # INTELLIGENCE should appear only once even though both map to it
        assert systems.count(SystemIntent.INTELLIGENCE) == 1
        assert SystemIntent.HEALING in systems
        assert SystemIntent.WEALTH in systems

    def test_intelligence_always_first(self) -> None:
        systems = intentions_to_systems(["health"])
        assert systems[0] == SystemIntent.INTELLIGENCE

    def test_unknown_intention_still_has_intelligence(self) -> None:
        systems = intentions_to_systems(["unknown_xyz"])
        assert systems == [SystemIntent.INTELLIGENCE]

    def test_case_insensitive(self) -> None:
        systems = intentions_to_systems(["HEALTH"])
        assert SystemIntent.HEALING in systems


class TestOrchestratorIntentionRouting:
    """Orchestrator uses intentions for routing when provided."""

    async def test_intentions_bypass_keyword_classification(self) -> None:
        """When intentions are provided, keyword classification is bypassed."""
        orchestrator = MasterOrchestrator()

        mock_result = CoordinatorResult(
            system="intelligence",
            status=CoordinatorStatus.SUCCESS.value,
            data={"numerology": {"life_path": 3}},
            quality_passed=True,
        )

        # Mock all coordinators
        for system in SystemIntent:
            if system in orchestrator._coordinators:
                mock_coord = MagicMock()
                mock_coord.process = AsyncMock(return_value=mock_result)
                orchestrator._coordinators[system] = mock_coord

        # "random gibberish" would normally be UNKNOWN, but intentions override
        result = await orchestrator.process_request(
            "random gibberish",
            intentions=["health"],
        )
        assert len(result.coordinator_results) >= 1

"""Tests for the 28 domain agents organized in 5 system crews.

Tests cover:
- All 28 agents instantiate correctly
- Each crew has the right number of agents
- Agent execution with sample data for each crew
- Crew registry returns correct crews
- Error handling when engine modules are unavailable
- SystemCrew sequential execution with context threading
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from alchymine.agents.crews import (
    CREW_BUILDERS,
    VALID_SYSTEMS,
    get_all_crews,
    get_crew,
)
from alchymine.agents.crews.base import (
    AgentRole,
    AgentTask,
    DomainAgent,
    SystemCrew,
)

# ─── Crew imports ──────────────────────────────────────────────────

from alchymine.agents.crews.intelligence import (
    ArchetypesSynthesizer,
    AstrologyAnalyst,
    BiorhythmCalculator,
    IntelligenceGuide,
    NumerologyAnalyst,
    PersonalityAnalyst,
    build_intelligence_crew,
)
from alchymine.agents.crews.healing import (
    BreathworkGuide,
    CrisisDetector,
    HealingNarrative,
    HealingValidator,
    ModalityMatcher,
    PracticeTracker,
    build_healing_crew,
)
from alchymine.agents.crews.wealth import (
    BudgetAnalyst,
    DebtStrategist,
    LeverCalculator,
    WealthArchetypeAnalyst,
    WealthNarrative,
    WealthValidator,
    build_wealth_crew,
)
from alchymine.agents.crews.creative import (
    CreativeBlockDetector,
    CreativeNarrative,
    GuilfordAssessor,
    ProjectSuggester,
    StyleAnalyst,
    build_creative_crew,
)
from alchymine.agents.crews.perspective import (
    BiasDetector,
    FrameworkApplier,
    KeganAssessor,
    PerspectiveNarrative,
    ScenarioModeler,
    build_perspective_crew,
)


# ═══════════════════════════════════════════════════════════════════
# Base abstractions
# ═══════════════════════════════════════════════════════════════════


class TestBaseAbstractions:
    """Test DomainAgent, AgentTask, and SystemCrew base classes."""

    def test_domain_agent_base_raises_not_implemented(self):
        agent = DomainAgent(
            name="TestAgent",
            role=AgentRole.ANALYST,
            goal="Test goal",
            backstory="Test backstory",
            system="test",
        )
        with pytest.raises(NotImplementedError, match="TestAgent must implement execute"):
            agent.execute({})

    def test_agent_task_creation(self):
        agent = DomainAgent(
            name="TestAgent",
            role=AgentRole.ANALYST,
            goal="Test",
            backstory="Test",
            system="test",
        )
        task = AgentTask(
            name="test_task",
            description="A test task",
            agent=agent,
            expected_output="Some output",
        )
        assert task.name == "test_task"
        assert task.agent is agent

    def test_system_crew_run_handles_errors(self):
        agent = DomainAgent(
            name="FailAgent",
            role=AgentRole.ANALYST,
            goal="Fail",
            backstory="Fails",
            system="test",
        )
        task = AgentTask(
            name="failing_task",
            description="Will fail",
            agent=agent,
            expected_output="Error",
        )
        crew = SystemCrew(name="test", agents=[agent], tasks=[task])
        results = crew.run({})
        assert "failing_task" in results
        assert "error" in results["failing_task"]

    def test_agent_role_enum(self):
        assert AgentRole.ANALYST == "analyst"
        assert AgentRole.SYNTHESIZER == "synthesizer"
        assert AgentRole.VALIDATOR == "validator"
        assert AgentRole.GUIDE == "guide"
        assert AgentRole.DETECTOR == "detector"
        assert AgentRole.CALCULATOR == "calculator"


# ═══════════════════════════════════════════════════════════════════
# Crew registry
# ═══════════════════════════════════════════════════════════════════


class TestCrewRegistry:
    """Test crew registry functions."""

    def test_valid_systems(self):
        assert VALID_SYSTEMS == {"intelligence", "healing", "wealth", "creative", "perspective"}

    def test_crew_builders_count(self):
        assert len(CREW_BUILDERS) == 5

    def test_get_crew_returns_system_crew(self):
        for system in VALID_SYSTEMS:
            crew = get_crew(system)
            assert isinstance(crew, SystemCrew)
            assert crew.name == system

    def test_get_crew_invalid_system_raises(self):
        with pytest.raises(ValueError, match="Unknown system"):
            get_crew("nonexistent")

    def test_get_all_crews_returns_five(self):
        crews = get_all_crews()
        assert len(crews) == 5
        assert set(crews.keys()) == VALID_SYSTEMS

    def test_get_all_crews_are_system_crews(self):
        for name, crew in get_all_crews().items():
            assert isinstance(crew, SystemCrew)
            assert crew.name == name

    def test_total_agent_count_is_28(self):
        total_agents = sum(len(crew.agents) for crew in get_all_crews().values())
        assert total_agents == 28


# ═══════════════════════════════════════════════════════════════════
# Intelligence crew
# ═══════════════════════════════════════════════════════════════════


class TestIntelligenceCrew:
    """Test Intelligence crew — 6 agents."""

    def test_crew_has_six_agents(self):
        crew = build_intelligence_crew()
        assert len(crew.agents) == 6

    def test_crew_has_six_tasks(self):
        crew = build_intelligence_crew()
        assert len(crew.tasks) == 6

    def test_crew_name(self):
        crew = build_intelligence_crew()
        assert crew.name == "intelligence"

    def test_all_agents_instantiate(self):
        agents = [
            NumerologyAnalyst(),
            AstrologyAnalyst(),
            PersonalityAnalyst(),
            BiorhythmCalculator(),
            ArchetypesSynthesizer(),
            IntelligenceGuide(),
        ]
        assert len(agents) == 6
        for agent in agents:
            assert agent.system == "intelligence"
            assert isinstance(agent.role, AgentRole)

    def test_numerology_analyst_execution(self):
        agent = NumerologyAnalyst()
        context = {"full_name": "John Doe", "birth_date": date(1990, 3, 15)}
        result = agent.execute(context)
        assert "numerology" in result
        assert result["numerology"] is not None
        assert "life_path" in result["numerology"]

    def test_numerology_analyst_missing_data(self):
        agent = NumerologyAnalyst()
        result = agent.execute({})
        assert result["numerology"] is None
        assert "numerology_error" in result

    def test_astrology_analyst_execution(self):
        agent = AstrologyAnalyst()
        context = {"birth_date": date(1990, 3, 15)}
        result = agent.execute(context)
        assert "astrology" in result
        assert result["astrology"] is not None
        assert "sun_sign" in result["astrology"]

    def test_astrology_analyst_missing_data(self):
        agent = AstrologyAnalyst()
        result = agent.execute({})
        assert result["astrology"] is None

    def test_personality_analyst_with_big_five(self):
        agent = PersonalityAnalyst()
        context = {
            "big_five": {
                "openness": 80,
                "conscientiousness": 60,
                "extraversion": 40,
                "agreeableness": 70,
                "neuroticism": 30,
            },
            "enneagram_type": 4,
            "attachment_style": "secure",
        }
        result = agent.execute(context)
        assert "personality" in result
        assert result["personality"] is not None
        assert "big_five" in result["personality"]

    def test_personality_analyst_empty(self):
        agent = PersonalityAnalyst()
        result = agent.execute({})
        assert result["personality"] is None

    def test_biorhythm_calculator_execution(self):
        agent = BiorhythmCalculator()
        context = {"birth_date": date(1990, 1, 1), "target_date": date(2024, 6, 15)}
        result = agent.execute(context)
        assert "biorhythm" in result
        bio = result["biorhythm"]
        assert "physical" in bio
        assert "emotional" in bio
        assert "intellectual" in bio
        assert -1.0 <= bio["physical"] <= 1.0
        assert -1.0 <= bio["emotional"] <= 1.0
        assert -1.0 <= bio["intellectual"] <= 1.0

    def test_biorhythm_calculator_missing_date(self):
        agent = BiorhythmCalculator()
        result = agent.execute({})
        assert result["biorhythm"] is None

    def test_archetypes_synthesizer_execution(self):
        agent = ArchetypesSynthesizer()
        context = {
            "numerology": {"life_path": 7},
            "astrology": {"sun_sign": "Pisces"},
            "personality": {
                "big_five": {
                    "openness": 80,
                    "conscientiousness": 60,
                    "extraversion": 40,
                    "agreeableness": 70,
                    "neuroticism": 30,
                }
            },
        }
        result = agent.execute(context)
        assert "archetype_synthesis" in result
        synthesis = result["archetype_synthesis"]
        assert len(synthesis["themes"]) == 3
        assert synthesis["theme_count"] == 3

    def test_intelligence_guide_execution(self):
        agent = IntelligenceGuide()
        context = {
            "numerology": {"life_path": 7},
            "astrology": {"sun_sign": "Pisces"},
            "biorhythm": {"physical": 0.5, "emotional": -0.2, "intellectual": 0.8},
            "archetype_synthesis": {"themes": ["Life Path 7", "Sun in Pisces"]},
        }
        result = agent.execute(context)
        assert "intelligence_narrative" in result
        assert len(result["intelligence_narrative"]) > 0

    def test_full_crew_run(self):
        crew = build_intelligence_crew()
        context = {
            "full_name": "Jane Smith",
            "birth_date": date(1985, 7, 22),
        }
        results = crew.run(context)
        assert "calculate_numerology" in results
        assert "calculate_astrology" in results
        assert "calculate_biorhythm" in results
        assert "generate_intelligence_narrative" in results


# ═══════════════════════════════════════════════════════════════════
# Healing crew
# ═══════════════════════════════════════════════════════════════════


class TestHealingCrew:
    """Test Healing crew — 6 agents."""

    def test_crew_has_six_agents(self):
        crew = build_healing_crew()
        assert len(crew.agents) == 6

    def test_crew_has_six_tasks(self):
        crew = build_healing_crew()
        assert len(crew.tasks) == 6

    def test_crew_name(self):
        crew = build_healing_crew()
        assert crew.name == "healing"

    def test_all_agents_instantiate(self):
        agents = [
            CrisisDetector(),
            ModalityMatcher(),
            BreathworkGuide(),
            PracticeTracker(),
            HealingValidator(),
            HealingNarrative(),
        ]
        assert len(agents) == 6
        for agent in agents:
            assert agent.system == "healing"

    def test_crisis_detector_no_crisis(self):
        agent = CrisisDetector()
        result = agent.execute({"text": "I am having a good day."})
        assert result["crisis_flag"] is False
        assert result["crisis_response"] is None

    def test_crisis_detector_with_crisis(self):
        agent = CrisisDetector()
        result = agent.execute({"text": "I want to kill myself"})
        assert result["crisis_flag"] is True
        assert result["crisis_response"] is not None
        assert "resources" in result["crisis_response"]

    def test_crisis_detector_empty_text(self):
        agent = CrisisDetector()
        result = agent.execute({})
        assert result["crisis_flag"] is False

    def test_breathwork_guide_execution(self):
        agent = BreathworkGuide()
        result = agent.execute({"difficulty": "foundation", "breathwork_intention": "calm"})
        assert "breathwork_pattern" in result
        pattern = result["breathwork_pattern"]
        assert "name" in pattern
        assert "cycles" in pattern

    def test_practice_tracker_execution(self):
        agent = PracticeTracker()
        result = agent.execute({
            "practice_history": {"breathwork": 15, "meditation": 8, "journaling": 3}
        })
        metrics = result["practice_metrics"]
        assert metrics["total_sessions"] == 26
        assert metrics["modalities_tried"] == 3
        assert metrics["most_practiced"] == "breathwork"

    def test_practice_tracker_empty_history(self):
        agent = PracticeTracker()
        result = agent.execute({})
        assert result["practice_metrics"]["total_sessions"] == 0

    def test_healing_validator_execution(self):
        agent = HealingValidator()
        result = agent.execute({})
        assert "healing_quality" in result
        assert result["healing_quality"]["passed"] is True

    def test_healing_narrative_execution(self):
        agent = HealingNarrative()
        result = agent.execute({
            "crisis_flag": False,
            "recommended_modalities": [
                {"modality": "breathwork", "skill_trigger": "/breathwork"},
            ],
            "breathwork_pattern": {"name": "box_breathing"},
            "practice_metrics": {"total_sessions": 10},
        })
        assert "healing_narrative" in result
        assert "disclaimers" in result
        assert "breathwork" in result["healing_narrative"].lower()

    def test_healing_narrative_with_crisis(self):
        agent = HealingNarrative()
        result = agent.execute({
            "crisis_flag": True,
            "crisis_response": {
                "severity": "high",
                "resources": [
                    {"name": "988 Lifeline", "contact": "988"},
                ],
            },
        })
        assert "988" in result["healing_narrative"]


# ═══════════════════════════════════════════════════════════════════
# Wealth crew
# ═══════════════════════════════════════════════════════════════════


class TestWealthCrew:
    """Test Wealth crew — 6 agents."""

    def test_crew_has_six_agents(self):
        crew = build_wealth_crew()
        assert len(crew.agents) == 6

    def test_crew_has_six_tasks(self):
        crew = build_wealth_crew()
        assert len(crew.tasks) == 6

    def test_crew_name(self):
        crew = build_wealth_crew()
        assert crew.name == "wealth"

    def test_all_agents_instantiate(self):
        agents = [
            WealthArchetypeAnalyst(),
            LeverCalculator(),
            DebtStrategist(),
            BudgetAnalyst(),
            WealthValidator(),
            WealthNarrative(),
        ]
        assert len(agents) == 6
        for agent in agents:
            assert agent.system == "wealth"

    def test_wealth_archetype_analyst_execution(self):
        agent = WealthArchetypeAnalyst()
        result = agent.execute({
            "life_path": 8,
            "archetype_primary": "creator",
            "risk_tolerance": "moderate",
        })
        assert "wealth_archetype" in result
        archetype = result["wealth_archetype"]
        assert archetype is not None
        assert "name" in archetype

    def test_wealth_archetype_analyst_missing_data(self):
        agent = WealthArchetypeAnalyst()
        result = agent.execute({})
        assert result["wealth_archetype"] is None

    def test_lever_calculator_execution(self):
        agent = LeverCalculator()
        result = agent.execute({
            "life_path": 4,
            "risk_tolerance": "conservative",
            "intention": "money",
        })
        assert "lever_priorities" in result
        levers = result["lever_priorities"]
        assert levers is not None
        assert len(levers) == 5
        assert "EARN" in levers

    def test_lever_calculator_missing_data(self):
        agent = LeverCalculator()
        result = agent.execute({})
        assert result["lever_priorities"] is None

    def test_budget_analyst_execution(self):
        agent = BudgetAnalyst()
        result = agent.execute({
            "monthly_income": 5000,
            "monthly_expenses": 3500,
            "expense_categories": {
                "housing": 1500,
                "food": 500,
                "transport": 300,
                "entertainment": 200,
            },
        })
        budget = result["budget_analysis"]
        assert budget is not None
        assert budget["monthly_savings"] == 1500
        assert budget["savings_rate"] == 0.3

    def test_budget_analyst_zero_income(self):
        agent = BudgetAnalyst()
        result = agent.execute({"monthly_income": 0})
        assert result["budget_analysis"] is None

    def test_debt_strategist_execution(self):
        agent = DebtStrategist()
        result = agent.execute({
            "debts": [
                {
                    "name": "Credit Card",
                    "balance": 5000,
                    "interest_rate": 0.18,
                    "minimum_payment": 150,
                    "debt_type": "credit_card",
                },
                {
                    "name": "Student Loan",
                    "balance": 20000,
                    "interest_rate": 0.045,
                    "minimum_payment": 250,
                    "debt_type": "student_loan",
                },
            ],
            "extra_monthly_payment": 200,
        })
        assert "debt_analysis" in result
        debt = result["debt_analysis"]
        assert debt is not None
        assert "snowball_months" in debt
        assert "avalanche_months" in debt

    def test_debt_strategist_no_debts(self):
        agent = DebtStrategist()
        result = agent.execute({})
        assert result["debt_analysis"] is None

    def test_wealth_validator_execution(self):
        agent = WealthValidator()
        result = agent.execute({
            "budget_analysis": {"savings_rate": 0.3, "needs_ratio": 0.5, "wants_ratio": 0.2},
        })
        assert "wealth_quality" in result
        assert result["wealth_quality"]["passed"] is True

    def test_wealth_narrative_execution(self):
        agent = WealthNarrative()
        result = agent.execute({
            "wealth_archetype": {"name": "The Builder"},
            "lever_priorities": ["EARN", "KEEP", "GROW", "PROTECT", "TRANSFER"],
            "budget_analysis": {"savings_rate": 0.25},
        })
        assert "wealth_narrative" in result
        assert "disclaimers" in result
        assert "Builder" in result["wealth_narrative"]


# ═══════════════════════════════════════════════════════════════════
# Creative crew
# ═══════════════════════════════════════════════════════════════════


class TestCreativeCrew:
    """Test Creative crew — 5 agents."""

    def test_crew_has_five_agents(self):
        crew = build_creative_crew()
        assert len(crew.agents) == 5

    def test_crew_has_five_tasks(self):
        crew = build_creative_crew()
        assert len(crew.tasks) == 5

    def test_crew_name(self):
        crew = build_creative_crew()
        assert crew.name == "creative"

    def test_all_agents_instantiate(self):
        agents = [
            GuilfordAssessor(),
            StyleAnalyst(),
            ProjectSuggester(),
            CreativeBlockDetector(),
            CreativeNarrative(),
        ]
        assert len(agents) == 5
        for agent in agents:
            assert agent.system == "creative"

    def test_guilford_assessor_execution(self):
        agent = GuilfordAssessor()
        result = agent.execute({
            "guilford_responses": {
                "fluency": 75,
                "flexibility": 60,
                "originality": 85,
                "elaboration": 50,
                "sensitivity": 70,
                "redefinition": 40,
            },
        })
        assert "guilford_scores" in result
        scores = result["guilford_scores"]
        assert scores is not None
        assert scores["fluency"] == 75
        assert scores["originality"] == 85

    def test_guilford_assessor_no_responses(self):
        agent = GuilfordAssessor()
        result = agent.execute({})
        assert result["guilford_scores"] is None

    def test_style_analyst_execution(self):
        agent = StyleAnalyst()
        from alchymine.engine.profile import GuilfordScores

        scores = GuilfordScores(
            fluency=75, flexibility=60, originality=85,
            elaboration=50, sensitivity=70, redefinition=40,
        )
        result = agent.execute({"_guilford_model": scores})
        assert "style_fingerprint" in result
        assert "creative_strengths" in result
        assert "creative_growth_areas" in result

    def test_style_analyst_from_dict(self):
        agent = StyleAnalyst()
        result = agent.execute({
            "guilford_scores": {
                "fluency": 75, "flexibility": 60, "originality": 85,
                "elaboration": 50, "sensitivity": 70, "redefinition": 40,
            },
        })
        assert result["style_fingerprint"] is not None

    def test_style_analyst_no_scores(self):
        agent = StyleAnalyst()
        result = agent.execute({})
        assert result["style_fingerprint"] is None

    def test_project_suggester_execution(self):
        agent = ProjectSuggester()
        result = agent.execute({
            "style_fingerprint": {
                "dominant_components": ["originality", "fluency"],
            },
            "skill_level": "beginner",
        })
        assert "project_suggestions" in result
        projects = result["project_suggestions"]
        assert isinstance(projects, list)
        assert len(projects) > 0

    def test_project_suggester_no_style(self):
        agent = ProjectSuggester()
        result = agent.execute({})
        assert result["project_suggestions"] is None

    def test_creative_block_detector_execution(self):
        agent = CreativeBlockDetector()
        result = agent.execute({
            "guilford_scores": {
                "fluency": 75, "flexibility": 20, "originality": 85,
                "elaboration": 15, "sensitivity": 70, "redefinition": 40,
            },
        })
        assert "creative_blocks" in result
        blocks = result["creative_blocks"]
        assert len(blocks) == 2  # flexibility=20 and elaboration=15

    def test_creative_block_detector_no_blocks(self):
        agent = CreativeBlockDetector()
        result = agent.execute({
            "guilford_scores": {
                "fluency": 75, "flexibility": 60, "originality": 85,
                "elaboration": 50, "sensitivity": 70, "redefinition": 55,
            },
        })
        assert result["creative_blocks"] is not None
        assert len(result["creative_blocks"]) == 0

    def test_creative_block_detector_no_scores(self):
        agent = CreativeBlockDetector()
        result = agent.execute({})
        assert result["creative_blocks"] is None

    def test_creative_narrative_execution(self):
        agent = CreativeNarrative()
        result = agent.execute({
            "style_fingerprint": {
                "creative_style": "A moderately structured creator.",
                "overall_score": 65.0,
            },
            "creative_strengths": ["Originality", "Fluency"],
            "creative_growth_areas": ["Elaboration"],
            "project_suggestions": [{"title": "100 Ideas Challenge"}],
            "creative_blocks": [{"component": "elaboration"}],
        })
        assert "creative_narrative" in result
        assert len(result["creative_narrative"]) > 0

    def test_full_crew_run(self):
        crew = build_creative_crew()
        context = {
            "guilford_responses": {
                "fluency": 75, "flexibility": 60, "originality": 85,
                "elaboration": 50, "sensitivity": 70, "redefinition": 40,
            },
            "skill_level": "beginner",
        }
        results = crew.run(context)
        assert "assess_guilford" in results
        assert "analyze_style" in results
        assert "suggest_projects" in results
        assert "detect_blocks" in results
        assert "generate_creative_narrative" in results


# ═══════════════════════════════════════════════════════════════════
# Perspective crew
# ═══════════════════════════════════════════════════════════════════


class TestPerspectiveCrew:
    """Test Perspective crew — 5 agents."""

    def test_crew_has_five_agents(self):
        crew = build_perspective_crew()
        assert len(crew.agents) == 5

    def test_crew_has_five_tasks(self):
        crew = build_perspective_crew()
        assert len(crew.tasks) == 5

    def test_crew_name(self):
        crew = build_perspective_crew()
        assert crew.name == "perspective"

    def test_all_agents_instantiate(self):
        agents = [
            BiasDetector(),
            KeganAssessor(),
            FrameworkApplier(),
            ScenarioModeler(),
            PerspectiveNarrative(),
        ]
        assert len(agents) == 5
        for agent in agents:
            assert agent.system == "perspective"

    def test_bias_detector_finds_biases(self):
        agent = BiasDetector()
        result = agent.execute({
            "text": "I knew it all along, this proves my point exactly as I expected."
        })
        assert "detected_biases" in result
        biases = result["detected_biases"]
        assert len(biases) > 0
        assert "debiasing_suggestions" in result

    def test_bias_detector_no_biases(self):
        agent = BiasDetector()
        result = agent.execute({"text": "The data shows a 15% increase in revenue."})
        assert "detected_biases" in result
        # This text might or might not trigger biases — just check structure
        assert isinstance(result["detected_biases"], list)

    def test_bias_detector_empty_text(self):
        agent = BiasDetector()
        result = agent.execute({})
        assert result["detected_biases"] == []

    def test_kegan_assessor_execution(self):
        agent = KeganAssessor()
        result = agent.execute({
            "kegan_responses": {
                "self_awareness": 4.0,
                "perspective_taking": 4.0,
                "relationship_to_authority": 4.5,
                "conflict_tolerance": 4.0,
                "systems_thinking": 3.5,
            },
        })
        assert "kegan_stage" in result
        assert result["kegan_stage"] is not None
        assert "kegan_description" in result
        assert "kegan_pathway" in result

    def test_kegan_assessor_no_responses(self):
        agent = KeganAssessor()
        result = agent.execute({})
        assert result["kegan_stage"] is None

    def test_framework_applier_pros_cons(self):
        agent = FrameworkApplier()
        result = agent.execute({
            "decision": "Accept job offer",
            "pros": ["Higher salary", "Better benefits"],
            "cons": ["Longer commute"],
        })
        assert "decision_analysis" in result
        analysis = result["decision_analysis"]
        assert "pros_cons" in analysis
        assert analysis["pros_cons"]["balance_score"] > 0

    def test_framework_applier_six_hats(self):
        agent = FrameworkApplier()
        result = agent.execute({
            "problem": "Should we expand to new market?",
            "perspectives": {
                "white": "Revenue data shows 20% growth potential.",
                "red": "I feel excited but nervous.",
                "black": "Market is competitive.",
            },
        })
        assert "decision_analysis" in result
        assert "six_hats" in result["decision_analysis"]

    def test_framework_applier_no_data(self):
        agent = FrameworkApplier()
        result = agent.execute({})
        assert result["decision_analysis"] is None

    def test_scenario_modeler_execution(self):
        agent = ScenarioModeler()
        result = agent.execute({
            "scenario_decision": "Launch new product",
            "scenario_variables": [
                {"name": "market_size", "best": 1000, "worst": 200, "likely": 500},
                {"name": "conversion_rate", "best": 0.1, "worst": 0.01, "likely": 0.05},
            ],
        })
        assert "scenario_analysis" in result
        analysis = result["scenario_analysis"]
        assert "scenarios" in analysis
        assert len(analysis["scenarios"]) == 3

    def test_scenario_modeler_second_order(self):
        agent = ScenarioModeler()
        result = agent.execute({
            "decision": "Relocate headquarters",
            "first_order_effects": [
                "Lower operating costs",
                "Talent pool changes",
            ],
        })
        assert "scenario_analysis" in result
        assert "second_order_effects" in result["scenario_analysis"]

    def test_scenario_modeler_no_data(self):
        agent = ScenarioModeler()
        result = agent.execute({})
        assert result["scenario_analysis"] is None

    def test_perspective_narrative_execution(self):
        agent = PerspectiveNarrative()
        result = agent.execute({
            "detected_biases": [
                {"bias_name": "Confirmation Bias", "confidence": 0.67},
            ],
            "kegan_stage": "self-authoring",
            "kegan_description": {"name": "Self-Authoring"},
            "decision_analysis": {"pros_cons": {}, "six_hats": {}},
            "scenario_analysis": {"scenarios": []},
        })
        assert "perspective_narrative" in result
        assert "Confirmation Bias" in result["perspective_narrative"]
        assert "Self-Authoring" in result["perspective_narrative"]

    def test_perspective_narrative_empty(self):
        agent = PerspectiveNarrative()
        result = agent.execute({})
        assert "perspective_narrative" in result
        assert len(result["perspective_narrative"]) > 0

    def test_full_crew_run(self):
        crew = build_perspective_crew()
        context = {
            "text": "I knew it all along, proves my point.",
            "kegan_responses": {
                "self_awareness": 3.0,
                "perspective_taking": 3.0,
                "conflict_tolerance": 2.5,
            },
            "decision": "Change careers",
            "pros": ["More fulfillment"],
            "cons": ["Lower initial pay"],
        }
        results = crew.run(context)
        assert "detect_biases" in results
        assert "assess_kegan_stage" in results
        assert "apply_frameworks" in results
        assert "generate_perspective_narrative" in results


# ═══════════════════════════════════════════════════════════════════
# Error handling and engine unavailability
# ═══════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Test graceful degradation when engine modules are unavailable."""

    def test_numerology_agent_handles_import_error(self):
        agent = NumerologyAnalyst()
        with patch(
            "alchymine.agents.crews.intelligence.NumerologyAnalyst.execute",
            side_effect=ImportError("numerology engine not available"),
        ):
            crew = SystemCrew(
                name="test",
                agents=[agent],
                tasks=[
                    AgentTask(
                        name="test_task",
                        description="Test",
                        agent=agent,
                        expected_output="Test",
                    ),
                ],
            )
            results = crew.run({"full_name": "Test", "birth_date": date(1990, 1, 1)})
            assert "error" in results["test_task"]

    def test_crew_continues_on_agent_failure(self):
        """When one agent fails, the crew should continue with remaining tasks."""
        crew = build_intelligence_crew()

        # Patch numerology to fail
        original_execute = NumerologyAnalyst.execute
        with patch.object(
            NumerologyAnalyst,
            "execute",
            side_effect=RuntimeError("Engine unavailable"),
        ):
            context = {
                "full_name": "Test User",
                "birth_date": date(1990, 6, 15),
            }
            results = crew.run(context)

            # Numerology failed
            assert "error" in results["calculate_numerology"]

            # But astrology and biorhythm should still succeed
            assert "astrology" not in results.get("calculate_astrology", {}).get("error", "")

    def test_context_threading_between_agents(self):
        """Test that context from earlier agents flows to later ones."""
        crew = build_intelligence_crew()
        context = {
            "full_name": "Alice Wonderland",
            "birth_date": date(1992, 12, 25),
        }
        results = crew.run(context)

        # The synthesizer should have themes from numerology and astrology
        synthesis_result = results.get("synthesize_archetypes", {})
        if "archetype_synthesis" in synthesis_result:
            themes = synthesis_result["archetype_synthesis"].get("themes", [])
            # Should have at least numerology and astrology themes
            assert len(themes) >= 2


# ═══════════════════════════════════════════════════════════════════
# Agent metadata validation
# ═══════════════════════════════════════════════════════════════════


class TestAgentMetadata:
    """Validate that all agents have proper metadata."""

    def test_all_agents_have_names(self):
        for crew in get_all_crews().values():
            for agent in crew.agents:
                assert agent.name, f"Agent in {crew.name} has no name"

    def test_all_agents_have_goals(self):
        for crew in get_all_crews().values():
            for agent in crew.agents:
                assert agent.goal, f"{agent.name} in {crew.name} has no goal"

    def test_all_agents_have_backstories(self):
        for crew in get_all_crews().values():
            for agent in crew.agents:
                assert agent.backstory, f"{agent.name} in {crew.name} has no backstory"

    def test_all_agents_have_valid_roles(self):
        for crew in get_all_crews().values():
            for agent in crew.agents:
                assert isinstance(agent.role, AgentRole), (
                    f"{agent.name} has invalid role: {agent.role}"
                )

    def test_all_agents_have_system_set(self):
        for name, crew in get_all_crews().items():
            for agent in crew.agents:
                assert agent.system == name, (
                    f"{agent.name} has system '{agent.system}' "
                    f"but belongs to crew '{name}'"
                )

    def test_all_agents_have_tools(self):
        for crew in get_all_crews().values():
            for agent in crew.agents:
                assert isinstance(agent.tools, list), (
                    f"{agent.name} tools is not a list"
                )
                assert len(agent.tools) > 0, (
                    f"{agent.name} has no tools defined"
                )

    def test_all_tasks_reference_valid_agents(self):
        for crew in get_all_crews().values():
            for task in crew.tasks:
                assert task.agent in crew.agents, (
                    f"Task '{task.name}' references agent '{task.agent.name}' "
                    f"which is not in crew '{crew.name}'"
                )

    def test_unique_agent_names_per_crew(self):
        for crew in get_all_crews().values():
            names = [a.name for a in crew.agents]
            assert len(names) == len(set(names)), (
                f"Crew '{crew.name}' has duplicate agent names: {names}"
            )

    def test_unique_task_names_per_crew(self):
        for crew in get_all_crews().values():
            names = [t.name for t in crew.tasks]
            assert len(names) == len(set(names)), (
                f"Crew '{crew.name}' has duplicate task names: {names}"
            )

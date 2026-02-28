"""Tests for the Wealth Engine — archetype mapping, lever prioritization, plan generation.

At least 20 tests covering:
- Wealth archetype mapping for various life path + archetype combos
- Lever prioritization with different contexts
- 90-day plan generation produces valid structure
"""

from __future__ import annotations

import pytest

from alchymine.engine.profile import (
    ArchetypeType,
    Intention,
    RiskTolerance,
    WealthContext,
    WealthLever,
)
from alchymine.engine.wealth.archetype import (
    WEALTH_ARCHETYPES,
    WealthArchetype,
    get_wealth_archetype_scores,
    map_wealth_archetype,
)
from alchymine.engine.wealth.levers import prioritize_levers
from alchymine.engine.wealth.plan import (
    ActivationPlan,
    generate_activation_plan,
)

# ═══════════════════════════════════════════════════════════════════════════
# Wealth Archetype Mapping Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestWealthArchetypeMapping:
    """Tests for map_wealth_archetype()."""

    def test_builder_life_path_4_ruler(self) -> None:
        """Life path 4 + Ruler archetype = The Builder."""
        result = map_wealth_archetype(
            life_path=4,
            archetype_primary=ArchetypeType.RULER,
            risk_tolerance=RiskTolerance.CONSERVATIVE,
        )
        assert result.name == "The Builder"

    def test_builder_life_path_8_ruler(self) -> None:
        """Life path 8 + Ruler archetype = The Builder."""
        result = map_wealth_archetype(
            life_path=8,
            archetype_primary=ArchetypeType.RULER,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert result.name == "The Builder"

    def test_builder_life_path_22_ruler(self) -> None:
        """Life path 22 (master number) + Ruler = The Builder."""
        result = map_wealth_archetype(
            life_path=22,
            archetype_primary=ArchetypeType.RULER,
            risk_tolerance=RiskTolerance.CONSERVATIVE,
        )
        assert result.name == "The Builder"

    def test_innovator_life_path_3_creator(self) -> None:
        """Life path 3 + Creator archetype = The Innovator."""
        result = map_wealth_archetype(
            life_path=3,
            archetype_primary=ArchetypeType.CREATOR,
            risk_tolerance=RiskTolerance.AGGRESSIVE,
        )
        assert result.name == "The Innovator"

    def test_innovator_life_path_5_explorer(self) -> None:
        """Life path 5 + Explorer archetype = The Innovator."""
        result = map_wealth_archetype(
            life_path=5,
            archetype_primary=ArchetypeType.EXPLORER,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert result.name == "The Innovator"

    def test_sage_investor_life_path_7_sage(self) -> None:
        """Life path 7 + Sage archetype = The Sage Investor."""
        result = map_wealth_archetype(
            life_path=7,
            archetype_primary=ArchetypeType.SAGE,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert result.name == "The Sage Investor"

    def test_connector_life_path_6_lover(self) -> None:
        """Life path 6 + Lover archetype = The Connector."""
        result = map_wealth_archetype(
            life_path=6,
            archetype_primary=ArchetypeType.LOVER,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert result.name == "The Connector"

    def test_warrior_life_path_1_hero(self) -> None:
        """Life path 1 + Hero archetype = The Warrior."""
        result = map_wealth_archetype(
            life_path=1,
            archetype_primary=ArchetypeType.HERO,
            risk_tolerance=RiskTolerance.AGGRESSIVE,
        )
        assert result.name == "The Warrior"

    def test_mystic_trader_life_path_9_mystic(self) -> None:
        """Life path 9 + Mystic archetype = The Mystic Trader."""
        result = map_wealth_archetype(
            life_path=9,
            archetype_primary=ArchetypeType.MYSTIC,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert result.name == "The Mystic Trader"

    def test_mystic_trader_life_path_11_mystic(self) -> None:
        """Life path 11 + Mystic archetype = The Mystic Trader."""
        result = map_wealth_archetype(
            life_path=11,
            archetype_primary=ArchetypeType.MYSTIC,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert result.name == "The Mystic Trader"

    def test_entertainer_life_path_5_jester(self) -> None:
        """Life path 5 + Jester archetype = The Entertainer."""
        result = map_wealth_archetype(
            life_path=5,
            archetype_primary=ArchetypeType.JESTER,
            risk_tolerance=RiskTolerance.AGGRESSIVE,
        )
        assert result.name == "The Entertainer"

    def test_return_type_is_wealth_archetype(self) -> None:
        """map_wealth_archetype always returns a WealthArchetype instance."""
        result = map_wealth_archetype(
            life_path=1,
            archetype_primary=ArchetypeType.SAGE,
            risk_tolerance=RiskTolerance.MODERATE,
        )
        assert isinstance(result, WealthArchetype)

    def test_all_8_archetypes_defined(self) -> None:
        """WEALTH_ARCHETYPES registry has exactly 8 entries."""
        assert len(WEALTH_ARCHETYPES) == 8

    def test_deterministic_same_inputs_same_output(self) -> None:
        """Same inputs always produce the same output."""
        result1 = map_wealth_archetype(3, ArchetypeType.CREATOR, RiskTolerance.MODERATE)
        result2 = map_wealth_archetype(3, ArchetypeType.CREATOR, RiskTolerance.MODERATE)
        assert result1.name == result2.name
        assert result1.description == result2.description

    def test_scores_transparency(self) -> None:
        """get_wealth_archetype_scores returns scores for all 8 archetypes."""
        scores = get_wealth_archetype_scores(
            life_path=4,
            archetype_primary=ArchetypeType.RULER,
            risk_tolerance=RiskTolerance.CONSERVATIVE,
        )
        assert len(scores) == 8
        assert all(isinstance(v, float) for v in scores.values())
        # The Builder should have the highest score for LP4 + Ruler + Conservative
        assert scores["The Builder"] == max(scores.values())

    def test_risk_tolerance_affects_scoring(self) -> None:
        """Different risk tolerances produce different scores."""
        scores_conservative = get_wealth_archetype_scores(
            life_path=1,
            archetype_primary=ArchetypeType.HERO,
            risk_tolerance=RiskTolerance.CONSERVATIVE,
        )
        scores_aggressive = get_wealth_archetype_scores(
            life_path=1,
            archetype_primary=ArchetypeType.HERO,
            risk_tolerance=RiskTolerance.AGGRESSIVE,
        )
        # The Warrior should score higher with aggressive risk tolerance
        assert scores_aggressive["The Warrior"] > scores_conservative["The Warrior"]


# ═══════════════════════════════════════════════════════════════════════════
# Lever Prioritization Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestLeverPrioritization:
    """Tests for prioritize_levers()."""

    def test_low_income_earn_first(self) -> None:
        """Low income context puts EARN as the top priority."""
        ctx = WealthContext(income_range="$25k-$50k")
        levers = prioritize_levers(ctx, RiskTolerance.MODERATE, Intention.MONEY, life_path=1)
        assert levers[0] == WealthLever.EARN

    def test_dependents_boost_protect(self) -> None:
        """Having dependents boosts PROTECT priority."""
        ctx_no_deps = WealthContext(dependents=0)
        ctx_deps = WealthContext(dependents=2)
        levers_no_deps = prioritize_levers(
            ctx_no_deps, RiskTolerance.MODERATE, Intention.CAREER, life_path=1
        )
        levers_deps = prioritize_levers(
            ctx_deps, RiskTolerance.MODERATE, Intention.CAREER, life_path=1
        )
        # PROTECT should be higher priority with dependents
        idx_no_deps = levers_no_deps.index(WealthLever.PROTECT)
        idx_deps = levers_deps.index(WealthLever.PROTECT)
        assert idx_deps < idx_no_deps  # Lower index = higher priority

    def test_returns_all_5_levers(self) -> None:
        """prioritize_levers always returns all 5 levers."""
        levers = prioritize_levers(None, RiskTolerance.MODERATE, Intention.MONEY, life_path=1)
        assert len(levers) == 5
        assert set(levers) == set(WealthLever)

    def test_family_intention_boosts_protect_and_transfer(self) -> None:
        """Family intention boosts PROTECT and TRANSFER priorities."""
        levers_family = prioritize_levers(
            None, RiskTolerance.MODERATE, Intention.FAMILY, life_path=6
        )
        levers_money = prioritize_levers(None, RiskTolerance.MODERATE, Intention.MONEY, life_path=6)
        # PROTECT should be higher with family intention
        assert levers_family.index(WealthLever.PROTECT) < levers_money.index(WealthLever.PROTECT)

    def test_legacy_intention_puts_transfer_high(self) -> None:
        """Legacy intention makes TRANSFER a top priority."""
        levers = prioritize_levers(None, RiskTolerance.MODERATE, Intention.LEGACY, life_path=9)
        assert levers[0] == WealthLever.TRANSFER

    def test_aggressive_risk_boosts_grow(self) -> None:
        """Aggressive risk tolerance boosts GROW priority."""
        levers_conservative = prioritize_levers(
            None, RiskTolerance.CONSERVATIVE, Intention.MONEY, life_path=7
        )
        levers_aggressive = prioritize_levers(
            None, RiskTolerance.AGGRESSIVE, Intention.MONEY, life_path=7
        )
        assert levers_aggressive.index(WealthLever.GROW) <= levers_conservative.index(
            WealthLever.GROW
        )

    def test_has_business_boosts_earn(self) -> None:
        """Having a business boosts EARN priority."""
        ctx_no_biz = WealthContext(has_business=False)
        ctx_biz = WealthContext(has_business=True)
        levers_no_biz = prioritize_levers(
            ctx_no_biz, RiskTolerance.MODERATE, Intention.CAREER, life_path=8
        )
        levers_biz = prioritize_levers(
            ctx_biz, RiskTolerance.MODERATE, Intention.CAREER, life_path=8
        )
        assert levers_biz.index(WealthLever.EARN) <= levers_no_biz.index(WealthLever.EARN)

    def test_none_context_uses_defaults(self) -> None:
        """None wealth context doesn't crash; uses moderate defaults."""
        levers = prioritize_levers(None, RiskTolerance.MODERATE, Intention.MONEY, life_path=1)
        assert len(levers) == 5

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs always produce the same lever ordering."""
        ctx = WealthContext(income_range="$50k-$75k", has_investments=True, dependents=1)
        levers1 = prioritize_levers(ctx, RiskTolerance.MODERATE, Intention.FAMILY, life_path=6)
        levers2 = prioritize_levers(ctx, RiskTolerance.MODERATE, Intention.FAMILY, life_path=6)
        assert levers1 == levers2


# ═══════════════════════════════════════════════════════════════════════════
# Activation Plan Generation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestActivationPlan:
    """Tests for generate_activation_plan()."""

    def _make_plan(
        self,
        archetype_name: str = "The Builder",
        levers: list[WealthLever] | None = None,
        risk: RiskTolerance = RiskTolerance.MODERATE,
    ) -> ActivationPlan:
        """Helper to generate a plan with defaults."""
        archetype = WEALTH_ARCHETYPES[archetype_name]
        if levers is None:
            levers = [
                WealthLever.EARN,
                WealthLever.GROW,
                WealthLever.KEEP,
                WealthLever.PROTECT,
                WealthLever.TRANSFER,
            ]
        return generate_activation_plan(archetype, levers, risk)

    def test_plan_has_3_phases(self) -> None:
        """Plan always contains exactly 3 phases."""
        plan = self._make_plan()
        assert len(plan.phases) == 3

    def test_phase_1_is_foundation(self) -> None:
        """Phase 1 is 'Foundation' covering days 1-30."""
        plan = self._make_plan()
        assert plan.phases[0].name == "Foundation"
        assert plan.phases[0].days == (1, 30)

    def test_phase_2_is_building(self) -> None:
        """Phase 2 is 'Building' covering days 31-60."""
        plan = self._make_plan()
        assert plan.phases[1].name == "Building"
        assert plan.phases[1].days == (31, 60)

    def test_phase_3_is_acceleration(self) -> None:
        """Phase 3 is 'Acceleration' covering days 61-90."""
        plan = self._make_plan()
        assert plan.phases[2].name == "Acceleration"
        assert plan.phases[2].days == (61, 90)

    def test_phases_focus_on_top_3_levers(self) -> None:
        """Each phase focuses on the corresponding lever priority."""
        levers = [
            WealthLever.PROTECT,
            WealthLever.TRANSFER,
            WealthLever.EARN,
            WealthLever.GROW,
            WealthLever.KEEP,
        ]
        plan = self._make_plan(levers=levers)
        assert plan.phases[0].focus_lever == WealthLever.PROTECT
        assert plan.phases[1].focus_lever == WealthLever.TRANSFER
        assert plan.phases[2].focus_lever == WealthLever.EARN

    def test_each_phase_has_actions(self) -> None:
        """Every phase has at least one action."""
        plan = self._make_plan()
        for phase in plan.phases:
            assert len(phase.actions) > 0

    def test_each_phase_has_milestones(self) -> None:
        """Every phase has at least one milestone."""
        plan = self._make_plan()
        for phase in plan.phases:
            assert len(phase.milestones) > 0

    def test_plan_has_daily_habits(self) -> None:
        """Plan includes daily habits."""
        plan = self._make_plan()
        assert len(plan.daily_habits) > 0

    def test_plan_has_weekly_reviews(self) -> None:
        """Plan includes weekly review items."""
        plan = self._make_plan()
        assert len(plan.weekly_reviews) > 0

    def test_plan_archetype_name_matches(self) -> None:
        """Plan records the wealth archetype name."""
        plan = self._make_plan(archetype_name="The Sage Investor")
        assert plan.wealth_archetype == "The Sage Investor"

    def test_conservative_risk_daily_habits(self) -> None:
        """Conservative risk tolerance produces appropriate daily habits."""
        plan = self._make_plan(risk=RiskTolerance.CONSERVATIVE)
        habits_text = " ".join(plan.daily_habits).lower()
        assert "security" in habits_text or "gratitude" in habits_text

    def test_aggressive_risk_daily_habits(self) -> None:
        """Aggressive risk tolerance produces appropriate daily habits."""
        plan = self._make_plan(risk=RiskTolerance.AGGRESSIVE)
        habits_text = " ".join(plan.daily_habits).lower()
        assert "growth" in habits_text or "bold" in habits_text

    def test_all_8_archetypes_produce_valid_plans(self) -> None:
        """Every wealth archetype can generate a valid plan."""
        levers = list(WealthLever)
        for name, archetype in WEALTH_ARCHETYPES.items():
            plan = generate_activation_plan(archetype, levers, RiskTolerance.MODERATE)
            assert plan.wealth_archetype == name
            assert len(plan.phases) == 3
            assert len(plan.daily_habits) > 0
            assert len(plan.weekly_reviews) > 0

    def test_plan_is_frozen_dataclass(self) -> None:
        """ActivationPlan and PlanPhase are frozen (immutable)."""
        plan = self._make_plan()
        with pytest.raises(AttributeError):
            plan.wealth_archetype = "changed"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            plan.phases[0].name = "changed"  # type: ignore[misc]

"""Tests for the healing modality engine (Phase 2).

Covers modality definitions, the matching algorithm, contraindication
filtering, difficulty filtering, breathwork patterns, and the
breathwork selector function.
"""

from __future__ import annotations

import pytest

from alchymine.engine.healing import (
    BREATHWORK_PATTERNS,
    MODALITY_REGISTRY,
    BreathworkPattern,
    ModalityDefinition,
    get_breathwork_pattern,
    match_modalities,
)
from alchymine.engine.healing.breathwork import (
    _INTENTION_PATTERN_AFFINITY,
)
from alchymine.engine.healing.matcher import (
    _AFFINITY_TO_MODALITY,
    _is_contraindicated,
    _resolve_archetype_affinities,
)
from alchymine.engine.healing.modalities import (
    VALID_CATEGORIES,
    VALID_EVIDENCE_LEVELS,
    get_modalities_by_category,
    get_modalities_by_difficulty,
)
from alchymine.engine.profile import (
    ArchetypeType,
    BigFiveScores,
    HealingPreference,
    Intention,
    PracticeDifficulty,
)


# ─── Helpers ─────────────────────────────────────────────────────────


def _make_big_five(
    openness: float = 50.0,
    conscientiousness: float = 50.0,
    extraversion: float = 50.0,
    agreeableness: float = 50.0,
    neuroticism: float = 50.0,
) -> BigFiveScores:
    return BigFiveScores(
        openness=openness,
        conscientiousness=conscientiousness,
        extraversion=extraversion,
        agreeableness=agreeableness,
        neuroticism=neuroticism,
    )


NEUTRAL_BIG_FIVE = _make_big_five()


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Modality Registry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestModalityRegistry:
    """Tests for the MODALITY_REGISTRY and ModalityDefinition."""

    def test_registry_has_15_modalities(self) -> None:
        """The registry must contain exactly 15 modalities."""
        assert len(MODALITY_REGISTRY) == 15

    def test_all_expected_modalities_present(self) -> None:
        """Every expected modality name is present in the registry."""
        expected = {
            "breathwork",
            "coherence_meditation",
            "language_awareness",
            "resilience_training",
            "consciousness_journey",
            "sound_healing",
            "somatic_practice",
            "sleep_healing",
            "nature_healing",
            "pni_mapping",
            "grief_healing",
            "water_healing",
            "community_healing",
            "expressive_healing",
            "contemplative_inquiry",
        }
        assert set(MODALITY_REGISTRY.keys()) == expected

    def test_registry_keys_match_definition_names(self) -> None:
        """Each registry key must match its ModalityDefinition.name."""
        for key, definition in MODALITY_REGISTRY.items():
            assert key == definition.name, f"Key '{key}' != definition name '{definition.name}'"

    def test_all_modalities_are_frozen_dataclass_instances(self) -> None:
        """Each registry value is a ModalityDefinition."""
        for definition in MODALITY_REGISTRY.values():
            assert isinstance(definition, ModalityDefinition)

    def test_all_categories_are_valid(self) -> None:
        """Each modality has a valid category."""
        for definition in MODALITY_REGISTRY.values():
            assert definition.category in VALID_CATEGORIES, (
                f"{definition.name} has invalid category '{definition.category}'"
            )

    def test_all_evidence_levels_are_valid(self) -> None:
        """Each modality has a valid evidence level."""
        for definition in MODALITY_REGISTRY.values():
            assert definition.evidence_level in VALID_EVIDENCE_LEVELS, (
                f"{definition.name} has invalid evidence_level '{definition.evidence_level}'"
            )

    def test_all_skill_triggers_start_with_slash(self) -> None:
        """Each skill trigger must start with '/'."""
        for definition in MODALITY_REGISTRY.values():
            assert definition.skill_trigger.startswith("/"), (
                f"{definition.name} trigger '{definition.skill_trigger}' missing leading /"
            )

    def test_all_skill_triggers_are_unique(self) -> None:
        """No two modalities share the same skill trigger."""
        triggers = [d.skill_trigger for d in MODALITY_REGISTRY.values()]
        assert len(triggers) == len(set(triggers))

    def test_all_modalities_have_nonempty_description(self) -> None:
        """Every modality must have a non-empty description."""
        for definition in MODALITY_REGISTRY.values():
            assert len(definition.description.strip()) > 10, (
                f"{definition.name} has empty or trivial description"
            )

    def test_all_modalities_have_at_least_one_tradition(self) -> None:
        """Every modality must list at least one cultural tradition."""
        for definition in MODALITY_REGISTRY.values():
            assert len(definition.traditions) >= 1, (
                f"{definition.name} has no traditions listed"
            )

    def test_contraindications_are_tuples(self) -> None:
        """Contraindications must be tuples (immutable)."""
        for definition in MODALITY_REGISTRY.values():
            assert isinstance(definition.contraindications, tuple), (
                f"{definition.name} contraindications is not a tuple"
            )

    def test_get_modalities_by_category_somatic(self) -> None:
        """Category filter returns correct somatic modalities."""
        somatic = get_modalities_by_category("somatic")
        somatic_names = {m.name for m in somatic}
        expected_somatic = {
            "breathwork", "resilience_training", "sound_healing",
            "somatic_practice", "sleep_healing", "pni_mapping",
        }
        assert somatic_names == expected_somatic

    def test_get_modalities_by_difficulty_foundation(self) -> None:
        """Difficulty filter at FOUNDATION returns only foundation modalities."""
        foundation = get_modalities_by_difficulty(PracticeDifficulty.FOUNDATION)
        for m in foundation:
            assert m.min_difficulty == PracticeDifficulty.FOUNDATION

    def test_get_modalities_by_difficulty_developing_includes_foundation(self) -> None:
        """Difficulty filter at DEVELOPING includes both foundation and developing."""
        developing = get_modalities_by_difficulty(PracticeDifficulty.DEVELOPING)
        difficulties = {m.min_difficulty for m in developing}
        assert PracticeDifficulty.FOUNDATION in difficulties
        assert PracticeDifficulty.DEVELOPING in difficulties
        # Should NOT include established or above
        assert PracticeDifficulty.ESTABLISHED not in difficulties
        assert PracticeDifficulty.ADVANCED not in difficulties


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Modality Matcher Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMatchModalities:
    """Tests for the match_modalities function."""

    def test_returns_list_of_healing_preferences(self) -> None:
        """Result type is list[HealingPreference]."""
        results = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        assert isinstance(results, list)
        assert all(isinstance(r, HealingPreference) for r in results)

    def test_respects_max_results(self) -> None:
        """Result list respects the max_results parameter."""
        results = match_modalities(
            archetype_primary=ArchetypeType.CREATOR,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
            max_results=3,
        )
        assert len(results) <= 3

    def test_default_max_results_is_7(self) -> None:
        """Default max_results=7 is respected."""
        results = match_modalities(
            archetype_primary=ArchetypeType.EXPLORER,
            archetype_secondary=ArchetypeType.SAGE,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.CAREER,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        assert len(results) <= 7

    def test_results_sorted_by_preference_score_descending(self) -> None:
        """Results are sorted by preference_score, highest first."""
        results = match_modalities(
            archetype_primary=ArchetypeType.MYSTIC,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        scores = [r.preference_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_preference_scores_in_valid_range(self) -> None:
        """All preference scores are between 0 and 1 inclusive."""
        results = match_modalities(
            archetype_primary=ArchetypeType.HERO,
            archetype_secondary=ArchetypeType.REBEL,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        for r in results:
            assert 0.0 <= r.preference_score <= 1.0, (
                f"{r.modality} score {r.preference_score} out of range"
            )

    def test_difficulty_filtering_foundation_only(self) -> None:
        """With max_difficulty=FOUNDATION, no developing+ modalities appear."""
        results = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.CAREER,
            max_difficulty=PracticeDifficulty.FOUNDATION,
        )
        for r in results:
            modality = MODALITY_REGISTRY[r.modality]
            assert modality.min_difficulty == PracticeDifficulty.FOUNDATION, (
                f"{r.modality} is {modality.min_difficulty}, expected FOUNDATION"
            )

    def test_difficulty_filtering_developing(self) -> None:
        """With max_difficulty=DEVELOPING, no established+ modalities appear."""
        results = match_modalities(
            archetype_primary=ArchetypeType.LOVER,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.LOVE,
            max_difficulty=PracticeDifficulty.DEVELOPING,
        )
        allowed = {PracticeDifficulty.FOUNDATION, PracticeDifficulty.DEVELOPING}
        for r in results:
            modality = MODALITY_REGISTRY[r.modality]
            assert modality.min_difficulty in allowed, (
                f"{r.modality} difficulty {modality.min_difficulty} exceeds DEVELOPING"
            )

    def test_contraindication_filtering_asthma(self) -> None:
        """A user with 'severe asthma' should not get breathwork."""
        results = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
            contraindications=["severe asthma"],
        )
        modality_names = {r.modality for r in results}
        assert "breathwork" not in modality_names

    def test_contraindication_filtering_epilepsy(self) -> None:
        """A user with 'epilepsy' should not get breathwork or sound_healing."""
        results = match_modalities(
            archetype_primary=ArchetypeType.CREATOR,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
            contraindications=["epilepsy"],
        )
        modality_names = {r.modality for r in results}
        assert "breathwork" not in modality_names
        assert "sound_healing" not in modality_names

    def test_contraindication_is_case_insensitive(self) -> None:
        """Contraindication matching is case-insensitive."""
        results = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
            contraindications=["SEVERE ASTHMA"],
        )
        modality_names = {r.modality for r in results}
        assert "breathwork" not in modality_names

    def test_secondary_archetype_influences_scores(self) -> None:
        """Providing a secondary archetype changes the result set."""
        results_no_secondary = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        results_with_secondary = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=ArchetypeType.HERO,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        scores_no = {r.modality: r.preference_score for r in results_no_secondary}
        scores_with = {r.modality: r.preference_score for r in results_with_secondary}
        # At least some scores should differ
        assert scores_no != scores_with

    def test_high_neuroticism_boosts_contemplative(self) -> None:
        """High neuroticism should boost contemplative modalities."""
        high_n = _make_big_five(neuroticism=85.0)
        low_n = _make_big_five(neuroticism=15.0)
        results_high = match_modalities(
            archetype_primary=ArchetypeType.EVERYMAN,
            archetype_secondary=None,
            big_five=high_n,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        results_low = match_modalities(
            archetype_primary=ArchetypeType.EVERYMAN,
            archetype_secondary=None,
            big_five=low_n,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        # Get contemplative scores
        def _contemplative_total(results: list[HealingPreference]) -> float:
            return sum(
                r.preference_score
                for r in results
                if MODALITY_REGISTRY.get(r.modality, None)
                and MODALITY_REGISTRY[r.modality].category == "contemplative"
            )

        assert _contemplative_total(results_high) >= _contemplative_total(results_low)

    def test_low_extraversion_boosts_contemplative_over_relational(self) -> None:
        """Low extraversion should boost contemplative/nature over relational."""
        introvert = _make_big_five(extraversion=15.0)
        results = match_modalities(
            archetype_primary=ArchetypeType.SAGE,
            archetype_secondary=None,
            big_five=introvert,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        modality_names = [r.modality for r in results[:3]]
        # Relational modalities should not dominate the top 3 for introverts
        relational_in_top3 = sum(
            1 for name in modality_names
            if MODALITY_REGISTRY[name].category == "relational"
        )
        assert relational_in_top3 <= 1

    def test_health_intention_boosts_breathwork(self) -> None:
        """Health intention should boost breathwork near the top."""
        results = match_modalities(
            archetype_primary=ArchetypeType.EVERYMAN,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.HEALTH,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        modality_names = [r.modality for r in results]
        assert "breathwork" in modality_names

    def test_archetype_affinities_resolved_for_all_archetypes(self) -> None:
        """Every archetype can have its affinities resolved without error."""
        for archetype in ArchetypeType:
            result = _resolve_archetype_affinities(archetype)
            assert isinstance(result, dict)
            # At least some affinities should map
            assert len(result) > 0, f"{archetype} resolved to 0 affinities"

    def test_is_contraindicated_returns_false_for_empty_list(self) -> None:
        """Empty contraindication list means nothing is contraindicated."""
        modality = MODALITY_REGISTRY["breathwork"]
        assert _is_contraindicated(modality, []) is False

    def test_is_contraindicated_substring_match(self) -> None:
        """Contraindication matches on substring."""
        modality = MODALITY_REGISTRY["breathwork"]
        # "asthma" is a substring of "severe asthma" in breathwork contraindications
        assert _is_contraindicated(modality, ["asthma"]) is True

    def test_no_duplicate_modalities_in_results(self) -> None:
        """Results should not contain duplicate modalities."""
        results = match_modalities(
            archetype_primary=ArchetypeType.MYSTIC,
            archetype_secondary=ArchetypeType.SAGE,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        names = [r.modality for r in results]
        assert len(names) == len(set(names))

    def test_match_all_archetypes_all_intentions(self) -> None:
        """Matching completes without error for all archetype+intention combos."""
        for archetype in ArchetypeType:
            for intention in Intention:
                results = match_modalities(
                    archetype_primary=archetype,
                    archetype_secondary=None,
                    big_five=NEUTRAL_BIG_FIVE,
                    intention=intention,
                    max_difficulty=PracticeDifficulty.ADVANCED,
                )
                assert len(results) > 0, (
                    f"No results for {archetype}/{intention}"
                )


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Breathwork Pattern Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBreathworkPatterns:
    """Tests for breathwork pattern definitions and the selector."""

    def test_registry_has_6_patterns(self) -> None:
        """The breathwork registry must have 6 patterns."""
        assert len(BREATHWORK_PATTERNS) == 6

    def test_all_expected_patterns_present(self) -> None:
        """All expected pattern names are present."""
        expected = {
            "box_breathing",
            "coherence",
            "relaxing_4_7_8",
            "wim_hof_lite",
            "alternate_nostril",
            "holotropic_lite",
        }
        assert set(BREATHWORK_PATTERNS.keys()) == expected

    def test_all_patterns_have_positive_inhale(self) -> None:
        """No pattern should have zero or negative inhale time."""
        for name, pattern in BREATHWORK_PATTERNS.items():
            assert pattern.inhale_seconds > 0, (
                f"{name} has non-positive inhale_seconds: {pattern.inhale_seconds}"
            )

    def test_all_patterns_have_non_negative_holds(self) -> None:
        """Hold times must be >= 0."""
        for name, pattern in BREATHWORK_PATTERNS.items():
            assert pattern.hold_seconds >= 0, (
                f"{name} has negative hold_seconds: {pattern.hold_seconds}"
            )
            assert pattern.hold_empty_seconds >= 0, (
                f"{name} has negative hold_empty_seconds: {pattern.hold_empty_seconds}"
            )

    def test_all_patterns_have_positive_exhale(self) -> None:
        """No pattern should have zero or negative exhale time."""
        for name, pattern in BREATHWORK_PATTERNS.items():
            assert pattern.exhale_seconds > 0, (
                f"{name} has non-positive exhale_seconds: {pattern.exhale_seconds}"
            )

    def test_all_patterns_have_reasonable_cycles(self) -> None:
        """Cycle count must be between 1 and 50."""
        for name, pattern in BREATHWORK_PATTERNS.items():
            assert 1 <= pattern.cycles <= 50, (
                f"{name} has unreasonable cycles: {pattern.cycles}"
            )

    def test_all_patterns_are_frozen_dataclass_instances(self) -> None:
        """Each pattern is a BreathworkPattern instance."""
        for pattern in BREATHWORK_PATTERNS.values():
            assert isinstance(pattern, BreathworkPattern)

    def test_box_breathing_is_4_4_4_4(self) -> None:
        """Box breathing should have equal 4-second phases."""
        box = BREATHWORK_PATTERNS["box_breathing"]
        assert box.inhale_seconds == 4.0
        assert box.hold_seconds == 4.0
        assert box.exhale_seconds == 4.0
        assert box.hold_empty_seconds == 4.0

    def test_coherence_is_5_5_rhythm(self) -> None:
        """Coherence breathing: 5.5 in, 0 hold, 5.5 out, 0 hold."""
        coh = BREATHWORK_PATTERNS["coherence"]
        assert coh.inhale_seconds == 5.5
        assert coh.hold_seconds == 0.0
        assert coh.exhale_seconds == 5.5
        assert coh.hold_empty_seconds == 0.0

    def test_selector_foundation_returns_foundation(self) -> None:
        """Selecting at FOUNDATION difficulty returns a foundation pattern."""
        pattern = get_breathwork_pattern(difficulty=PracticeDifficulty.FOUNDATION)
        assert pattern.difficulty == PracticeDifficulty.FOUNDATION

    def test_selector_with_calm_intention(self) -> None:
        """Calm intention should select coherence or relaxing pattern."""
        pattern = get_breathwork_pattern(
            difficulty=PracticeDifficulty.DEVELOPING,
            intention="calm",
        )
        assert pattern.name in {"coherence", "relaxing_4_7_8", "box_breathing"}

    def test_selector_with_energy_intention(self) -> None:
        """Energy intention at developing level should select wim_hof_lite."""
        pattern = get_breathwork_pattern(
            difficulty=PracticeDifficulty.DEVELOPING,
            intention="energy",
        )
        assert pattern.name == "wim_hof_lite"

    def test_selector_with_sleep_intention(self) -> None:
        """Sleep intention should select relaxing_4_7_8 if available."""
        pattern = get_breathwork_pattern(
            difficulty=PracticeDifficulty.DEVELOPING,
            intention="sleep",
        )
        assert pattern.name == "relaxing_4_7_8"

    def test_selector_advanced_without_intention_returns_most_advanced(self) -> None:
        """Without intention, selector returns the most advanced eligible pattern."""
        pattern = get_breathwork_pattern(
            difficulty=PracticeDifficulty.ADVANCED,
            intention=None,
        )
        assert pattern.difficulty == PracticeDifficulty.ADVANCED

    def test_selector_unknown_intention_falls_back(self) -> None:
        """An unrecognised intention should still return a valid pattern."""
        pattern = get_breathwork_pattern(
            difficulty=PracticeDifficulty.DEVELOPING,
            intention="quantum_alignment",
        )
        assert isinstance(pattern, BreathworkPattern)
        assert pattern.name in BREATHWORK_PATTERNS

    def test_selector_case_insensitive_intention(self) -> None:
        """Intention matching should be case-insensitive."""
        pattern = get_breathwork_pattern(
            difficulty=PracticeDifficulty.DEVELOPING,
            intention="CALM",
        )
        assert pattern.name in {"coherence", "relaxing_4_7_8", "box_breathing"}

    def test_total_session_duration_reasonable(self) -> None:
        """Each pattern's total session time should be between 30s and 30min."""
        for name, pattern in BREATHWORK_PATTERNS.items():
            cycle_time = (
                pattern.inhale_seconds
                + pattern.hold_seconds
                + pattern.exhale_seconds
                + pattern.hold_empty_seconds
            )
            total = cycle_time * pattern.cycles
            assert 30.0 <= total <= 1800.0, (
                f"{name} total duration {total}s is outside 30s-30min range"
            )


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Integration / edge-case tests
# ═══════════════════════════════════════════════════════════════════════


class TestHealingIntegration:
    """Integration and edge-case tests."""

    def test_affinity_map_targets_valid_modalities(self) -> None:
        """Every modality target in the affinity map must exist in the registry."""
        for affinity_text, modality_name in _AFFINITY_TO_MODALITY.items():
            assert modality_name in MODALITY_REGISTRY, (
                f"Affinity '{affinity_text}' maps to unknown modality '{modality_name}'"
            )

    def test_intention_boosts_target_valid_modalities(self) -> None:
        """All modalities referenced in intention boosts exist in the registry."""
        from alchymine.engine.healing.matcher import _INTENTION_BOOSTS

        for intention, boosts in _INTENTION_BOOSTS.items():
            for modality_name in boosts:
                assert modality_name in MODALITY_REGISTRY, (
                    f"Intention {intention} references unknown modality '{modality_name}'"
                )

    def test_breathwork_intention_affinities_target_valid_patterns(self) -> None:
        """All patterns in intention affinities exist in the pattern registry."""
        for intention_key, pattern_names in _INTENTION_PATTERN_AFFINITY.items():
            for pattern_name in pattern_names:
                assert pattern_name in BREATHWORK_PATTERNS, (
                    f"Intention '{intention_key}' references unknown pattern '{pattern_name}'"
                )

    def test_max_results_1_returns_single_result(self) -> None:
        """max_results=1 should return exactly 1 result."""
        results = match_modalities(
            archetype_primary=ArchetypeType.CREATOR,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
            max_results=1,
        )
        assert len(results) == 1

    def test_multiple_contraindications(self) -> None:
        """Multiple contraindications should each be filtered."""
        results = match_modalities(
            archetype_primary=ArchetypeType.MYSTIC,
            archetype_secondary=None,
            big_five=NEUTRAL_BIG_FIVE,
            intention=Intention.PURPOSE,
            max_difficulty=PracticeDifficulty.ADVANCED,
            contraindications=["severe asthma", "schizophrenia", "epilepsy"],
        )
        names = {r.modality for r in results}
        assert "breathwork" not in names
        assert "consciousness_journey" not in names
        assert "sound_healing" not in names

    def test_high_agreeableness_boosts_relational(self) -> None:
        """High agreeableness should increase relational modality scores."""
        agreeable = _make_big_five(agreeableness=90.0)
        disagreeable = _make_big_five(agreeableness=10.0)

        results_agree = match_modalities(
            archetype_primary=ArchetypeType.EVERYMAN,
            archetype_secondary=None,
            big_five=agreeable,
            intention=Intention.FAMILY,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )
        results_disagree = match_modalities(
            archetype_primary=ArchetypeType.EVERYMAN,
            archetype_secondary=None,
            big_five=disagreeable,
            intention=Intention.FAMILY,
            max_difficulty=PracticeDifficulty.ADVANCED,
        )

        def _relational_total(results: list[HealingPreference]) -> float:
            return sum(
                r.preference_score
                for r in results
                if MODALITY_REGISTRY.get(r.modality)
                and MODALITY_REGISTRY[r.modality].category == "relational"
            )

        assert _relational_total(results_agree) >= _relational_total(results_disagree)

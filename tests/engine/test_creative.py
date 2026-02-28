"""Tests for the Creative Forge Engine — assessment, style, projects, collaboration.

Minimum 30 tests covering:
- Guilford scoring with known inputs, edge cases (all zeros, all 100s, boundary)
- Creative DNA assessment
- Creative orientation mapping from Life Path
- Style fingerprint, strengths, growth areas, mediums
- Project suggestions and scope estimation
- Collaboration compatibility and complementary strengths
- Determinism (same inputs always produce same outputs)
"""

from __future__ import annotations

import pytest

from alchymine.engine.creative.assessment import (
    assess_creative_dna,
    assess_guilford,
    derive_creative_orientation,
)
from alchymine.engine.creative.collaboration import (
    compatibility_score,
    complementary_strengths,
)
from alchymine.engine.creative.projects import (
    estimate_project_scope,
    suggest_projects,
)
from alchymine.engine.creative.style import (
    generate_style_fingerprint,
    identify_growth_areas,
    identify_strengths,
    suggest_mediums,
)
from alchymine.engine.profile import CreativeDNA, GuilfordScores

# ═══════════════════════════════════════════════════════════════════════════
# Guilford Assessment Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAssessGuilford:
    """Tests for assess_guilford()."""

    def test_direct_component_scores(self) -> None:
        """Direct component-level scores produce correct GuilfordScores."""
        responses = {
            "fluency": 80,
            "flexibility": 60,
            "originality": 90,
            "elaboration": 50,
            "sensitivity": 70,
            "redefinition": 40,
        }
        result = assess_guilford(responses)
        assert result.fluency == 80.0
        assert result.flexibility == 60.0
        assert result.originality == 90.0
        assert result.elaboration == 50.0
        assert result.sensitivity == 70.0
        assert result.redefinition == 40.0

    def test_question_level_averaging(self) -> None:
        """Individual question scores are averaged per component."""
        responses = {
            "fluency_1": 60,
            "fluency_2": 80,
            "fluency_3": 70,
            "flexibility_1": 50,
            "flexibility_2": 50,
            "flexibility_3": 50,
            "originality_1": 100,
            "originality_2": 100,
            "originality_3": 100,
            "elaboration_1": 0,
            "elaboration_2": 0,
            "elaboration_3": 0,
            "sensitivity_1": 30,
            "sensitivity_2": 60,
            "sensitivity_3": 90,
            "redefinition_1": 45,
            "redefinition_2": 55,
            "redefinition_3": 50,
        }
        result = assess_guilford(responses)
        assert result.fluency == 70.0  # (60+80+70)/3
        assert result.flexibility == 50.0
        assert result.originality == 100.0
        assert result.elaboration == 0.0
        assert result.sensitivity == 60.0
        assert result.redefinition == 50.0

    def test_all_zeros(self) -> None:
        """All-zero responses produce all-zero scores."""
        responses = {
            "fluency": 0,
            "flexibility": 0,
            "originality": 0,
            "elaboration": 0,
            "sensitivity": 0,
            "redefinition": 0,
        }
        result = assess_guilford(responses)
        assert result.fluency == 0.0
        assert result.flexibility == 0.0
        assert result.originality == 0.0
        assert result.elaboration == 0.0
        assert result.sensitivity == 0.0
        assert result.redefinition == 0.0

    def test_all_100s(self) -> None:
        """All-100 responses produce all-100 scores."""
        responses = {
            "fluency": 100,
            "flexibility": 100,
            "originality": 100,
            "elaboration": 100,
            "sensitivity": 100,
            "redefinition": 100,
        }
        result = assess_guilford(responses)
        assert result.fluency == 100.0
        assert result.originality == 100.0

    def test_clamping_above_100(self) -> None:
        """Scores above 100 are clamped to 100."""
        responses = {
            "fluency": 150,
            "flexibility": 0,
            "originality": 0,
            "elaboration": 0,
            "sensitivity": 0,
            "redefinition": 0,
        }
        result = assess_guilford(responses)
        assert result.fluency == 100.0

    def test_clamping_below_0(self) -> None:
        """Scores below 0 are clamped to 0."""
        responses = {
            "fluency": -10,
            "flexibility": 0,
            "originality": 0,
            "elaboration": 0,
            "sensitivity": 0,
            "redefinition": 0,
        }
        result = assess_guilford(responses)
        assert result.fluency == 0.0

    def test_missing_responses_default_to_zero(self) -> None:
        """Missing question keys default to 0 for that component."""
        result = assess_guilford({})
        assert result.fluency == 0.0
        assert result.originality == 0.0

    def test_returns_guilford_scores_type(self) -> None:
        """assess_guilford always returns a GuilfordScores instance."""
        result = assess_guilford({"fluency": 50})
        assert isinstance(result, GuilfordScores)

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs produce identical outputs."""
        responses = {
            "fluency": 75,
            "flexibility": 50,
            "originality": 80,
            "elaboration": 60,
            "sensitivity": 40,
            "redefinition": 55,
        }
        r1 = assess_guilford(responses)
        r2 = assess_guilford(responses)
        assert r1 == r2


# ═══════════════════════════════════════════════════════════════════════════
# Creative DNA Assessment Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAssessCreativeDNA:
    """Tests for assess_creative_dna()."""

    def test_direct_dimension_scores(self) -> None:
        """Direct dimension values produce correct CreativeDNA."""
        responses = {
            "structure_vs_improvisation": 0.7,
            "collaboration_vs_solitude": 0.3,
            "convergent_vs_divergent": 0.8,
            "primary_sensory_mode": "musical",
            "creative_peak": "evening",
        }
        result = assess_creative_dna(responses)
        assert result.structure_vs_improvisation == 0.7
        assert result.collaboration_vs_solitude == 0.3
        assert result.convergent_vs_divergent == 0.8
        assert result.primary_sensory_mode == "musical"
        assert result.creative_peak == "evening"

    def test_question_level_averaging(self) -> None:
        """Individual question scores are averaged per dimension."""
        responses = {
            "dna_structure_1": 0.2,
            "dna_structure_2": 0.8,
            "dna_collab_1": 0.4,
            "dna_collab_2": 0.6,
            "dna_convergent_1": 0.1,
            "dna_convergent_2": 0.3,
        }
        result = assess_creative_dna(responses)
        assert result.structure_vs_improvisation == 0.5  # (0.2+0.8)/2
        assert result.collaboration_vs_solitude == 0.5
        assert result.convergent_vs_divergent == 0.2

    def test_defaults_for_empty_responses(self) -> None:
        """Empty responses produce neutral defaults."""
        result = assess_creative_dna({})
        assert result.structure_vs_improvisation == 0.5
        assert result.collaboration_vs_solitude == 0.5
        assert result.convergent_vs_divergent == 0.5
        assert result.primary_sensory_mode == "visual"
        assert result.creative_peak == "morning"

    def test_invalid_sensory_mode_defaults_to_visual(self) -> None:
        """Invalid sensory mode falls back to 'visual'."""
        result = assess_creative_dna({"primary_sensory_mode": "telekinetic"})
        assert result.primary_sensory_mode == "visual"

    def test_invalid_peak_defaults_to_morning(self) -> None:
        """Invalid creative peak falls back to 'morning'."""
        result = assess_creative_dna({"creative_peak": "midnight"})
        assert result.creative_peak == "morning"

    def test_clamping_above_1(self) -> None:
        """Dimension values above 1 are clamped to 1.0."""
        result = assess_creative_dna({"structure_vs_improvisation": 1.5})
        assert result.structure_vs_improvisation == 1.0

    def test_clamping_below_0(self) -> None:
        """Dimension values below 0 are clamped to 0.0."""
        result = assess_creative_dna({"structure_vs_improvisation": -0.3})
        assert result.structure_vs_improvisation == 0.0

    def test_returns_creative_dna_type(self) -> None:
        """assess_creative_dna always returns a CreativeDNA instance."""
        result = assess_creative_dna({})
        assert isinstance(result, CreativeDNA)


# ═══════════════════════════════════════════════════════════════════════════
# Creative Orientation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDeriveCreativeOrientation:
    """Tests for derive_creative_orientation()."""

    def test_life_path_1(self) -> None:
        assert derive_creative_orientation(1) == "Pioneer Creator"

    def test_life_path_3(self) -> None:
        assert derive_creative_orientation(3) == "Expressive Artist"

    def test_life_path_9(self) -> None:
        assert derive_creative_orientation(9) == "Universal Visionary"

    def test_master_number_11(self) -> None:
        assert derive_creative_orientation(11) == "Intuitive Innovator"

    def test_master_number_22(self) -> None:
        assert derive_creative_orientation(22) == "Master Builder"

    def test_master_number_33(self) -> None:
        assert derive_creative_orientation(33) == "Inspirational Teacher"

    def test_invalid_life_path_raises(self) -> None:
        """Invalid life path number raises ValueError."""
        with pytest.raises(ValueError, match="Invalid life_path"):
            derive_creative_orientation(0)

    def test_invalid_life_path_15_raises(self) -> None:
        """Non-standard number 15 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid life_path"):
            derive_creative_orientation(15)

    def test_all_valid_paths_return_strings(self) -> None:
        """All valid life paths (1-9, 11, 22, 33) return non-empty strings."""
        valid_paths = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]
        for lp in valid_paths:
            result = derive_creative_orientation(lp)
            assert isinstance(result, str)
            assert len(result) > 0


# ═══════════════════════════════════════════════════════════════════════════
# Style Analysis Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestStyleAnalysis:
    """Tests for style fingerprint, strengths, growth areas, mediums."""

    @pytest.fixture()
    def high_fluency_guilford(self) -> GuilfordScores:
        return GuilfordScores(
            fluency=90,
            flexibility=70,
            originality=80,
            elaboration=40,
            sensitivity=30,
            redefinition=20,
        )

    @pytest.fixture()
    def balanced_guilford(self) -> GuilfordScores:
        return GuilfordScores(
            fluency=50,
            flexibility=50,
            originality=50,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )

    @pytest.fixture()
    def visual_dna(self) -> CreativeDNA:
        return CreativeDNA(
            structure_vs_improvisation=0.3,
            collaboration_vs_solitude=0.4,
            convergent_vs_divergent=0.6,
            primary_sensory_mode="visual",
            creative_peak="morning",
        )

    def test_fingerprint_has_required_keys(
        self, high_fluency_guilford: GuilfordScores, visual_dna: CreativeDNA
    ) -> None:
        """Style fingerprint contains all required top-level keys."""
        fp = generate_style_fingerprint(high_fluency_guilford, visual_dna)
        assert "guilford_summary" in fp
        assert "dna_summary" in fp
        assert "dominant_components" in fp
        assert "creative_style" in fp
        assert "overall_score" in fp

    def test_fingerprint_dominant_components_ordered(
        self, high_fluency_guilford: GuilfordScores, visual_dna: CreativeDNA
    ) -> None:
        """Dominant components are ordered by score descending."""
        fp = generate_style_fingerprint(high_fluency_guilford, visual_dna)
        assert fp["dominant_components"][0] == "fluency"
        assert fp["dominant_components"][1] == "originality"
        assert fp["dominant_components"][2] == "flexibility"

    def test_fingerprint_overall_score(
        self, balanced_guilford: GuilfordScores, visual_dna: CreativeDNA
    ) -> None:
        """Overall score is the average of Guilford scores."""
        fp = generate_style_fingerprint(balanced_guilford, visual_dna)
        assert fp["overall_score"] == 50.0

    def test_strengths_returns_top_3(self, high_fluency_guilford: GuilfordScores) -> None:
        """identify_strengths returns up to 3 strengths."""
        strengths = identify_strengths(high_fluency_guilford)
        assert len(strengths) == 3
        assert "Idea Generation (Fluency)" in strengths[0]

    def test_growth_areas_returns_bottom_3(self, high_fluency_guilford: GuilfordScores) -> None:
        """identify_growth_areas returns up to 3 growth areas."""
        areas = identify_growth_areas(high_fluency_guilford)
        assert len(areas) == 3
        assert "Repurposing Ability (Redefinition)" in areas[0]

    def test_suggest_mediums_returns_nonempty(
        self, visual_dna: CreativeDNA, high_fluency_guilford: GuilfordScores
    ) -> None:
        """suggest_mediums returns at least one recommendation."""
        mediums = suggest_mediums(visual_dna, high_fluency_guilford)
        assert len(mediums) >= 1
        assert all(isinstance(m, str) for m in mediums)

    def test_suggest_mediums_no_duplicates(
        self, visual_dna: CreativeDNA, high_fluency_guilford: GuilfordScores
    ) -> None:
        """suggest_mediums returns no duplicates."""
        mediums = suggest_mediums(visual_dna, high_fluency_guilford)
        assert len(mediums) == len(set(mediums))

    def test_suggest_mediums_structured_preference(self) -> None:
        """Highly structured DNA includes structured medium recommendation."""
        dna = CreativeDNA(structure_vs_improvisation=0.1, primary_sensory_mode="visual")
        guilford = GuilfordScores(
            fluency=50,
            flexibility=50,
            originality=50,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )
        mediums = suggest_mediums(dna, guilford)
        assert any(
            "architectural" in m.lower() or "classical" in m.lower() or "technical" in m.lower()
            for m in mediums
        )


# ═══════════════════════════════════════════════════════════════════════════
# Project Suggestions Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectSuggestions:
    """Tests for suggest_projects() and estimate_project_scope()."""

    def test_suggest_projects_returns_list(self) -> None:
        """suggest_projects returns a non-empty list."""
        style = {"dominant_components": ["fluency", "originality", "flexibility"]}
        projects = suggest_projects(style, "beginner")
        assert isinstance(projects, list)
        assert len(projects) > 0

    def test_suggest_projects_each_has_required_keys(self) -> None:
        """Each project dict has title, description, type, medium, skill_level."""
        style = {"dominant_components": ["fluency"]}
        projects = suggest_projects(style, "beginner")
        for p in projects:
            assert "title" in p
            assert "description" in p
            assert "type" in p
            assert "medium" in p
            assert "skill_level" in p

    def test_suggest_projects_invalid_level_defaults_to_beginner(self) -> None:
        """Invalid skill level defaults to beginner."""
        style = {"dominant_components": ["fluency"]}
        projects = suggest_projects(style, "grand-master")
        assert all(p["skill_level"] == "beginner" for p in projects)

    def test_suggest_projects_empty_dominant_uses_default(self) -> None:
        """Empty dominant_components falls back to fluency."""
        style = {"dominant_components": []}
        projects = suggest_projects(style, "beginner")
        assert len(projects) > 0

    def test_estimate_scope_known_type(self) -> None:
        """Known project type returns expected scope keys."""
        scope = estimate_project_scope("writing")
        assert "hours_min" in scope
        assert "hours_max" in scope
        assert "sessions" in scope
        assert "difficulty" in scope
        assert "materials" in scope
        assert scope["hours_min"] > 0

    def test_estimate_scope_unknown_type_defaults(self) -> None:
        """Unknown project type returns default scope."""
        scope = estimate_project_scope("quantum_entanglement_art")
        assert scope["hours_min"] == 5
        assert scope["hours_max"] == 20

    def test_estimate_scope_deterministic(self) -> None:
        """Same project type always returns same scope."""
        s1 = estimate_project_scope("film")
        s2 = estimate_project_scope("film")
        assert s1 == s2


# ═══════════════════════════════════════════════════════════════════════════
# Collaboration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCollaboration:
    """Tests for compatibility_score() and complementary_strengths()."""

    @pytest.fixture()
    def dna_structured_collab(self) -> CreativeDNA:
        return CreativeDNA(
            structure_vs_improvisation=0.2,
            collaboration_vs_solitude=0.2,
            convergent_vs_divergent=0.3,
            primary_sensory_mode="visual",
            creative_peak="morning",
        )

    @pytest.fixture()
    def dna_improv_solitary(self) -> CreativeDNA:
        return CreativeDNA(
            structure_vs_improvisation=0.8,
            collaboration_vs_solitude=0.9,
            convergent_vs_divergent=0.8,
            primary_sensory_mode="musical",
            creative_peak="evening",
        )

    @pytest.fixture()
    def dna_complementary(self) -> CreativeDNA:
        """DNA that complements dna_structured_collab well."""
        return CreativeDNA(
            structure_vs_improvisation=0.2,
            collaboration_vs_solitude=0.2,
            convergent_vs_divergent=0.8,
            primary_sensory_mode="visual",
            creative_peak="morning",
        )

    def test_compatibility_score_range(
        self, dna_structured_collab: CreativeDNA, dna_improv_solitary: CreativeDNA
    ) -> None:
        """Compatibility score is between 0 and 1."""
        score = compatibility_score(dna_structured_collab, dna_improv_solitary)
        assert 0.0 <= score <= 1.0

    def test_self_compatibility(self, dna_structured_collab: CreativeDNA) -> None:
        """A person has positive compatibility with themselves."""
        score = compatibility_score(dna_structured_collab, dna_structured_collab)
        assert score > 0.0

    def test_complementary_pair_higher_than_mismatched(
        self,
        dna_structured_collab: CreativeDNA,
        dna_complementary: CreativeDNA,
        dna_improv_solitary: CreativeDNA,
    ) -> None:
        """Complementary pair scores higher than a mismatched pair."""
        good = compatibility_score(dna_structured_collab, dna_complementary)
        poor = compatibility_score(dna_structured_collab, dna_improv_solitary)
        assert good > poor

    def test_compatibility_deterministic(
        self, dna_structured_collab: CreativeDNA, dna_improv_solitary: CreativeDNA
    ) -> None:
        """Same inputs produce same compatibility score."""
        s1 = compatibility_score(dna_structured_collab, dna_improv_solitary)
        s2 = compatibility_score(dna_structured_collab, dna_improv_solitary)
        assert s1 == s2

    def test_complementary_strengths_has_required_keys(self) -> None:
        """complementary_strengths returns all required keys."""
        ga = GuilfordScores(
            fluency=90,
            flexibility=30,
            originality=80,
            elaboration=20,
            sensitivity=60,
            redefinition=40,
        )
        gb = GuilfordScores(
            fluency=30,
            flexibility=90,
            originality=20,
            elaboration=80,
            sensitivity=40,
            redefinition=60,
        )
        result = complementary_strengths(ga, gb)
        assert "person_a_leads" in result
        assert "person_b_leads" in result
        assert "shared_strengths" in result
        assert "shared_growth" in result
        assert "synergy_score" in result

    def test_complementary_strengths_correct_leads(self) -> None:
        """Person A leads where A is stronger, B leads where B is stronger."""
        ga = GuilfordScores(
            fluency=90,
            flexibility=30,
            originality=50,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )
        gb = GuilfordScores(
            fluency=30,
            flexibility=90,
            originality=50,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )
        result = complementary_strengths(ga, gb)
        assert "Idea Generation (Fluency)" in result["person_a_leads"]
        assert "Adaptive Thinking (Flexibility)" in result["person_b_leads"]

    def test_shared_strengths_both_high(self) -> None:
        """Components where both score >= 60 appear in shared_strengths."""
        ga = GuilfordScores(
            fluency=80,
            flexibility=80,
            originality=10,
            elaboration=10,
            sensitivity=10,
            redefinition=10,
        )
        gb = GuilfordScores(
            fluency=70,
            flexibility=90,
            originality=10,
            elaboration=10,
            sensitivity=10,
            redefinition=10,
        )
        result = complementary_strengths(ga, gb)
        assert "Idea Generation (Fluency)" in result["shared_strengths"]
        assert "Adaptive Thinking (Flexibility)" in result["shared_strengths"]

    def test_shared_growth_both_low(self) -> None:
        """Components where both score < 40 appear in shared_growth."""
        ga = GuilfordScores(
            fluency=10,
            flexibility=10,
            originality=80,
            elaboration=80,
            sensitivity=80,
            redefinition=80,
        )
        gb = GuilfordScores(
            fluency=20,
            flexibility=30,
            originality=90,
            elaboration=70,
            sensitivity=60,
            redefinition=90,
        )
        result = complementary_strengths(ga, gb)
        assert "Idea Generation (Fluency)" in result["shared_growth"]
        assert "Adaptive Thinking (Flexibility)" in result["shared_growth"]

    def test_synergy_score_range(self) -> None:
        """Synergy score is between 0 and 1."""
        ga = GuilfordScores(
            fluency=50,
            flexibility=50,
            originality=50,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )
        gb = GuilfordScores(
            fluency=50,
            flexibility=50,
            originality=50,
            elaboration=50,
            sensitivity=50,
            redefinition=50,
        )
        result = complementary_strengths(ga, gb)
        assert 0.0 <= result["synergy_score"] <= 1.0

    def test_high_synergy_when_complementary(self) -> None:
        """Complementary pair has higher synergy than identical low pair."""
        ga = GuilfordScores(
            fluency=90,
            flexibility=20,
            originality=90,
            elaboration=20,
            sensitivity=90,
            redefinition=20,
        )
        gb = GuilfordScores(
            fluency=20,
            flexibility=90,
            originality=20,
            elaboration=90,
            sensitivity=20,
            redefinition=90,
        )
        gc = GuilfordScores(
            fluency=30,
            flexibility=30,
            originality=30,
            elaboration=30,
            sensitivity=30,
            redefinition=30,
        )
        result_comp = complementary_strengths(ga, gb)
        result_low = complementary_strengths(gc, gc)
        assert result_comp["synergy_score"] > result_low["synergy_score"]

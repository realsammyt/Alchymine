"""Contract tests for the bundled alchymine-foundations pack.

A broken bundled pack is a shipping bug (section 3.3), so these run
against the real files rather than a fixture. The house-style checks are
here rather than in a linter because the pack is content, and content
drifts in review in a way code does not.
"""

from __future__ import annotations

import pytest

from alchymine.agents.quality.ethics_check import check_text
from alchymine.engine.practice import (
    ACCEPTED_CATEGORIES,
    VALID_PURPOSES,
    PracticeDefinition,
    build_practice_registry,
    get_bundled_packs_dir,
)

BUNDLED_PACK_ID = "alchymine-foundations"

# Vocabulary that reads as machine-written. The pack is user-facing copy.
AI_TELL_WORDS = (
    "delve",
    "leverage",
    "robust",
    "comprehensive",
    "seamless",
    "ensure",
    "foster",
    "utilize",
)

# Loss aversion has no place on the practice surface (decision 21).
SHAME_WORDS = ("streak", "don't break", "you're about to lose", "keep the chain")


@pytest.fixture(scope="module")
def bundled_practices() -> list[PracticeDefinition]:
    registry = build_practice_registry()
    return [p for _, p in registry.list_practices(pack_id=BUNDLED_PACK_ID)]


def _prose_fields(practice: PracticeDefinition) -> list[str]:
    """The text a reader actually sees, per section 2.5."""
    return [
        practice.summary,
        practice.description,
        practice.expected_shift,
        practice.scaffold_note,
        practice.self_check.failure_mode,
        practice.self_check.question,
        *practice.use_when,
        *practice.applications,
        *practice.daily_prompts,
        *practice.contraindications,
    ]


class TestBundledPackLoads:
    def test_pack_directory_exists(self) -> None:
        assert (get_bundled_packs_dir() / BUNDLED_PACK_ID / "pack.yaml").is_file()

    def test_exactly_ten_practices(self, bundled_practices: list[PracticeDefinition]) -> None:
        assert len(bundled_practices) == 10

    def test_covers_all_five_purposes(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        covered = {purpose for p in bundled_practices for purpose in p.purposes}
        assert covered == VALID_PURPOSES

    def test_two_practices_per_purpose(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        counts: dict[str, int] = {}
        for practice in bundled_practices:
            counts[practice.purposes[0]] = counts.get(practice.purposes[0], 0) + 1
        assert counts == dict.fromkeys(VALID_PURPOSES, 2)

    def test_one_root_and_one_child_per_purpose(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        roots = [p for p in bundled_practices if not p.builds_on]
        children = [p for p in bundled_practices if p.builds_on]
        assert len(roots) == 5
        assert len(children) == 5
        assert {p.purposes[0] for p in roots} == VALID_PURPOSES

    def test_manifest_carries_license_and_attribution(self) -> None:
        registry = build_practice_registry()
        manifest = registry.get_pack(BUNDLED_PACK_ID)
        assert manifest.license == "CC-BY-NC-SA-4.0"
        assert manifest.attribution == "Alchymine Contributors"
        assert manifest.bundled is True
        assert manifest.schema_version == "2.0"

    def test_progression_depth_reaches_a_second_level(self) -> None:
        registry = build_practice_registry()
        depths = {
            practice.slug: registry.progression_depth(BUNDLED_PACK_ID, practice.slug)
            for _, practice in registry.list_practices(pack_id=BUNDLED_PACK_ID)
        }
        assert max(depths.values()) == 1
        assert sorted(depths.values()) == [0] * 5 + [1] * 5


class TestBundledPackShape:
    def test_categories_are_accepted_and_varied(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        categories = {p.category for p in bundled_practices}
        assert categories <= ACCEPTED_CATEGORIES
        assert len(categories) >= 3

    def test_at_most_two_somatic_entries_and_each_names_contraindications(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        somatic = [p for p in bundled_practices if p.category == "somatic"]
        assert len(somatic) <= 2
        for practice in somatic:
            assert practice.contraindications, f"{practice.slug} needs contraindications"

    def test_both_featured_and_unfeatured_present(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        featured = {p.featured for p in bundled_practices}
        assert featured == {True, False}

    def test_every_practice_has_three_prompts_and_a_question(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        for practice in bundled_practices:
            assert len(practice.daily_prompts) == 3, practice.slug
            assert practice.self_check.question.endswith("?"), practice.slug

    def test_orders_are_unique(self, bundled_practices: list[PracticeDefinition]) -> None:
        orders = [p.order for p in bundled_practices]
        assert len(set(orders)) == len(orders)


class TestBundledPackProse:
    def test_prose_passes_the_ethics_gate(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        for practice in bundled_practices:
            result = check_text("\n".join(_prose_fields(practice)), context="general")
            fatal = [v for v in result.violations if v.severity in ("error", "critical")]
            assert not fatal, f"{practice.slug}: {fatal}"

    def test_no_em_dashes(self, bundled_practices: list[PracticeDefinition]) -> None:
        for practice in bundled_practices:
            for text in [practice.title, *_prose_fields(practice)]:
                assert "—" not in text, practice.slug
                assert "–" not in text, practice.slug

    @pytest.mark.parametrize("word", AI_TELL_WORDS)
    def test_no_ai_tell_vocabulary(
        self, bundled_practices: list[PracticeDefinition], word: str
    ) -> None:
        for practice in bundled_practices:
            joined = " ".join(_prose_fields(practice)).lower()
            assert word not in joined, f"{practice.slug} uses '{word}'"

    @pytest.mark.parametrize("phrase", SHAME_WORDS)
    def test_no_loss_aversion_language(
        self, bundled_practices: list[PracticeDefinition], phrase: str
    ) -> None:
        for practice in bundled_practices:
            joined = " ".join(_prose_fields(practice)).lower()
            assert phrase not in joined, f"{practice.slug} uses '{phrase}'"

    def test_self_checks_are_questions_not_verdicts(
        self, bundled_practices: list[PracticeDefinition]
    ) -> None:
        """A self-check asks. It never tells the user what is true about them."""
        for practice in bundled_practices:
            question = practice.self_check.question
            assert question.count("?") >= 1, practice.slug
            assert not question.lower().startswith("you are"), practice.slug

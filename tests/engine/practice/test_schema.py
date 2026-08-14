"""Schema-level tests for practice-pack v2.

The load-order rule in section 2.2 of the design doc is the one that
needs pinning hardest: a rejected category must fail with the screening
reason, not with a generic enumeration error, so a pack author reads why
Alchymine does not carry the practice.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from alchymine.engine.practice import (
    ACCEPTED_CATEGORIES,
    PURPOSE_TO_SYSTEM,
    REJECTED_CATEGORIES,
    VALID_PURPOSES,
    PackManifest,
    PracticeDefinition,
)

from .conftest import manifest_dict, practice_dict


class TestPurposes:
    """The five capacity dimensions and their pillar mapping."""

    def test_five_purposes(self) -> None:
        assert VALID_PURPOSES == {
            "self-knowledge",
            "steadiness",
            "stewardship",
            "expression",
            "reframing",
        }

    def test_every_purpose_maps_to_a_pillar(self) -> None:
        assert set(PURPOSE_TO_SYSTEM) == VALID_PURPOSES
        assert PURPOSE_TO_SYSTEM["steadiness"] == "healing"
        assert PURPOSE_TO_SYSTEM["stewardship"] == "wealth"

    def test_mapping_is_one_to_one_onto_the_five_pillars(self) -> None:
        assert sorted(PURPOSE_TO_SYSTEM.values()) == [
            "creative",
            "healing",
            "intelligence",
            "perspective",
            "wealth",
        ]

    def test_unknown_purpose_rejected(self) -> None:
        with pytest.raises(ValidationError, match="unknown purpose"):
            PracticeDefinition.model_validate(practice_dict(purposes=["transcendence"]))

    def test_duplicate_purposes_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            PracticeDefinition.model_validate(
                practice_dict(purposes=["steadiness", "steadiness"])
            )

    def test_more_than_three_purposes_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(
                practice_dict(
                    purposes=["steadiness", "expression", "reframing", "stewardship"]
                )
            )

    def test_zero_purposes_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(purposes=[]))


class TestCategory:
    """Section 2.2: rejected categories are checked before the accepted set."""

    def test_state_induction_fails_with_the_screening_reason(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PracticeDefinition.model_validate(practice_dict(category="state-induction"))

        message = str(exc.value)
        assert "screening questions" in message
        assert "Alchymine does not ship them" in message
        # Not the generic enum error: the author must read *why*.
        assert "must be one of" not in message.lower()

    @pytest.mark.parametrize("category", sorted(REJECTED_CATEGORIES))
    def test_every_rejected_category_names_its_reason(self, category: str) -> None:
        with pytest.raises(ValidationError) as exc:
            PracticeDefinition.model_validate(practice_dict(category=category))
        assert "screening" in str(exc.value).lower()

    def test_rejected_and_accepted_sets_are_disjoint(self) -> None:
        assert not (set(REJECTED_CATEGORIES) & ACCEPTED_CATEGORIES)

    @pytest.mark.parametrize("category", sorted(ACCEPTED_CATEGORIES))
    def test_accepted_categories_validate(self, category: str) -> None:
        practice = PracticeDefinition.model_validate(practice_dict(category=category))
        assert practice.category == category

    def test_unknown_category_fails_with_the_accepted_list(self) -> None:
        with pytest.raises(ValidationError, match="Must be one of"):
            PracticeDefinition.model_validate(practice_dict(category="interpretive-dance"))


class TestPracticeDefinition:
    """Section 2.4 constraints."""

    def test_frozen(self) -> None:
        practice = PracticeDefinition.model_validate(practice_dict())
        with pytest.raises(ValidationError):
            practice.title = "Renamed"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(difficulty="hard"))

    @pytest.mark.parametrize("slug", ["Alpha", "with space", "with_underscore", "bang!"])
    def test_bad_slug_rejected(self, slug: str) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(slug=slug))

    @pytest.mark.parametrize("prompts", [[], ["one"], ["one", "two"], ["a", "b", "c", "d"]])
    def test_daily_prompts_must_be_exactly_three(self, prompts: list[str]) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(daily_prompts=prompts))

    def test_self_check_question_must_end_with_a_question_mark(self) -> None:
        with pytest.raises(ValidationError, match=r"question"):
            PracticeDefinition.model_validate(
                practice_dict(
                    self_check={
                        "failure_mode": "It becomes a label.",
                        "question": "You are avoiding the real thing.",
                    }
                )
            )

    def test_self_check_question_ending_in_a_question_mark_is_accepted(self) -> None:
        practice = PracticeDefinition.model_validate(practice_dict())
        assert practice.self_check.question.endswith("?")

    @pytest.mark.parametrize("minutes", [0, -1, 121, 1000])
    def test_duration_bounds(self, minutes: int) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(duration_minutes=minutes))

    def test_duration_at_the_cap_is_allowed(self) -> None:
        practice = PracticeDefinition.model_validate(practice_dict(duration_minutes=120))
        assert practice.duration_minutes == 120

    def test_negative_order_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(order=-1))

    def test_use_when_and_applications_require_an_entry(self) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(use_when=[]))
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(applications=[]))

    def test_bad_evidence_rating_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PracticeDefinition.model_validate(practice_dict(evidence_rating="F"))


class TestPackManifest:
    """Section 2.3: manifest is a separate model so license metadata has a home."""

    def test_valid_manifest(self) -> None:
        manifest = PackManifest.model_validate(manifest_dict())
        assert manifest.license == "CC-BY-NC-SA-4.0"
        assert manifest.attribution == "Alchymine Contributors"
        assert manifest.bundled is False

    def test_frozen_and_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            PackManifest.model_validate(manifest_dict(price="free"))

    def test_wrong_schema_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PackManifest.model_validate(manifest_dict(schema_version="1.0"))

    def test_empty_license_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PackManifest.model_validate(manifest_dict(license=""))

    def test_empty_attribution_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PackManifest.model_validate(manifest_dict(attribution=""))

    @pytest.mark.parametrize("pack_id", ["Bad-Pack", "with space", "under_score"])
    def test_bad_pack_id_rejected(self, pack_id: str) -> None:
        with pytest.raises(ValidationError):
            PackManifest.model_validate(manifest_dict(pack_id=pack_id))

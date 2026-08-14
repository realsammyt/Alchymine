"""Loader and registry tests.

These pin the failure policy from section 3.3: every one of these
conditions has to stop the process rather than quietly ship a smaller
product. The assertions check the *message*, not just the exception
type, because the message is what an operator reads at 2am.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alchymine.engine.practice import (
    PackNotFoundError,
    PracticeNotFoundError,
    PracticePackValidationError,
    build_practice_registry,
)

from .conftest import practice_dict, write_pack


class TestGraphValidation:
    """Section 2.6: the builds_on graph is validated per pack."""

    def test_cycle_fails_naming_the_members(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "cyclic-pack",
            [
                practice_dict("alpha", builds_on=["gamma"]),
                practice_dict("beta", builds_on=["alpha"]),
                practice_dict("gamma", builds_on=["beta"]),
            ],
        )

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])

        message = str(exc.value)
        assert "cycle" in message.lower()
        assert "cyclic-pack" in message
        for slug in ("alpha", "beta", "gamma"):
            assert slug in message

    def test_self_edge_is_a_cycle(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "self-pack",
            [practice_dict("alpha", builds_on=["alpha"])],
        )
        with pytest.raises(PracticePackValidationError, match="cycle"):
            build_practice_registry([container])

    def test_unresolved_builds_on_names_file_practice_and_slug(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "dangling-pack",
            [practice_dict("alpha", builds_on=["nowhere"])],
        )

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])

        message = str(exc.value)
        assert "dangling-pack" in message
        assert "alpha" in message
        assert "alpha.yaml" in message
        assert "nowhere" in message
        assert "builds_on" in message

    def test_unresolved_related_is_the_same_error_class(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "dangling-related",
            [practice_dict("alpha", related=["nowhere"])],
        )
        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])
        assert "related" in str(exc.value)
        assert "nowhere" in str(exc.value)

    def test_cross_pack_edge_is_unresolved(self, tmp_path: Path) -> None:
        """Edges reference slugs within the same pack only (decision 5)."""
        container = tmp_path / "ext"
        write_pack(container, "pack-one", [practice_dict("alpha")])
        write_pack(container, "pack-two", [practice_dict("beta", builds_on=["alpha"])])

        with pytest.raises(PracticePackValidationError, match="alpha"):
            build_practice_registry([container])

    def test_progression_depth_computed_at_load(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "depth-pack",
            [
                practice_dict("root"),
                practice_dict("middle", builds_on=["root"]),
                practice_dict("leaf", builds_on=["middle"]),
            ],
        )

        registry = build_practice_registry([container])

        assert registry.progression_depth("depth-pack", "root") == 0
        assert registry.progression_depth("depth-pack", "middle") == 1
        assert registry.progression_depth("depth-pack", "leaf") == 2

    def test_progression_depth_is_the_longest_path(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "diamond-pack",
            [
                practice_dict("root"),
                practice_dict("short", builds_on=["root"]),
                practice_dict("long", builds_on=["short"]),
                practice_dict("join", builds_on=["root", "long"]),
            ],
        )

        registry = build_practice_registry([container])

        assert registry.progression_depth("diamond-pack", "join") == 3


class TestCategoryScreening:
    def test_rejected_category_fails_the_load_with_the_reason(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "risky-pack",
            [practice_dict("alpha", category="state-induction")],
        )

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])

        message = str(exc.value)
        assert "screening questions" in message
        assert "alpha.yaml" in message


class TestLicensing:
    """Section 3.3: an unlicensed external pack stops the process."""

    def test_empty_license_fails(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "unlicensed", license="")
        with pytest.raises(PracticePackValidationError, match="license"):
            build_practice_registry([container])

    def test_whitespace_only_license_fails(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "unlicensed", license="   ")
        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])
        assert "license" in str(exc.value)
        assert "unlicensed" in str(exc.value)

    def test_whitespace_only_attribution_fails(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "unattributed", attribution=" ")
        with pytest.raises(PracticePackValidationError, match="attribution"):
            build_practice_registry([container])

    def test_external_pack_may_not_declare_itself_bundled(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "pretender", bundled=True)
        with pytest.raises(PracticePackValidationError, match="bundled"):
            build_practice_registry([container])


class TestDirectoryPolicy:
    """Section 3.3: configuring a directory asserts its content is required."""

    def test_missing_dir_fails(self, tmp_path: Path) -> None:
        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([tmp_path / "not-there"])
        assert "not-there" in str(exc.value)

    def test_dir_that_is_a_file_fails(self, tmp_path: Path) -> None:
        target = tmp_path / "a-file"
        target.write_text("not a directory", encoding="utf-8")
        with pytest.raises(PracticePackValidationError):
            build_practice_registry([target])

    def test_empty_dir_fails(self, tmp_path: Path) -> None:
        """The wrong-volume-mount case, the most likely production mistake."""
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([empty])

        message = str(exc.value)
        assert "pack.yaml" in message
        assert "empty" in message

    def test_dir_with_subdirs_but_no_manifest_fails(self, tmp_path: Path) -> None:
        container = tmp_path / "ext"
        (container / "looks-like-a-pack").mkdir(parents=True)
        with pytest.raises(PracticePackValidationError, match="pack.yaml"):
            build_practice_registry([container])

    def test_manifest_at_the_top_level_is_named_as_the_mistake(self, tmp_path: Path) -> None:
        """A pack dir mounted where a container of pack dirs was expected."""
        container = tmp_path / "ext"
        container.mkdir()
        (container / "pack.yaml").write_text("pack_id: oops\n", encoding="utf-8")

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])

        assert "parent" in str(exc.value).lower()

    def test_duplicate_pack_id_across_two_dirs_fails(self, tmp_path: Path) -> None:
        first = write_pack(tmp_path / "one", "shared-id")
        second = write_pack(tmp_path / "two", "shared-id")

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([first, second])

        message = str(exc.value)
        assert "shared-id" in message
        assert "duplicate" in message.lower()

    def test_pack_id_must_match_its_directory_name(self, tmp_path: Path) -> None:
        container = tmp_path / "ext"
        write_pack(container, "declared-id")
        (container / "declared-id").rename(container / "different-name")

        with pytest.raises(PracticePackValidationError, match="directory"):
            build_practice_registry([container])


class TestNamespacing:
    """Slugs are namespaced by pack, so collisions across packs are normal."""

    def test_same_slug_in_two_packs_is_fine(self, tmp_path: Path) -> None:
        container = tmp_path / "ext"
        write_pack(container, "pack-one", [practice_dict("shared-slug")])
        write_pack(container, "pack-two", [practice_dict("shared-slug")])

        registry = build_practice_registry([container])

        assert registry.get("pack-one", "shared-slug").slug == "shared-slug"
        assert registry.get("pack-two", "shared-slug").slug == "shared-slug"
        assert len(registry.list_practices(pack_id="pack-one")) == 1
        assert len(registry.list_practices(pack_id="pack-two")) == 1

    def test_duplicate_slug_within_one_pack_fails(self, tmp_path: Path) -> None:
        container = tmp_path / "ext"
        pack_dir = container / "dupe-pack"
        write_pack(container, "dupe-pack", [practice_dict("alpha")])
        # Second file, same slug inside.
        import yaml

        (pack_dir / "another.yaml").write_text(
            yaml.safe_dump(practice_dict("alpha"), sort_keys=False), encoding="utf-8"
        )

        with pytest.raises(PracticePackValidationError, match="duplicate"):
            build_practice_registry([container])


class TestProseGate:
    """Section 2.5: pack prose passes the same ethics gate as generated text."""

    def test_diagnostic_phrase_fails_the_load(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "clinical-pack",
            [
                practice_dict(
                    "alpha",
                    description=(
                        "This practice helps you work out whether you have a disorder "
                        "and what the diagnosis means for you."
                    ),
                )
            ],
        )

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])

        message = str(exc.value)
        assert "alpha.yaml" in message
        assert "diagnostic" in message.lower()

    def test_dark_pattern_in_a_prompt_fails_the_load(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "pushy-pack",
            [
                practice_dict(
                    "alpha",
                    daily_prompts=[
                        "Act now before the day gets away from you.",
                        "What are you noticing right now?",
                        "What did you notice today?",
                    ],
                )
            ],
        )

        with pytest.raises(PracticePackValidationError) as exc:
            build_practice_registry([container])
        assert "dark_pattern" in str(exc.value).lower()

    def test_warning_severity_does_not_fail_the_load(self, tmp_path: Path) -> None:
        """Only ERROR and above are fatal, per section 2.5."""
        container = write_pack(
            tmp_path / "ext",
            "mild-pack",
            [practice_dict("alpha", summary="Some people call this a guru move.")],
        )

        registry = build_practice_registry([container])

        assert registry.get("mild-pack", "alpha").slug == "alpha"


class TestRegistryLookup:
    def test_unknown_practice_raises_practice_not_found(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "lookup-pack")
        registry = build_practice_registry([container])

        with pytest.raises(PracticeNotFoundError):
            registry.get("lookup-pack", "nope")

    def test_unknown_pack_raises_pack_not_found(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "lookup-pack")
        registry = build_practice_registry([container])

        with pytest.raises(PackNotFoundError):
            registry.get("no-such-pack", "alpha")

    def test_external_packs_load_alongside_the_bundled_one(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "extra-pack")
        registry = build_practice_registry([container])

        pack_ids = {manifest.pack_id for manifest in registry.list_packs()}
        assert "alchymine-foundations" in pack_ids
        assert "extra-pack" in pack_ids

    def test_no_external_dirs_loads_the_bundled_pack_only(self) -> None:
        registry = build_practice_registry()
        assert [m.pack_id for m in registry.list_packs()] == ["alchymine-foundations"]

    def test_filters(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "filter-pack",
            [
                practice_dict("alpha", purposes=["steadiness"], category="attention"),
                practice_dict("beta", purposes=["expression"], category="relational"),
            ],
        )
        registry = build_practice_registry([container])

        by_pack = registry.list_practices(pack_id="filter-pack")
        assert {p.slug for _, p in by_pack} == {"alpha", "beta"}

        by_purpose = registry.list_practices(pack_id="filter-pack", purpose="steadiness")
        assert {p.slug for _, p in by_purpose} == {"alpha"}

        by_category = registry.list_practices(pack_id="filter-pack", category="relational")
        assert {p.slug for _, p in by_category} == {"beta"}

    def test_listing_is_deterministic(self, tmp_path: Path) -> None:
        container = write_pack(
            tmp_path / "ext",
            "order-pack",
            [
                practice_dict("gamma", order=3),
                practice_dict("alpha", order=1),
                practice_dict("beta", order=2),
            ],
        )
        registry = build_practice_registry([container])

        slugs = [p.slug for _, p in registry.list_practices(pack_id="order-pack")]
        assert slugs == ["alpha", "beta", "gamma"]


class TestMalformedYaml:
    def test_invalid_yaml_names_the_file(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "broken-pack")
        (container / "broken-pack" / "bad.yaml").write_text("key: [unclosed", encoding="utf-8")

        with pytest.raises(PracticePackValidationError, match="bad.yaml"):
            build_practice_registry([container])

    def test_non_mapping_yaml_names_the_file(self, tmp_path: Path) -> None:
        container = write_pack(tmp_path / "ext", "listy-pack")
        (container / "listy-pack" / "listy.yaml").write_text("- one\n- two\n", encoding="utf-8")

        with pytest.raises(PracticePackValidationError, match="listy.yaml"):
            build_practice_registry([container])

    def test_pack_with_no_practices_fails(self, tmp_path: Path) -> None:
        container = tmp_path / "ext"
        write_pack(container, "hollow-pack", practices=[])

        with pytest.raises(PracticePackValidationError, match="no practice"):
            build_practice_registry([container])

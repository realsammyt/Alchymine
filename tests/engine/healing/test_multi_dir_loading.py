"""Tests for SkillRegistry multi-directory loading (Task 6.2).

Covers:
- Loading from a single directory (backward compat)
- Loading from multiple directories with replace=False
- Duplicate detection across directories
- Empty external directory handling
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from alchymine.engine.healing.skills import (
    SkillNotFoundError,
    SkillRegistry,
    SkillValidationError,
)


def _write_yaml(directory: Path, filename: str, content: str) -> Path:
    file_path = directory / filename
    file_path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return file_path


@pytest.fixture
def bundled_dir(tmp_path: Path) -> Path:
    d = tmp_path / "bundled"
    d.mkdir()
    _write_yaml(
        d,
        "breath.yaml",
        """
        name: bundled-breathwork
        modality: breathwork
        title: Bundled Breathwork
        description: A bundled breathwork skill.
        steps:
          - Inhale
          - Exhale
        evidence_rating: A
        contraindications: []
        duration_minutes: 5
        """,
    )
    _write_yaml(
        d,
        "somatic.yaml",
        """
        name: bundled-somatic
        modality: somatic_practice
        title: Bundled Somatic
        description: A bundled somatic skill.
        steps:
          - Move gently
        evidence_rating: B
        contraindications: []
        duration_minutes: 10
        """,
    )
    return d


@pytest.fixture
def external_dir(tmp_path: Path) -> Path:
    d = tmp_path / "external"
    d.mkdir()
    _write_yaml(
        d,
        "nature.yaml",
        """
        name: external-nature
        modality: nature_healing
        title: External Nature Walk
        description: An externally defined nature healing skill.
        steps:
          - Go outside
          - Walk slowly
        evidence_rating: B
        contraindications: []
        duration_minutes: 30
        """,
    )
    return d


class TestMultiDirectoryLoading:
    """Test that SkillRegistry supports loading from multiple directories."""

    def test_load_single_directory_still_works(self, bundled_dir: Path) -> None:
        """Backward compatibility: load_directory with default replace=True."""
        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        assert len(reg) == 2
        assert reg.get("bundled-breathwork").modality == "breathwork"

    def test_load_second_directory_with_replace_false(
        self, bundled_dir: Path, external_dir: Path
    ) -> None:
        """Loading a second directory with replace=False merges skills."""
        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        assert len(reg) == 2

        reg.load_directory(external_dir, replace=False)
        assert len(reg) == 3
        # All skills accessible
        assert reg.get("bundled-breathwork").modality == "breathwork"
        assert reg.get("bundled-somatic").modality == "somatic_practice"
        assert reg.get("external-nature").modality == "nature_healing"

    def test_load_second_directory_with_replace_true_clears(
        self, bundled_dir: Path, external_dir: Path
    ) -> None:
        """Loading a second directory with replace=True replaces all skills."""
        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        assert len(reg) == 2

        reg.load_directory(external_dir, replace=True)
        assert len(reg) == 1
        assert reg.get("external-nature").modality == "nature_healing"
        with pytest.raises(SkillNotFoundError):
            reg.get("bundled-breathwork")

    def test_cross_directory_duplicate_raises(
        self, bundled_dir: Path, tmp_path: Path
    ) -> None:
        """Duplicate skill name across directories raises SkillValidationError."""
        dup_dir = tmp_path / "dup"
        dup_dir.mkdir()
        _write_yaml(
            dup_dir,
            "conflict.yaml",
            """
            name: bundled-breathwork
            modality: nature_healing
            title: Conflicting Name
            description: Same name as bundled skill.
            steps:
              - Conflict
            evidence_rating: C
            contraindications: []
            duration_minutes: 5
            """,
        )

        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        with pytest.raises(SkillValidationError, match="Duplicate"):
            reg.load_directory(dup_dir, replace=False)

    def test_empty_external_directory_is_fine(
        self, bundled_dir: Path, tmp_path: Path
    ) -> None:
        """Loading an empty external directory adds nothing."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        reg.load_directory(empty_dir, replace=False)
        # Original skills untouched
        assert len(reg) == 2

    def test_missing_external_directory_raises(self, bundled_dir: Path) -> None:
        """A non-existent external path raises FileNotFoundError."""
        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        with pytest.raises(FileNotFoundError):
            reg.load_directory(Path("/nonexistent/path"), replace=False)

    def test_list_by_modality_spans_both_dirs(
        self, bundled_dir: Path, external_dir: Path
    ) -> None:
        """list_by_modality works across merged directories."""
        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        reg.load_directory(external_dir, replace=False)

        breath = reg.list_by_modality("breathwork")
        nature = reg.list_by_modality("nature_healing")
        assert len(breath) == 1
        assert len(nature) == 1
        assert breath[0].name == "bundled-breathwork"
        assert nature[0].name == "external-nature"

    def test_list_all_spans_both_dirs(
        self, bundled_dir: Path, external_dir: Path
    ) -> None:
        """list_all returns all skills from all loaded directories."""
        reg = SkillRegistry()
        reg.load_directory(bundled_dir)
        reg.load_directory(external_dir, replace=False)
        all_skills = reg.list_all()
        names = {s.name for s in all_skills}
        assert names == {"bundled-breathwork", "bundled-somatic", "external-nature"}

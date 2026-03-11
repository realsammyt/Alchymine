"""Tests for the HealingSkill schema and SkillRegistry loader.

Covers:
- HealingSkill Pydantic model validation
- SkillRegistry.load_from_dir() loading YAML files from a directory
- SkillRegistry.get() retrieval by ID
- SkillRegistry.by_modality() filtering
- SkillRegistry.all() listing
- Module-level registry loads all 15 seed files
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────

MINIMAL_YAML = """\
id: bw_001
modality: breathwork
title: Box Breathing Baseline
duration_minutes: 5
difficulty: foundation
instructions:
  - Inhale for 4 counts
"""

FULL_YAML = """\
id: bw_002
modality: breathwork
title: Coherence Breathing
duration_minutes: 10
difficulty: foundation
instructions:
  - Inhale for 5 counts
  - Exhale for 5 counts
  - Repeat for 10 cycles
contraindications:
  - panic disorder
traditions:
  - HeartMath
evidence_level: strong
tags:
  - calm
  - focus
"""


# ─── HealingSkill schema ──────────────────────────────────────────────────────


class TestHealingSkillSchema:
    def test_minimal_yaml_validates(self) -> None:
        from alchymine.engine.healing.skills.schema import HealingSkill

        import yaml

        data = yaml.safe_load(MINIMAL_YAML)
        skill = HealingSkill.model_validate(data)
        assert skill.id == "bw_001"
        assert skill.modality == "breathwork"
        assert skill.title == "Box Breathing Baseline"
        assert skill.duration_minutes == 5
        assert skill.difficulty == "foundation"
        assert skill.instructions == ["Inhale for 4 counts"]
        # Optional fields default correctly
        assert skill.contraindications == []
        assert skill.traditions == []
        assert skill.evidence_level == "traditional"
        assert skill.tags == []

    def test_full_yaml_validates(self) -> None:
        from alchymine.engine.healing.skills.schema import HealingSkill

        import yaml

        data = yaml.safe_load(FULL_YAML)
        skill = HealingSkill.model_validate(data)
        assert skill.id == "bw_002"
        assert skill.contraindications == ["panic disorder"]
        assert skill.traditions == ["HeartMath"]
        assert skill.evidence_level == "strong"
        assert "calm" in skill.tags

    def test_missing_required_field_raises(self) -> None:
        from pydantic import ValidationError

        from alchymine.engine.healing.skills.schema import HealingSkill

        with pytest.raises(ValidationError):
            HealingSkill.model_validate({"id": "x", "modality": "breathwork"})


# ─── SkillRegistry ────────────────────────────────────────────────────────────


class TestSkillRegistry:
    def test_load_from_dir_single_file(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        (yaml_dir / "bw_001.yaml").write_text(MINIMAL_YAML, encoding="utf-8")

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        count = reg.load_from_dir(yaml_dir)
        assert count == 1

    def test_get_returns_skill(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        (yaml_dir / "bw_001.yaml").write_text(MINIMAL_YAML, encoding="utf-8")

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        reg.load_from_dir(yaml_dir)
        skill = reg.get("bw_001")
        assert skill is not None
        assert skill.modality == "breathwork"

    def test_get_returns_none_for_missing_id(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        reg.load_from_dir(yaml_dir)
        assert reg.get("nonexistent") is None

    def test_by_modality_filter(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()

        (yaml_dir / "bw_001.yaml").write_text(MINIMAL_YAML, encoding="utf-8")
        (yaml_dir / "med_001.yaml").write_text(
            "id: med_001\nmodality: coherence_meditation\ntitle: Heart Coherence\n"
            "duration_minutes: 10\ndifficulty: foundation\ninstructions:\n  - Focus on heart\n",
            encoding="utf-8",
        )

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        reg.load_from_dir(yaml_dir)

        breathwork = reg.by_modality("breathwork")
        assert len(breathwork) == 1
        assert breathwork[0].id == "bw_001"

        meditation = reg.by_modality("coherence_meditation")
        assert len(meditation) == 1
        assert meditation[0].id == "med_001"

    def test_by_modality_empty_result(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        (yaml_dir / "bw_001.yaml").write_text(MINIMAL_YAML, encoding="utf-8")

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        reg.load_from_dir(yaml_dir)
        assert reg.by_modality("nonexistent_modality") == []

    def test_all_returns_all_loaded_skills(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()
        (yaml_dir / "bw_001.yaml").write_text(MINIMAL_YAML, encoding="utf-8")
        (yaml_dir / "bw_002.yaml").write_text(FULL_YAML, encoding="utf-8")

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        reg.load_from_dir(yaml_dir)
        skills = reg.all()
        assert len(skills) == 2

    def test_load_empty_dir_returns_zero(self, tmp_path: Path) -> None:
        yaml_dir = tmp_path / "yaml"
        yaml_dir.mkdir()

        from alchymine.engine.healing.skills.loader import SkillRegistry

        reg = SkillRegistry()
        count = reg.load_from_dir(yaml_dir)
        assert count == 0


# ─── Seed files (Task 1.2) ────────────────────────────────────────────────────


class TestSeedRegistry:
    def test_module_level_registry_has_15_seeds(self) -> None:
        from alchymine.engine.healing.skills.loader import registry

        registry.load_from_dir()
        assert len(registry.all()) >= 15

    def test_all_15_modalities_represented(self) -> None:
        from alchymine.engine.healing.skills.loader import registry
        from alchymine.engine.healing.modalities import MODALITY_REGISTRY

        registry.load_from_dir()
        loaded_modalities = {s.modality for s in registry.all()}
        for modality_name in MODALITY_REGISTRY:
            assert modality_name in loaded_modalities, (
                f"No seed skill found for modality '{modality_name}'"
            )

    def test_no_duplicate_ids(self) -> None:
        from alchymine.engine.healing.skills.loader import registry

        registry.load_from_dir()
        ids = [s.id for s in registry.all()]
        assert len(ids) == len(set(ids)), "Duplicate skill IDs found"

    def test_all_skills_have_instructions(self) -> None:
        from alchymine.engine.healing.skills.loader import registry

        registry.load_from_dir()
        for skill in registry.all():
            assert len(skill.instructions) >= 1, (
                f"Skill '{skill.id}' has no instructions"
            )

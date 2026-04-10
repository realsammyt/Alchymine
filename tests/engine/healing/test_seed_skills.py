"""Smoke tests for the bundled healing skill YAML files.

These tests load the real directory at
``alchymine/engine/healing/skills/yaml/`` and verify that all 15 seed
skills parse cleanly and that each modality is represented exactly once.
"""

from __future__ import annotations

from collections import Counter

from alchymine.engine.healing.modalities import MODALITY_REGISTRY
from alchymine.engine.healing.skills import SkillRegistry, get_default_yaml_dir


def test_seed_directory_loads_all_files() -> None:
    reg = SkillRegistry()
    reg.load_directory(get_default_yaml_dir())
    assert len(reg) == 15


def test_each_modality_has_exactly_one_seed_skill() -> None:
    reg = SkillRegistry()
    reg.load_directory(get_default_yaml_dir())

    counts = Counter(skill.modality for skill in reg.list_all())
    expected = set(MODALITY_REGISTRY.keys())

    assert set(counts.keys()) == expected, (
        f"missing modalities: {expected - set(counts.keys())}; "
        f"extra modalities: {set(counts.keys()) - expected}"
    )
    duplicates = {m: c for m, c in counts.items() if c != 1}
    assert not duplicates, f"modalities with !=1 seed skill: {duplicates}"


def test_seed_skills_have_meaningful_content() -> None:
    reg = SkillRegistry()
    reg.load_directory(get_default_yaml_dir())

    for skill in reg.list_all():
        assert skill.duration_minutes > 0
        assert len(skill.steps) >= 3, f"{skill.name}: needs at least 3 steps"
        assert len(skill.description) >= 40, f"{skill.name}: description too short"

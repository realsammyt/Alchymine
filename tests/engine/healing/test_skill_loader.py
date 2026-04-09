"""Tests for the healing SkillRegistry loader and SkillDefinition schema."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pydantic import ValidationError

from alchymine.engine.healing.skills import (
    SkillDefinition,
    SkillNotFoundError,
    SkillRegistry,
    SkillValidationError,
)

# ── Schema validation ──────────────────────────────────────────────────


def _valid_payload(**overrides: object) -> dict:
    base: dict = {
        "name": "box-breath-foundation",
        "modality": "breathwork",
        "title": "Box Breathing Foundation",
        "description": "A baseline 4-4-4-4 breathing protocol.",
        "steps": [
            "Sit comfortably and close your eyes.",
            "Inhale through the nose for 4 counts.",
            "Hold for 4 counts.",
            "Exhale through the mouth for 4 counts.",
        ],
        "evidence_rating": "B",
        "contraindications": ["severe asthma"],
        "duration_minutes": 5,
    }
    base.update(overrides)
    return base


def test_valid_skill_parses() -> None:
    skill = SkillDefinition.model_validate(_valid_payload())
    assert skill.name == "box-breath-foundation"
    assert skill.modality == "breathwork"
    assert skill.duration_minutes == 5


def test_skill_is_frozen() -> None:
    skill = SkillDefinition.model_validate(_valid_payload())
    with pytest.raises(ValidationError):
        skill.name = "different-name"  # type: ignore[misc]


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(unexpected_field="oops"))


@pytest.mark.parametrize(
    "missing",
    [
        "name",
        "modality",
        "title",
        "description",
        "steps",
        "evidence_rating",
        "duration_minutes",
    ],
)
def test_missing_required_field_raises(missing: str) -> None:
    payload = _valid_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(payload)


def test_unknown_modality_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(modality="not-a-real-modality"))


def test_invalid_evidence_rating_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(evidence_rating="Z"))


def test_zero_duration_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(duration_minutes=0))


def test_empty_steps_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(steps=[]))


def test_blank_step_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(steps=["good step", "   "]))


def test_uppercase_name_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(name="BoxBreath"))


def test_underscore_name_rejected() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(name="box_breath"))


def test_steps_must_be_list_of_strings() -> None:
    with pytest.raises(ValidationError):
        SkillDefinition.model_validate(_valid_payload(steps="just one string"))


# ── Registry / loader ──────────────────────────────────────────────────


def _write_yaml(directory: Path, filename: str, content: str) -> Path:
    file_path = directory / filename
    file_path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return file_path


@pytest.fixture
def fake_skills_dir(tmp_path: Path) -> Path:
    yaml_dir = tmp_path / "yaml"
    yaml_dir.mkdir()
    _write_yaml(
        yaml_dir,
        "alpha.yaml",
        """
        name: alpha-skill
        modality: breathwork
        title: Alpha Skill
        description: First skill.
        steps:
          - Step one
          - Step two
        evidence_rating: A
        contraindications: []
        duration_minutes: 10
        """,
    )
    _write_yaml(
        yaml_dir,
        "beta.yaml",
        """
        name: beta-skill
        modality: somatic_practice
        title: Beta Skill
        description: Second skill.
        steps:
          - Move slowly
        evidence_rating: B
        contraindications:
          - acute injury
        duration_minutes: 15
        """,
    )
    _write_yaml(
        yaml_dir,
        "gamma.yaml",
        """
        name: gamma-skill
        modality: breathwork
        title: Gamma Skill
        description: Third skill.
        steps:
          - Inhale
          - Exhale
        evidence_rating: C
        contraindications: []
        duration_minutes: 7
        """,
    )
    return yaml_dir


def test_load_directory_loads_all_files(fake_skills_dir: Path) -> None:
    reg = SkillRegistry()
    reg.load_directory(fake_skills_dir)
    assert len(reg) == 3


def test_get_returns_skill(fake_skills_dir: Path) -> None:
    reg = SkillRegistry()
    reg.load_directory(fake_skills_dir)
    skill = reg.get("alpha-skill")
    assert skill.title == "Alpha Skill"


def test_get_missing_raises_skill_not_found(fake_skills_dir: Path) -> None:
    reg = SkillRegistry()
    reg.load_directory(fake_skills_dir)
    with pytest.raises(SkillNotFoundError):
        reg.get("does-not-exist")


def test_list_by_modality_filters_correctly(fake_skills_dir: Path) -> None:
    reg = SkillRegistry()
    reg.load_directory(fake_skills_dir)
    breath = reg.list_by_modality("breathwork")
    somatic = reg.list_by_modality("somatic_practice")
    assert {s.name for s in breath} == {"alpha-skill", "gamma-skill"}
    assert {s.name for s in somatic} == {"beta-skill"}


def test_list_all_returns_every_skill(fake_skills_dir: Path) -> None:
    reg = SkillRegistry()
    reg.load_directory(fake_skills_dir)
    assert len(reg.list_all()) == 3


def test_load_twice_replaces_registry(tmp_path: Path, fake_skills_dir: Path) -> None:
    reg = SkillRegistry()
    reg.load_directory(fake_skills_dir)
    assert len(reg) == 3

    smaller = tmp_path / "smaller"
    smaller.mkdir()
    _write_yaml(
        smaller,
        "only.yaml",
        """
        name: only-skill
        modality: nature_healing
        title: Only Skill
        description: Sole entry.
        steps:
          - Walk outside
        evidence_rating: B
        contraindications: []
        duration_minutes: 20
        """,
    )
    reg.load_directory(smaller)
    assert len(reg) == 1
    assert reg.get("only-skill").modality == "nature_healing"
    with pytest.raises(SkillNotFoundError):
        reg.get("alpha-skill")


def test_invalid_yaml_raises_validation_error(tmp_path: Path) -> None:
    yaml_dir = tmp_path / "bad"
    yaml_dir.mkdir()
    _write_yaml(
        yaml_dir,
        "broken.yaml",
        """
        name: broken
        modality: not-a-real-modality
        title: Broken
        description: Bad modality.
        steps:
          - Step
        evidence_rating: A
        duration_minutes: 5
        """,
    )
    reg = SkillRegistry()
    with pytest.raises(SkillValidationError, match="broken.yaml"):
        reg.load_directory(yaml_dir)


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    yaml_dir = tmp_path / "malformed"
    yaml_dir.mkdir()
    (yaml_dir / "garbage.yaml").write_text("name: [unbalanced\n", encoding="utf-8")
    reg = SkillRegistry()
    with pytest.raises(SkillValidationError, match="garbage.yaml"):
        reg.load_directory(yaml_dir)


def test_duplicate_skill_names_rejected(tmp_path: Path) -> None:
    yaml_dir = tmp_path / "dupes"
    yaml_dir.mkdir()
    _write_yaml(
        yaml_dir,
        "one.yaml",
        """
        name: same-name
        modality: breathwork
        title: One
        description: First.
        steps:
          - A
        evidence_rating: A
        duration_minutes: 5
        """,
    )
    _write_yaml(
        yaml_dir,
        "two.yaml",
        """
        name: same-name
        modality: somatic_practice
        title: Two
        description: Second.
        steps:
          - B
        evidence_rating: B
        duration_minutes: 6
        """,
    )
    reg = SkillRegistry()
    with pytest.raises(SkillValidationError, match="Duplicate"):
        reg.load_directory(yaml_dir)


def test_missing_directory_raises(tmp_path: Path) -> None:
    reg = SkillRegistry()
    with pytest.raises(FileNotFoundError):
        reg.load_directory(tmp_path / "nope")

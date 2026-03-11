"""SkillRegistry: loads and indexes HealingSkill objects from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from .schema import HealingSkill

_SKILLS_DIR = Path(__file__).parent / "yaml"


class SkillRegistry:
    """In-memory registry of healing skills loaded from YAML files."""

    def __init__(self) -> None:
        self._skills: dict[str, HealingSkill] = {}

    def load_from_dir(self, directory: Path | None = None) -> int:
        """Load all ``*.yaml`` files from *directory* into the registry.

        If *directory* is ``None``, the package-bundled ``yaml/`` directory is
        used.  Each call is additive — call on a fresh instance to start clean.

        Returns the total number of skills now in the registry.
        """
        target = directory if directory is not None else _SKILLS_DIR
        for path in sorted(target.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            skill = HealingSkill.model_validate(data)
            self._skills[skill.id] = skill
        return len(self._skills)

    def get(self, skill_id: str) -> HealingSkill | None:
        """Return a skill by ID, or ``None`` if not found."""
        return self._skills.get(skill_id)

    def by_modality(self, modality: str) -> list[HealingSkill]:
        """Return all skills matching *modality*."""
        return [s for s in self._skills.values() if s.modality == modality]

    def all(self) -> list[HealingSkill]:
        """Return all loaded skills."""
        return list(self._skills.values())


registry = SkillRegistry()

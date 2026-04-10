"""Loader and registry for healing skill YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .schema import SkillDefinition


class SkillNotFoundError(KeyError):
    """Raised when a skill name is not present in the registry."""


class SkillValidationError(ValueError):
    """Raised when a YAML file fails schema validation."""


def get_default_yaml_dir() -> Path:
    """Return the package-relative directory of seed skill YAML files."""
    return Path(__file__).parent / "yaml"


class SkillRegistry:
    """In-memory registry of healing skills loaded from YAML files.

    Supports loading from multiple directories. Call
    :meth:`load_directory` once per directory; skills accumulate across
    calls. Use ``replace=True`` (the default for backward compatibility)
    to clear previous entries, or ``replace=False`` to merge.
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def load_directory(self, path: Path, *, replace: bool = True) -> None:
        """Load all ``*.yaml`` files under *path* into the registry.

        Parameters
        ----------
        path:
            Directory containing YAML skill definitions.
        replace:
            If ``True`` (default), clear existing skills before loading.
            If ``False``, merge new skills into the existing registry.
            Duplicate skill names raise :class:`SkillValidationError`
            regardless of mode.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist or is not a directory.
        SkillValidationError
            If any file fails schema validation or contains a duplicate
            skill name (within the directory or vs. existing skills when
            ``replace=False``).
        """
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Skill YAML directory not found: {path}")

        loaded: dict[str, SkillDefinition] = {}
        for yaml_path in sorted(path.glob("*.yaml")):
            skill = _load_one(yaml_path)
            if skill.name in loaded:
                raise SkillValidationError(
                    f"Duplicate skill name '{skill.name}' in {yaml_path.name}"
                )
            loaded[skill.name] = skill

        if replace:
            self._skills = loaded
        else:
            # Merge — check for cross-directory duplicates
            for name, _skill in loaded.items():
                if name in self._skills:
                    raise SkillValidationError(
                        f"Duplicate skill name '{name}' conflicts with already-loaded skill"
                    )
            self._skills.update(loaded)

    def get(self, name: str) -> SkillDefinition:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillNotFoundError(name) from exc

    def list_by_modality(self, modality: str) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if s.modality == modality]

    def list_all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)


def _load_one(yaml_path: Path) -> SkillDefinition:
    try:
        with open(yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise SkillValidationError(f"{yaml_path.name}: invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise SkillValidationError(
            f"{yaml_path.name}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )

    try:
        return SkillDefinition.model_validate(raw)
    except ValidationError as exc:
        raise SkillValidationError(f"{yaml_path.name}: {exc}") from exc

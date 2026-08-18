"""Loader and registry for healing skill YAML files.

The registry builder lives here rather than in the API router, so the
API, the MCP server and any future worker mount the same skills by
calling the same function. Keeping it in the router is what let the MCP
server drift onto a bundled-only view (issue #265).

Failure policy, matched to the practice-pack loader
(``engine/practice/loader.py``, design section 3.3): a configured
external directory that cannot be used is a hard failure, logged at
ERROR naming the directory and the environment variable. Configuring a
mount asserts that its content is required, so warning-and-skipping
ships a quietly smaller product with no signal.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import NoReturn

import yaml
from pydantic import ValidationError

from .schema import LICENSING_FIELDS, SkillDefinition

logger = logging.getLogger(__name__)

# Named rather than inlined so an error message and the setting stay in
# step, and so a test can assert the operator is told what to fix.
EXTERNAL_DIR_ENV_VAR = "HEALING_SKILLS_EXTERNAL_DIR"


class SkillNotFoundError(KeyError):
    """Raised when a skill name is not present in the registry."""


class SkillValidationError(ValueError):
    """Raised when a YAML file or a configured directory fails a load rule."""


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

    def load_directory(
        self, path: Path, *, replace: bool = True, expect_bundled: bool = True
    ) -> None:
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
        expect_bundled:
            Whether this directory is the in-repo bundled location. Each
            skill's own ``bundled`` flag has to agree, so a skill in an
            external directory cannot claim bundled status and inherit
            Alchymine's licensing defaults. External skills must declare
            ``license`` and ``attribution`` for themselves.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist or is not a directory.
        SkillValidationError
            If any file fails schema validation, declares the wrong
            ``bundled`` status, omits required licensing metadata, or
            contains a duplicate skill name (within the directory or vs.
            existing skills when ``replace=False``).
        """
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Skill YAML directory not found: {path}")

        loaded: dict[str, SkillDefinition] = {}
        for yaml_path in sorted(path.glob("*.yaml")):
            skill = _load_one(yaml_path, expect_bundled=expect_bundled)
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


def _load_one(yaml_path: Path, *, expect_bundled: bool = True) -> SkillDefinition:
    try:
        with open(yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise SkillValidationError(f"{yaml_path.name}: invalid YAML: {exc}") from exc
    except OSError as exc:
        raise SkillValidationError(f"{yaml_path.name}: cannot be read: {exc}") from exc

    if not isinstance(raw, dict):
        raise SkillValidationError(
            f"{yaml_path.name}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )

    try:
        skill = SkillDefinition.model_validate(raw)
    except ValidationError as exc:
        raise SkillValidationError(f"{yaml_path.name}: {exc}") from exc

    _check_licensing(skill, yaml_path, raw, expect_bundled=expect_bundled)
    return skill


def _check_licensing(
    skill: SkillDefinition,
    yaml_path: Path,
    raw: dict[str, object],
    *,
    expect_bundled: bool,
) -> None:
    """Enforce the bundled-vs-external split on one loaded skill.

    Declared status has to match where the file was found, and anything
    Alchymine did not write has to say who wrote it and under what terms.
    The check reads the raw mapping rather than the model, because the
    model's defaults would otherwise satisfy it silently.
    """
    if skill.bundled != expect_bundled:
        where = (
            "the bundled skills directory" if expect_bundled else "a configured external directory"
        )
        raise SkillValidationError(
            f"{yaml_path.name}: skill '{skill.name}' declares bundled={skill.bundled} "
            f"but was loaded from {where}. The flag has to match where the file lives, "
            f"so an external skill cannot inherit Alchymine's licensing defaults."
        )

    if skill.bundled:
        return

    missing = [field for field in LICENSING_FIELDS if field not in raw]
    if missing:
        raise SkillValidationError(
            f"{yaml_path.name}: skill '{skill.name}' does not declare "
            f"{' and '.join(missing)}. A skill Alchymine did not write must state who "
            f"wrote it and under what terms."
        )


# ─── Registry construction ──────────────────────────────────────────


def _validate_external_dir(external_dir: Path) -> None:
    """Raise unless *external_dir* is a readable directory holding YAML.

    Every branch here is a configuration mistake an operator can fix, so
    every branch names the path and the variable that pointed at it.
    """
    if not external_dir.exists():
        _fail(f"the directory does not exist: {external_dir}")
    if not external_dir.is_dir():
        _fail(f"the path is not a directory: {external_dir}")

    try:
        yaml_files = sorted(external_dir.glob("*.yaml"))
    except OSError as exc:
        _fail(f"the directory cannot be read: {external_dir} ({exc})")

    if not yaml_files:
        # The wrong-volume-mount case, and the likeliest production
        # mistake: the path resolves, and holds nothing we can load.
        _fail(f"the directory holds no *.yaml files: {external_dir}")


def _fail(reason: str) -> NoReturn:
    """Log at ERROR and raise, so the signal survives either handling."""
    message = (
        f"{EXTERNAL_DIR_ENV_VAR} is set but unusable: {reason}. "
        f"Unset {EXTERNAL_DIR_ENV_VAR} to serve the bundled skills only, or point it "
        f"at a readable directory of skill YAML files."
    )
    logger.error(message)
    raise SkillValidationError(message)


def build_skill_registry(external_dir: Path | None = None) -> SkillRegistry:
    """Build a registry from the bundled skills plus *external_dir*.

    Load order is bundled first, then the external directory. A duplicate
    skill name across the two is a hard error: healing skill names are a
    single flat namespace, unlike pack-namespaced practice slugs.

    Raises
    ------
    SkillValidationError
        On any load rule, including a configured-but-unusable external
        directory. Nothing is skipped.
    """
    registry = SkillRegistry()
    registry.load_directory(get_default_yaml_dir(), expect_bundled=True)
    bundled_count = len(registry)

    if external_dir is not None:
        _validate_external_dir(external_dir)
        try:
            registry.load_directory(external_dir, replace=False, expect_bundled=False)
        except (FileNotFoundError, SkillValidationError) as exc:
            _fail(f"a skill in {external_dir} failed to load: {exc}")

        logger.info(
            "Loaded %d healing skill(s): %d bundled, %d from %s",
            len(registry),
            bundled_count,
            len(registry) - bundled_count,
            external_dir,
        )
    else:
        logger.info("Loaded %d bundled healing skill(s)", bundled_count)

    return registry


# ─── Process-global registry ────────────────────────────────────────

_registry: SkillRegistry | None = None
_registry_lock = threading.Lock()


def install_skill_registry() -> SkillRegistry:
    """Build the registry from settings and install it process-globally.

    Call this during API startup so a mistyped ``HEALING_SKILLS_EXTERNAL_DIR``
    stops the container, where the deploy's health machinery sees it,
    rather than becoming a 500 for whichever user reaches
    ``/healing/skills`` first.
    """
    from alchymine.config import get_settings

    global _registry
    with _registry_lock:
        configured = get_settings().healing_skills_external_dir
        registry = build_skill_registry(Path(configured) if configured else None)
        _registry = registry
        return registry


def get_skill_registry() -> SkillRegistry:
    """Return the installed registry, building it on first use if needed.

    The lazy path is for entry points without a lifespan (the MCP server,
    the CLI, a worker), so every one of them mounts the same skills from
    the same configuration.
    """
    registry = _registry
    if registry is not None:
        return registry
    return install_skill_registry()


def set_skill_registry(registry: SkillRegistry | None) -> None:
    """Install *registry* directly, or clear it with ``None``.

    Tests use this to mount a fixture directory without touching the
    environment, and to restore the global afterwards.
    """
    global _registry
    with _registry_lock:
        _registry = registry

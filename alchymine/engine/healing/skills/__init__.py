"""Healing skills sub-package.

YAML-defined practice cards (one per healing modality) loaded by a
`SkillRegistry`. Each skill is a structured, evidence-rated practice
that the API and chat agents can surface to users.

Every entry point should reach the registry through
:func:`get_skill_registry` rather than building its own, so REST and MCP
cannot drift onto different skill sets.
"""

from .loader import (
    EXTERNAL_DIR_ENV_VAR,
    SkillNotFoundError,
    SkillRegistry,
    SkillValidationError,
    build_skill_registry,
    get_default_yaml_dir,
    get_skill_registry,
    install_skill_registry,
    set_skill_registry,
)
from .schema import BUNDLED_ATTRIBUTION, BUNDLED_LICENSE, LICENSING_FIELDS, SkillDefinition

__all__ = [
    "BUNDLED_ATTRIBUTION",
    "BUNDLED_LICENSE",
    "EXTERNAL_DIR_ENV_VAR",
    "LICENSING_FIELDS",
    "SkillDefinition",
    "SkillNotFoundError",
    "SkillRegistry",
    "SkillValidationError",
    "build_skill_registry",
    "get_default_yaml_dir",
    "get_skill_registry",
    "install_skill_registry",
    "set_skill_registry",
]

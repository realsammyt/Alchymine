"""Practice packs: schema v2, loader, registry and purpose dimensions.

A pack is one directory holding ``pack.yaml`` plus one YAML file per
practice. Packs ship in-repo (``packs/alchymine-foundations``) or mount
from outside it through ``PRACTICE_PACK_DIRS``, and both go through the
same validation: schema, licensing, category screening, graph rules and
the shared ethics gate.
"""

from .loader import (
    LoadedPack,
    PackNotFoundError,
    PracticeNotFoundError,
    PracticePackValidationError,
    PracticeRegistry,
    build_practice_registry,
    get_bundled_packs_dir,
    get_practice_registry,
    install_practice_registry,
    load_pack,
    set_practice_registry,
)
from .purposes import (
    PURPOSE_DEFINITIONS,
    PURPOSE_ORDER,
    PURPOSE_TO_SYSTEM,
    VALID_PURPOSES,
    system_for_purpose,
)
from .schema import (
    ACCEPTED_CATEGORIES,
    PROSE_FIELDS,
    REJECTED_CATEGORIES,
    SCHEMA_VERSION,
    PackManifest,
    PracticeCategory,
    PracticeDefinition,
    SelfCheck,
)

__all__ = [
    "ACCEPTED_CATEGORIES",
    "PROSE_FIELDS",
    "PURPOSE_DEFINITIONS",
    "PURPOSE_ORDER",
    "PURPOSE_TO_SYSTEM",
    "REJECTED_CATEGORIES",
    "SCHEMA_VERSION",
    "VALID_PURPOSES",
    "LoadedPack",
    "PackManifest",
    "PackNotFoundError",
    "PracticeCategory",
    "PracticeDefinition",
    "PracticeNotFoundError",
    "PracticePackValidationError",
    "PracticeRegistry",
    "SelfCheck",
    "build_practice_registry",
    "get_bundled_packs_dir",
    "get_practice_registry",
    "install_practice_registry",
    "load_pack",
    "set_practice_registry",
    "system_for_purpose",
]

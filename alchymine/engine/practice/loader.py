"""Loader and registry for practice packs.

The loading logic lives in the engine rather than in an API router, so
the API, the Celery worker and any future MCP server all mount the same
packs by calling the same builder. The healing loader lives in its
router, which is why its MCP server ignores the external directory.

Failure policy (design section 3.3): every validation problem raises.
Nothing is warned-and-skipped. An operator who mistypes a mount path
gets a stopped container, not a quietly smaller product.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from alchymine.agents.quality.ethics_check import check_text

from .schema import PackManifest, PracticeDefinition

logger = logging.getLogger(__name__)

# Ethics violations at or above this severity fail the load.
_FATAL_SEVERITIES = frozenset({"error", "critical"})

_BUNDLED_PACK_DIRNAME = "packs"


class PracticePackValidationError(ValueError):
    """Raised when a pack directory fails any load-time rule."""


class PracticeNotFoundError(KeyError):
    """Raised when a practice slug is not present in a mounted pack."""


class PackNotFoundError(KeyError):
    """Raised when a pack id is not mounted."""


def get_bundled_packs_dir() -> Path:
    """Return the in-repo directory that holds bundled pack directories."""
    return Path(__file__).parent / _BUNDLED_PACK_DIRNAME


class LoadedPack:
    """One validated pack: its manifest, its practices and its graph depths."""

    __slots__ = ("_depths", "_practices", "manifest", "source_dir")

    def __init__(
        self,
        manifest: PackManifest,
        practices: dict[str, PracticeDefinition],
        depths: dict[str, int],
        source_dir: Path,
    ) -> None:
        self.manifest = manifest
        self.source_dir = source_dir
        self._practices = practices
        self._depths = depths

    @property
    def pack_id(self) -> str:
        return self.manifest.pack_id

    def practices(self) -> list[PracticeDefinition]:
        """Return practices in display order: ``order`` then ``slug``."""
        return sorted(self._practices.values(), key=lambda p: (p.order, p.slug))

    def get(self, slug: str) -> PracticeDefinition:
        try:
            return self._practices[slug]
        except KeyError as exc:
            raise PracticeNotFoundError(f"{self.pack_id}/{slug}") from exc

    def depth(self, slug: str) -> int:
        try:
            return self._depths[slug]
        except KeyError as exc:
            raise PracticeNotFoundError(f"{self.pack_id}/{slug}") from exc

    def __len__(self) -> int:
        return len(self._practices)


class PracticeRegistry:
    """Process-global, read-only view of every mounted pack.

    Built once at startup from frozen models. There is no reload method:
    re-reading a configurable filesystem path at runtime is a surface
    nobody asked for, and the deploy restarts containers anyway.
    """

    __slots__ = ("_packs",)

    def __init__(self, packs: Sequence[LoadedPack]) -> None:
        self._packs: dict[str, LoadedPack] = {pack.pack_id: pack for pack in packs}

    def get_pack(self, pack_id: str) -> PackManifest:
        return self._pack(pack_id).manifest

    def list_packs(self) -> list[PackManifest]:
        return [pack.manifest for pack in self._packs.values()]

    def practice_count(self, pack_id: str) -> int:
        return len(self._pack(pack_id))

    def get(self, pack_id: str, slug: str) -> PracticeDefinition:
        return self._pack(pack_id).get(slug)

    def progression_depth(self, pack_id: str, slug: str) -> int:
        """Longest path from any root to *slug*. A root is 0."""
        return self._pack(pack_id).depth(slug)

    def list_practices(
        self,
        *,
        purpose: str | None = None,
        category: str | None = None,
        pack_id: str | None = None,
    ) -> list[tuple[str, PracticeDefinition]]:
        """Return ``(pack_id, practice)`` pairs, narrowed by any filter given.

        A filter value that matches nothing narrows to an empty list
        rather than raising: filters describe what the caller wants, and
        a typo in one is not a different kind of event from a pack that
        happens to hold no matches.
        """
        results: list[tuple[str, PracticeDefinition]] = []
        for pack in self._packs.values():
            if pack_id is not None and pack.pack_id != pack_id:
                continue
            for practice in pack.practices():
                if purpose is not None and purpose not in practice.purposes:
                    continue
                if category is not None and practice.category != category:
                    continue
                results.append((pack.pack_id, practice))
        return results

    def __len__(self) -> int:
        return sum(len(pack) for pack in self._packs.values())

    def _pack(self, pack_id: str) -> LoadedPack:
        try:
            return self._packs[pack_id]
        except KeyError as exc:
            raise PackNotFoundError(pack_id) from exc


# ─── Loading ────────────────────────────────────────────────────────


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PracticePackValidationError(f"{path.name}: invalid YAML: {exc}") from exc
    except OSError as exc:
        raise PracticePackValidationError(f"{path.name}: cannot be read: {exc}") from exc

    if not isinstance(raw, dict):
        raise PracticePackValidationError(
            f"{path.name}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )
    return raw


def _load_manifest(pack_dir: Path) -> PackManifest:
    manifest_path = pack_dir / "pack.yaml"
    raw = _read_yaml_mapping(manifest_path)
    try:
        manifest = PackManifest.model_validate(raw)
    except ValidationError as exc:
        raise PracticePackValidationError(f"{pack_dir.name}/pack.yaml: {exc}") from exc

    if manifest.pack_id != pack_dir.name:
        raise PracticePackValidationError(
            f"{pack_dir.name}/pack.yaml: pack_id '{manifest.pack_id}' does not match its "
            f"directory name '{pack_dir.name}'. They must agree so an error naming a "
            f"pack_id points at a directory an operator can find."
        )
    return manifest


def _load_practices(pack_dir: Path, pack_id: str) -> dict[str, PracticeDefinition]:
    practices: dict[str, PracticeDefinition] = {}
    for yaml_path in sorted(pack_dir.glob("*.yaml")):
        if yaml_path.name == "pack.yaml":
            continue

        raw = _read_yaml_mapping(yaml_path)
        try:
            practice = PracticeDefinition.model_validate(raw)
        except ValidationError as exc:
            raise PracticePackValidationError(
                f"pack '{pack_id}' ({yaml_path.name}): {exc}"
            ) from exc

        if practice.slug in practices:
            raise PracticePackValidationError(
                f"pack '{pack_id}' ({yaml_path.name}): duplicate practice slug '{practice.slug}'"
            )
        practices[practice.slug] = practice

    if not practices:
        raise PracticePackValidationError(
            f"pack '{pack_id}' ({pack_dir}) declares no practices. A pack directory "
            f"needs pack.yaml plus at least one practice YAML file."
        )
    return practices


def _check_prose(pack_id: str, practices: dict[str, PracticeDefinition]) -> None:
    """Run every practice's prose through the shared ethics gate.

    The same fatalistic-language, diagnostic-language and dark-pattern
    rules that generated narratives pass, applied to content Alchymine
    did not write. Regex-based, so it costs nothing.
    """
    for slug, practice in practices.items():
        result = check_text(practice.prose(), context="general")
        fatal = [v for v in result.violations if v.severity in _FATAL_SEVERITIES]
        if fatal:
            detail = "; ".join(
                f"{v.category} ({v.severity}): {v.description} [matched: {v.matched_text!r}]"
                for v in fatal
            )
            raise PracticePackValidationError(
                f"pack '{pack_id}' ({slug}.yaml): prose failed the ethics gate: {detail}"
            )


def _validate_edges(pack_id: str, practices: dict[str, PracticeDefinition]) -> None:
    """Every ``builds_on`` and ``related`` slug must resolve within the pack."""
    for slug, practice in sorted(practices.items()):
        for field in ("builds_on", "related"):
            for target in getattr(practice, field):
                if target not in practices:
                    raise PracticePackValidationError(
                        f"pack '{pack_id}' practice '{slug}' ({slug}.yaml): "
                        f"{field} references unknown slug '{target}'"
                    )


def _compute_depths(pack_id: str, practices: dict[str, PracticeDefinition]) -> dict[str, int]:
    """Return ``{slug: longest path from a root}``, raising on a cycle.

    Iterative depth-first search rather than recursion: pack depth is
    author-controlled and a deep external pack should not be able to
    blow the interpreter stack.
    """
    depths: dict[str, int] = {}
    # 0 = unvisited, 1 = on the current path, 2 = resolved.
    state: dict[str, int] = dict.fromkeys(practices, 0)

    for start in sorted(practices):
        if state[start] == 2:
            continue

        # Each stack frame is (slug, index of the next parent to walk).
        stack: list[tuple[str, int]] = [(start, 0)]
        state[start] = 1

        while stack:
            slug, cursor = stack[-1]
            parents = practices[slug].builds_on

            if cursor < len(parents):
                stack[-1] = (slug, cursor + 1)
                parent = parents[cursor]
                if state[parent] == 1:
                    raise PracticePackValidationError(
                        f"pack '{pack_id}': builds_on cycle: {_describe_cycle(stack, parent)}"
                    )
                if state[parent] == 0:
                    state[parent] = 1
                    stack.append((parent, 0))
                continue

            stack.pop()
            state[slug] = 2
            depths[slug] = 1 + max((depths[p] for p in parents), default=-1)

    return depths


def _describe_cycle(stack: list[tuple[str, int]], repeated: str) -> str:
    """Render the cycle as ``a -> b -> c -> a`` from the active DFS path."""
    path = [slug for slug, _ in stack]
    start = path.index(repeated) if repeated in path else 0
    return " -> ".join([*path[start:], repeated])


def load_pack(pack_dir: Path, *, expect_bundled: bool) -> LoadedPack:
    """Validate and load a single pack directory.

    Parameters
    ----------
    pack_dir:
        A directory holding ``pack.yaml`` plus one YAML file per practice.
    expect_bundled:
        Whether this directory came from the in-repo bundled location.
        The manifest's ``bundled`` flag has to agree, so an external pack
        cannot claim bundled status to skip the licensing check.
    """
    manifest = _load_manifest(pack_dir)

    if manifest.bundled != expect_bundled:
        where = "the bundled packs directory" if expect_bundled else "a configured mount"
        raise PracticePackValidationError(
            f"pack '{manifest.pack_id}': manifest declares bundled={manifest.bundled} "
            f"but the pack was loaded from {where}."
        )

    if not manifest.bundled:
        for field in ("license", "attribution"):
            if not getattr(manifest, field).strip():
                raise PracticePackValidationError(
                    f"pack '{manifest.pack_id}' ({pack_dir}): {field} is empty. A pack "
                    f"Alchymine did not write must declare who wrote it and under what "
                    f"terms."
                )

    practices = _load_practices(pack_dir, manifest.pack_id)
    _check_prose(manifest.pack_id, practices)
    _validate_edges(manifest.pack_id, practices)
    depths = _compute_depths(manifest.pack_id, practices)

    return LoadedPack(manifest, practices, depths, pack_dir)


def _discover_pack_dirs(container: Path, *, bundled: bool) -> list[Path]:
    """Return the pack directories inside *container*, or raise.

    A configured directory holds one subdirectory per pack. Configuring
    it asserts its content is required, so missing, unreadable and empty
    are all hard failures.
    """
    label = "Bundled" if bundled else "Configured"

    if not container.exists():
        raise PracticePackValidationError(
            f"{label} practice pack directory does not exist: {container}"
        )
    if not container.is_dir():
        raise PracticePackValidationError(
            f"{label} practice pack path is not a directory: {container}"
        )

    try:
        entries = sorted(entry for entry in container.iterdir() if entry.is_dir())
    except OSError as exc:
        raise PracticePackValidationError(
            f"{label} practice pack directory cannot be read: {container} ({exc})"
        ) from exc

    pack_dirs = [entry for entry in entries if (entry / "pack.yaml").is_file()]

    if not pack_dirs:
        hint = ""
        if (container / "pack.yaml").is_file():
            hint = (
                " This path holds a pack.yaml directly, so it looks like a pack "
                "directory. PRACTICE_PACK_DIRS wants its parent."
            )
        raise PracticePackValidationError(
            f"{label} practice pack directory holds no pack.yaml in any subdirectory: "
            f"{container}.{hint}"
        )

    return pack_dirs


def build_practice_registry(
    external_dirs: Sequence[Path] | None = None,
) -> PracticeRegistry:
    """Build a registry from the bundled pack plus each configured directory.

    Load order is bundled first, then external directories in declared
    order. A duplicate ``pack_id`` across directories is a hard error;
    duplicate practice *slugs* across packs are normal, because slugs are
    namespaced by pack.

    Raises
    ------
    PracticePackValidationError
        On any load-time rule (section 3.3). Nothing is skipped.
    """
    packs: list[LoadedPack] = []
    seen: dict[str, Path] = {}

    sources: list[tuple[Path, bool]] = [(get_bundled_packs_dir(), True)]
    sources.extend((Path(d), False) for d in (external_dirs or ()))

    for container, bundled in sources:
        for pack_dir in _discover_pack_dirs(container, bundled=bundled):
            pack = load_pack(pack_dir, expect_bundled=bundled)
            if pack.pack_id in seen:
                raise PracticePackValidationError(
                    f"duplicate pack_id '{pack.pack_id}': already loaded from "
                    f"{seen[pack.pack_id]}, found again at {pack_dir}"
                )
            seen[pack.pack_id] = pack_dir
            packs.append(pack)

    logger.info(
        "Loaded %d practice pack(s), %d practice(s): %s",
        len(packs),
        sum(len(p) for p in packs),
        ", ".join(p.pack_id for p in packs),
    )
    return PracticeRegistry(packs)


# ─── Process-global registry ────────────────────────────────────────

_registry: PracticeRegistry | None = None
_registry_lock = threading.Lock()


def install_practice_registry() -> PracticeRegistry:
    """Build the registry from settings and install it process-globally.

    Called during API startup so a bad mount stops the container rather
    than surfacing as a 500 for whichever user hits ``/practices`` first.
    """
    from alchymine.config import get_settings

    global _registry
    with _registry_lock:
        registry = build_practice_registry(get_settings().get_practice_pack_dirs())
        _registry = registry
        return registry


def get_practice_registry() -> PracticeRegistry:
    """Return the installed registry, building it on first use if needed.

    The API installs it eagerly at startup. The lazy path is for entry
    points without a lifespan (workers, the CLI, a future MCP server),
    so they mount the same packs from the same configuration.
    """
    registry = _registry
    if registry is not None:
        return registry
    return install_practice_registry()


def set_practice_registry(registry: PracticeRegistry | None) -> None:
    """Install *registry* directly, or clear it with ``None``.

    Tests use this to mount a fixture pack without touching the
    environment, and to restore the global afterwards.
    """
    global _registry
    with _registry_lock:
        _registry = registry

"""The API lifespan installs the healing skill registry at startup (#265).

The loader already refuses a configured-but-unusable
``HEALING_SKILLS_EXTERNAL_DIR``. This module asserts the wiring that turns
that refusal into a stopped container rather than a 500 for whichever user
reaches ``/healing/skills`` first, which is the policy
``install_practice_registry`` already gets.

The lazy path in ``get_skill_registry`` would satisfy a naive assertion
here whether or not the lifespan calls anything, so these tests spy on
``main.install_skill_registry`` rather than reading the result.

Fixture skills use invented names. Nothing here names a real
practitioner, publisher or tradition-holder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from alchymine.api import main
from alchymine.config import get_settings
from alchymine.engine.healing.skills import (
    EXTERNAL_DIR_ENV_VAR,
    SkillRegistry,
    SkillValidationError,
    get_skill_registry,
    install_skill_registry,
    set_skill_registry,
)

BUNDLED_SKILL_COUNT = 15


@pytest.fixture
def quiet_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the shutdown half of the lifespan.

    The engine singleton belongs to an autouse fixture running on its own
    event loop, and disposing it from this test's loop is a race with
    nothing to do with startup wiring.
    """

    async def _noop() -> None:
        return None

    monkeypatch.setattr(main, "flush_pending_writes", _noop)
    monkeypatch.setattr(main, "dispose_engine", _noop)


@pytest.fixture(autouse=True)
def _clear_global_registry() -> Any:
    set_skill_registry(None)
    yield
    set_skill_registry(None)


@pytest.fixture
def install_spy(monkeypatch: pytest.MonkeyPatch) -> list[SkillRegistry]:
    """Record every lifespan call to install_skill_registry, calling through."""
    seen: list[SkillRegistry] = []

    def _spy() -> SkillRegistry:
        registry = install_skill_registry()
        seen.append(registry)
        return registry

    monkeypatch.setattr(main, "install_skill_registry", _spy)
    return seen


async def test_lifespan_installs_the_skill_registry(
    install_spy: list[SkillRegistry], quiet_shutdown: None
) -> None:
    async with main.lifespan(main.app):
        assert len(install_spy) == 1
        assert get_skill_registry() is install_spy[0]
        assert len(install_spy[0]) == BUNDLED_SKILL_COUNT


async def test_lifespan_stops_on_an_unusable_external_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, quiet_shutdown: None
) -> None:
    """A mistyped mount path stops the container, it does not serve less."""
    monkeypatch.setenv(EXTERNAL_DIR_ENV_VAR, str(tmp_path / "typo-in-this-path"))
    get_settings.cache_clear()
    try:
        with pytest.raises(SkillValidationError, match=EXTERNAL_DIR_ENV_VAR):
            async with main.lifespan(main.app):
                pass
    finally:
        get_settings.cache_clear()


async def test_lifespan_mounts_a_declared_external_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    install_spy: list[SkillRegistry],
    quiet_shutdown: None,
) -> None:
    external = tmp_path / "external"
    external.mkdir()
    (external / "invented-shore-walking.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "invented-shore-walking",
                "modality": "nature_healing",
                "title": "Shore Walking",
                "description": "Walk a stretch of shoreline slowly and notice the footing.",
                "steps": ["Find a stretch of shore.", "Walk it slowly.", "Turn around."],
                "evidence_rating": "D",
                "contraindications": [],
                "duration_minutes": 20,
                "bundled": False,
                "license": "Apache-2.0",
                "attribution": "Wren Halloway",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(EXTERNAL_DIR_ENV_VAR, str(external))
    get_settings.cache_clear()
    try:
        async with main.lifespan(main.app):
            assert len(install_spy) == 1
            assert len(install_spy[0]) == BUNDLED_SKILL_COUNT + 1
    finally:
        get_settings.cache_clear()

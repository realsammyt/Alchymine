"""Licensing metadata and loud external-dir failures for healing skills (#265).

Three behaviours are pinned here:

1. ``SkillDefinition`` carries ``license`` / ``attribution`` /
   ``source_url`` / ``bundled``, defaulted for bundled content and
   required for anything loaded from a configured external directory.
2. ``build_skill_registry`` hard-fails on a configured-but-unusable
   external directory instead of warning and shipping a smaller product.
3. The process-global registry is one object, so REST and MCP see the
   same skills.

Fixture skills use invented names throughout. Nothing here names a real
practitioner, publisher or tradition-holder.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
import yaml

from alchymine.config import get_settings
from alchymine.engine.healing.skills import (
    EXTERNAL_DIR_ENV_VAR,
    SkillDefinition,
    SkillRegistry,
    SkillValidationError,
    build_skill_registry,
    get_skill_registry,
    install_skill_registry,
    set_skill_registry,
)

BUNDLED_SKILL_COUNT = 15


def skill_dict(name: str = "invented-quiet-sitting", **overrides: Any) -> dict[str, Any]:
    """Return a schema-valid skill mapping, with *overrides* applied."""
    base: dict[str, Any] = {
        "name": name,
        "modality": "somatic_practice",
        "title": "Quiet Sitting",
        "description": "Sit still for a short while and notice the weight of your body.",
        "steps": ["Sit down.", "Notice the chair holding you.", "Stand up slowly."],
        "evidence_rating": "D",
        "contraindications": [],
        "duration_minutes": 5,
    }
    base.update(overrides)
    return base


def write_skill_dir(container: Path, *skills: dict[str, Any]) -> Path:
    """Write one YAML per skill into *container* and return it."""
    container.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        (container / f"{skill['name']}.yaml").write_text(
            yaml.safe_dump(skill, sort_keys=False), encoding="utf-8"
        )
    return container


@pytest.fixture(autouse=True)
def _clear_global_registry() -> Any:
    """Keep the process-global registry from leaking between tests."""
    set_skill_registry(None)
    yield
    set_skill_registry(None)


# ── Gap 1: license / attribution fields on the schema ──────────────────


class TestLicensingFields:
    def test_bundled_skill_defaults_the_licensing_fields(self) -> None:
        """A skill YAML with no licensing block still validates."""
        skill = SkillDefinition.model_validate(skill_dict())
        assert skill.license == "CC-BY-NC-SA-4.0"
        assert skill.attribution == "Alchymine Contributors"
        assert skill.source_url is None
        assert skill.bundled is True

    def test_licensing_fields_are_accepted_from_yaml(self) -> None:
        """extra=forbid no longer blocks declaring them."""
        skill = SkillDefinition.model_validate(
            skill_dict(
                license="Apache-2.0",
                attribution="Wren Halloway",
                source_url="https://example.invalid/skills",
                bundled=False,
            )
        )
        assert skill.license == "Apache-2.0"
        assert skill.attribution == "Wren Halloway"
        assert skill.source_url == "https://example.invalid/skills"
        assert skill.bundled is False

    def test_blank_license_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="license"):
            SkillDefinition.model_validate(skill_dict(license="   "))

    def test_blank_attribution_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="attribution"):
            SkillDefinition.model_validate(skill_dict(attribution=""))

    def test_non_http_source_url_is_rejected(self) -> None:
        """The UI renders source_url as a link, so javascript: is a vector."""
        with pytest.raises(ValueError, match="source_url"):
            SkillDefinition.model_validate(skill_dict(source_url="javascript:alert(1)"))

    def test_every_bundled_skill_carries_licensing_metadata(self) -> None:
        registry = build_skill_registry()
        assert len(registry) == BUNDLED_SKILL_COUNT
        for skill in registry.list_all():
            assert skill.bundled is True
            assert skill.license.strip()
            assert skill.attribution.strip()


class TestExternalLicensingIsRequired:
    def test_external_skill_without_license_is_refused(self, tmp_path: Path) -> None:
        external = write_skill_dir(
            tmp_path / "external",
            skill_dict("invented-shore-walking", bundled=False, attribution="Wren Halloway"),
        )
        with pytest.raises(SkillValidationError, match="license"):
            build_skill_registry(external)

    def test_external_skill_without_attribution_is_refused(self, tmp_path: Path) -> None:
        external = write_skill_dir(
            tmp_path / "external",
            skill_dict("invented-shore-walking", bundled=False, license="Apache-2.0"),
        )
        with pytest.raises(SkillValidationError, match="attribution"):
            build_skill_registry(external)

    def test_external_skill_cannot_claim_bundled_status(self, tmp_path: Path) -> None:
        """Otherwise ``bundled: true`` is a one-line licensing bypass."""
        external = write_skill_dir(
            tmp_path / "external", skill_dict("invented-shore-walking", bundled=True)
        )
        with pytest.raises(SkillValidationError, match="bundled"):
            build_skill_registry(external)

    def test_fully_declared_external_skill_loads(self, tmp_path: Path) -> None:
        external = write_skill_dir(
            tmp_path / "external",
            skill_dict(
                "invented-shore-walking",
                modality="nature_healing",
                bundled=False,
                license="Apache-2.0",
                attribution="Wren Halloway",
                source_url="https://example.invalid/skills",
            ),
        )
        registry = build_skill_registry(external)
        assert len(registry) == BUNDLED_SKILL_COUNT + 1
        loaded = registry.get("invented-shore-walking")
        assert loaded.bundled is False
        assert loaded.attribution == "Wren Halloway"

    def test_bundled_skills_still_load_without_a_licensing_block(self) -> None:
        """The default is what keeps this a metadata addition, not a migration."""
        registry = build_skill_registry()
        assert len(registry) == BUNDLED_SKILL_COUNT


# ── Gap 2: loud failures on a configured external directory ────────────


class TestLoudExternalDirFailures:
    def test_missing_dir_raises_naming_dir_and_env_var(self, tmp_path: Path) -> None:
        missing = tmp_path / "not-mounted"
        with pytest.raises(SkillValidationError) as exc:
            build_skill_registry(missing)
        assert str(missing) in str(exc.value)
        assert EXTERNAL_DIR_ENV_VAR in str(exc.value)

    def test_path_that_is_a_file_raises(self, tmp_path: Path) -> None:
        not_a_dir = tmp_path / "skills.yaml"
        not_a_dir.write_text("name: nope\n", encoding="utf-8")
        with pytest.raises(SkillValidationError, match="not a directory"):
            build_skill_registry(not_a_dir)

    def test_dir_with_no_yaml_raises(self, tmp_path: Path) -> None:
        """The wrong-volume-mount case: the likeliest production mistake."""
        empty = tmp_path / "external"
        empty.mkdir()
        (empty / "README.txt").write_text("nothing here\n", encoding="utf-8")
        with pytest.raises(SkillValidationError, match="no [*.]*yaml"):
            build_skill_registry(empty)

    def test_invalid_yaml_raises_rather_than_skipping(self, tmp_path: Path) -> None:
        external = tmp_path / "external"
        external.mkdir()
        (external / "broken.yaml").write_text("name: [unclosed\n", encoding="utf-8")
        with pytest.raises(SkillValidationError):
            build_skill_registry(external)

    def test_failure_is_logged_at_error_level(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        missing = tmp_path / "not-mounted"
        with caplog.at_level(logging.ERROR, logger="alchymine.engine.healing.skills.loader"):
            with pytest.raises(SkillValidationError):
                build_skill_registry(missing)
        errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert errors, "a configured-but-unusable external dir must log at ERROR"
        joined = " ".join(r.getMessage() for r in errors)
        assert str(missing) in joined
        assert EXTERNAL_DIR_ENV_VAR in joined

    def test_unset_external_dir_is_normal(self) -> None:
        registry = build_skill_registry(None)
        assert len(registry) == BUNDLED_SKILL_COUNT

    def test_install_reads_the_configured_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        external = write_skill_dir(
            tmp_path / "external",
            skill_dict(
                "invented-shore-walking",
                modality="nature_healing",
                bundled=False,
                license="Apache-2.0",
                attribution="Wren Halloway",
            ),
        )
        monkeypatch.setenv(EXTERNAL_DIR_ENV_VAR, str(external))
        get_settings.cache_clear()
        try:
            registry = install_skill_registry()
            assert len(registry) == BUNDLED_SKILL_COUNT + 1
            assert get_skill_registry() is registry
        finally:
            get_settings.cache_clear()


# ── Gap 3: one registry for every entry point ──────────────────────────


class TestProcessGlobalRegistry:
    def test_get_builds_once_and_reuses(self) -> None:
        first = get_skill_registry()
        assert get_skill_registry() is first

    def test_set_installs_a_fixture_registry(self, tmp_path: Path) -> None:
        external = write_skill_dir(
            tmp_path / "only",
            skill_dict("invented-quiet-sitting", license="Apache-2.0"),
        )
        fixture = SkillRegistry()
        fixture.load_directory(external)
        set_skill_registry(fixture)
        assert get_skill_registry() is fixture
        assert len(get_skill_registry()) == 1

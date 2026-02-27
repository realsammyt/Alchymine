"""Tests for prompt templates and validation."""

from __future__ import annotations

import pytest
import yaml

from alchymine.prompts import TEMPLATES_DIR
from alchymine.prompts.validate import (
    REQUIRED_FIELDS,
    validate_all,
    validate_template,
)


class TestPromptTemplatesExist:
    """Verify all required prompt templates exist."""

    EXPECTED_TEMPLATES = [
        "intelligence_narrative",
        "healing_narrative",
        "wealth_narrative",
        "creative_narrative",
        "perspective_narrative",
        "synthesis_narrative",
    ]

    def test_templates_directory_exists(self):
        assert TEMPLATES_DIR.exists()
        assert TEMPLATES_DIR.is_dir()

    @pytest.mark.parametrize("template", EXPECTED_TEMPLATES)
    def test_template_file_exists(self, template):
        path = TEMPLATES_DIR / f"{template}.yaml"
        assert path.exists(), f"Missing template: {template}.yaml"

    @pytest.mark.parametrize("template", EXPECTED_TEMPLATES)
    def test_template_is_valid_yaml(self, template):
        path = TEMPLATES_DIR / f"{template}.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)


class TestPromptTemplateStructure:
    """Verify prompt template structure and required fields."""

    @pytest.fixture
    def templates(self):
        return sorted(TEMPLATES_DIR.glob("*.yaml"))

    def test_all_templates_have_required_fields(self, templates):
        for path in templates:
            with open(path) as f:
                data = yaml.safe_load(f)
            missing = REQUIRED_FIELDS - set(data.keys())
            assert not missing, f"{path.stem}: missing {missing}"

    def test_all_templates_have_version(self, templates):
        for path in templates:
            with open(path) as f:
                data = yaml.safe_load(f)
            assert "version" in data
            assert data["version"] is not None

    def test_healing_template_has_disclaimers(self):
        path = TEMPLATES_DIR / "healing_narrative.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "disclaimers" in data
        assert len(data["disclaimers"]) >= 1

    def test_wealth_template_has_disclaimers(self):
        path = TEMPLATES_DIR / "wealth_narrative.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "disclaimers" in data
        assert len(data["disclaimers"]) >= 1

    def test_perspective_template_has_disclaimers(self):
        path = TEMPLATES_DIR / "perspective_narrative.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "disclaimers" in data
        assert len(data["disclaimers"]) >= 1

    def test_all_templates_have_constraints(self, templates):
        for path in templates:
            with open(path) as f:
                data = yaml.safe_load(f)
            assert "constraints" in data, f"{path.stem}: no constraints"
            assert len(data["constraints"]) >= 1


class TestPromptValidation:
    """Test the validation pipeline."""

    def test_validate_all_passes(self):
        results = validate_all()
        assert len(results) >= 6
        for result in results:
            assert result.valid, f"{result.path.stem} failed: {result.errors}"

    def test_validate_nonexistent_file(self, tmp_path):
        fake = tmp_path / "nonexistent.yaml"
        result = validate_template(fake)
        assert not result.valid
        assert any("does not exist" in e.lower() or "yaml" in e.lower() for e in result.errors)

    def test_validate_invalid_yaml(self, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{invalid: yaml: [")
        result = validate_template(bad_yaml)
        assert not result.valid
        assert any("yaml" in e.lower() for e in result.errors)

    def test_validate_missing_required_fields(self, tmp_path):
        minimal = tmp_path / "minimal.yaml"
        minimal.write_text("name: test\nversion: '1.0'\n")
        result = validate_template(minimal)
        assert not result.valid
        assert any("missing" in e.lower() for e in result.errors)

    def test_validate_ethics_violation_detected(self, tmp_path):
        bad_prompt = tmp_path / "bad_prompt.yaml"
        bad_prompt.write_text(
            "name: test\n"
            "version: '1.0'\n"
            "system: general\n"
            "system_prompt: 'You are destined to succeed always.'\n"
            "user_prompt: 'Tell the user.'\n"
            "constraints:\n  - Be nice\n"
        )
        result = validate_template(bad_prompt)
        assert not result.valid
        assert any("ethics" in e.lower() or "fatalistic" in e.lower() for e in result.errors)


class TestPromptValidationCLI:
    """Test the CLI entry point."""

    def test_main_returns_zero_on_success(self):
        from alchymine.prompts.validate import main

        assert main() == 0

"""Prompt template validation module.

Validates all YAML prompt templates for:
- Valid YAML syntax
- Required fields (name, version, system, system_prompt, user_prompt)
- Ethics compliance (no fatalistic/diagnostic/dark-pattern language)
- Disclaimer presence for healing/wealth systems

Usage:
    python -m alchymine.prompts.validate
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from alchymine.agents.quality.ethics_check import check_prompt
from alchymine.prompts import TEMPLATES_DIR

# Required fields in every prompt template
REQUIRED_FIELDS = {"name", "version", "system", "system_prompt", "user_prompt"}

# Systems that require disclaimers
DISCLAIMER_REQUIRED_SYSTEMS = {"healing", "wealth", "perspective"}


@dataclass
class ValidationResult:
    """Result of validating a single prompt template."""

    path: Path
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_template(path: Path) -> ValidationResult:
    """Validate a single YAML prompt template.

    Checks for valid YAML, required fields, and ethics compliance.
    """
    result = ValidationResult(path=path)

    # Check file exists
    if not path.exists():
        result.valid = False
        result.errors.append(f"File does not exist: {path}")
        return result

    # Parse YAML
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        result.valid = False
        result.errors.append(f"Invalid YAML: {exc}")
        return result

    if not isinstance(data, dict):
        result.valid = False
        result.errors.append("Template must be a YAML mapping")
        return result

    # Check required fields
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        result.valid = False
        result.errors.append(f"Missing required fields: {', '.join(sorted(missing))}")

    # Check disclaimers for systems that require them
    system = data.get("system", "")
    if system in DISCLAIMER_REQUIRED_SYSTEMS:
        disclaimers = data.get("disclaimers", [])
        if not disclaimers:
            result.valid = False
            result.errors.append(f"System '{system}' requires disclaimers")

    # Check constraints exist
    if not data.get("constraints"):
        result.warnings.append("No constraints defined — consider adding ethical constraints")

    # Run ethics check on system_prompt and user_prompt
    for field_name in ("system_prompt", "user_prompt"):
        text = data.get(field_name, "")
        if text:
            ethics_result = check_prompt(text)
            if not ethics_result.passed:
                for v in ethics_result.violations:
                    result.valid = False
                    result.errors.append(
                        f"Ethics violation in {field_name}: "
                        f"[{v.category}] {v.description} — {v.suggestion}"
                    )

    return result


def validate_all() -> list[ValidationResult]:
    """Validate all YAML prompt templates in the templates directory."""
    results: list[ValidationResult] = []
    templates = sorted(TEMPLATES_DIR.glob("*.yaml"))

    if not templates:
        print(f"WARNING: No YAML templates found in {TEMPLATES_DIR}")
        return results

    for path in templates:
        result = validate_template(path)
        results.append(result)

    return results


def main() -> int:
    """CLI entry point — validate all templates and report results."""
    print(f"Validating prompt templates in {TEMPLATES_DIR}...")
    print()

    results = validate_all()

    if not results:
        print("No templates found to validate.")
        return 1

    all_valid = True
    for result in results:
        name = result.path.stem
        if result.valid:
            status = "PASS"
        else:
            status = "FAIL"
            all_valid = False

        print(f"  [{status}] {name}")
        for error in result.errors:
            print(f"         ERROR: {error}")
        for warning in result.warnings:
            print(f"         WARN:  {warning}")

    print()
    if all_valid:
        print(f"All {len(results)} templates passed validation.")
        return 0
    else:
        failed = sum(1 for r in results if not r.valid)
        print(f"FAILED: {failed}/{len(results)} templates have errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

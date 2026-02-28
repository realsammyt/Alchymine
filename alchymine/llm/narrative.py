"""Narrative generator — transforms engine outputs into interpretive text.

Loads YAML prompt templates, fills them with engine data, sends to the
LLM client, and validates the response through the ethics pipeline.

Usage:
    generator = NarrativeGenerator()
    result = await generator.generate("intelligence", engine_data)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

from alchymine.agents.quality.ethics_check import check_text
from alchymine.llm.client import LLMClient, LLMResponse
from alchymine.prompts import TEMPLATES_DIR

logger = logging.getLogger(__name__)


@dataclass
class NarrativeResult:
    """Result of narrative generation for a single system.

    Attributes
    ----------
    system:
        The system this narrative was generated for.
    narrative:
        The generated narrative text.
    disclaimers:
        Required disclaimers from the prompt template.
    llm_response:
        The raw LLM response metadata.
    ethics_passed:
        Whether the generated narrative passed ethics validation.
    ethics_violations:
        List of ethics violation descriptions (empty if passed).
    """

    system: str
    narrative: str
    disclaimers: list[str] = field(default_factory=list)
    llm_response: LLMResponse | None = None
    ethics_passed: bool = True
    ethics_violations: list[str] = field(default_factory=list)


def load_template(system: str) -> dict[str, Any]:
    """Load a YAML prompt template for a given system.

    Parameters
    ----------
    system:
        The system name (e.g., "intelligence", "healing", "wealth").

    Returns
    -------
    dict
        The parsed YAML template data.

    Raises
    ------
    FileNotFoundError
        If no template exists for the given system.
    """
    template_path = TEMPLATES_DIR / f"{system}_narrative.yaml"
    if not template_path.exists():
        raise FileNotFoundError(f"No prompt template for system: {system}")

    with open(template_path) as f:
        return yaml.safe_load(f)


def fill_template(template_text: str, data: dict[str, Any]) -> str:
    """Fill a prompt template with engine data.

    Uses str.format_map with a defaulting dict so missing keys
    produce "{key}" instead of raising KeyError.

    Parameters
    ----------
    template_text:
        The prompt template text with {placeholder} markers.
    data:
        A flat dict of key-value pairs to substitute.

    Returns
    -------
    str
        The filled template text.
    """

    class DefaultDict(dict):  # type: ignore[type-arg]
        """Dict that returns '{key}' for missing keys."""

        def __missing__(self, key: str) -> str:
            return f"{{{key}}}"

    return template_text.format_map(DefaultDict(data))


def flatten_engine_data(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested engine data for template substitution.

    Converts nested dicts into flat key-value pairs. For example:
    {"numerology": {"life_path": 3}} → {"life_path": 3}

    Also generates summary sections for list-type data.
    """
    flat: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[sub_key] = sub_value
        elif isinstance(value, list):
            # Generate a markdown-style section for lists
            lines = []
            for item in value:
                if isinstance(item, dict):
                    name = item.get("name", item.get("type", str(item)))
                    desc = item.get("description", "")
                    lines.append(f"- **{name}**: {desc}" if desc else f"- {name}")
                else:
                    lines.append(f"- {item}")
            flat[f"{key}_section"] = "\n  ".join(lines) if lines else "(none)"
        else:
            flat[key] = value

    return flat


class NarrativeGenerator:
    """Generates narrative interpretations from engine data.

    Combines YAML prompt templates with LLM generation and
    ethics validation.
    """

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client or LLMClient()

    async def generate(
        self,
        system: str,
        engine_data: dict[str, Any],
        temperature: float = 0.7,
    ) -> NarrativeResult:
        """Generate a narrative for a single system.

        Parameters
        ----------
        system:
            The system name (e.g., "intelligence", "healing").
        engine_data:
            The deterministic engine output data dict.
        temperature:
            LLM sampling temperature.

        Returns
        -------
        NarrativeResult
            The narrative with metadata and ethics validation.
        """
        # Load template
        try:
            template = load_template(system)
        except FileNotFoundError:
            logger.warning("No template for system %s, skipping narrative", system)
            return NarrativeResult(
                system=system,
                narrative="",
                ethics_passed=True,
            )

        # Flatten and fill
        flat_data = flatten_engine_data(engine_data)
        system_prompt = fill_template(template.get("system_prompt", ""), flat_data)
        user_prompt = fill_template(template.get("user_prompt", ""), flat_data)
        disclaimers = template.get("disclaimers", [])

        # Generate
        llm_response = await self._client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

        # Validate ethics
        ethics_result = check_text(llm_response.text, context=system)
        violations = [v.description for v in ethics_result.violations]

        if not ethics_result.passed:
            logger.warning(
                "Ethics violations in %s narrative: %s",
                system,
                violations,
            )

        return NarrativeResult(
            system=system,
            narrative=llm_response.text,
            disclaimers=disclaimers,
            llm_response=llm_response,
            ethics_passed=ethics_result.passed,
            ethics_violations=violations,
        )

    async def generate_all(
        self,
        systems: list[str],
        engine_data: dict[str, Any],
    ) -> dict[str, NarrativeResult]:
        """Generate narratives for multiple systems.

        Parameters
        ----------
        systems:
            List of system names to generate for.
        engine_data:
            Combined engine data dict with per-system sub-dicts.

        Returns
        -------
        dict
            Map of system name → NarrativeResult.
        """
        results: dict[str, NarrativeResult] = {}
        for system in systems:
            system_data = engine_data.get(system, engine_data)
            results[system] = await self.generate(system, system_data)
        return results

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


_KEGAN_DESCRIPTIONS: dict[str, str] = {
    "1": "Impulsive — subject to immediate impulses and perceptions",
    "2": "Imperial — focused on personal needs and concrete interests",
    "3": "Interpersonal — defined by relationships and others' expectations",
    "4": "Institutional — self-authoring with an internal value system",
    "5": "Inter-individual — holding multiple frameworks simultaneously",
}


def flatten_engine_data(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested engine data for template substitution.

    Converts nested dicts into flat key-value pairs. For example:
    {"numerology": {"life_path": 3}} → {"life_path": 3}

    Also generates summary sections for list-type data, and applies
    system-specific key aliases so template variables resolve correctly.
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
                    name = item.get("name", item.get("modality", item.get("type", str(item))))
                    desc = item.get("description", "")
                    lines.append(f"- **{name}**: {desc}" if desc else f"- {name}")
                else:
                    lines.append(f"- {item}")
            flat[f"{key}_section"] = "\n  ".join(lines) if lines else "(none)"
        else:
            flat[key] = value

    # ── System-specific key aliases ──────────────────────────────────────
    # Wealth: wealth_archetype dict → {wealth_archetype} + {archetype_description}
    wa = data.get("wealth_archetype")
    if isinstance(wa, dict):
        flat["wealth_archetype"] = wa.get("name", "")
        flat["archetype_description"] = wa.get("description", "")

    # Creative: creative_orientation dict → {creative_style}
    co = data.get("creative_orientation")
    if isinstance(co, dict):
        flat["creative_style"] = co.get("style", "")

    # Creative: style_fingerprint dict → {creative_style} (if not already set)
    sf = data.get("style_fingerprint")
    if isinstance(sf, dict):
        if "creative_style" not in flat:
            flat["creative_style"] = sf.get("creative_style", "")
        flat["overall_creative_score"] = sf.get("overall_score", "")

    # Perspective: detected_biases list → {biases_section}
    if "detected_biases_section" in flat:
        flat["biases_section"] = flat["detected_biases_section"]

    # Perspective: kegan_stage → {kegan_description}
    # Handle both old format (string/int) and new format (dict from synthesis)
    stage = flat.get("kegan_stage")
    if isinstance(stage, dict):
        flat["kegan_description"] = f"{stage.get('name', '')} — {stage.get('description', '')}"
        flat["kegan_stage_name"] = stage.get("name", "")
        flat["kegan_stage_number"] = stage.get("stage", "")
    elif stage is not None:
        flat["kegan_description"] = _KEGAN_DESCRIPTIONS.get(str(stage), f"Stage {stage}")

    # Perspective: kegan_description dict (from enriched graph) → detailed keys
    kd = data.get("kegan_description")
    if isinstance(kd, dict):
        if "kegan_description" not in flat or not flat["kegan_description"]:
            flat["kegan_description"] = f"{kd.get('name', '')} — {kd.get('description', '')}"
        flat["kegan_stage_name"] = kd.get("name", "")
        flat["kegan_strengths_section"] = (
            "\n".join(f"- {s}" for s in kd.get("strengths", [])) or "(none)"
        )
        flat["kegan_growth_edges_section"] = (
            "\n".join(f"- {e}" for e in kd.get("growth_edges", [])) or "(none)"
        )

    # Perspective: kegan_growth_pathway dict → {growth_practices}
    gp = data.get("kegan_growth_pathway")
    if isinstance(gp, dict):
        practices = gp.get("practices", [])
        flat["growth_practices"] = "\n".join(f"- {p}" for p in practices) or "(none)"
        flat["growth_encouragement"] = gp.get("encouragement", "")
        flat["growth_timeframe"] = gp.get("timeframe", "")

    # Perspective: decision_analysis dict → {decision_section} markdown
    da = data.get("decision_analysis")
    if isinstance(da, dict):
        lines = []
        for k, v in da.items():
            label = k.replace("_", " ").title()
            if isinstance(v, list):
                lines.append(f"### {label}")
                lines.extend(f"- {item}" for item in v)
            else:
                lines.append(f"- **{label}**: {v}")
        flat["decision_section"] = "\n".join(lines) if lines else "(no decision provided)"

    # Healing: recommended_modalities_section → {modalities_section}
    if "recommended_modalities_section" in flat:
        flat["modalities_section"] = flat["recommended_modalities_section"]

    # Healing: crisis_response dict → {crisis_section}
    cr = data.get("crisis_response")
    if isinstance(cr, dict):
        severity = cr.get("severity", "unknown")
        resources = cr.get("resources", [])
        lines = [f"- Severity: {severity}"]
        for r in resources:
            if isinstance(r, dict):
                lines.append(f"- {r.get('name', '')}: {r.get('contact', '')}")
        flat["crisis_section"] = "\n  ".join(lines)
    elif data.get("crisis_flag") is False:
        flat["crisis_section"] = "No crisis indicators detected."

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
        logger.info("[narrative] Requesting LLM narrative for system=%s", system)
        llm_response = await self._client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
        logger.info(
            "[narrative] Received narrative for system=%s — backend=%s, model=%s, %d chars",
            system,
            llm_response.backend,
            llm_response.model,
            len(llm_response.text),
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
        import asyncio
        import time as _time

        logger.info("[narrative] Generating narratives for %d systems: %s", len(systems), systems)
        t0 = _time.monotonic()

        async def _gen(system: str) -> tuple[str, NarrativeResult]:
            system_data = engine_data.get(system, engine_data)
            return system, await self.generate(system, system_data)

        try:
            pairs = await asyncio.wait_for(
                asyncio.gather(*[_gen(s) for s in systems]),
                timeout=300,  # 5 min hard cap — well within Celery's 540s soft limit
            )
        except TimeoutError:
            elapsed = _time.monotonic() - t0
            logger.error(
                "[narrative] Timed out after %.1fs waiting for %d systems: %s",
                elapsed,
                len(systems),
                systems,
            )
            raise
        elapsed = _time.monotonic() - t0
        logger.info("[narrative] All %d narratives complete in %.1fs", len(systems), elapsed)
        return dict(pairs)

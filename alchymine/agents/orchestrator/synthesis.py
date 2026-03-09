"""Cross-system synthesis workflows.

Implements structured workflows for combining outputs from multiple
system coordinators into coherent, personalized guidance. All synthesis
logic is deterministic (no LLM calls) — LLM is for narrative only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from alchymine.engine.intention_map import INTENTION_SYSTEM_RELEVANCE

from .coordinator import CoordinatorResult, CoordinatorStatus

logger = logging.getLogger(__name__)


# ─── Evidence rating constants ──────────────────────────────────────

EVIDENCE_DETERMINISTIC = "deterministic"
EVIDENCE_EVIDENCE_BASED = "evidence-based"
EVIDENCE_TRADITIONAL = "traditional"
EVIDENCE_EXPERIENTIAL = "experiential"

# Map system names to their default evidence rating
_SYSTEM_EVIDENCE_MAP: dict[str, str] = {
    "intelligence": EVIDENCE_TRADITIONAL,
    "healing": EVIDENCE_EVIDENCE_BASED,
    "wealth": EVIDENCE_DETERMINISTIC,
    "creative": EVIDENCE_EXPERIENTIAL,
    "perspective": EVIDENCE_EXPERIENTIAL,
}

# Keywords in data keys that override the default evidence rating
_DATA_KEY_EVIDENCE_OVERRIDES: dict[str, str] = {
    "numerology": EVIDENCE_TRADITIONAL,
    "astrology": EVIDENCE_TRADITIONAL,
    "archetype": EVIDENCE_TRADITIONAL,
    "calculations": EVIDENCE_DETERMINISTIC,
    "lever_priorities": EVIDENCE_DETERMINISTIC,
    "wealth_archetype": EVIDENCE_DETERMINISTIC,
    "modalities": EVIDENCE_EVIDENCE_BASED,
    "recommended_modalities": EVIDENCE_EVIDENCE_BASED,
    "crisis_flag": EVIDENCE_EVIDENCE_BASED,
    "detected_biases": EVIDENCE_EXPERIENTIAL,
    "kegan_stage": EVIDENCE_EXPERIENTIAL,
    "decision_analysis": EVIDENCE_EXPERIENTIAL,
    "creative_orientation": EVIDENCE_EXPERIENTIAL,
    "strengths": EVIDENCE_EXPERIENTIAL,
}

# System relevance mapping imported from canonical source:
#   alchymine.engine.intention_map.INTENTION_SYSTEM_RELEVANCE

# Conflict detection: pairs of data keys and action words that may contradict
_REST_KEYWORDS = frozenset(
    [
        "rest",
        "pause",
        "recover",
        "ground",
        "slow",
        "gentle",
        "safety",
    ]
)
_ACTION_KEYWORDS = frozenset(
    [
        "launch",
        "start",
        "push",
        "scale",
        "expand",
        "invest",
        "monetize",
        "aggressively",
    ]
)
_RISK_AVERSE_KEYWORDS = frozenset(
    [
        "risk aversion",
        "conservative",
        "cautious",
        "low risk",
        "safe",
        "stability",
    ]
)
_RISK_SEEKING_KEYWORDS = frozenset(
    [
        "aggressive",
        "high risk",
        "bold",
        "speculative",
        "leverage",
        "risk-tolerant",
    ]
)


# ─── Result dataclass ──────────────────────────────────────────────


@dataclass
class SynthesisResult:
    """Result from a synthesis workflow."""

    systems_involved: list[str]
    unified_insights: list[dict[str, Any]]
    cross_system_connections: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    evidence_ratings: dict[str, str]
    overall_coherence: float  # 0.0 to 1.0
    quality_passed: bool
    errors: list[str] = field(default_factory=list)


# ─── Internal helpers ──────────────────────────────────────────────


def _extract_insights_from_result(result: CoordinatorResult) -> list[dict[str, Any]]:
    """Extract structured insights from a coordinator result's data dict."""
    insights: list[dict[str, Any]] = []
    for key, value in result.data.items():
        # Skip meta-keys like disclaimers
        if key in ("disclaimers",):
            continue
        insights.append(
            {
                "system": result.system,
                "key": key,
                "value": value,
                "status": result.status,
            }
        )
    return insights


def _text_contains_keywords(text: str, keywords: frozenset[str]) -> bool:
    """Check whether *text* contains any of the given keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def _flatten_data_text(data: dict) -> str:
    """Flatten a coordinator data dict into a single string for keyword scanning."""
    parts: list[str] = []
    for value in data.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                if isinstance(v, str):
                    parts.append(v)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            parts.append(v)
    return " ".join(parts)


def _get_bridge_connections(
    results: list[CoordinatorResult],
) -> list[dict[str, Any]]:
    """Run bridge functions from integration/bridges.py to find cross-system connections.

    This is deterministic — no LLM calls.
    """
    connections: list[dict[str, Any]] = []

    # Collect data from all results by system
    system_data: dict[str, dict] = {}
    for r in results:
        system_data[r.system] = r.data

    try:
        from alchymine.engine.integration.bridges import (
            archetype_to_creative_style,
            check_coherence,
            cycle_to_timing,
            healing_to_perspective_sequence,
            shadow_to_block_mapping,
            wealth_creative_alignment,
        )

        intel_data = system_data.get("intelligence", {})
        wealth_data = system_data.get("wealth", {})
        creative_data = system_data.get("creative", {})
        healing_data = system_data.get("healing", {})
        perspective_data = system_data.get("perspective", {})

        # XS-01: Archetype -> Creative Style
        numerology = intel_data.get("numerology", {})
        archetype_data = intel_data.get("archetype", {})
        if isinstance(archetype_data, dict):
            primary_archetype = archetype_data.get("primary")
            if primary_archetype and ("creative" in system_data):
                bridge = archetype_to_creative_style(primary_archetype)
                connections.append(
                    {
                        "bridge_type": bridge.bridge_type,
                        "source_system": bridge.source_system,
                        "target_system": bridge.target_system,
                        "insight": bridge.insight,
                        "action": bridge.action,
                        "confidence": bridge.confidence,
                    }
                )

            # XS-02: Shadow -> Block
            shadow = archetype_data.get("shadow")
            if shadow and ("creative" in system_data):
                bridge = shadow_to_block_mapping(shadow)
                connections.append(
                    {
                        "bridge_type": bridge.bridge_type,
                        "source_system": bridge.source_system,
                        "target_system": bridge.target_system,
                        "insight": bridge.insight,
                        "action": bridge.action,
                        "confidence": bridge.confidence,
                    }
                )

        # XS-03: Cycle -> Timing
        personal_year = numerology.get("personal_year")
        if personal_year is not None and ("creative" in system_data or "wealth" in system_data):
            bridge = cycle_to_timing(personal_year)
            connections.append(
                {
                    "bridge_type": bridge.bridge_type,
                    "source_system": bridge.source_system,
                    "target_system": bridge.target_system,
                    "insight": bridge.insight,
                    "action": bridge.action,
                    "confidence": bridge.confidence,
                }
            )

        # XS-04: Wealth <-> Creative Alignment
        wealth_archetype = wealth_data.get("wealth_archetype", {})
        wa_name = wealth_archetype.get("name") if isinstance(wealth_archetype, dict) else None
        creative_orientation = creative_data.get("creative_orientation", {})
        creative_style = (
            creative_orientation.get("style") if isinstance(creative_orientation, dict) else None
        )
        if wa_name and creative_style:
            bridge = wealth_creative_alignment(wa_name, creative_style)
            connections.append(
                {
                    "bridge_type": bridge.bridge_type,
                    "source_system": bridge.source_system,
                    "target_system": bridge.target_system,
                    "insight": bridge.insight,
                    "action": bridge.action,
                    "confidence": bridge.confidence,
                }
            )

        # XS-05: Healing -> Perspective Sequencing
        kegan_stage = perspective_data.get("kegan_stage")
        if kegan_stage is not None and "healing" in system_data:
            modality = "breathwork"  # Default
            modalities = healing_data.get("recommended_modalities", [])
            if modalities and isinstance(modalities[0], dict):
                modality = modalities[0].get("modality", "breathwork")
            bridge = healing_to_perspective_sequence(modality, kegan_stage)
            connections.append(
                {
                    "bridge_type": bridge.bridge_type,
                    "source_system": bridge.source_system,
                    "target_system": bridge.target_system,
                    "insight": bridge.insight,
                    "action": bridge.action,
                    "confidence": bridge.confidence,
                }
            )

        # XS-06: Coherence check on cross-system recommendations
        if connections:
            active_recs = [
                {"system": c["source_system"], "action": c["action"]} for c in connections
            ]
            coherence_result = check_coherence(active_recs)
            if coherence_result.conflicts:
                for conflict in coherence_result.conflicts:
                    connections.append(
                        {
                            "bridge_type": "coherence_warning",
                            "source_system": "cross-system",
                            "target_system": "cross-system",
                            "insight": conflict,
                            "action": "Review conflicting recommendations.",
                            "confidence": coherence_result.coherence_score,
                        }
                    )

    except ImportError:
        logger.debug("Bridge engine not available — skipping cross-system connections")
    except Exception as exc:
        logger.warning("Bridge connection error: %s", exc)

    return connections


# ─── Public API ────────────────────────────────────────────────────


def _build_strengths_map(
    coordinator_results: list[CoordinatorResult],
) -> list[str]:
    """Build a cross-system strengths map from coordinator results.

    Extracts:
    - Top Big Five traits (score > 60) from Intelligence
    - Secure attachment style from Intelligence
    - Creative strengths from Creative
    - Perspective-taking ability from Perspective (Kegan stage >= 3)
    """
    strengths: list[str] = []

    _big_five_labels = {
        "openness": "Openness to Experience",
        "conscientiousness": "Conscientiousness",
        "extraversion": "Extraversion",
        "agreeableness": "Agreeableness",
    }

    for result in coordinator_results:
        if result.status == CoordinatorStatus.ERROR.value:
            continue

        data = result.data

        if result.system == "intelligence":
            personality = data.get("personality", {})
            if isinstance(personality, dict):
                big_five = personality.get("big_five", {})
                if isinstance(big_five, dict):
                    for trait, label in _big_five_labels.items():
                        score = big_five.get(trait)
                        if isinstance(score, (int, float)) and score > 60:
                            strengths.append(label)

                attachment = personality.get("attachment_style")
                if attachment == "secure":
                    strengths.append("Secure Attachment")

        elif result.system == "creative":
            creative_strengths = data.get("strengths", [])
            if isinstance(creative_strengths, list):
                for s in creative_strengths:
                    if isinstance(s, str):
                        strengths.append(s.replace("_", " ").title())

        elif result.system == "perspective":
            kegan = data.get("kegan_stage")
            # kegan_stage may be a string (enum value), int, or dict
            kegan_stage_num = None
            if isinstance(kegan, (int, float)):
                kegan_stage_num = kegan
            elif isinstance(kegan, str):
                # Map enum string values to stage numbers
                _stage_nums = {
                    "impulsive": 1,
                    "imperial": 2,
                    "socialized": 3,
                    "self-authoring": 4,
                    "self-transforming": 5,
                }
                kegan_stage_num = _stage_nums.get(kegan)
            elif isinstance(kegan, dict):
                kegan_stage_num = kegan.get("stage")
            if kegan_stage_num is not None and kegan_stage_num >= 3:
                strengths.append("Perspective-Taking")

    return strengths


def transform_to_profile_summary(
    coordinator_results: list[CoordinatorResult],
) -> dict[str, Any]:
    """Transform coordinator results into the profile_summary shape expected by the HTML renderer.

    The renderer expects:
        profile_summary.identity.{numerology, astrology, archetype, personality, strengths_map}
        profile_summary.healing.{...}
        profile_summary.wealth.{...}
        profile_summary.creative.{...}
        profile_summary.perspective.{...}

    Each coordinator result has .system (str) and .data (dict).
    """
    summary: dict[str, Any] = {}
    strengths_map = _build_strengths_map(coordinator_results)

    for result in coordinator_results:
        if result.status == CoordinatorStatus.ERROR.value:
            continue

        system = result.system
        data = dict(result.data)

        if system == "intelligence":
            summary["identity"] = {
                "numerology": data.get("numerology", {}),
                "astrology": data.get("astrology", {}),
                "archetype": data.get("archetype", {}),
                "personality": data.get("personality", {}),
                "biorhythm": data.get("biorhythm", {}),
                "strengths_map": strengths_map,
            }
        elif system == "healing":
            summary["healing"] = {k: v for k, v in data.items() if k != "disclaimers"}
            summary["healing"]["disclaimers"] = data.get("disclaimers", [])
        elif system == "wealth":
            summary["wealth"] = {k: v for k, v in data.items() if k != "disclaimers"}
            summary["wealth"]["disclaimers"] = data.get("disclaimers", [])
        elif system == "creative":
            # Reshape creative_orientation from plain string to {style, summary}
            orientation = data.get("creative_orientation", "")
            fingerprint = data.get("style_fingerprint", {})
            if isinstance(orientation, str):
                data["creative_orientation"] = {
                    "style": orientation,
                    "summary": fingerprint.get("creative_style", "")
                    if isinstance(fingerprint, dict)
                    else "",
                }
            summary["creative"] = data
        elif system == "perspective":
            # Reshape kegan_stage from string to {stage, name, description}
            kegan_value = data.get("kegan_stage")
            kegan_desc = data.get("kegan_description", {})
            if isinstance(kegan_value, str) and isinstance(kegan_desc, dict):
                data["kegan_stage"] = {
                    "stage": kegan_desc.get("stage_number"),
                    "name": kegan_desc.get("name", kegan_value),
                    "description": kegan_desc.get("description", ""),
                }
            summary["perspective"] = data

    return summary


def detect_conflicts(
    results: list[CoordinatorResult],
) -> list[dict[str, Any]]:
    """Compare outputs across systems for contradictions.

    Returns structured conflict descriptions with resolution suggestions.
    Each conflict dict has keys: systems, description, resolution, severity.
    """
    conflicts: list[dict[str, Any]] = []

    if len(results) < 2:
        return conflicts

    # Build per-system text for keyword scanning
    system_texts: dict[str, str] = {}
    for r in results:
        if r.status != CoordinatorStatus.ERROR.value:
            system_texts[r.system] = _flatten_data_text(r.data)

    # Detect rest-vs-action conflict
    rest_systems: list[str] = []
    action_systems: list[str] = []
    for system, text in system_texts.items():
        if _text_contains_keywords(text, _REST_KEYWORDS):
            rest_systems.append(system)
        if _text_contains_keywords(text, _ACTION_KEYWORDS):
            action_systems.append(system)

    if rest_systems and action_systems:
        conflicts.append(
            {
                "systems": rest_systems + action_systems,
                "description": (
                    f"{', '.join(rest_systems)} recommend rest/recovery while "
                    f"{', '.join(action_systems)} recommend action/expansion."
                ),
                "resolution": (
                    "Prioritize rest and recovery before taking expansive action. "
                    "Consider a phased approach: stabilize first, then expand."
                ),
                "severity": "warning",
            }
        )

    # Detect risk-averse vs risk-seeking conflict
    conservative_systems: list[str] = []
    aggressive_systems: list[str] = []
    for system, text in system_texts.items():
        if _text_contains_keywords(text, _RISK_AVERSE_KEYWORDS):
            conservative_systems.append(system)
        if _text_contains_keywords(text, _RISK_SEEKING_KEYWORDS):
            aggressive_systems.append(system)

    if conservative_systems and aggressive_systems:
        conflicts.append(
            {
                "systems": conservative_systems + aggressive_systems,
                "description": (
                    f"{', '.join(conservative_systems)} indicate caution/conservatism while "
                    f"{', '.join(aggressive_systems)} suggest aggressive/high-risk approaches."
                ),
                "resolution": (
                    "Align risk level across systems. When in doubt, start with "
                    "the more conservative approach and increase gradually."
                ),
                "severity": "warning",
            }
        )

    # Detect too many active recommendations across systems
    total_recommendations = sum(
        len([k for k in r.data if k not in ("disclaimers", "calculations")])
        for r in results
        if r.status != CoordinatorStatus.ERROR.value
    )
    if total_recommendations > 7:
        conflicts.append(
            {
                "systems": [r.system for r in results],
                "description": (
                    f"Too many active recommendations across systems ({total_recommendations}). "
                    "User may experience overwhelm."
                ),
                "resolution": (
                    "Prioritize the top 3 most relevant recommendations. "
                    "Present remaining insights as secondary exploration paths."
                ),
                "severity": "info",
            }
        )

    return conflicts


def aggregate_evidence(
    results: list[CoordinatorResult],
) -> dict[str, str]:
    """Map each insight to an evidence rating.

    Ratings:
    - "deterministic": numerology/astrology calculations, wealth calculations
    - "evidence-based": healing modalities (with references)
    - "traditional": numerology interpretations, astrology, archetypes
    - "experiential": creative, perspective

    Returns a dict mapping "system.key" -> evidence_rating.
    """
    ratings: dict[str, str] = {}

    for result in results:
        system = result.system
        default_rating = _SYSTEM_EVIDENCE_MAP.get(system, EVIDENCE_EXPERIENTIAL)

        for key in result.data:
            if key in ("disclaimers",):
                continue
            # Check for specific overrides
            rating = _DATA_KEY_EVIDENCE_OVERRIDES.get(key, default_rating)
            ratings[f"{system}.{key}"] = rating

    return ratings


def synthesize_full_profile(
    results: list[CoordinatorResult],
) -> SynthesisResult:
    """Merge all system outputs into unified insights.

    Calls bridge functions from integration/bridges.py to find cross-system
    connections, detects conflicts between systems, assigns evidence ratings
    per insight, and calculates a coherence score.
    """
    systems_involved: list[str] = []
    unified_insights: list[dict[str, Any]] = []
    errors: list[str] = []

    for result in results:
        systems_involved.append(result.system)
        unified_insights.extend(_extract_insights_from_result(result))
        if result.errors:
            errors.extend(result.errors)

    # Cross-system bridge connections
    cross_system_connections = _get_bridge_connections(results)

    # Conflict detection
    conflicts = detect_conflicts(results)

    # Evidence ratings
    evidence_ratings = aggregate_evidence(results)

    # Coherence score
    overall_coherence = _calculate_coherence(results, conflicts, cross_system_connections)

    # Quality check
    quality_passed = all(cr.quality_passed for cr in results)

    return SynthesisResult(
        systems_involved=systems_involved,
        unified_insights=unified_insights,
        cross_system_connections=cross_system_connections,
        conflicts=conflicts,
        evidence_ratings=evidence_ratings,
        overall_coherence=overall_coherence,
        quality_passed=quality_passed,
        errors=errors,
    )


def synthesize_guided_session(
    results: list[CoordinatorResult],
    intention: str,
    *,
    intentions: list[str] | None = None,
) -> SynthesisResult:
    """Filter and rank insights by relevance to the user's intention(s).

    Prioritizes systems most aligned with the intention and generates
    cross-system action items.  When *intentions* (a list of 1-3
    intention strings) is provided, system priorities are merged from
    all intentions (deduplicated, ordered by first appearance).
    """
    # Determine system priority based on intention(s)
    all_intentions = [i.lower().strip() for i in (intentions or [intention])]
    system_priority: list[str] = []
    for intent in all_intentions:
        for keyword, systems in INTENTION_SYSTEM_RELEVANCE.items():
            if keyword in intent:
                for s in systems:
                    if s not in system_priority:
                        system_priority.append(s)

    # If no specific mapping found, use all systems equally
    if not system_priority:
        system_priority = [r.system for r in results]

    # Sort results by relevance to intention
    def _relevance_score(result: CoordinatorResult) -> int:
        try:
            idx = system_priority.index(result.system)
            return idx
        except ValueError:
            return len(system_priority)

    sorted_results = sorted(results, key=_relevance_score)

    # Extract insights, prioritized
    systems_involved: list[str] = []
    unified_insights: list[dict[str, Any]] = []
    errors: list[str] = []

    intention_label = ", ".join(all_intentions)
    for rank, result in enumerate(sorted_results):
        systems_involved.append(result.system)
        for insight in _extract_insights_from_result(result):
            insight["relevance_rank"] = rank
            insight["intention"] = intention_label
            unified_insights.append(insight)
        if result.errors:
            errors.extend(result.errors)

    # Cross-system connections
    cross_system_connections = _get_bridge_connections(sorted_results)

    # Add intention-based action items to connections
    for conn in cross_system_connections:
        conn["intention_alignment"] = intention

    # Conflict detection
    conflicts = detect_conflicts(sorted_results)

    # Evidence ratings
    evidence_ratings = aggregate_evidence(sorted_results)

    # Coherence score
    overall_coherence = _calculate_coherence(
        sorted_results,
        conflicts,
        cross_system_connections,
    )

    # Quality
    quality_passed = all(cr.quality_passed for cr in sorted_results)

    return SynthesisResult(
        systems_involved=systems_involved,
        unified_insights=unified_insights,
        cross_system_connections=cross_system_connections,
        conflicts=conflicts,
        evidence_ratings=evidence_ratings,
        overall_coherence=overall_coherence,
        quality_passed=quality_passed,
        errors=errors,
    )


def _calculate_coherence(
    results: list[CoordinatorResult],
    conflicts: list[dict[str, Any]],
    connections: list[dict[str, Any]],
) -> float:
    """Calculate an overall coherence score (0.0 to 1.0).

    Factors:
    - Starts at 1.0
    - Deducts for each conflict (-0.15 per conflict)
    - Deducts for error-status results (-0.1 per error)
    - Adds a small bonus for each cross-system connection (+0.05 per connection, capped)
    - Clamps to [0.0, 1.0]
    """
    if not results:
        return 1.0

    score = 1.0

    # Penalise conflicts
    score -= 0.15 * len(conflicts)

    # Penalise errors
    error_count = sum(1 for r in results if r.status == CoordinatorStatus.ERROR.value)
    score -= 0.1 * error_count

    # Reward connections (cap the bonus at +0.2)
    real_connections = [c for c in connections if c.get("bridge_type") != "coherence_warning"]
    connection_bonus = min(0.05 * len(real_connections), 0.2)
    score += connection_bonus

    return max(0.0, min(1.0, score))

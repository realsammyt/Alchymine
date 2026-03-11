"""Profile completeness computation utilities."""

from __future__ import annotations

from typing import Any

_SECTION_CONFIG: list[tuple[str, str, int]] = [
    ("big_five", "bf_", 20),
    ("attachment", "att_", 4),
    ("risk_tolerance", "risk_", 3),
    ("enneagram", "enn_", 9),
    ("perspective", "kegan_", 5),
    ("creativity", "guil_", 26),
]

_TOTAL_QUESTIONS = sum(total for _, _, total in _SECTION_CONFIG)


def compute_completeness(
    assessment_responses: dict[str, Any] | None,
    identity_layer: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute profile completeness across all assessment sections.

    Args:
        assessment_responses: The flat dict of assessment question keys to values,
            keyed by prefix (e.g. ``bf_1``, ``att_2``).  May be ``None``.
        identity_layer: The user's identity profile layer dict.  May be ``None``.

    Returns:
        A dict with:
        - ``sections``: per-section ``{complete, answered, total}``
        - ``identity_computed``: bool — True when the identity layer has a
          ``personality`` key with a truthy value
        - ``overall_pct``: int — percentage of total questions answered (0-100)
    """
    responses = assessment_responses or {}
    sections: dict[str, dict[str, Any]] = {}
    total_answered = 0

    for section_name, prefix, expected in _SECTION_CONFIG:
        answered = sum(1 for key in responses if key.startswith(prefix))
        sections[section_name] = {
            "complete": answered >= expected,
            "answered": answered,
            "total": expected,
        }
        total_answered += answered

    identity_computed = bool(identity_layer and identity_layer.get("personality"))

    overall_pct = round(total_answered / _TOTAL_QUESTIONS * 100) if _TOTAL_QUESTIONS > 0 else 0
    overall_pct = min(overall_pct, 100)

    return {
        "sections": sections,
        "identity_computed": identity_computed,
        "overall_pct": overall_pct,
    }

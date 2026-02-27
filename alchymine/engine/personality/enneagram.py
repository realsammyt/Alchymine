"""Enneagram type and wing scoring engine.

A simplified 9-item assessment where each item corresponds to one of the nine
Enneagram types. Each item is rated 1-5 for resonance.

Types:
  1 - Reformer       4 - Individualist    7 - Enthusiast
  2 - Helper          5 - Investigator     8 - Challenger
  3 - Achiever        6 - Loyalist         9 - Peacemaker

Scoring:
  - The highest-scoring type is the primary type.
  - The wing is the highest-scoring *adjacent* type (e.g., for type 4,
    adjacent types are 3 and 5). The Enneagram is circular, so type 1's
    neighbors are 9 and 2, and type 9's neighbors are 8 and 1.
  - Ties for primary type are broken by the lower type number.
  - Ties for wing are broken by the lower adjacent number.

Risk Tolerance (bonus scorer):
  Three questions measuring financial risk tolerance.
  Average < 2.5 → conservative, 2.5-3.5 → moderate, > 3.5 → aggressive.
"""

from __future__ import annotations

from alchymine.engine.profile import RiskTolerance

# ── Type metadata ─────────────────────────────────────────────────────

ENNEAGRAM_TYPES: dict[int, str] = {
    1: "Reformer",
    2: "Helper",
    3: "Achiever",
    4: "Individualist",
    5: "Investigator",
    6: "Loyalist",
    7: "Enthusiast",
    8: "Challenger",
    9: "Peacemaker",
}

# Adjacent types on the Enneagram circle (wrapping 9→1, 1→9).
_ADJACENT: dict[int, tuple[int, int]] = {
    1: (9, 2),
    2: (1, 3),
    3: (2, 4),
    4: (3, 5),
    5: (4, 6),
    6: (5, 7),
    7: (6, 8),
    8: (7, 9),
    9: (8, 1),
}

# Expected question IDs: enn_1 through enn_9.
_REQUIRED_KEYS = {f"enn_{i}" for i in range(1, 10)}

# Risk tolerance question IDs.
_RISK_KEYS = {"risk_1", "risk_2", "risk_3"}


def _validate_responses(responses: dict[str, int]) -> None:
    """Validate that all 9 items are present and in the 1-5 range."""
    missing = _REQUIRED_KEYS - set(responses.keys())
    if missing:
        raise ValueError(f"Missing Enneagram items: {sorted(missing)}")
    for qid in _REQUIRED_KEYS:
        val = responses[qid]
        if not isinstance(val, int) or val < 1 or val > 5:
            raise ValueError(
                f"Item '{qid}' must be an integer 1-5, got {val!r}"
            )


def score_enneagram(responses: dict[str, int]) -> tuple[int, int]:
    """Score a simplified Enneagram assessment.

    Parameters
    ----------
    responses:
        Mapping of question_id -> raw score (1-5).
        Expected keys: enn_1 through enn_9.

    Returns
    -------
    Tuple of (primary_type, wing) where both are integers 1-9.

    Raises
    ------
    ValueError
        If any items are missing or out of range.
    """
    _validate_responses(responses)

    # Build {type_number: score} mapping.
    type_scores: dict[int, int] = {
        i: responses[f"enn_{i}"] for i in range(1, 10)
    }

    # Primary type: highest score, ties broken by lower type number.
    primary = max(
        range(1, 10),
        key=lambda t: (type_scores[t], -t),
    )

    # Wing: highest-scoring adjacent type, ties broken by lower number.
    adj_left, adj_right = _ADJACENT[primary]
    wing_candidates = sorted(
        [adj_left, adj_right],
        key=lambda t: (type_scores[t], -t),
        reverse=True,
    )
    wing = wing_candidates[0]

    return primary, wing


def _validate_risk_responses(responses: dict[str, int]) -> None:
    """Validate that all 3 risk items are present and in the 1-5 range."""
    missing = _RISK_KEYS - set(responses.keys())
    if missing:
        raise ValueError(f"Missing risk tolerance items: {sorted(missing)}")
    for qid in _RISK_KEYS:
        val = responses[qid]
        if not isinstance(val, int) or val < 1 or val > 5:
            raise ValueError(
                f"Item '{qid}' must be an integer 1-5, got {val!r}"
            )


def score_risk_tolerance(responses: dict[str, int]) -> RiskTolerance:
    """Score financial risk tolerance from three self-report items.

    Parameters
    ----------
    responses:
        Mapping of question_id -> raw score (1-5).
        Required keys: risk_1, risk_2, risk_3.

    Returns
    -------
    RiskTolerance enum member (conservative / moderate / aggressive).

    Raises
    ------
    ValueError
        If any items are missing or out of range.
    """
    _validate_risk_responses(responses)

    avg = sum(responses[k] for k in _RISK_KEYS) / len(_RISK_KEYS)

    if avg < 2.5:
        return RiskTolerance.CONSERVATIVE
    if avg > 3.5:
        return RiskTolerance.AGGRESSIVE
    return RiskTolerance.MODERATE

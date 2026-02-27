"""Attachment style scoring engine.

A simplified 4-question assessment that maps to one of six attachment styles:
  - secure
  - anxious
  - avoidant
  - disorganized
  - anxious-secure  (blended)
  - avoidant-secure  (blended)

Questions (each rated 1-5):
  att_closeness   — Comfort with closeness
  att_abandonment — Worry about abandonment
  att_trust       — Trust in others
  att_self_reliance — Self-reliance preference

Classification algorithm (applied on thresholded dimensions):

  HIGH closeness + LOW abandonment + HIGH trust        → Secure
  HIGH closeness + HIGH abandonment                    → Anxious
  LOW  closeness + LOW abandonment + HIGH self_reliance → Avoidant
  HIGH closeness + HIGH abandonment + LOW trust         → Disorganized

  When scores fall near thresholds, blended types are produced:
    - anxious-secure: moderate closeness/abandonment signals
    - avoidant-secure: moderate closeness/self-reliance signals
"""

from __future__ import annotations

from alchymine.engine.profile import AttachmentStyle

# ── Question IDs ──────────────────────────────────────────────────────

_REQUIRED_KEYS = {"att_closeness", "att_abandonment", "att_trust", "att_self_reliance"}

# Threshold: >=4 is HIGH, <=2 is LOW, 3 is MODERATE.
_HIGH = 4
_LOW = 2


def _validate_responses(responses: dict[str, int]) -> None:
    """Validate that all 4 items are present and in the 1-5 range."""
    missing = _REQUIRED_KEYS - set(responses.keys())
    if missing:
        raise ValueError(f"Missing attachment items: {sorted(missing)}")
    for qid in _REQUIRED_KEYS:
        val = responses[qid]
        if not isinstance(val, int) or val < 1 or val > 5:
            raise ValueError(
                f"Item '{qid}' must be an integer 1-5, got {val!r}"
            )


def score_attachment(responses: dict[str, int]) -> AttachmentStyle:
    """Score attachment style from four self-report items.

    Parameters
    ----------
    responses:
        Mapping of question_id -> raw score (1-5).
        Required keys: att_closeness, att_abandonment, att_trust,
                        att_self_reliance.

    Returns
    -------
    AttachmentStyle enum member.

    Raises
    ------
    ValueError
        If any items are missing or out of range.
    """
    _validate_responses(responses)

    closeness = responses["att_closeness"]
    abandonment = responses["att_abandonment"]
    trust = responses["att_trust"]
    self_reliance = responses["att_self_reliance"]

    high_closeness = closeness >= _HIGH
    low_closeness = closeness <= _LOW
    high_abandonment = abandonment >= _HIGH
    low_abandonment = abandonment <= _LOW
    high_trust = trust >= _HIGH
    low_trust = trust <= _LOW
    high_self_reliance = self_reliance >= _HIGH

    # ── Primary patterns (clear signals) ────────────────────────────

    # Disorganized: high closeness desire + high abandonment fear + low trust
    # Check before Anxious since it is a more specific (narrower) pattern.
    if high_closeness and high_abandonment and low_trust:
        return AttachmentStyle.DISORGANIZED

    # Anxious: high closeness desire + high abandonment fear
    if high_closeness and high_abandonment:
        return AttachmentStyle.ANXIOUS

    # Avoidant: low closeness desire + low abandonment worry + high self-reliance
    if low_closeness and low_abandonment and high_self_reliance:
        return AttachmentStyle.AVOIDANT

    # Secure: high closeness + low abandonment + high trust
    if high_closeness and low_abandonment and high_trust:
        return AttachmentStyle.SECURE

    # ── Blended patterns (moderate / ambiguous signals) ─────────────

    # Anxious-secure blend: moderate-to-high closeness with moderate abandonment
    # Captures people trending anxious but with enough security signals.
    if closeness >= 3 and abandonment >= 3 and trust >= 3:
        return AttachmentStyle.ANXIOUS_SECURE

    # Avoidant-secure blend: moderate-to-low closeness with moderate self-reliance
    if closeness <= 3 and self_reliance >= 3 and abandonment <= 3:
        return AttachmentStyle.AVOIDANT_SECURE

    # ── Fallback ────────────────────────────────────────────────────
    # If none of the patterns match cleanly, use a dimensional approach:
    # Compute an "insecurity" score and pick the closest style.
    anxiety_signal = abandonment - trust  # positive = anxious leaning
    avoidance_signal = self_reliance - closeness  # positive = avoidant leaning

    if anxiety_signal > 0 and avoidance_signal > 0:
        return AttachmentStyle.DISORGANIZED
    if anxiety_signal > 0:
        return AttachmentStyle.ANXIOUS_SECURE
    if avoidance_signal > 0:
        return AttachmentStyle.AVOIDANT_SECURE

    # Default to secure when nothing else matches.
    return AttachmentStyle.SECURE

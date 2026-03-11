"""Tests for profile completeness computation.

These tests exercise ``compute_completeness`` directly (unit) so they don't
require a running database or HTTP client.
"""

from __future__ import annotations

import pytest

from alchymine.api.schemas.completeness import compute_completeness

# ─── Unit tests for compute_completeness ───────────────────────────────


def test_empty_profile_all_incomplete() -> None:
    """None inputs produce all-incomplete sections and 0% overall."""
    result = compute_completeness(None, None)

    assert result["overall_pct"] == 0
    assert result["identity_computed"] is False

    for section_name, _prefix, total in [
        ("big_five", "bf_", 20),
        ("attachment", "att_", 4),
        ("risk_tolerance", "risk_", 3),
        ("enneagram", "enn_", 9),
        ("perspective", "kegan_", 5),
        ("creativity", "guil_", 26),
    ]:
        section = result["sections"][section_name]
        assert section["complete"] is False, f"{section_name} should be incomplete"
        assert section["answered"] == 0
        assert section["total"] == total


def test_big_five_complete_with_20_items() -> None:
    """Exactly 20 bf_* keys marks big_five as complete."""
    responses = {f"bf_{i}": i for i in range(1, 21)}
    result = compute_completeness(responses, None)

    assert result["sections"]["big_five"]["complete"] is True
    assert result["sections"]["big_five"]["answered"] == 20
    assert result["sections"]["big_five"]["total"] == 20


def test_partial_completion() -> None:
    """2 bf_* keys produces answered=2 and complete=False for big_five."""
    responses = {"bf_1": 3, "bf_2": 4}
    result = compute_completeness(responses, None)

    section = result["sections"]["big_five"]
    assert section["complete"] is False
    assert section["answered"] == 2
    assert section["total"] == 20


def test_identity_layer_detected() -> None:
    """A personality key in the identity layer sets identity_computed=True."""
    identity = {"personality": {"openness": 0.8, "conscientiousness": 0.7}}
    result = compute_completeness(None, identity)

    assert result["identity_computed"] is True


def test_identity_not_computed_when_none() -> None:
    """None identity layer produces identity_computed=False."""
    result = compute_completeness(None, None)

    assert result["identity_computed"] is False


def test_identity_not_computed_when_personality_missing() -> None:
    """Identity layer without personality key still yields identity_computed=False."""
    identity = {"numerology": {"life_path": 7}}
    result = compute_completeness(None, identity)

    assert result["identity_computed"] is False


def test_overall_pct_reflects_answered_fraction() -> None:
    """overall_pct is rounded percentage of answered vs total (67 questions)."""
    # Answer all 20 big_five questions only (20/67 ≈ 29.85 → 30)
    responses = {f"bf_{i}": i for i in range(1, 21)}
    result = compute_completeness(responses, None)

    expected_pct = round(20 / 67 * 100)
    assert result["overall_pct"] == expected_pct


def test_overall_pct_capped_at_100() -> None:
    """overall_pct never exceeds 100 even with extra keys."""
    # Feed far more keys than expected — extra keys for each prefix
    responses = {f"bf_{i}": i for i in range(1, 200)}
    result = compute_completeness(responses, None)

    assert result["overall_pct"] <= 100


def test_keys_from_other_sections_dont_pollute() -> None:
    """bf_* keys don't count toward att_* section answered count."""
    responses = {f"bf_{i}": i for i in range(1, 21)}
    result = compute_completeness(responses, None)

    assert result["sections"]["attachment"]["answered"] == 0


@pytest.mark.parametrize(
    "section_name,prefix,total",
    [
        ("big_five", "bf_", 20),
        ("attachment", "att_", 4),
        ("risk_tolerance", "risk_", 3),
        ("enneagram", "enn_", 9),
        ("perspective", "kegan_", 5),
        ("creativity", "guil_", 26),
    ],
)
def test_each_section_completeness(section_name: str, prefix: str, total: int) -> None:
    """Each section is marked complete when its exact number of keyed answers are present."""
    responses = {f"{prefix}{i}": i for i in range(1, total + 1)}
    result = compute_completeness(responses, None)

    section = result["sections"][section_name]
    assert section["complete"] is True
    assert section["answered"] == total
    assert section["total"] == total

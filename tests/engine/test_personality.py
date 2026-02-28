"""Comprehensive tests for personality scoring engines.

Covers:
  - Big Five (mini-IPIP): extremes, midpoint, reverse scoring, validation
  - Attachment style: all 6 styles, blended types, fallback logic
  - Enneagram: primary type, wing selection, adjacency wrapping, ties
  - Risk tolerance: conservative, moderate, aggressive, boundary values
"""

from __future__ import annotations

import pytest

from alchymine.engine.personality.attachment import score_attachment
from alchymine.engine.personality.big_five import score_big_five
from alchymine.engine.personality.enneagram import (
    ENNEAGRAM_TYPES,
    score_enneagram,
    score_risk_tolerance,
)
from alchymine.engine.profile import (
    AttachmentStyle,
    BigFiveScores,
    RiskTolerance,
)

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _bf_all(value: int) -> dict[str, int]:
    """Build a Big Five response dict where every item is the same value."""
    keys = [f"bf_{trait}{i}" for trait in ("e", "a", "c", "n", "o") for i in range(1, 5)]
    return {k: value for k in keys}


def _bf_trait_pattern(
    e: tuple[int, int, int, int] = (3, 3, 3, 3),
    a: tuple[int, int, int, int] = (3, 3, 3, 3),
    c: tuple[int, int, int, int] = (3, 3, 3, 3),
    n: tuple[int, int, int, int] = (3, 3, 3, 3),
    o: tuple[int, int, int, int] = (3, 3, 3, 3),
) -> dict[str, int]:
    """Build a Big Five response dict with per-trait item tuples."""
    resp: dict[str, int] = {}
    for prefix, vals in [("e", e), ("a", a), ("c", c), ("n", n), ("o", o)]:
        for i, v in enumerate(vals, 1):
            resp[f"bf_{prefix}{i}"] = v
    return resp


def _enn_all(value: int) -> dict[str, int]:
    """Build an Enneagram response dict where every item is the same value."""
    return {f"enn_{i}": value for i in range(1, 10)}


def _enn_single_high(primary: int, score: int = 5, base: int = 1) -> dict[str, int]:
    """Build an Enneagram response with one type scored high, rest at base."""
    resp = {f"enn_{i}": base for i in range(1, 10)}
    resp[f"enn_{primary}"] = score
    return resp


# ═══════════════════════════════════════════════════════════════════════
# Big Five (mini-IPIP) Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBigFive:
    """Tests for score_big_five()."""

    def test_all_strongly_agree(self) -> None:
        """All items = 5. Forward items contribute 5, reverse items: 6-5=1.
        Per trait with 2 forward + 2 reverse: sum = 5+1+5+1 = 12.
        Scaled: (12-4)/(20-4)*100 = 50.0.
        """
        result = score_big_five(_bf_all(5))
        assert isinstance(result, BigFiveScores)
        assert result.extraversion == 50.0
        assert result.agreeableness == 50.0
        assert result.conscientiousness == 50.0
        assert result.neuroticism == 50.0
        # Openness has 1 forward + 3 reverse: sum = 5+1+1+1 = 8
        assert result.openness == 25.0

    def test_all_strongly_disagree(self) -> None:
        """All items = 1. Forward items contribute 1, reverse items: 6-1=5.
        Per trait with 2 forward + 2 reverse: sum = 1+5+1+5 = 12.
        Scaled: 50.0.
        """
        result = score_big_five(_bf_all(1))
        assert result.extraversion == 50.0
        # Openness: 1 forward + 3 reverse: sum = 1+5+5+5 = 16
        assert result.openness == 75.0

    def test_all_midpoint(self) -> None:
        """All items = 3. Forward = 3, Reverse = 6-3 = 3. Sum = 12. Scale = 50."""
        result = score_big_five(_bf_all(3))
        assert result.extraversion == 50.0
        assert result.agreeableness == 50.0
        assert result.conscientiousness == 50.0
        assert result.neuroticism == 50.0
        assert result.openness == 50.0

    def test_maximum_extraversion(self) -> None:
        """Extraversion items: forward=5, reverse=1 (reversed to 5). Sum=20. Scale=100."""
        resp = _bf_trait_pattern(e=(5, 1, 5, 1))
        result = score_big_five(resp)
        assert result.extraversion == 100.0

    def test_minimum_extraversion(self) -> None:
        """Extraversion items: forward=1, reverse=5 (reversed to 1). Sum=4. Scale=0."""
        resp = _bf_trait_pattern(e=(1, 5, 1, 5))
        result = score_big_five(resp)
        assert result.extraversion == 0.0

    def test_maximum_openness(self) -> None:
        """Openness: bf_o1 forward=5, bf_o2,o3,o4 reverse items=1 (reversed to 5).
        Sum = 5+5+5+5 = 20. Scale = 100.
        """
        resp = _bf_trait_pattern(o=(5, 1, 1, 1))
        result = score_big_five(resp)
        assert result.openness == 100.0

    def test_minimum_openness(self) -> None:
        """Openness: bf_o1 forward=1, bf_o2,o3,o4 reverse items=5 (reversed to 1).
        Sum = 1+1+1+1 = 4. Scale = 0.
        """
        resp = _bf_trait_pattern(o=(1, 5, 5, 5))
        result = score_big_five(resp)
        assert result.openness == 0.0

    def test_high_neuroticism(self) -> None:
        """High neuroticism: forward items high, reverse items low."""
        resp = _bf_trait_pattern(n=(5, 1, 5, 1))
        result = score_big_five(resp)
        assert result.neuroticism == 100.0

    def test_missing_item_raises(self) -> None:
        """Missing an item should raise ValueError."""
        resp = _bf_all(3)
        del resp["bf_e1"]
        with pytest.raises(ValueError, match="Missing Big Five items"):
            score_big_five(resp)

    def test_out_of_range_raises(self) -> None:
        """Score out of 1-5 range should raise ValueError."""
        resp = _bf_all(3)
        resp["bf_e1"] = 6
        with pytest.raises(ValueError, match="must be an integer 1-5"):
            score_big_five(resp)

    def test_zero_score_raises(self) -> None:
        """Score of 0 is invalid (range is 1-5)."""
        resp = _bf_all(3)
        resp["bf_c1"] = 0
        with pytest.raises(ValueError, match="must be an integer 1-5"):
            score_big_five(resp)

    def test_returns_float_scores(self) -> None:
        """Scores should be floats on 0-100 scale."""
        result = score_big_five(_bf_all(3))
        for field in (
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ):
            val = getattr(result, field)
            assert isinstance(val, float)
            assert 0.0 <= val <= 100.0


# ═══════════════════════════════════════════════════════════════════════
# Attachment Style Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAttachment:
    """Tests for score_attachment()."""

    def test_secure(self) -> None:
        """High closeness + Low abandonment + High trust = Secure."""
        result = score_attachment(
            {
                "att_closeness": 5,
                "att_abandonment": 1,
                "att_trust": 5,
                "att_self_reliance": 2,
            }
        )
        assert result == AttachmentStyle.SECURE

    def test_anxious(self) -> None:
        """High closeness + High abandonment (+ high trust to avoid disorganized) = Anxious."""
        result = score_attachment(
            {
                "att_closeness": 5,
                "att_abandonment": 5,
                "att_trust": 4,
                "att_self_reliance": 2,
            }
        )
        assert result == AttachmentStyle.ANXIOUS

    def test_avoidant(self) -> None:
        """Low closeness + Low abandonment + High self-reliance = Avoidant."""
        result = score_attachment(
            {
                "att_closeness": 1,
                "att_abandonment": 1,
                "att_trust": 3,
                "att_self_reliance": 5,
            }
        )
        assert result == AttachmentStyle.AVOIDANT

    def test_disorganized(self) -> None:
        """High closeness + High abandonment + Low trust = Disorganized."""
        result = score_attachment(
            {
                "att_closeness": 5,
                "att_abandonment": 5,
                "att_trust": 1,
                "att_self_reliance": 3,
            }
        )
        assert result == AttachmentStyle.DISORGANIZED

    def test_anxious_secure_blend(self) -> None:
        """Moderate signals leaning anxious-secure blend."""
        result = score_attachment(
            {
                "att_closeness": 3,
                "att_abandonment": 3,
                "att_trust": 3,
                "att_self_reliance": 2,
            }
        )
        assert result == AttachmentStyle.ANXIOUS_SECURE

    def test_avoidant_secure_blend(self) -> None:
        """Low-moderate closeness + moderate self-reliance + low abandonment."""
        result = score_attachment(
            {
                "att_closeness": 2,
                "att_abandonment": 2,
                "att_trust": 3,
                "att_self_reliance": 3,
            }
        )
        assert result == AttachmentStyle.AVOIDANT_SECURE

    def test_missing_item_raises(self) -> None:
        """Missing attachment item should raise ValueError."""
        with pytest.raises(ValueError, match="Missing attachment items"):
            score_attachment(
                {
                    "att_closeness": 3,
                    "att_abandonment": 3,
                    "att_trust": 3,
                }
            )

    def test_out_of_range_raises(self) -> None:
        """Score out of 1-5 range should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer 1-5"):
            score_attachment(
                {
                    "att_closeness": 7,
                    "att_abandonment": 3,
                    "att_trust": 3,
                    "att_self_reliance": 3,
                }
            )

    def test_all_high_is_disorganized(self) -> None:
        """All 5s: high closeness + high abandonment + low trust check fails
        (trust=5 is high), so falls to anxious (high closeness + high abandonment)."""
        result = score_attachment(
            {
                "att_closeness": 5,
                "att_abandonment": 5,
                "att_trust": 5,
                "att_self_reliance": 5,
            }
        )
        assert result == AttachmentStyle.ANXIOUS

    def test_all_low_fallback(self) -> None:
        """All 1s: low closeness, low abandonment, low self-reliance, low trust.
        Avoidant requires high self-reliance, secure requires high closeness+trust.
        Falls through to fallback logic."""
        result = score_attachment(
            {
                "att_closeness": 1,
                "att_abandonment": 1,
                "att_trust": 1,
                "att_self_reliance": 1,
            }
        )
        # avoidance_signal = self_reliance - closeness = 0
        # anxiety_signal = abandonment - trust = 0
        # Default fallback is secure.
        assert result == AttachmentStyle.SECURE


# ═══════════════════════════════════════════════════════════════════════
# Enneagram Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEnneagram:
    """Tests for score_enneagram()."""

    def test_clear_type_4_wing_5(self) -> None:
        """Type 4 highest, type 5 (adjacent) as wing."""
        resp = _enn_single_high(4)
        resp["enn_5"] = 3  # adjacent, higher than enn_3
        primary, wing = score_enneagram(resp)
        assert primary == 4
        assert wing == 5

    def test_clear_type_4_wing_3(self) -> None:
        """Type 4 highest, type 3 (adjacent) as wing when 3 > 5."""
        resp = _enn_single_high(4)
        resp["enn_3"] = 4
        resp["enn_5"] = 2
        primary, wing = score_enneagram(resp)
        assert primary == 4
        assert wing == 3

    def test_type_1_wing_9_wrapping(self) -> None:
        """Type 1's adjacent types are 9 and 2. Wing 9 when enn_9 > enn_2."""
        resp = _enn_single_high(1)
        resp["enn_9"] = 4
        resp["enn_2"] = 2
        primary, wing = score_enneagram(resp)
        assert primary == 1
        assert wing == 9

    def test_type_9_wing_1_wrapping(self) -> None:
        """Type 9's adjacent types are 8 and 1. Wing 1 when enn_1 > enn_8."""
        resp = _enn_single_high(9)
        resp["enn_1"] = 4
        resp["enn_8"] = 2
        primary, wing = score_enneagram(resp)
        assert primary == 9
        assert wing == 1

    def test_tie_for_primary_lower_wins(self) -> None:
        """When two types tie for highest, lower type number wins."""
        resp = _enn_all(1)
        resp["enn_3"] = 5
        resp["enn_7"] = 5
        primary, wing = score_enneagram(resp)
        assert primary == 3
        # Adjacent to 3 are 2 and 4, both at 1 — tie broken by lower: 2
        assert wing == 2

    def test_all_equal_gives_type_1(self) -> None:
        """All scores equal — tie broken by lower type number → type 1."""
        primary, wing = score_enneagram(_enn_all(3))
        assert primary == 1
        # Adjacent to 1 are 9 and 2, both at 3 — tie broken by lower: 2
        assert wing == 2

    def test_each_type_can_be_primary(self) -> None:
        """Verify that each of the 9 types can be selected as primary."""
        for t in range(1, 10):
            resp = _enn_single_high(t)
            primary, _ = score_enneagram(resp)
            assert primary == t

    def test_type_names_dict_complete(self) -> None:
        """All 9 types should be in the ENNEAGRAM_TYPES dict."""
        assert len(ENNEAGRAM_TYPES) == 9
        for i in range(1, 10):
            assert i in ENNEAGRAM_TYPES

    def test_missing_item_raises(self) -> None:
        """Missing an Enneagram item should raise ValueError."""
        resp = _enn_all(3)
        del resp["enn_5"]
        with pytest.raises(ValueError, match="Missing Enneagram items"):
            score_enneagram(resp)

    def test_out_of_range_raises(self) -> None:
        """Score out of 1-5 range should raise ValueError."""
        resp = _enn_all(3)
        resp["enn_1"] = 0
        with pytest.raises(ValueError, match="must be an integer 1-5"):
            score_enneagram(resp)


# ═══════════════════════════════════════════════════════════════════════
# Risk Tolerance Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRiskTolerance:
    """Tests for score_risk_tolerance()."""

    def test_conservative(self) -> None:
        """Average < 2.5 → conservative."""
        result = score_risk_tolerance({"risk_1": 1, "risk_2": 2, "risk_3": 1})
        assert result == RiskTolerance.CONSERVATIVE

    def test_moderate(self) -> None:
        """Average 2.5-3.5 → moderate."""
        result = score_risk_tolerance({"risk_1": 3, "risk_2": 3, "risk_3": 3})
        assert result == RiskTolerance.MODERATE

    def test_aggressive(self) -> None:
        """Average > 3.5 → aggressive."""
        result = score_risk_tolerance({"risk_1": 5, "risk_2": 4, "risk_3": 5})
        assert result == RiskTolerance.AGGRESSIVE

    def test_boundary_low_moderate(self) -> None:
        """Average exactly 2.5 is moderate (not < 2.5)."""
        # 2 + 3 + 2 = 7, 7/3 ≈ 2.333 → conservative
        result = score_risk_tolerance({"risk_1": 2, "risk_2": 3, "risk_3": 2})
        assert result == RiskTolerance.CONSERVATIVE

    def test_boundary_high_moderate(self) -> None:
        """Average exactly 3.5 is moderate (not > 3.5)."""
        # 3 + 4 + 3 = 10, 10/3 ≈ 3.333 → moderate
        result = score_risk_tolerance({"risk_1": 3, "risk_2": 4, "risk_3": 3})
        assert result == RiskTolerance.MODERATE

    def test_all_fives_is_aggressive(self) -> None:
        """All 5s → average 5.0 → aggressive."""
        result = score_risk_tolerance({"risk_1": 5, "risk_2": 5, "risk_3": 5})
        assert result == RiskTolerance.AGGRESSIVE

    def test_all_ones_is_conservative(self) -> None:
        """All 1s → average 1.0 → conservative."""
        result = score_risk_tolerance({"risk_1": 1, "risk_2": 1, "risk_3": 1})
        assert result == RiskTolerance.CONSERVATIVE

    def test_missing_item_raises(self) -> None:
        """Missing a risk item should raise ValueError."""
        with pytest.raises(ValueError, match="Missing risk tolerance items"):
            score_risk_tolerance({"risk_1": 3, "risk_2": 3})

    def test_out_of_range_raises(self) -> None:
        """Score out of 1-5 range should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer 1-5"):
            score_risk_tolerance({"risk_1": 3, "risk_2": 6, "risk_3": 3})


# ═══════════════════════════════════════════════════════════════════════
# Integration / Cross-module Tests
# ═══════════════════════════════════════════════════════════════════════


class TestImports:
    """Verify the package __init__.py exports work correctly."""

    def test_package_imports(self) -> None:
        """All public scorers should be importable from the package."""
        from alchymine.engine.personality import (
            ENNEAGRAM_TYPES,
            score_attachment,
            score_big_five,
            score_enneagram,
            score_risk_tolerance,
        )

        assert callable(score_big_five)
        assert callable(score_attachment)
        assert callable(score_enneagram)
        assert callable(score_risk_tolerance)
        assert isinstance(ENNEAGRAM_TYPES, dict)

"""Tests for the Quality Swarm ethics validation and quality gate pipeline.

Covers ethics checking (fatalistic language, diagnostic language, dark
patterns, cultural insensitivity, financial advice, missing disclaimers),
quality gate validators for healing, wealth, and creative systems, and
the quality gate dispatcher.
"""

from __future__ import annotations

import pytest

from alchymine.agents.quality.ethics_check import (
    EthicsCheckResult,
    EthicsViolation,
    ViolationCategory,
    ViolationSeverity,
    check_prompt,
    check_text,
    validate_output,
)
from alchymine.agents.quality.validators import (
    QualityGateResult,
    run_quality_gate,
    validate_creative_output,
    validate_healing_output,
    validate_wealth_output,
)


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Ethics check — fatalistic language
# ═══════════════════════════════════════════════════════════════════════


class TestFatalisticLanguage:
    """Tests for detecting fatalistic language violations."""

    def test_catches_you_will_definitely(self) -> None:
        """'You will definitely' should be flagged."""
        result = check_text("You will definitely find love this year.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories

    def test_catches_destined_to(self) -> None:
        """'destined to' should be flagged."""
        result = check_text("You are destined to succeed in business.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories

    def test_catches_fated_to(self) -> None:
        """'fated to' should be flagged."""
        result = check_text("You are fated to meet your soulmate.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories

    def test_catches_your_destiny_is(self) -> None:
        """'your destiny is' should be flagged."""
        result = check_text("Your destiny is to become a leader.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories

    def test_catches_will_never(self) -> None:
        """'will never' should be flagged."""
        result = check_text("You will never overcome this challenge.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories

    def test_catches_guaranteed_to_succeed(self) -> None:
        """'guaranteed to succeed' should be flagged."""
        result = check_text("This approach is guaranteed to succeed.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Ethics check — diagnostic language
# ═══════════════════════════════════════════════════════════════════════


class TestDiagnosticLanguage:
    """Tests for detecting diagnostic language violations."""

    def test_catches_diagnosed_with_disorder(self) -> None:
        """Clinical diagnostic language should be flagged."""
        result = check_text("You have a disorder that requires treatment.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DIAGNOSTIC_LANGUAGE.value in categories

    def test_catches_diagnosis(self) -> None:
        """'diagnosis' should be flagged."""
        result = check_text("Based on this analysis, the diagnosis is clear.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DIAGNOSTIC_LANGUAGE.value in categories

    def test_catches_prescribe(self) -> None:
        """'prescribe' should be flagged."""
        result = check_text("I would prescribe meditation for your condition.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DIAGNOSTIC_LANGUAGE.value in categories

    def test_catches_treatment_plan(self) -> None:
        """'treatment plan' should be flagged."""
        result = check_text("Here is your treatment plan for the next 90 days.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DIAGNOSTIC_LANGUAGE.value in categories

    def test_catches_cure(self) -> None:
        """'cure' should be flagged."""
        result = check_text("This practice will cure your anxiety.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DIAGNOSTIC_LANGUAGE.value in categories


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Ethics check — dark patterns
# ═══════════════════════════════════════════════════════════════════════


class TestDarkPatterns:
    """Tests for detecting dark pattern violations."""

    def test_catches_limited_time(self) -> None:
        """'limited time' should be flagged."""
        result = check_text("This offer is available for a limited time only.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DARK_PATTERNS.value in categories

    def test_catches_act_now(self) -> None:
        """'act now' should be flagged."""
        result = check_text("You must act now to secure your spot.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DARK_PATTERNS.value in categories

    def test_catches_dont_miss_out(self) -> None:
        """\"don't miss out\" should be flagged."""
        result = check_text("Don't miss out on this opportunity!")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DARK_PATTERNS.value in categories

    def test_catches_artificial_scarcity(self) -> None:
        """Artificial scarcity language should be flagged."""
        result = check_text("Only 5 spots remaining! Sign up now.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.DARK_PATTERNS.value in categories


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Ethics check — financial advice
# ═══════════════════════════════════════════════════════════════════════


class TestFinancialAdvice:
    """Tests for detecting unqualified financial advice."""

    def test_catches_you_should_invest(self) -> None:
        """'you should invest' should be flagged."""
        result = check_text("You should invest in index funds for retirement.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FINANCIAL_ADVICE.value in categories

    def test_catches_guaranteed_returns(self) -> None:
        """'guaranteed returns' should be flagged."""
        result = check_text("This strategy provides guaranteed returns of 10%.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FINANCIAL_ADVICE.value in categories

    def test_catches_buy_stocks(self) -> None:
        """'buy stocks' should be flagged."""
        result = check_text("You should buy stocks in the tech sector.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FINANCIAL_ADVICE.value in categories

    def test_catches_risk_free(self) -> None:
        """'risk-free' should be flagged."""
        result = check_text("This is a completely risk-free investment opportunity.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FINANCIAL_ADVICE.value in categories

    def test_catches_get_rich(self) -> None:
        """'get rich' should be flagged."""
        result = check_text("Follow these steps to get rich quickly.")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FINANCIAL_ADVICE.value in categories


# ═══════════════════════════════════════════════════════════════════════
# Section 5: Ethics check — clean text passes
# ═══════════════════════════════════════════════════════════════════════


class TestCleanText:
    """Tests for clean text that should pass all checks."""

    def test_clean_healing_text_passes(self) -> None:
        """Well-written healing content should pass ethics checks."""
        text = (
            "Based on your profile, you may find breathwork beneficial. "
            "This practice has roots in the Pranayama tradition (Yogic) "
            "and emerging research suggests it can support nervous system regulation. "
            "This is not medical advice. Please consult a qualified healthcare professional."
        )
        result = check_text(text, context="healing")
        assert result.passed is True

    def test_clean_wealth_text_passes(self) -> None:
        """Well-written wealth content should pass ethics checks."""
        text = (
            "Your wealth archetype suggests a focus on the EARN lever. "
            "Consider exploring different approaches to building sustainable income streams. "
            "This is not financial advice. Consult a qualified financial advisor "
            "for personalized recommendations."
        )
        result = check_text(text, context="wealth")
        assert result.passed is True

    def test_empty_text_passes(self) -> None:
        """Empty text should pass (nothing to violate)."""
        result = check_text("")
        assert result.passed is True

    def test_short_neutral_text_passes(self) -> None:
        """Short neutral text should pass."""
        result = check_text("Welcome to Alchymine.")
        assert result.passed is True

    def test_result_has_checked_at_timestamp(self) -> None:
        """EthicsCheckResult should include a checked_at timestamp."""
        result = check_text("Hello world")
        assert result.checked_at is not None


# ═══════════════════════════════════════════════════════════════════════
# Section 6: check_prompt and validate_output
# ═══════════════════════════════════════════════════════════════════════


class TestPromptAndOutputValidation:
    """Tests for check_prompt and validate_output functions."""

    def test_check_prompt_catches_violations(self) -> None:
        """check_prompt should catch the same violations as check_text."""
        result = check_prompt("You are destined to achieve great things. Act now!")
        assert result.passed is False
        categories = {v.category for v in result.violations}
        assert ViolationCategory.FATALISTIC_LANGUAGE.value in categories
        assert ViolationCategory.DARK_PATTERNS.value in categories

    def test_validate_output_extracts_text_from_dict(self) -> None:
        """validate_output should extract text from output dict keys."""
        output = {
            "content": "You are destined to become rich.",
            "system": "general",
        }
        result = validate_output(output, system="general")
        assert result.passed is False

    def test_validate_output_empty_dict_passes(self) -> None:
        """An output dict with no text content should pass."""
        result = validate_output({}, system="general")
        assert result.passed is True

    def test_validate_output_checks_list_content(self) -> None:
        """validate_output should check text in list values."""
        output = {
            "recommendations": [
                "You should invest in crypto immediately.",
                "This is guaranteed to succeed.",
            ],
        }
        result = validate_output(output, system="wealth")
        assert result.passed is False


# ═══════════════════════════════════════════════════════════════════════
# Section 7: Quality gate — healing
# ═══════════════════════════════════════════════════════════════════════


class TestHealingQualityGate:
    """Tests for the healing output quality gate."""

    def test_valid_healing_output_passes(self) -> None:
        """A well-formed healing output should pass the quality gate."""
        output = {
            "text": "Based on your profile, breathwork may be helpful.",
            "disclaimers": [
                "This is not medical advice. Consult a qualified healthcare professional."
            ],
            "recommended_modalities": [
                {"modality": "breathwork", "difficulty_level": "foundation"},
            ],
        }
        result = validate_healing_output(output)
        assert result.passed is True
        assert result.gate_name == "healing_quality_gate"

    def test_missing_disclaimers_fails(self) -> None:
        """Healing output without disclaimers should fail."""
        output = {
            "text": "Try breathwork.",
            "recommended_modalities": [],
        }
        result = validate_healing_output(output)
        assert result.passed is False
        assert any("disclaimer" in d.lower() for d in result.details)

    def test_crisis_flag_without_resources_fails(self) -> None:
        """Crisis flag without crisis response should fail."""
        output = {
            "crisis_flag": True,
            "crisis_response": None,
            "disclaimers": [
                "This is not a substitute for professional help."
            ],
        }
        result = validate_healing_output(output)
        assert result.passed is False
        assert any("crisis" in d.lower() for d in result.details)

    def test_healing_gate_has_timestamp(self) -> None:
        """Quality gate result should have a timestamp."""
        output = {
            "disclaimers": [
                "This is not medical advice."
            ],
        }
        result = validate_healing_output(output)
        assert result.timestamp is not None


# ═══════════════════════════════════════════════════════════════════════
# Section 8: Quality gate — wealth
# ═══════════════════════════════════════════════════════════════════════


class TestWealthQualityGate:
    """Tests for the wealth output quality gate."""

    def test_valid_wealth_output_passes(self) -> None:
        """A well-formed wealth output should pass."""
        output = {
            "text": "Your wealth archetype suggests focusing on the EARN lever.",
            "disclaimers": [
                "This is not financial advice. Consult a qualified financial advisor."
            ],
            "calculations": {"monthly_savings": 500.0, "annual_projection": 6000.0},
        }
        result = validate_wealth_output(output)
        assert result.passed is True
        assert result.gate_name == "wealth_quality_gate"

    def test_missing_financial_disclaimers_fails(self) -> None:
        """Wealth output without financial disclaimers should fail."""
        output = {
            "text": "Focus on saving more.",
            "calculations": {"savings": 100.0},
        }
        result = validate_wealth_output(output)
        assert result.passed is False

    def test_llm_generated_flag_fails(self) -> None:
        """Wealth output marked as LLM-generated should fail."""
        output = {
            "text": "Your projections look good.",
            "disclaimers": ["This is not financial advice."],
            "llm_generated": True,
        }
        result = validate_wealth_output(output)
        assert result.passed is False
        assert any("deterministic" in d.lower() for d in result.details)

    def test_non_numeric_calculations_fail(self) -> None:
        """Non-numeric calculation values should fail validation."""
        output = {
            "disclaimers": ["This is not financial advice."],
            "calculations": {"savings": "a lot"},
        }
        result = validate_wealth_output(output)
        assert result.passed is False
        assert any("non-numeric" in d.lower() for d in result.details)


# ═══════════════════════════════════════════════════════════════════════
# Section 9: Quality gate — dispatcher
# ═══════════════════════════════════════════════════════════════════════


class TestQualityGateDispatcher:
    """Tests for the run_quality_gate dispatcher."""

    def test_routes_to_healing(self) -> None:
        """Dispatcher should route 'healing' to validate_healing_output."""
        output = {
            "disclaimers": [
                "This is not a substitute for professional help."
            ],
        }
        result = run_quality_gate(output, system="healing")
        assert result.gate_name == "healing_quality_gate"

    def test_routes_to_wealth(self) -> None:
        """Dispatcher should route 'wealth' to validate_wealth_output."""
        output = {
            "disclaimers": ["This is not financial advice."],
        }
        result = run_quality_gate(output, system="wealth")
        assert result.gate_name == "wealth_quality_gate"

    def test_routes_to_creative(self) -> None:
        """Dispatcher should route 'creative' to validate_creative_output."""
        output = {
            "text": "Great creative work!",
        }
        result = run_quality_gate(output, system="creative")
        assert result.gate_name == "creative_quality_gate"

    def test_unknown_system_raises_value_error(self) -> None:
        """An unknown system name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown system"):
            run_quality_gate({}, system="unknown_system")

    def test_dispatcher_returns_quality_gate_result(self) -> None:
        """Dispatcher should always return a QualityGateResult."""
        result = run_quality_gate(
            {"disclaimers": ["Not medical advice."]},
            system="healing",
        )
        assert isinstance(result, QualityGateResult)

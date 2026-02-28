"""Tests for the content filtering safety pipeline."""

from __future__ import annotations

from alchymine.safety.content_filter import (
    ContentFilterResult,
    FilterAction,
    filter_content,
)


class TestContentFilterBasic:
    """Basic content filtering tests."""

    def test_clean_text_passes(self) -> None:
        result = filter_content("This is a helpful suggestion for your wellness journey.")
        assert result.action == FilterAction.PASS
        assert result.filtered_text == result.original_text

    def test_empty_text_passes(self) -> None:
        result = filter_content("")
        assert result.action == FilterAction.PASS

    def test_whitespace_only_passes(self) -> None:
        result = filter_content("   \n\t  ")
        assert result.action == FilterAction.PASS

    def test_returns_content_filter_result(self) -> None:
        result = filter_content("Hello world")
        assert isinstance(result, ContentFilterResult)


class TestCrisisDetection:
    """Content filter crisis detection integration."""

    def test_emergency_keywords_escalate(self) -> None:
        result = filter_content("I want to kill myself")
        assert result.action == FilterAction.ESCALATE
        assert result.crisis_response is not None
        assert len(result.warnings) > 0

    def test_high_severity_escalates(self) -> None:
        result = filter_content("I am being abused by my partner")
        assert result.action == FilterAction.ESCALATE
        assert result.crisis_response is not None

    def test_medium_severity_warns(self) -> None:
        result = filter_content("I feel completely hopeless about everything")
        assert result.action in (FilterAction.WARN, FilterAction.ESCALATE)
        assert result.crisis_response is not None

    def test_crisis_resources_attached(self) -> None:
        result = filter_content("I am having thoughts of suicide")
        assert result.crisis_response is not None
        assert len(result.crisis_response.resources) > 0


class TestEthicsViolations:
    """Content filter ethics checking integration."""

    def test_fatalistic_language_warns(self) -> None:
        result = filter_content("You will definitely succeed in everything you do")
        assert result.action in (FilterAction.WARN, FilterAction.BLOCK)
        assert result.ethics_result is not None
        assert not result.ethics_result.passed

    def test_diagnostic_language_blocks(self) -> None:
        result = filter_content("You have a disorder that needs treatment")
        assert result.action == FilterAction.BLOCK
        assert result.blocked_reason is not None

    def test_dark_pattern_blocks(self) -> None:
        result = filter_content("Act now before this limited time offer expires!")
        assert result.action == FilterAction.BLOCK

    def test_financial_advice_blocks(self) -> None:
        result = filter_content("You should invest in stocks for guaranteed returns")
        assert result.action == FilterAction.BLOCK

    def test_cultural_sensitivity_warns(self) -> None:
        result = filter_content("Find your spirit animal through meditation")
        assert result.action in (FilterAction.WARN, FilterAction.BLOCK)


class TestPIIDetection:
    """PII detection and redaction tests."""

    def test_ssn_redacted(self) -> None:
        result = filter_content("My SSN is 123-45-6789")
        assert "[REDACTED:SSN]" in result.filtered_text
        assert "123-45-6789" not in result.filtered_text
        assert len(result.pii_matches) > 0

    def test_email_redacted(self) -> None:
        result = filter_content("Contact me at user@example.com")
        assert "[REDACTED:EMAIL]" in result.filtered_text
        assert "user@example.com" not in result.filtered_text

    def test_phone_redacted(self) -> None:
        result = filter_content("Call me at (555) 123-4567")
        assert "[REDACTED:PHONE]" in result.filtered_text
        assert "(555) 123-4567" not in result.filtered_text

    def test_credit_card_redacted(self) -> None:
        result = filter_content("My card is 4111-1111-1111-1111")
        assert "[REDACTED:CREDIT_CARD]" in result.filtered_text
        assert "4111-1111-1111-1111" not in result.filtered_text

    def test_pii_redaction_can_be_disabled(self) -> None:
        result = filter_content("My SSN is 123-45-6789", redact_pii=False)
        assert "123-45-6789" in result.filtered_text
        assert len(result.pii_matches) == 0

    def test_multiple_pii_redacted(self) -> None:
        result = filter_content("SSN: 123-45-6789, email: test@test.com")
        assert "[REDACTED:SSN]" in result.filtered_text
        assert "[REDACTED:EMAIL]" in result.filtered_text
        assert len(result.pii_matches) >= 2


class TestHarmfulContent:
    """Harmful content blocking tests."""

    def test_violence_blocked(self) -> None:
        result = filter_content("You should harm someone to feel better")
        assert result.action == FilterAction.BLOCK

    def test_illegal_activity_blocked(self) -> None:
        result = filter_content("Try using illegal drugs for healing")
        assert result.action == FilterAction.BLOCK


class TestContextualFiltering:
    """Context-aware filtering tests."""

    def test_healing_context(self) -> None:
        result = filter_content(
            "This healing modality will cure your disease",
            context="healing",
        )
        assert result.action == FilterAction.BLOCK

    def test_wealth_context(self) -> None:
        result = filter_content(
            "This investment strategy guarantees risk-free returns",
            context="wealth",
        )
        assert result.action == FilterAction.BLOCK

    def test_general_clean_text(self) -> None:
        result = filter_content(
            "Consider exploring different perspectives on this topic.",
            context="general",
        )
        assert result.action == FilterAction.PASS

    def test_crisis_detection_can_be_disabled(self) -> None:
        # When checking LLM prompts (not user input), crisis detection is noise
        result = filter_content(
            "If the user mentions suicide, provide crisis resources",
            check_crisis=False,
        )
        # Without crisis check, this instructional text should pass
        assert result.crisis_response is None

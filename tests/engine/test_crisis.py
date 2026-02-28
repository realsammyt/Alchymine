"""Tests for the crisis detection and response module.

Covers keyword detection across severity levels, resource completeness,
disclaimer presence, edge cases, and integration with the healing engine.
"""

from __future__ import annotations

from alchymine.engine.healing.crisis import (
    CRISIS_KEYWORDS,
    CrisisResource,
    CrisisSeverity,
    detect_crisis,
    get_crisis_resources,
)

# ═══════════════════════════════════════════════════════════════════════
# Section 1: Crisis keyword list integrity
# ═══════════════════════════════════════════════════════════════════════


class TestCrisisKeywords:
    """Tests for the CRISIS_KEYWORDS list."""

    def test_crisis_keywords_is_nonempty(self) -> None:
        """The crisis keyword list must not be empty."""
        assert len(CRISIS_KEYWORDS) > 0

    def test_crisis_keywords_contains_suicidal(self) -> None:
        """'suicidal' must be in the crisis keyword list."""
        assert "suicidal" in CRISIS_KEYWORDS

    def test_crisis_keywords_contains_self_harm(self) -> None:
        """'self-harm' must be in the crisis keyword list."""
        assert "self-harm" in CRISIS_KEYWORDS

    def test_crisis_keywords_contains_abuse(self) -> None:
        """'abuse' must be in the crisis keyword list."""
        assert "abuse" in CRISIS_KEYWORDS

    def test_crisis_keywords_all_lowercase(self) -> None:
        """All crisis keywords should be lowercase."""
        for keyword in CRISIS_KEYWORDS:
            assert keyword == keyword.lower(), f"Keyword '{keyword}' is not lowercase"


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Crisis detection severity levels
# ═══════════════════════════════════════════════════════════════════════


class TestCrisisDetection:
    """Tests for detect_crisis function."""

    def test_emergency_severity_for_suicidal(self) -> None:
        """Text containing 'suicidal' should trigger EMERGENCY severity."""
        result = detect_crisis("I have been feeling suicidal lately")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_emergency_severity_for_suicide(self) -> None:
        """Text containing 'suicide' should trigger EMERGENCY severity."""
        result = detect_crisis("I keep thinking about suicide")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_emergency_severity_for_self_harm(self) -> None:
        """Text containing 'self-harm' should trigger EMERGENCY severity."""
        result = detect_crisis("I have a history of self-harm")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_emergency_severity_for_kill_myself(self) -> None:
        """Text containing 'kill myself' should trigger EMERGENCY severity."""
        result = detect_crisis("Sometimes I want to kill myself")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_emergency_severity_for_want_to_die(self) -> None:
        """Text containing 'want to die' should trigger EMERGENCY severity."""
        result = detect_crisis("I just want to die")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_high_severity_for_abuse(self) -> None:
        """Text containing 'abuse' should trigger HIGH severity."""
        result = detect_crisis("I experienced abuse growing up")
        assert result is not None
        assert result.severity == CrisisSeverity.HIGH

    def test_high_severity_for_domestic_violence(self) -> None:
        """Text containing 'domestic violence' should trigger HIGH severity."""
        result = detect_crisis("I am in a domestic violence situation")
        assert result is not None
        assert result.severity == CrisisSeverity.HIGH

    def test_medium_severity_for_hopeless(self) -> None:
        """Text containing 'hopeless' should trigger MEDIUM severity."""
        result = detect_crisis("Everything feels hopeless right now")
        assert result is not None
        assert result.severity == CrisisSeverity.MEDIUM

    def test_medium_severity_for_panic_attack(self) -> None:
        """Text containing 'panic attack' should trigger MEDIUM severity."""
        result = detect_crisis("I've been having a panic attack every day")
        assert result is not None
        assert result.severity == CrisisSeverity.MEDIUM

    def test_medium_severity_for_substance_abuse(self) -> None:
        """Text mentioning 'substance abuse' should trigger appropriately."""
        result = detect_crisis("I am struggling with substance abuse")
        assert result is not None
        # 'substance abuse' contains 'abuse' (HIGH) and 'substance abuse' (MEDIUM)
        # The highest severity should take precedence
        assert result.severity in (CrisisSeverity.HIGH, CrisisSeverity.MEDIUM)

    def test_non_crisis_text_returns_none(self) -> None:
        """Normal text without crisis keywords should return None."""
        result = detect_crisis("I am interested in learning about meditation and breathwork")
        assert result is None

    def test_empty_text_returns_none(self) -> None:
        """Empty text should return None."""
        result = detect_crisis("")
        assert result is None

    def test_whitespace_only_returns_none(self) -> None:
        """Whitespace-only text should return None."""
        result = detect_crisis("   \n\t  ")
        assert result is None

    def test_case_insensitive_detection(self) -> None:
        """Crisis detection should be case-insensitive."""
        result = detect_crisis("I have been SUICIDAL")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_highest_severity_wins_with_mixed_keywords(self) -> None:
        """When multiple severities are matched, the highest should win."""
        result = detect_crisis("I feel hopeless and have been thinking about suicide")
        assert result is not None
        assert result.severity == CrisisSeverity.EMERGENCY

    def test_matched_keywords_are_returned(self) -> None:
        """The response should include the matched keywords."""
        result = detect_crisis("I am suicidal and feeling hopeless")
        assert result is not None
        assert len(result.matched_keywords) >= 2
        assert "suicidal" in result.matched_keywords


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Crisis resources
# ═══════════════════════════════════════════════════════════════════════


class TestCrisisResources:
    """Tests for crisis resources and the CrisisResponse."""

    def test_get_crisis_resources_returns_list(self) -> None:
        """get_crisis_resources should return a non-empty list."""
        resources = get_crisis_resources()
        assert isinstance(resources, list)
        assert len(resources) > 0

    def test_resources_include_988_lifeline(self) -> None:
        """Resources must include the 988 Suicide & Crisis Lifeline."""
        resources = get_crisis_resources()
        names = [r.name for r in resources]
        assert any("988" in name for name in names)

    def test_resources_include_crisis_text_line(self) -> None:
        """Resources must include the Crisis Text Line."""
        resources = get_crisis_resources()
        names = [r.name for r in resources]
        assert any("Crisis Text" in name for name in names)

    def test_resources_include_hotline_numbers(self) -> None:
        """All resources must have a contact field."""
        resources = get_crisis_resources()
        for resource in resources:
            assert isinstance(resource, CrisisResource)
            assert len(resource.contact) > 0

    def test_crisis_response_includes_resources(self) -> None:
        """A CrisisResponse from detection must include resources."""
        result = detect_crisis("I am suicidal")
        assert result is not None
        assert len(result.resources) > 0

    def test_crisis_response_includes_disclaimer(self) -> None:
        """A CrisisResponse must always include the standard disclaimer."""
        result = detect_crisis("I am suicidal")
        assert result is not None
        assert len(result.disclaimers) > 0
        disclaimer_text = " ".join(result.disclaimers).lower()
        assert "not a substitute for professional help" in disclaimer_text

    def test_crisis_response_resources_include_emergency_services(self) -> None:
        """Crisis resources must include emergency services (911)."""
        resources = get_crisis_resources()
        contacts = [r.contact for r in resources]
        assert any("911" in contact for contact in contacts)

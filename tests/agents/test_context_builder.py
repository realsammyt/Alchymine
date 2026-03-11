"""Unit tests for the Growth Assistant context builder.

Tests the build_user_context() function that extracts profile data
from report result dicts and formats it as LLM context strings.
"""

from __future__ import annotations

from alchymine.agents.growth.context_builder import build_user_context


class TestBuildUserContext:
    def test_returns_empty_string_for_none(self) -> None:
        assert build_user_context(None) == ""

    def test_returns_header_only_for_empty_dict(self) -> None:
        result = build_user_context({})
        assert result == ""

    def test_returns_header_for_empty_profile_summary(self) -> None:
        result = build_user_context({"profile_summary": {"identity": {}}})
        assert result == "[User Profile Summary]"

    def test_includes_numerology(self) -> None:
        result = build_user_context(
            {
                "profile_summary": {
                    "identity": {
                        "numerology": {"life_path": 7, "expression": 3},
                    }
                }
            }
        )
        assert "Life Path: 7" in result
        assert "Expression: 3" in result

    def test_includes_astrology(self) -> None:
        result = build_user_context(
            {
                "profile_summary": {
                    "identity": {
                        "astrology": {"sun_sign": "Scorpio", "moon_sign": "Pisces"},
                    }
                }
            }
        )
        assert "Scorpio" in result
        assert "Pisces" in result

    def test_includes_archetype(self) -> None:
        result = build_user_context(
            {
                "profile_summary": {
                    "identity": {
                        "archetype": {"primary": "Sage"},
                    }
                }
            }
        )
        assert "Sage" in result

    def test_includes_big_five(self) -> None:
        result = build_user_context(
            {
                "profile_summary": {
                    "identity": {
                        "personality": {
                            "big_five": {
                                "openness": 82,
                                "conscientiousness": 64,
                                "extraversion": 45,
                            }
                        },
                    }
                }
            }
        )
        assert "O=82" in result
        assert "C=64" in result
        assert "E=45" in result

    def test_full_profile(self) -> None:
        result = build_user_context(
            {
                "profile_summary": {
                    "identity": {
                        "numerology": {"life_path": 7, "expression": 3},
                        "astrology": {"sun_sign": "Scorpio", "moon_sign": "Pisces"},
                        "archetype": {"primary": "Sage"},
                        "personality": {
                            "big_five": {
                                "openness": 82,
                                "conscientiousness": 64,
                                "extraversion": 45,
                            }
                        },
                    }
                }
            }
        )
        assert "Life Path: 7" in result
        assert "Scorpio" in result
        assert "Sage" in result
        assert "O=82" in result

    def test_starts_with_header(self) -> None:
        result = build_user_context(
            {"profile_summary": {"identity": {"numerology": {"life_path": 1, "expression": 1}}}}
        )
        assert result.startswith("[User Profile Summary]")

    def test_missing_fields_skipped_gracefully(self) -> None:
        result = build_user_context({"profile_summary": {"identity": {}}})
        assert "[User Profile Summary]" in result
        assert "Life Path" not in result
        assert "Sun:" not in result

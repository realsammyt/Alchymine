"""Tests for Pythagorean and Chaldean numerology engines."""

from __future__ import annotations

from datetime import date

import pytest

from alchymine.engine.numerology import (
    calculate_pythagorean_profile,
    chaldean_name_number,
    chaldean_name_number_full,
    expression,
    is_master_number,
    life_path,
    maturity,
    normalize_name,
    personal_month,
    personal_year,
    personality,
    reduce_to_single_digit,
    soul_urge,
)
from alchymine.engine.numerology.common import digit_sum, extract_consonants, extract_vowels


# ═══════════════════════════════════════════════════════════════════════
# Common utilities
# ═══════════════════════════════════════════════════════════════════════


class TestCommon:
    """Tests for shared numerology utilities."""

    def test_normalize_name_basic(self) -> None:
        assert normalize_name("John Smith") == "JOHN SMITH"

    def test_normalize_name_accents(self) -> None:
        assert normalize_name("José García") == "JOSE GARCIA"

    def test_normalize_name_hyphens(self) -> None:
        assert normalize_name("Jean-Pierre") == "JEANPIERRE"

    def test_normalize_name_strips_whitespace(self) -> None:
        assert normalize_name("  Maria del Carmen  ") == "MARIA DEL CARMEN"

    def test_reduce_to_single_digit_basic(self) -> None:
        assert reduce_to_single_digit(38) == 11  # 3+8=11, preserved as master number

    def test_reduce_preserves_master_11(self) -> None:
        assert reduce_to_single_digit(29) == 11  # 2+9=11, master

    def test_reduce_preserves_master_22(self) -> None:
        assert reduce_to_single_digit(22) == 22

    def test_reduce_preserves_master_33(self) -> None:
        assert reduce_to_single_digit(33) == 33

    def test_reduce_no_preserve_master(self) -> None:
        assert reduce_to_single_digit(29, preserve_master=False) == 2

    def test_digit_sum(self) -> None:
        assert digit_sum(1990) == 19
        assert digit_sum(29) == 11
        assert digit_sum(5) == 5

    def test_is_master_number(self) -> None:
        assert is_master_number(11) is True
        assert is_master_number(22) is True
        assert is_master_number(33) is True
        assert is_master_number(7) is False
        assert is_master_number(44) is False

    def test_extract_vowels(self) -> None:
        assert extract_vowels("JOHN SMITH") == "OI"

    def test_extract_vowels_y_as_vowel(self) -> None:
        result = extract_vowels("YOLANDA", y_as_vowel=True)
        assert "Y" in result

    def test_extract_consonants(self) -> None:
        result = extract_consonants("JOHN SMITH")
        assert "O" not in result
        assert "J" in result


# ═══════════════════════════════════════════════════════════════════════
# Pythagorean engine
# ═══════════════════════════════════════════════════════════════════════


class TestPythagorean:
    """Tests for Pythagorean numerology calculations."""

    def test_life_path_basic(self) -> None:
        """March 15, 1990: 3 + 6 + 19->10->1 = 10 -> 1."""
        result = life_path(date(1990, 3, 15))
        assert result == 1

    def test_life_path_master_number(self) -> None:
        """Nov 11, 2009: 2 + 2 + 11 = 15 -> 6. Not master."""
        result = life_path(date(2009, 11, 11))
        assert 1 <= result <= 33

    def test_expression_john_smith(self) -> None:
        result = expression("John Smith")
        assert result == 8

    def test_soul_urge_john_smith(self) -> None:
        result = soul_urge("John Smith")
        assert result == 6

    def test_personality_john_smith(self) -> None:
        result = personality("John Smith")
        assert result == 11  # master number!

    def test_personal_year_deterministic(self) -> None:
        result = personal_year(date(1990, 3, 15), current_year=2026)
        assert result == 1

    def test_personal_month_deterministic(self) -> None:
        result = personal_month(date(1990, 3, 15), current_year=2026, current_month=2)
        assert result == 3

    def test_maturity_john_smith(self) -> None:
        result = maturity(date(1990, 3, 15), "John Smith")
        assert result == 9  # life_path(1) + expression(8) = 9

    def test_full_profile_returns_dataclass(self) -> None:
        profile = calculate_pythagorean_profile(
            "Maria Elena Vasquez",
            date(1992, 3, 15),
            current_year=2026,
            current_month=2,
        )
        assert hasattr(profile, "life_path")
        assert hasattr(profile, "expression")
        assert hasattr(profile, "soul_urge")
        assert hasattr(profile, "personality")
        assert hasattr(profile, "personal_year")
        assert hasattr(profile, "personal_month")
        assert hasattr(profile, "maturity")
        assert hasattr(profile, "is_master_number")

    def test_full_profile_maria(self) -> None:
        """Maria Elena Vasquez, born 1992-03-15."""
        profile = calculate_pythagorean_profile(
            "Maria Elena Vasquez",
            date(1992, 3, 15),
            current_year=2026,
            current_month=2,
        )
        # Life path: 1992-03-15 → 3 + 6 + 21→3 = 12→3
        assert profile.life_path == 3
        assert isinstance(profile.is_master_number, bool)

    def test_all_results_in_valid_range(self) -> None:
        """All numbers should be 1-33 (accounting for master numbers)."""
        profile = calculate_pythagorean_profile(
            "Test User Name",
            date(1985, 7, 22),
            current_year=2026,
            current_month=1,
        )
        for field in ("life_path", "expression", "soul_urge", "personality", "maturity"):
            val = getattr(profile, field)
            assert 1 <= val <= 33, f"{field}={val} out of range"
        for field in ("personal_year", "personal_month"):
            val = getattr(profile, field)
            assert 1 <= val <= 9, f"{field}={val} out of range"


# ═══════════════════════════════════════════════════════════════════════
# Chaldean engine
# ═══════════════════════════════════════════════════════════════════════


class TestChaldean:
    """Tests for Chaldean numerology calculations."""

    def test_name_number_john_smith(self) -> None:
        result = chaldean_name_number("John Smith")
        assert result == 8

    def test_name_number_full_with_compound(self) -> None:
        result = chaldean_name_number_full("John Smith")
        assert result.name_number == 8
        assert result.compound_number == 35
        assert result.compound_meaning == "Inventiveness"

    def test_single_digit_no_compound(self) -> None:
        """Short names may sum to a single digit — no compound."""
        result = chaldean_name_number_full("Al")
        assert result.compound_number is None
        assert result.compound_meaning is None

    def test_chaldean_has_no_nine(self) -> None:
        """No letter should map to 9 in Chaldean system."""
        from alchymine.engine.numerology.chaldean import CHALDEAN_MAP

        assert 9 not in CHALDEAN_MAP.values()

    def test_deterministic(self) -> None:
        """Same input always produces same output."""
        a = chaldean_name_number("Maria Elena Vasquez")
        b = chaldean_name_number("Maria Elena Vasquez")
        assert a == b

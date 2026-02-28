"""Comprehensive tests for Pythagorean and Chaldean numerology engines.

All expected values are pre-computed by hand and cross-verified against
the engine outputs.  Every test is deterministic — no randomness.
"""

from __future__ import annotations

from datetime import date

import pytest

from alchymine.engine.numerology import (
    ChaldeanResult,
    PythagoreanProfile,
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
from alchymine.engine.numerology.chaldean import (
    CHALDEAN_MAP,
    COMPOUND_MEANINGS,
)
from alchymine.engine.numerology.chaldean import (
    letter_value as chal_letter_value,
)
from alchymine.engine.numerology.chaldean import (
    sum_letters as chal_sum_letters,
)
from alchymine.engine.numerology.common import (
    digit_sum,
    extract_consonants,
    extract_vowels,
)
from alchymine.engine.numerology.pythagorean import (
    PYTHAGOREAN_MAP,
)
from alchymine.engine.numerology.pythagorean import (
    letter_value as pyth_letter_value,
)
from alchymine.engine.numerology.pythagorean import (
    sum_letters as pyth_sum_letters,
)

# ═══════════════════════════════════════════════════════════════════════════
# 1. Shared utilities (common.py)
# ═══════════════════════════════════════════════════════════════════════════


class TestNormalizeName:
    """Tests for name normalization."""

    def test_basic_name(self) -> None:
        assert normalize_name("John Smith") == "JOHN SMITH"

    def test_preserves_inner_spaces(self) -> None:
        assert normalize_name("Maria del Carmen") == "MARIA DEL CARMEN"

    def test_strips_leading_trailing_whitespace(self) -> None:
        assert normalize_name("  Alice   ") == "ALICE"

    def test_removes_hyphens(self) -> None:
        assert normalize_name("Jean-Pierre") == "JEANPIERRE"

    def test_removes_accents_acute(self) -> None:
        assert normalize_name("Jos\u00e9 Garc\u00eda") == "JOSE GARCIA"

    def test_removes_accents_cedilla(self) -> None:
        assert normalize_name("Fran\u00e7ois") == "FRANCOIS"

    def test_removes_accents_umlaut(self) -> None:
        assert normalize_name("M\u00fcller") == "MULLER"

    def test_removes_apostrophe(self) -> None:
        assert normalize_name("O'Connor III") == "OCONNOR III"

    def test_mixed_case_uppercased(self) -> None:
        assert normalize_name("jOhN sMiTh") == "JOHN SMITH"


class TestReduceToSingleDigit:
    """Tests for digit reduction with master-number support."""

    def test_single_digits_unchanged(self) -> None:
        for n in range(1, 10):
            assert reduce_to_single_digit(n) == n

    def test_38_reduces_to_master_11(self) -> None:
        # 3+8=11, master preserved
        assert reduce_to_single_digit(38) == 11

    def test_29_reduces_to_master_11(self) -> None:
        assert reduce_to_single_digit(29) == 11

    def test_master_11_preserved(self) -> None:
        assert reduce_to_single_digit(11) == 11

    def test_master_22_preserved(self) -> None:
        assert reduce_to_single_digit(22) == 22

    def test_master_33_preserved(self) -> None:
        assert reduce_to_single_digit(33) == 33

    def test_master_not_preserved_when_disabled(self) -> None:
        assert reduce_to_single_digit(11, preserve_master=False) == 2
        assert reduce_to_single_digit(22, preserve_master=False) == 4
        assert reduce_to_single_digit(33, preserve_master=False) == 6

    def test_large_number_1990(self) -> None:
        # 1990 -> 19 -> 10 -> 1
        assert reduce_to_single_digit(1990) == 1

    def test_large_number_2026(self) -> None:
        # 2026 -> 10 -> 1
        assert reduce_to_single_digit(2026) == 1


class TestDigitSum:
    """Tests for the digit_sum helper."""

    def test_single_digit(self) -> None:
        assert digit_sum(7) == 7

    def test_two_digits(self) -> None:
        assert digit_sum(29) == 11

    def test_four_digits(self) -> None:
        assert digit_sum(1990) == 19

    def test_zero(self) -> None:
        assert digit_sum(0) == 0


class TestMasterNumber:
    """Tests for master number detection."""

    def test_master_numbers_true(self) -> None:
        assert is_master_number(11) is True
        assert is_master_number(22) is True
        assert is_master_number(33) is True

    def test_non_master_numbers_false(self) -> None:
        assert is_master_number(1) is False
        assert is_master_number(9) is False
        assert is_master_number(44) is False
        assert is_master_number(10) is False


class TestExtractVowelsConsonants:
    """Tests for vowel/consonant extraction."""

    def test_vowels_basic(self) -> None:
        assert extract_vowels("JOHN SMITH") == "OI"

    def test_consonants_basic(self) -> None:
        assert extract_consonants("JOHN SMITH") == "JHNSMTH"

    def test_y_as_vowel_extraction(self) -> None:
        assert extract_vowels("YOLANDA", y_as_vowel=True) == "YOAA"

    def test_y_default_is_consonant(self) -> None:
        assert "Y" not in extract_vowels("YOLANDA")
        assert "Y" in extract_consonants("YOLANDA")

    def test_y_as_vowel_excluded_from_consonants(self) -> None:
        assert "Y" not in extract_consonants("YOLANDA", y_as_vowel=True)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Pythagorean engine — letter mapping
# ═══════════════════════════════════════════════════════════════════════════


class TestPythagoreanLetterMapping:
    """Verify the Pythagorean A=1..I=9, J=1..R=9, S=1..Z=8 mapping."""

    def test_first_row_a_through_i(self) -> None:
        expected = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9}
        for letter, value in expected.items():
            assert pyth_letter_value(letter) == value

    def test_second_row_j_through_r(self) -> None:
        expected = {"J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "O": 6, "P": 7, "Q": 8, "R": 9}
        for letter, value in expected.items():
            assert pyth_letter_value(letter) == value

    def test_third_row_s_through_z(self) -> None:
        expected = {"S": 1, "T": 2, "U": 3, "V": 4, "W": 5, "X": 6, "Y": 7, "Z": 8}
        for letter, value in expected.items():
            assert pyth_letter_value(letter) == value

    def test_mapping_has_26_entries(self) -> None:
        assert len(PYTHAGOREAN_MAP) == 26

    def test_all_values_in_range_1_to_9(self) -> None:
        assert all(1 <= v <= 9 for v in PYTHAGOREAN_MAP.values())

    def test_sum_letters_john_smith(self) -> None:
        # J=1 O=6 H=8 N=5 S=1 M=4 I=9 T=2 H=8 => 44
        assert pyth_sum_letters("JOHN SMITH") == 44

    def test_sum_letters_empty_string(self) -> None:
        assert pyth_sum_letters("") == 0

    def test_sum_letters_spaces_only(self) -> None:
        assert pyth_sum_letters("   ") == 0


# ═══════════════════════════════════════════════════════════════════════════
# 3. Pythagorean — Life Path
# ═══════════════════════════════════════════════════════════════════════════


class TestLifePath:
    """Tests for Life Path calculation from birth dates."""

    def test_john_smith_1990_03_15(self) -> None:
        # month=3, day=15->6, year=1990->1  => 3+6+1=10 -> 1
        assert life_path(date(1990, 3, 15)) == 1

    def test_master_11(self) -> None:
        # month=11(master), day=29->11(master), year=2005->7
        # total = 11+11+7 = 29 -> 11 (master preserved)
        assert life_path(date(2005, 11, 29)) == 11

    def test_master_22(self) -> None:
        # month=8, day=7, year=1987->25->7
        # total = 8+7+7 = 22 (master preserved)
        assert life_path(date(1987, 8, 7)) == 22

    def test_master_33(self) -> None:
        # month=9, day=22(master), year=2000->2
        # total = 9+22+2 = 33 (master preserved)
        assert life_path(date(2000, 9, 22)) == 33

    def test_master_33_from_triple_11(self) -> None:
        # month=11(master), day=11(master), year=2009->11(master)
        # total = 11+11+11 = 33 (master preserved)
        assert life_path(date(2009, 11, 11)) == 33

    def test_simple_single_digit_result(self) -> None:
        # month=1, day=1, year=2000->2 => 1+1+2=4
        assert life_path(date(2000, 1, 1)) == 4

    def test_day_requiring_reduction(self) -> None:
        # month=7, day=28->10->1, year=1985->23->5
        # total = 7+1+5 = 13 -> 4
        assert life_path(date(1985, 7, 28)) == 4


# ═══════════════════════════════════════════════════════════════════════════
# 4. Pythagorean — Name-based numbers
# ═══════════════════════════════════════════════════════════════════════════


class TestExpression:
    """Tests for Expression/Destiny number."""

    def test_john_smith(self) -> None:
        assert expression("John Smith") == 8

    def test_alice_johnson(self) -> None:
        assert expression("Alice Johnson") == 8

    def test_robert_brown(self) -> None:
        assert expression("Robert Brown") == 6

    def test_case_insensitive(self) -> None:
        assert expression("JOHN SMITH") == expression("john smith") == expression("John Smith")

    def test_single_name(self) -> None:
        assert expression("Madonna") == 8

    def test_rene_descartes(self) -> None:
        assert expression("Rene Descartes") == 1

    def test_mary_jane_watson(self) -> None:
        assert expression("Mary Jane Watson") == 8


class TestSoulUrge:
    """Tests for Soul Urge / Heart's Desire number (vowels only)."""

    def test_john_smith(self) -> None:
        # Vowels: O=6, I=9 => 15 -> 6
        assert soul_urge("John Smith") == 6

    def test_alice_johnson(self) -> None:
        assert soul_urge("Alice Johnson") == 9

    def test_mary_jane_watson(self) -> None:
        assert soul_urge("Mary Jane Watson") == 5

    def test_y_as_vowel_changes_result(self) -> None:
        default_val = soul_urge("Yolanda Torres")
        y_vowel_val = soul_urge("Yolanda Torres", y_as_vowel=True)
        assert default_val == 1
        assert y_vowel_val == 8
        assert default_val != y_vowel_val


class TestPersonality:
    """Tests for Personality / Outer number (consonants only)."""

    def test_john_smith_master_11(self) -> None:
        # Consonants: J=1 H=8 N=5 S=1 M=4 T=2 H=8 => 29 -> 11 (master)
        assert personality("John Smith") == 11

    def test_mary_jane_watson(self) -> None:
        assert personality("Mary Jane Watson") == 3

    def test_robert_brown(self) -> None:
        assert personality("Robert Brown") == 7

    def test_y_as_vowel_changes_personality(self) -> None:
        default_val = personality("Yolanda Torres")
        y_vowel_val = personality("Yolanda Torres", y_as_vowel=True)
        assert default_val == 4
        assert y_vowel_val == 33  # master number!


# ═══════════════════════════════════════════════════════════════════════════
# 5. Pythagorean — Time-cycle numbers
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonalYear:
    """Tests for Personal Year cycle."""

    @pytest.mark.parametrize(
        "year, expected",
        [
            (2024, 8),
            (2025, 9),
            (2026, 1),
            (2027, 2),
        ],
    )
    def test_john_smith_personal_years(self, year: int, expected: int) -> None:
        assert personal_year(date(1990, 3, 15), current_year=year) == expected

    def test_no_master_number_preservation(self) -> None:
        # Personal Year does NOT preserve master numbers.
        # 1990-03-15 in 2027: 3+15+2027=2045 -> 11 -> 2 (reduced, not kept as 11)
        assert personal_year(date(1990, 3, 15), current_year=2027) == 2


class TestPersonalMonth:
    """Tests for Personal Month cycle."""

    def test_john_smith_february_2026(self) -> None:
        # PY=1, month=2 -> 3
        assert personal_month(date(1990, 3, 15), current_year=2026, current_month=2) == 3

    @pytest.mark.parametrize(
        "month, expected",
        [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 8),
            (8, 9),
            (9, 1),
            (10, 2),
            (11, 3),
            (12, 4),
        ],
    )
    def test_john_smith_2026_all_twelve_months(self, month: int, expected: int) -> None:
        result = personal_month(date(1990, 3, 15), current_year=2026, current_month=month)
        assert result == expected


class TestMaturity:
    """Tests for Maturity Number (Life Path + Expression, reduced)."""

    def test_john_smith(self) -> None:
        # life_path=1 + expression=8 = 9
        assert maturity(date(1990, 3, 15), "John Smith") == 9

    def test_rene_descartes(self) -> None:
        # life_path=1 + expression=1 = 2
        assert maturity(date(1596, 3, 31), "Rene Descartes") == 2


# ═══════════════════════════════════════════════════════════════════════════
# 6. Pythagorean — Full profile
# ═══════════════════════════════════════════════════════════════════════════


class TestFullPythagoreanProfile:
    """Tests for the complete Pythagorean profile calculation."""

    def test_john_smith_all_fields(self) -> None:
        p = calculate_pythagorean_profile(
            "John Smith", date(1990, 3, 15), current_year=2026, current_month=2
        )
        assert isinstance(p, PythagoreanProfile)
        assert p.life_path == 1
        assert p.expression == 8
        assert p.soul_urge == 6
        assert p.personality == 11
        assert p.personal_year == 1
        assert p.personal_month == 3
        assert p.maturity == 9
        assert p.is_master_number is False

    def test_master_number_flag_true_for_lp_11(self) -> None:
        p = calculate_pythagorean_profile(
            "Test Name", date(2005, 11, 29), current_year=2026, current_month=1
        )
        assert p.is_master_number is True
        assert p.life_path == 11

    def test_master_number_flag_false_for_lp_1(self) -> None:
        p = calculate_pythagorean_profile(
            "John Smith", date(1990, 3, 15), current_year=2026, current_month=2
        )
        assert p.is_master_number is False

    def test_rene_descartes_profile(self) -> None:
        p = calculate_pythagorean_profile(
            "Rene Descartes", date(1596, 3, 31), current_year=2026, current_month=2
        )
        assert p.life_path == 1
        assert p.expression == 1
        assert p.soul_urge == 3
        assert p.personality == 7
        assert p.maturity == 2

    def test_hyphenated_name_mary_jane_watson(self) -> None:
        p = calculate_pythagorean_profile(
            "Mary-Jane Watson", date(1985, 7, 22), current_year=2026, current_month=2
        )
        assert p.life_path == 7
        assert p.expression == 8
        assert p.soul_urge == 5
        assert p.personality == 3
        assert p.maturity == 6

    def test_maria_elena_vasquez_profile(self) -> None:
        p = calculate_pythagorean_profile(
            "Maria Elena Vasquez", date(1992, 3, 15), current_year=2026, current_month=2
        )
        assert p.life_path == 3
        assert p.expression == 1
        assert p.soul_urge == 4
        assert p.personality == 6
        assert p.maturity == 4
        assert p.is_master_number is False

    def test_profile_has_all_expected_attributes(self) -> None:
        p = calculate_pythagorean_profile(
            "Maria Elena Vasquez", date(1992, 3, 15), current_year=2026, current_month=2
        )
        for attr in (
            "life_path",
            "expression",
            "soul_urge",
            "personality",
            "personal_year",
            "personal_month",
            "maturity",
            "is_master_number",
        ):
            assert hasattr(p, attr), f"Missing attribute: {attr}"

    def test_frozen_dataclass_prevents_mutation(self) -> None:
        p = calculate_pythagorean_profile(
            "John Smith", date(1990, 3, 15), current_year=2026, current_month=2
        )
        with pytest.raises(AttributeError):
            p.life_path = 99  # type: ignore[misc]

    def test_y_as_vowel_changes_soul_and_personality_only(self) -> None:
        p_default = calculate_pythagorean_profile(
            "Yolanda Torres", date(1990, 1, 1), current_year=2026, current_month=1
        )
        p_y_vowel = calculate_pythagorean_profile(
            "Yolanda Torres",
            date(1990, 1, 1),
            current_year=2026,
            current_month=1,
            y_as_vowel=True,
        )
        assert p_default.soul_urge != p_y_vowel.soul_urge
        assert p_default.personality != p_y_vowel.personality
        # These should remain identical regardless of Y treatment
        assert p_default.life_path == p_y_vowel.life_path
        assert p_default.expression == p_y_vowel.expression
        assert p_default.personal_year == p_y_vowel.personal_year

    def test_all_values_in_valid_range(self) -> None:
        p = calculate_pythagorean_profile(
            "Alice Johnson", date(1992, 6, 14), current_year=2026, current_month=6
        )
        for attr in ("life_path", "expression", "soul_urge", "personality", "maturity"):
            val = getattr(p, attr)
            assert (1 <= val <= 9) or val in (11, 22, 33), f"{attr}={val} out of range"
        assert 1 <= p.personal_year <= 9
        assert 1 <= p.personal_month <= 9


# ═══════════════════════════════════════════════════════════════════════════
# 7. Chaldean engine — letter mapping
# ═══════════════════════════════════════════════════════════════════════════


class TestChaldeanLetterMapping:
    """Verify the Chaldean letter mapping (9 is sacred, not assigned)."""

    def test_no_letter_maps_to_9(self) -> None:
        assert 9 not in CHALDEAN_MAP.values()

    def test_mapping_has_26_entries(self) -> None:
        assert len(CHALDEAN_MAP) == 26

    def test_all_specific_values(self) -> None:
        expected = {
            "A": 1,
            "B": 2,
            "C": 3,
            "D": 4,
            "E": 5,
            "F": 8,
            "G": 3,
            "H": 5,
            "I": 1,
            "J": 1,
            "K": 2,
            "L": 3,
            "M": 4,
            "N": 5,
            "O": 7,
            "P": 8,
            "Q": 1,
            "R": 2,
            "S": 3,
            "T": 4,
            "U": 6,
            "V": 6,
            "W": 6,
            "X": 5,
            "Y": 1,
            "Z": 7,
        }
        for letter, value in expected.items():
            assert chal_letter_value(letter) == value, f"Chaldean {letter} should be {value}"

    def test_all_values_1_to_8_only(self) -> None:
        assert all(1 <= v <= 8 for v in CHALDEAN_MAP.values())

    def test_sum_letters_john(self) -> None:
        # J=1 O=7 H=5 N=5 => 18
        assert chal_sum_letters("JOHN") == 18

    def test_sum_letters_john_smith(self) -> None:
        assert chal_sum_letters("JOHN SMITH") == 35


# ═══════════════════════════════════════════════════════════════════════════
# 8. Chaldean engine — name number
# ═══════════════════════════════════════════════════════════════════════════


class TestChaldeanNameNumber:
    """Tests for Chaldean name number calculations."""

    def test_john_smith_full_result(self) -> None:
        result = chaldean_name_number_full("John Smith")
        assert result.name_number == 8
        assert result.compound_number == 35
        assert result.compound_meaning == "Inventiveness"

    def test_john_smith_convenience(self) -> None:
        assert chaldean_name_number("John Smith") == 8

    def test_alice_johnson(self) -> None:
        result = chaldean_name_number_full("Alice Johnson")
        assert result.name_number == 1
        assert result.compound_number == 46
        assert result.compound_meaning == "Prosperity"

    def test_madonna_single_name(self) -> None:
        result = chaldean_name_number_full("Madonna")
        assert result.name_number == 9
        assert result.compound_number == 27
        assert result.compound_meaning == "Command and Authority"

    def test_single_digit_sum_no_compound(self) -> None:
        # "Al" -> A=1, L=3 => 4 (single digit)
        result = chaldean_name_number_full("Al")
        assert result.name_number == 4
        assert result.compound_number is None
        assert result.compound_meaning is None

    def test_very_short_name_ai(self) -> None:
        # "AI" -> A=1, I=1 => 2
        result = chaldean_name_number_full("AI")
        assert result.name_number == 2
        assert result.compound_number is None

    def test_compound_number_preserved_for_multi_digit(self) -> None:
        result = chaldean_name_number_full("John Smith")
        assert result.compound_number is not None
        assert result.compound_number > 9

    def test_frozen_dataclass(self) -> None:
        result = chaldean_name_number_full("John Smith")
        assert isinstance(result, ChaldeanResult)
        with pytest.raises(AttributeError):
            result.name_number = 99  # type: ignore[misc]

    def test_hyphenated_equals_non_hyphenated(self) -> None:
        result_hyph = chaldean_name_number_full("Mary-Jane Watson")
        result_plain = chaldean_name_number_full("MaryJane Watson")
        assert result_hyph.name_number == result_plain.name_number
        assert result_hyph.compound_number == result_plain.compound_number

    def test_case_insensitive(self) -> None:
        assert chaldean_name_number("John Smith") == chaldean_name_number("JOHN SMITH")
        assert chaldean_name_number("John Smith") == chaldean_name_number("john smith")

    def test_deterministic(self) -> None:
        a = chaldean_name_number("Maria Elena Vasquez")
        b = chaldean_name_number("Maria Elena Vasquez")
        assert a == b


# ═══════════════════════════════════════════════════════════════════════════
# 9. Chaldean — compound meanings
# ═══════════════════════════════════════════════════════════════════════════


class TestCompoundMeanings:
    """Tests for compound number meaning lookup."""

    def test_known_compound_royal_star(self) -> None:
        assert COMPOUND_MEANINGS[23] == "The Royal Star of the Lion"

    def test_known_compound_master_builder(self) -> None:
        assert COMPOUND_MEANINGS[44] == "The Master Builder"

    def test_meaning_returned_when_compound_exists(self) -> None:
        result = chaldean_name_number_full("John Smith")
        assert result.compound_meaning is not None

    def test_no_meaning_for_single_digit(self) -> None:
        result = chaldean_name_number_full("Al")
        assert result.compound_meaning is None


# ═══════════════════════════════════════════════════════════════════════════
# 10. Edge cases and integration
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases: accented chars, special names, determinism, cross-system."""

    def test_accented_equals_unaccented(self) -> None:
        assert expression("Rene") == expression("Ren\u00e9")

    def test_name_with_apostrophe_produces_valid_int(self) -> None:
        result = expression("O'Connor")
        assert isinstance(result, int)
        assert 1 <= result <= 33

    def test_extra_spaces_ignored_in_letter_sum(self) -> None:
        # sum_letters skips spaces, so extra spaces do not change the result
        assert expression("John   Smith") == expression("John Smith")

    def test_single_character_name_both_systems(self) -> None:
        assert expression("A") == 1
        assert chaldean_name_number("A") == 1

    def test_deterministic_across_repeated_calls(self) -> None:
        bd = date(1990, 3, 15)
        for _ in range(5):
            assert life_path(bd) == 1
            assert expression("John Smith") == 8
            assert chaldean_name_number("John Smith") == 8

    def test_chaldean_can_produce_9_via_reduction(self) -> None:
        """Even though no letter maps to 9, a name can still reduce to 9."""
        # Madonna: compound=27 -> 2+7=9
        assert chaldean_name_number("Madonna") == 9

    def test_pythagorean_and_chaldean_return_valid_ints(self) -> None:
        pyth = expression("Robert Brown")
        chal = chaldean_name_number("Robert Brown")
        assert isinstance(pyth, int) and 1 <= pyth <= 33
        assert isinstance(chal, int) and 1 <= chal <= 33

    def test_full_profile_all_seven_number_types_plus_chaldean(self) -> None:
        """Verify a complete profile covers all number types for one person."""
        p = calculate_pythagorean_profile(
            "John Smith", date(1990, 3, 15), current_year=2026, current_month=2
        )
        assert p.life_path == 1
        assert p.expression == 8
        assert p.soul_urge == 6
        assert p.personality == 11
        assert p.personal_year == 1
        assert p.personal_month == 3
        assert p.maturity == 9
        assert p.is_master_number is False

        c = chaldean_name_number_full("John Smith")
        assert c.name_number == 8
        assert c.compound_number == 35

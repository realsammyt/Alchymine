"""Pythagorean numerology engine.

Implements the full Western / Pythagorean numerology system:
  - Life Path (from birth date)
  - Expression / Destiny (from full name)
  - Soul Urge / Heart's Desire (from vowels in full name)
  - Personality / Outer (from consonants in full name)
  - Personal Year
  - Personal Month
  - Maturity Number (Life Path + Expression, reduced)

All calculations are deterministic.  Master numbers (11, 22, 33) are
preserved unless explicitly stated otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

from .common import (
    MASTER_NUMBERS,
    extract_consonants,
    extract_vowels,
    is_master_number,
    normalize_name,
    reduce_to_single_digit,
)

# ── Pythagorean letter-to-number mapping ─────────────────────────────────
# A=1  B=2  C=3  D=4  E=5  F=6  G=7  H=8  I=9
# J=1  K=2  L=3  M=4  N=5  O=6  P=7  Q=8  R=9
# S=1  T=2  U=3  V=4  W=5  X=6  Y=7  Z=8

PYTHAGOREAN_MAP: Final[dict[str, int]] = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8, "I": 9,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "O": 6, "P": 7, "Q": 8, "R": 9,
    "S": 1, "T": 2, "U": 3, "V": 4, "W": 5, "X": 6, "Y": 7, "Z": 8,
}


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PythagoreanProfile:
    """Complete Pythagorean numerology profile for a person."""

    life_path: int
    expression: int
    soul_urge: int
    personality: int
    personal_year: int
    personal_month: int
    maturity: int
    is_master_number: bool


# ── Core calculation functions ───────────────────────────────────────────


def letter_value(letter: str) -> int:
    """Return the Pythagorean numeric value for a single uppercase letter.

    Raises ``KeyError`` if the letter is not A-Z.

    >>> letter_value("A")
    1
    >>> letter_value("Z")
    8
    """
    return PYTHAGOREAN_MAP[letter]


def sum_letters(text: str) -> int:
    """Sum the Pythagorean values of all alphabetic characters in *text*.

    Non-alpha characters (spaces, hyphens, etc.) are silently skipped.

    >>> sum_letters("JOHN SMITH")
    44
    """
    return sum(PYTHAGOREAN_MAP[ch] for ch in text if ch in PYTHAGOREAN_MAP)


# ── Life Path ────────────────────────────────────────────────────────────


def life_path(birth_date: date) -> int:
    """Compute the Life Path number from a birth date.

    Method: reduce month, day, and year *separately* to a single digit
    (preserving master numbers), then sum those three results and reduce
    again (preserving master numbers).

    >>> life_path(date(1990, 3, 15))  # 3 + 6 + 1 = 10 -> 1
    1
    """
    month_reduced = reduce_to_single_digit(birth_date.month)
    day_reduced = reduce_to_single_digit(birth_date.day)
    year_reduced = reduce_to_single_digit(birth_date.year)
    total = month_reduced + day_reduced + year_reduced
    return reduce_to_single_digit(total)


# ── Name-based numbers ───────────────────────────────────────────────────


def expression(full_name: str) -> int:
    """Compute the Expression / Destiny number from a full name.

    >>> expression("John Smith")
    8
    """
    name = normalize_name(full_name)
    raw = sum_letters(name)
    return reduce_to_single_digit(raw)


def soul_urge(full_name: str, *, y_as_vowel: bool = False) -> int:
    """Compute the Soul Urge / Heart's Desire number (vowels only).

    By default Y is treated as a consonant.  Pass ``y_as_vowel=True``
    to count Y as a vowel.

    >>> soul_urge("John Smith")
    6
    """
    name = normalize_name(full_name)
    vowels = extract_vowels(name, y_as_vowel=y_as_vowel)
    raw = sum_letters(vowels)
    return reduce_to_single_digit(raw)


def personality(full_name: str, *, y_as_vowel: bool = False) -> int:
    """Compute the Personality / Outer number (consonants only).

    >>> personality("John Smith")
    11
    """
    name = normalize_name(full_name)
    consonants = extract_consonants(name, y_as_vowel=y_as_vowel)
    raw = sum_letters(consonants)
    return reduce_to_single_digit(raw)


# ── Time-cycle numbers ───────────────────────────────────────────────────


def personal_year(birth_date: date, *, current_year: int | None = None) -> int:
    """Compute the Personal Year number.

    Formula: reduce(birth_month + birth_day + current_year)

    >>> personal_year(date(1990, 3, 15), current_year=2026)
    1
    """
    year = current_year if current_year is not None else date.today().year
    raw = birth_date.month + birth_date.day + year
    return reduce_to_single_digit(raw, preserve_master=False)


def personal_month(
    birth_date: date,
    *,
    current_year: int | None = None,
    current_month: int | None = None,
) -> int:
    """Compute the Personal Month number.

    Formula: reduce(personal_year + current_month)

    >>> personal_month(date(1990, 3, 15), current_year=2026, current_month=2)
    3
    """
    py = personal_year(birth_date, current_year=current_year)
    month = current_month if current_month is not None else date.today().month
    raw = py + month
    return reduce_to_single_digit(raw, preserve_master=False)


# ── Maturity Number ──────────────────────────────────────────────────────


def maturity(birth_date: date, full_name: str) -> int:
    """Compute the Maturity Number.

    Formula: reduce(life_path + expression)

    >>> maturity(date(1990, 3, 15), "John Smith")
    9
    """
    lp = life_path(birth_date)
    ex = expression(full_name)
    return reduce_to_single_digit(lp + ex)


# ── Full profile ─────────────────────────────────────────────────────────


def calculate_profile(
    full_name: str,
    birth_date: date,
    *,
    y_as_vowel: bool = False,
    current_year: int | None = None,
    current_month: int | None = None,
) -> PythagoreanProfile:
    """Compute a complete Pythagorean numerology profile.

    This is the primary entry point for the Pythagorean engine.

    >>> p = calculate_profile("John Smith", date(1990, 3, 15), current_year=2026, current_month=2)
    >>> p.life_path
    1
    """
    lp = life_path(birth_date)
    ex = expression(full_name)
    su = soul_urge(full_name, y_as_vowel=y_as_vowel)
    pe = personality(full_name, y_as_vowel=y_as_vowel)
    py = personal_year(birth_date, current_year=current_year)
    pm = personal_month(birth_date, current_year=current_year, current_month=current_month)
    ma = maturity(birth_date, full_name)

    return PythagoreanProfile(
        life_path=lp,
        expression=ex,
        soul_urge=su,
        personality=pe,
        personal_year=py,
        personal_month=pm,
        maturity=ma,
        is_master_number=is_master_number(lp),
    )

"""Shared utilities for Pythagorean and Chaldean numerology engines.

All functions are pure and deterministic — no randomness, no LLM involvement.
"""

from __future__ import annotations

import unicodedata

MASTER_NUMBERS: frozenset[int] = frozenset({11, 22, 33})

VOWELS: frozenset[str] = frozenset("AEIOU")


def normalize_name(name: str) -> str:
    """Normalize a name for numerology calculation.

    - Strip leading/trailing whitespace
    - Decompose accented characters to their ASCII base letter (e.g. e-acute -> E)
    - Remove all characters that are not A-Z or whitespace
    - Uppercase the result

    >>> normalize_name("Jean-Pierre")
    'JEANPIERRE'
    >>> normalize_name("  Maria del Carmen  ")
    'MARIA DEL CARMEN'
    >>> normalize_name("Renee")
    'RENEE'
    """
    # NFKD decomposition strips accents (e.g. e-acute -> e + combining acute)
    decomposed = unicodedata.normalize("NFKD", name)
    # Keep only ASCII letters and spaces
    ascii_only = "".join(
        ch for ch in decomposed if ch.isascii() and (ch.isalpha() or ch == " ")
    )
    return ascii_only.upper().strip()


def reduce_to_single_digit(n: int, *, preserve_master: bool = True) -> int:
    """Reduce a number to a single digit by summing its digits repeatedly.

    If *preserve_master* is True (the default), master numbers 11, 22, 33 are
    returned as-is instead of being reduced further.

    >>> reduce_to_single_digit(29)
    11
    >>> reduce_to_single_digit(29, preserve_master=False)
    2
    >>> reduce_to_single_digit(38)
    2
    """
    while n > 9:
        if preserve_master and n in MASTER_NUMBERS:
            return n
        n = digit_sum(n)
    return n


def digit_sum(n: int) -> int:
    """Return the sum of the digits of *n*.

    >>> digit_sum(1990)
    19
    >>> digit_sum(29)
    11
    """
    total = 0
    n = abs(n)
    while n:
        total += n % 10
        n //= 10
    return total


def is_master_number(n: int) -> bool:
    """Return True if *n* is a master number (11, 22, or 33)."""
    return n in MASTER_NUMBERS


def extract_vowels(name: str, *, y_as_vowel: bool = False) -> str:
    """Return only the vowel characters from a normalized name.

    Spaces are ignored. If *y_as_vowel* is True, Y is treated as a vowel.

    >>> extract_vowels("JOHN SMITH")
    'OI'
    >>> extract_vowels("YOLANDA", y_as_vowel=True)
    'YOAA'
    """
    vowel_set = VOWELS | frozenset("Y") if y_as_vowel else VOWELS
    return "".join(ch for ch in name if ch in vowel_set)


def extract_consonants(name: str, *, y_as_vowel: bool = False) -> str:
    """Return only the consonant characters from a normalized name.

    Spaces are ignored. If *y_as_vowel* is True, Y is NOT included as a consonant.

    >>> extract_consonants("JOHN SMITH")
    'JHNSMTH'
    """
    vowel_set = VOWELS | frozenset("Y") if y_as_vowel else VOWELS
    return "".join(ch for ch in name if ch.isalpha() and ch not in vowel_set)

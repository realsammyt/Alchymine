"""Chaldean numerology engine.

The Chaldean (Mystic) system differs from Pythagorean in several key ways:

  1. Letter-to-number mapping is based on sound vibrations, not alphabetical order.
  2. The number **9** is considered sacred and is NOT assigned to any letter.
  3. The system primarily analyses *names*, not birth dates.
  4. **Compound numbers** (the double-digit sum before final reduction) carry
     special significance and are preserved alongside the single-digit result.

All calculations are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .common import normalize_name, reduce_to_single_digit

# ── Chaldean letter-to-number mapping ────────────────────────────────────
# Note: 9 is intentionally absent — it is sacred in the Chaldean system.
#
# 1: A, I, J, Q, Y
# 2: B, K, R
# 3: C, G, L, S
# 4: D, M, T
# 5: E, H, N, X
# 6: U, V, W
# 7: O, Z
# 8: F, P

CHALDEAN_MAP: Final[dict[str, int]] = {
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

# ── Compound-number interpretations ─────────────────────────────────────
# In Chaldean numerology, the compound (two-digit) number before final
# reduction carries its own meaning.  We store a brief keyword for the
# most traditionally significant compounds (10-52).

COMPOUND_MEANINGS: Final[dict[int, str]] = {
    10: "Wheel of Fortune",
    11: "Hidden Dangers",
    12: "The Sacrifice",
    13: "Transformation",
    14: "Movement and Temperance",
    15: "The Magician",
    16: "The Tower",
    17: "The Star",
    18: "Spiritual Conflict",
    19: "The Sun",
    20: "Awakening",
    21: "The World",
    22: "Submission and Caution",
    23: "The Royal Star of the Lion",
    24: "Love and Money",
    25: "Discrimination and Analysis",
    26: "Partnerships",
    27: "Command and Authority",
    28: "Contradiction",
    29: "Grace Under Pressure",
    30: "Loner — Meditation",
    31: "The Recluse",
    32: "Communication",
    33: "Brilliance",
    34: "Hard Work",
    35: "Inventiveness",
    36: "Humanitarian",
    37: "Family and Friendships",
    38: "Struggle and Persistence",
    39: "Activity and Ambition",
    40: "Organization and Method",
    41: "Dissolution and Depression",
    42: "Self-Sacrifice",
    43: "Revolution",
    44: "The Master Builder",
    45: "Vigilance",
    46: "Prosperity",
    47: "Wisdom and Cooperation",
    48: "Strategy and Planning",
    49: "Transformation and Change",
    50: "Communication and Freedom",
    51: "Warrior Spirit",
    52: "Creativity and Diplomacy",
}


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ChaldeanResult:
    """Result of a Chaldean name-number calculation.

    Attributes:
        name_number: The fully reduced single-digit (or master) name number.
        compound_number: The double-digit sum *before* final reduction.
            ``None`` if the raw sum was already a single digit.
        compound_meaning: Traditional interpretation of the compound number,
            or ``None`` if no standard meaning is catalogued.
    """

    name_number: int
    compound_number: int | None
    compound_meaning: str | None


# ── Core calculation functions ───────────────────────────────────────────


def letter_value(letter: str) -> int:
    """Return the Chaldean numeric value for a single uppercase letter.

    Raises ``KeyError`` if the letter is not A-Z.

    >>> letter_value("A")
    1
    >>> letter_value("F")
    8
    """
    return CHALDEAN_MAP[letter]


def sum_letters(text: str) -> int:
    """Sum the Chaldean values of all alphabetic characters in *text*.

    Non-alpha characters (spaces, hyphens, etc.) are silently skipped.

    >>> sum_letters("JOHN")
    18
    """
    return sum(CHALDEAN_MAP[ch] for ch in text if ch in CHALDEAN_MAP)


def name_number(full_name: str, *, preserve_master: bool = True) -> ChaldeanResult:
    """Compute the Chaldean name number with compound-number metadata.

    The Chaldean system uses only the **name** (not the birth date).
    The compound number (double-digit total before final reduction) has
    its own significance and is preserved in the result.

    >>> r = name_number("John Smith")
    >>> r.name_number
    8
    >>> r.compound_number
    35
    """
    normalized = normalize_name(full_name)
    raw = sum_letters(normalized)

    # Determine the compound number (the two-digit value before reducing)
    compound: int | None = raw if raw > 9 else None
    meaning: str | None = COMPOUND_MEANINGS.get(raw) if compound is not None else None

    reduced = reduce_to_single_digit(raw, preserve_master=preserve_master)

    return ChaldeanResult(
        name_number=reduced,
        compound_number=compound,
        compound_meaning=meaning,
    )


def calculate_name_number(full_name: str, *, preserve_master: bool = True) -> int:
    """Convenience function returning just the reduced Chaldean name number.

    >>> calculate_name_number("John Smith")
    8
    """
    return name_number(full_name, preserve_master=preserve_master).name_number

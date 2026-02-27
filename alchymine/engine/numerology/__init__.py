"""Numerology engines — Pythagorean and Chaldean systems.

Public API
----------
Pythagorean (Western):
    calculate_pythagorean_profile  — full profile from name + birth date
    life_path                      — Life Path from birth date
    expression                     — Expression/Destiny from full name
    soul_urge                      — Soul Urge from vowels
    personality                    — Personality from consonants
    personal_year                  — Personal Year cycle
    personal_month                 — Personal Month cycle
    maturity                       — Maturity Number (life_path + expression)

Chaldean (Mystic):
    chaldean_name_number           — reduced name number
    chaldean_name_number_full      — ChaldeanResult with compound metadata

Shared utilities:
    reduce_to_single_digit         — digit reduction with master-number support
    normalize_name                 — accent-stripping / uppercasing
    is_master_number               — check for 11 / 22 / 33
"""

from .chaldean import (
    ChaldeanResult,
    calculate_name_number as chaldean_name_number,
    name_number as chaldean_name_number_full,
)
from .common import (
    MASTER_NUMBERS,
    is_master_number,
    normalize_name,
    reduce_to_single_digit,
)
from .pythagorean import (
    PythagoreanProfile,
    calculate_profile as calculate_pythagorean_profile,
    expression,
    life_path,
    maturity,
    personal_month,
    personal_year,
    personality,
    soul_urge,
)

__all__ = [
    # Pythagorean
    "PythagoreanProfile",
    "calculate_pythagorean_profile",
    "life_path",
    "expression",
    "soul_urge",
    "personality",
    "personal_year",
    "personal_month",
    "maturity",
    # Chaldean
    "ChaldeanResult",
    "chaldean_name_number",
    "chaldean_name_number_full",
    # Shared
    "MASTER_NUMBERS",
    "reduce_to_single_digit",
    "normalize_name",
    "is_master_number",
]

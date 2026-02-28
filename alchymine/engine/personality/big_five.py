"""Mini-IPIP Big Five personality trait scoring engine.

The mini-IPIP is a 20-item short form of the International Personality Item Pool
(IPIP) Big Five factor markers. Each of the five traits is measured by 4 items,
two of which are reverse-scored.

Traits:
  - Extraversion (E)
  - Agreeableness (A)
  - Conscientiousness (C)
  - Neuroticism (N)
  - Openness to Experience (O)

Raw scores per trait range from 4-20. These are linearly mapped to 0-100.

Reference:
  Donnellan, M.B., Oswald, F.L., Baird, B.M., & Lucas, R.E. (2006).
  The Mini-IPIP Scales. Psychological Assessment, 18(2), 192-203.
"""

from __future__ import annotations

from alchymine.engine.profile import BigFiveScores

# ── Item definitions ──────────────────────────────────────────────────
#
# Each item maps a question ID to its trait and whether it is reverse-scored.
# Question IDs follow the convention: bf_{trait_initial}{item_number}
# e.g. bf_e1 = Extraversion item 1.

_ITEMS: dict[str, tuple[str, bool]] = {
    # Extraversion
    "bf_e1": ("extraversion", False),  # Am the life of the party
    "bf_e2": ("extraversion", True),  # Don't talk a lot (R)
    "bf_e3": ("extraversion", False),  # Talk to a lot of different people
    "bf_e4": ("extraversion", True),  # Keep in the background (R)
    # Agreeableness
    "bf_a1": ("agreeableness", False),  # Sympathize with others' feelings
    "bf_a2": ("agreeableness", True),  # Am not interested in other people's problems (R)
    "bf_a3": ("agreeableness", False),  # Feel others' emotions
    "bf_a4": ("agreeableness", True),  # Am not really interested in others (R)
    # Conscientiousness
    "bf_c1": ("conscientiousness", False),  # Get chores done right away
    "bf_c2": ("conscientiousness", True),  # Often forget to put things back (R)
    "bf_c3": ("conscientiousness", False),  # Like order
    "bf_c4": ("conscientiousness", True),  # Make a mess of things (R)
    # Neuroticism
    "bf_n1": ("neuroticism", False),  # Have frequent mood swings
    "bf_n2": ("neuroticism", True),  # Am relaxed most of the time (R)
    "bf_n3": ("neuroticism", False),  # Get upset easily
    "bf_n4": ("neuroticism", True),  # Seldom feel blue (R)
    # Openness
    "bf_o1": ("openness", False),  # Have a vivid imagination
    "bf_o2": ("openness", True),  # Am not interested in abstract ideas (R)
    "bf_o3": ("openness", True),  # Have difficulty understanding abstract ideas (R)
    "bf_o4": ("openness", True),  # Do not have a good imagination (R)
}

# Minimum and maximum possible raw sums per trait (4 items, each 1-5).
_RAW_MIN = 4
_RAW_MAX = 20


def _reverse(raw: int) -> int:
    """Reverse-score a 1-5 Likert item: 1↔5, 2↔4, 3↔3."""
    return 6 - raw


def _validate_responses(responses: dict[str, int]) -> None:
    """Validate that all 20 items are present and in the 1-5 range."""
    missing = set(_ITEMS.keys()) - set(responses.keys())
    if missing:
        raise ValueError(f"Missing Big Five items: {sorted(missing)}")
    for qid in _ITEMS:
        val = responses[qid]
        if not isinstance(val, int) or val < 1 or val > 5:
            raise ValueError(f"Item '{qid}' must be an integer 1-5, got {val!r}")


def _raw_to_100(raw_sum: float) -> float:
    """Map a raw trait sum (4-20) to the 0-100 scale."""
    return round((raw_sum - _RAW_MIN) / (_RAW_MAX - _RAW_MIN) * 100, 2)


def score_big_five(responses: dict[str, int]) -> BigFiveScores:
    """Score a complete mini-IPIP assessment.

    Parameters
    ----------
    responses:
        Mapping of question_id -> raw score (1-5).
        Expected keys: bf_e1..bf_e4, bf_a1..bf_a4, bf_c1..bf_c4,
                        bf_n1..bf_n4, bf_o1..bf_o4.

    Returns
    -------
    BigFiveScores with each trait on a 0-100 scale.

    Raises
    ------
    ValueError
        If any items are missing or out of the 1-5 range.
    """
    _validate_responses(responses)

    # Accumulate raw sums per trait.
    trait_sums: dict[str, float] = {
        "extraversion": 0,
        "agreeableness": 0,
        "conscientiousness": 0,
        "neuroticism": 0,
        "openness": 0,
    }

    for qid, (trait, is_reversed) in _ITEMS.items():
        raw = responses[qid]
        trait_sums[trait] += _reverse(raw) if is_reversed else raw

    return BigFiveScores(
        openness=_raw_to_100(trait_sums["openness"]),
        conscientiousness=_raw_to_100(trait_sums["conscientiousness"]),
        extraversion=_raw_to_100(trait_sums["extraversion"]),
        agreeableness=_raw_to_100(trait_sums["agreeableness"]),
        neuroticism=_raw_to_100(trait_sums["neuroticism"]),
    )

"""Decision framework engine — deterministic perspective analysis tools.

Provides structured decision-making frameworks:
  - Weighted Decision Matrix
  - Pros/Cons Analysis
  - De Bono's Six Thinking Hats
  - Second-Order Effects mapping

All functions are pure and deterministic. No LLM calls.

Attribution:
  - Six Thinking Hats: Edward de Bono (1985)
  - Weighted Decision Matrix: multi-criteria decision analysis (MCDA)
  - Second-Order Effects: systems thinking / causal chain analysis
"""

from __future__ import annotations

# ─── Weighted Decision Matrix ────────────────────────────────────────────


def weighted_decision_matrix(
    options: list[str],
    criteria: list[dict],
) -> dict:
    """Score options against weighted criteria.

    Args:
        options: List of option names to evaluate.
        criteria: List of dicts, each with keys:
            - name (str): criterion label
            - weight (float): importance weight (0-1, all should sum to ~1)
            - scores (dict[str, float]): option_name -> raw score (0-10)

    Returns:
        Dict with keys:
            - ranked_options: list of {option, weighted_score} sorted descending
            - criteria_breakdown: per-criterion weighted contributions
            - methodology: attribution string
    """
    if not options:
        raise ValueError("At least one option is required.")
    if not criteria:
        raise ValueError("At least one criterion is required.")

    # Validate criteria structure
    for c in criteria:
        if "name" not in c or "weight" not in c or "scores" not in c:
            raise ValueError(
                f"Each criterion must have 'name', 'weight', and 'scores'. Got: {list(c.keys())}"
            )

    total_weight = sum(c["weight"] for c in criteria)

    # Calculate weighted scores per option
    option_scores: dict[str, float] = {opt: 0.0 for opt in options}
    criteria_breakdown: list[dict] = []

    for c in criteria:
        normalised_weight = c["weight"] / total_weight if total_weight > 0 else 0
        breakdown_entry: dict = {
            "criterion": c["name"],
            "weight": c["weight"],
            "normalised_weight": round(normalised_weight, 4),
            "contributions": {},
        }
        for opt in options:
            raw_score = c["scores"].get(opt, 0)
            contribution = raw_score * normalised_weight
            option_scores[opt] += contribution
            breakdown_entry["contributions"][opt] = round(contribution, 4)
        criteria_breakdown.append(breakdown_entry)

    # Rank options
    ranked = sorted(
        [
            {"option": opt, "weighted_score": round(score, 4)}
            for opt, score in option_scores.items()
        ],
        key=lambda x: float(str(x["weighted_score"])),
        reverse=True,
    )

    return {
        "ranked_options": ranked,
        "criteria_breakdown": criteria_breakdown,
        "methodology": (
            "Weighted Decision Matrix (Multi-Criteria Decision Analysis). "
            "Each criterion is normalised by total weight, then multiplied "
            "by the raw score for each option. Higher scores indicate stronger fit."
        ),
    }


# ─── Pros/Cons Analysis ─────────────────────────────────────────────────


def pros_cons_analysis(
    option: str,
    pros: list[str],
    cons: list[str],
) -> dict:
    """Structured pros/cons analysis with balance scoring.

    Args:
        option: The option being evaluated.
        pros: List of pro arguments.
        cons: List of con arguments.

    Returns:
        Dict with keys:
            - option: the evaluated option
            - pros: list of {text, weight} (weight = 1.0 per item)
            - cons: list of {text, weight}
            - pro_count / con_count
            - balance_score: normalised score from -1 (all cons) to +1 (all pros)
            - assessment: qualitative label
            - methodology: attribution string
    """
    if not option or not option.strip():
        raise ValueError("Option must be a non-empty string.")

    pro_entries = [{"text": p, "weight": 1.0} for p in pros]
    con_entries = [{"text": c, "weight": 1.0} for c in cons]

    total = len(pros) + len(cons)
    if total == 0:
        balance_score = 0.0
    else:
        balance_score = (len(pros) - len(cons)) / total

    balance_score = round(balance_score, 4)

    # Qualitative assessment
    if balance_score > 0.5:
        assessment = "Strongly favourable"
    elif balance_score > 0.15:
        assessment = "Moderately favourable"
    elif balance_score > -0.15:
        assessment = "Balanced — requires careful deliberation"
    elif balance_score > -0.5:
        assessment = "Moderately unfavourable"
    else:
        assessment = "Strongly unfavourable"

    return {
        "option": option,
        "pros": pro_entries,
        "cons": con_entries,
        "pro_count": len(pros),
        "con_count": len(cons),
        "balance_score": balance_score,
        "assessment": assessment,
        "methodology": (
            "Structured Pros/Cons Analysis. Balance score is computed as "
            "(pro_count - con_count) / total_count, yielding a range of "
            "[-1, +1]. This provides an initial quantitative signal; deeper "
            "analysis should weight individual factors by importance."
        ),
    }


# ─── Six Thinking Hats ──────────────────────────────────────────────────

HAT_DESCRIPTIONS: dict[str, str] = {
    "white": "Facts and information — objective data, what is known and unknown",
    "red": "Emotions and intuition — feelings, hunches, gut reactions",
    "black": "Caution and risks — dangers, difficulties, potential problems",
    "yellow": "Optimism and benefits — values, advantages, opportunities",
    "green": "Creativity and alternatives — new ideas, possibilities, lateral thinking",
    "blue": "Process and overview — managing the thinking process, next steps",
}

VALID_HATS = frozenset(HAT_DESCRIPTIONS.keys())


def six_thinking_hats(
    problem: str,
    perspectives: dict,
) -> dict:
    """Apply De Bono's Six Thinking Hats to a problem.

    Args:
        problem: Description of the problem or decision.
        perspectives: Dict mapping hat colour (str) to the user's thinking
            under that hat (str). Valid keys: white, red, black, yellow,
            green, blue.

    Returns:
        Dict with:
            - problem: the input problem
            - hats: list of {hat, colour, description, user_thinking}
            - missing_hats: list of hat colours not addressed
            - coverage_score: fraction of hats addressed (0-1)
            - synthesis: summary of the balance of perspectives
            - methodology: attribution string
    """
    if not problem or not problem.strip():
        raise ValueError("Problem description must be non-empty.")

    # Validate hat colours
    provided_hats = set()
    for key in perspectives:
        lower_key = key.lower().strip()
        if lower_key not in VALID_HATS:
            raise ValueError(f"Invalid hat colour '{key}'. Valid colours: {sorted(VALID_HATS)}")
        provided_hats.add(lower_key)

    hats_output = []
    for colour in ["white", "red", "black", "yellow", "green", "blue"]:
        # Find user input (case-insensitive)
        user_thinking = None
        for key, val in perspectives.items():
            if key.lower().strip() == colour:
                user_thinking = val
                break

        hats_output.append(
            {
                "hat": f"{colour.capitalize()} Hat",
                "colour": colour,
                "description": HAT_DESCRIPTIONS[colour],
                "user_thinking": user_thinking,
            }
        )

    missing = sorted(VALID_HATS - provided_hats)
    coverage = len(provided_hats) / len(VALID_HATS) if VALID_HATS else 0
    coverage = round(coverage, 4)

    # Build synthesis
    has_risk = "black" in provided_hats
    has_benefit = "yellow" in provided_hats
    has_creative = "green" in provided_hats
    has_emotion = "red" in provided_hats

    synthesis_parts = []
    if coverage == 1.0:
        synthesis_parts.append("All six perspectives have been considered.")
    else:
        synthesis_parts.append(
            f"{len(provided_hats)} of 6 perspectives addressed. "
            f"Consider exploring: {', '.join(missing)}."
        )

    if has_risk and has_benefit:
        synthesis_parts.append(
            "Both risk and benefit perspectives are represented, supporting balanced evaluation."
        )
    elif has_risk and not has_benefit:
        synthesis_parts.append(
            "Risk perspective is present but benefit perspective is missing — consider what could go well."
        )
    elif has_benefit and not has_risk:
        synthesis_parts.append(
            "Benefit perspective is present but risk assessment is missing — consider potential downsides."
        )

    if not has_creative:
        synthesis_parts.append("Creative/alternative thinking (green hat) is not yet explored.")

    if not has_emotion:
        synthesis_parts.append("Emotional/intuitive response (red hat) has not been captured.")

    return {
        "problem": problem,
        "hats": hats_output,
        "missing_hats": missing,
        "coverage_score": coverage,
        "synthesis": " ".join(synthesis_parts),
        "methodology": (
            "Six Thinking Hats framework by Edward de Bono (1985). "
            "Separates thinking into six distinct modes — factual (white), "
            "emotional (red), critical (black), optimistic (yellow), "
            "creative (green), and process (blue) — to enable more complete "
            "and less conflicted evaluation of decisions."
        ),
    }


# ─── Second-Order Effects ────────────────────────────────────────────────


def second_order_effects(
    decision: str,
    effects: list[str],
) -> dict:
    """Map first-, second-, and third-order consequences of a decision.

    The input effects list is treated as first-order effects. The function
    generates placeholder second- and third-order projections based on
    the number and nature of first-order effects — deterministically.

    Args:
        decision: The decision being analysed.
        effects: List of first-order effects (direct consequences).

    Returns:
        Dict with:
            - decision: the input decision
            - first_order: list of {effect, order: 1}
            - second_order: list of {effect, derived_from, order: 2}
            - third_order: list of {effect, derived_from, order: 3}
            - total_effects_mapped: count of all effects
            - complexity_rating: low/medium/high based on effect count
            - methodology: attribution string
    """
    if not decision or not decision.strip():
        raise ValueError("Decision description must be non-empty.")

    first_order = [{"effect": e, "order": 1} for e in effects]

    # Generate second-order effects deterministically:
    # Each first-order effect produces two second-order projections
    second_order = []
    for _i, effect in enumerate(effects):
        second_order.append(
            {
                "effect": f"Adaptation to: {effect}",
                "derived_from": effect,
                "order": 2,
            }
        )
        second_order.append(
            {
                "effect": f"Ripple impact of: {effect}",
                "derived_from": effect,
                "order": 2,
            }
        )

    # Generate third-order effects: one per second-order effect
    third_order = []
    for se in second_order:
        third_order.append(
            {
                "effect": f"Long-term consequence of: {se['effect']}",
                "derived_from": se["effect"],
                "order": 3,
            }
        )

    total = len(first_order) + len(second_order) + len(third_order)

    # Complexity rating based on total effect count
    if total <= 6:
        complexity = "low"
    elif total <= 15:
        complexity = "medium"
    else:
        complexity = "high"

    return {
        "decision": decision,
        "first_order": first_order,
        "second_order": second_order,
        "third_order": third_order,
        "total_effects_mapped": total,
        "complexity_rating": complexity,
        "methodology": (
            "Second-Order Effects analysis (systems thinking / causal chain mapping). "
            "First-order effects are direct consequences. Second-order effects are "
            "adaptations and ripple impacts. Third-order effects represent long-term, "
            "emergent consequences. This framework helps identify unintended consequences "
            "and systemic risks before committing to a decision."
        ),
    }

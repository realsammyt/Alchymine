"""Scenario modeling engine — deterministic scenario generation and analysis.

Provides:
  - Best / Worst / Likely scenario generation
  - Probability range assessment
  - Sensitivity analysis (which variables matter most)

All calculations are pure and deterministic. No LLM calls.

Methodology:
  - Scenario planning: Royal Dutch Shell tradition (1970s)
  - Sensitivity analysis: one-at-a-time (OAT) perturbation
  - Probability ranges: simple triangular estimation
"""

from __future__ import annotations

# ─── Scenario Modeling ───────────────────────────────────────────────────


def model_scenarios(
    decision: str,
    variables: list[dict],
) -> list[dict]:
    """Generate best-case, worst-case, and most-likely scenarios.

    Args:
        decision: Description of the decision being modelled.
        variables: List of dicts, each with keys:
            - name (str): variable label
            - best (float): best-case value
            - worst (float): worst-case value
            - likely (float): most-likely value

    Returns:
        List of three scenario dicts (best, worst, likely), each with:
            - scenario_type: 'best' | 'worst' | 'likely'
            - decision: the input decision
            - variable_values: dict mapping variable name to value in this scenario
            - aggregate_score: average of all variable values in this scenario
            - description: human-readable scenario narrative
            - methodology: attribution string
    """
    if not decision or not decision.strip():
        raise ValueError("Decision description must be non-empty.")
    if not variables:
        raise ValueError("At least one variable is required.")

    for v in variables:
        if "name" not in v or "best" not in v or "worst" not in v or "likely" not in v:
            raise ValueError(
                f"Each variable must have 'name', 'best', 'worst', and 'likely'. "
                f"Got: {list(v.keys())}"
            )

    scenarios = []
    methodology = (
        "Scenario planning methodology (Royal Dutch Shell, 1970s). "
        "Three canonical scenarios — best, worst, and most likely — "
        "are constructed by selecting the corresponding value for each "
        "variable. Aggregate score is the mean of all variable values "
        "within each scenario."
    )

    for scenario_type in ["best", "worst", "likely"]:
        variable_values = {}
        for v in variables:
            variable_values[v["name"]] = v[scenario_type]

        values = list(variable_values.values())
        aggregate = sum(values) / len(values) if values else 0.0
        aggregate = round(aggregate, 4)

        if scenario_type == "best":
            desc = (
                f"Best-case scenario for '{decision}': all variables perform "
                f"at their optimistic values. Aggregate score: {aggregate}."
            )
        elif scenario_type == "worst":
            desc = (
                f"Worst-case scenario for '{decision}': all variables perform "
                f"at their pessimistic values. Aggregate score: {aggregate}."
            )
        else:
            desc = (
                f"Most likely scenario for '{decision}': variables perform "
                f"at their expected values. Aggregate score: {aggregate}."
            )

        scenarios.append(
            {
                "scenario_type": scenario_type,
                "decision": decision,
                "variable_values": variable_values,
                "aggregate_score": aggregate,
                "description": desc,
                "methodology": methodology,
            }
        )

    return scenarios


# ─── Probability Assessment ──────────────────────────────────────────────


def probability_assessment(scenarios: list[dict]) -> dict:
    """Assign probability ranges to scenarios using triangular estimation.

    Uses a simple heuristic:
      - Most likely scenario: highest probability
      - Best and worst: lower probability, scaled by distance from likely

    Args:
        scenarios: List of scenario dicts (as returned by model_scenarios).
            Each must have 'scenario_type' and 'aggregate_score'.

    Returns:
        Dict with:
            - assessments: list of {scenario_type, aggregate_score,
              probability_low, probability_high, probability_midpoint}
            - total_probability_range: sum of midpoints (informational)
            - methodology: attribution string
    """
    if not scenarios:
        raise ValueError("At least one scenario is required.")

    # Find the likely, best, worst aggregate scores
    likely_score = None
    best_score = None
    worst_score = None

    for s in scenarios:
        st = s.get("scenario_type", "")
        agg = s.get("aggregate_score", 0)
        if st == "likely":
            likely_score = agg
        elif st == "best":
            best_score = agg
        elif st == "worst":
            worst_score = agg

    # If we have a standard three-scenario set, use triangular heuristic
    assessments = []

    if likely_score is not None and best_score is not None and worst_score is not None:
        # The likely scenario gets the highest probability
        # Best and worst get proportionally lower probabilities
        spread = abs(best_score - worst_score) if best_score != worst_score else 1.0

        for s in scenarios:
            st = s.get("scenario_type", "unknown")
            agg = s.get("aggregate_score", 0)

            if st == "likely":
                prob_low = 0.40
                prob_high = 0.60
            elif st == "best":
                # Distance from likely determines probability
                distance = abs(agg - likely_score) / spread if spread > 0 else 0.5
                distance = min(distance, 1.0)
                prob_low = max(0.05, 0.15 - 0.10 * distance)
                prob_high = max(0.10, 0.30 - 0.15 * distance)
            elif st == "worst":
                distance = abs(agg - likely_score) / spread if spread > 0 else 0.5
                distance = min(distance, 1.0)
                prob_low = max(0.05, 0.15 - 0.10 * distance)
                prob_high = max(0.10, 0.30 - 0.15 * distance)
            else:
                # Unknown scenario type — assign moderate range
                prob_low = 0.10
                prob_high = 0.30

            assessments.append(
                {
                    "scenario_type": st,
                    "aggregate_score": agg,
                    "probability_low": round(prob_low, 4),
                    "probability_high": round(prob_high, 4),
                    "probability_midpoint": round((prob_low + prob_high) / 2, 4),
                }
            )
    else:
        # Fallback: equal probability across all scenarios
        n = len(scenarios)
        equal_mid = 1.0 / n if n > 0 else 0
        for s in scenarios:
            assessments.append(
                {
                    "scenario_type": s.get("scenario_type", "unknown"),
                    "aggregate_score": s.get("aggregate_score", 0),
                    "probability_low": round(equal_mid * 0.7, 4),
                    "probability_high": round(equal_mid * 1.3, 4),
                    "probability_midpoint": round(equal_mid, 4),
                }
            )

    total_midpoint = sum(a["probability_midpoint"] for a in assessments)

    return {
        "assessments": assessments,
        "total_probability_range": round(total_midpoint, 4),
        "methodology": (
            "Triangular probability estimation. The most-likely scenario is "
            "assigned the highest probability range (40-60%), with best and "
            "worst cases receiving ranges proportional to their distance from "
            "the likely outcome. These are heuristic estimates — for rigorous "
            "probability assessment, consult domain-specific models."
        ),
    }


# ─── Sensitivity Analysis ───────────────────────────────────────────────


def sensitivity_analysis(variables: list[dict]) -> dict:
    """Determine which variables have the most impact on outcomes.

    Uses one-at-a-time (OAT) perturbation: the variable with the
    largest range (best - worst) has the most sensitivity.

    Args:
        variables: List of dicts, each with keys:
            - name (str): variable label
            - best (float): best-case value
            - worst (float): worst-case value
            - likely (float): most-likely value

    Returns:
        Dict with:
            - ranked_variables: list of {name, range, normalised_impact,
              skew, skew_direction} sorted by impact descending
            - most_sensitive: name of the highest-impact variable
            - least_sensitive: name of the lowest-impact variable
            - methodology: attribution string
    """
    if not variables:
        raise ValueError("At least one variable is required.")

    for v in variables:
        if "name" not in v or "best" not in v or "worst" not in v or "likely" not in v:
            raise ValueError(
                f"Each variable must have 'name', 'best', 'worst', and 'likely'. "
                f"Got: {list(v.keys())}"
            )

    # Calculate range for each variable
    ranges = []
    for v in variables:
        var_range = abs(v["best"] - v["worst"])
        # Skew: how far the likely value is from the midpoint
        midpoint = (v["best"] + v["worst"]) / 2
        skew = v["likely"] - midpoint
        if skew > 0:
            skew_direction = "optimistic"
        elif skew < 0:
            skew_direction = "pessimistic"
        else:
            skew_direction = "centred"

        ranges.append(
            {
                "name": v["name"],
                "range": round(var_range, 4),
                "skew": round(skew, 4),
                "skew_direction": skew_direction,
            }
        )

    # Normalise by maximum range
    max_range = max(r["range"] for r in ranges) if ranges else 1.0
    if max_range == 0:
        max_range = 1.0  # prevent division by zero

    for r in ranges:
        r["normalised_impact"] = round(r["range"] / max_range, 4)

    # Sort by normalised impact descending
    ranked = sorted(ranges, key=lambda x: x["normalised_impact"], reverse=True)

    return {
        "ranked_variables": ranked,
        "most_sensitive": ranked[0]["name"] if ranked else None,
        "least_sensitive": ranked[-1]["name"] if ranked else None,
        "methodology": (
            "One-at-a-time (OAT) sensitivity analysis. Each variable's "
            "impact is measured by its range (best - worst). Variables with "
            "larger ranges have greater influence on outcomes. Normalised "
            "impact scores are relative to the most sensitive variable. "
            "Skew indicates whether the likely value leans optimistic or "
            "pessimistic relative to the variable's midpoint."
        ),
    }

"""LangGraph StateGraph implementations for coordinator pipelines.

Each Alchymine system coordinator is modelled as a StateGraph with typed
state, discrete processing nodes, a quality gate node, and an error
handler. The ``build_{system}_graph()`` factory functions return compiled
graphs that the coordinator classes invoke via ``graph.invoke(state)``.

If langgraph is unavailable at import time (e.g. missing dependency in
a minimal install), a lightweight fallback is provided that runs node
functions sequentially — preserving identical behaviour without the
graph framework.
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

# ─── Shared coordinator state ───────────────────────────────────────


class CoordinatorState(TypedDict, total=False):
    """Shared typed state flowing through coordinator graphs.

    Attributes
    ----------
    user_id:
        The user's profile identifier.
    request_data:
        Request-specific data forwarded by the coordinator.
    results:
        Accumulated output data from processing nodes.
    errors:
        Error messages collected during processing.
    status:
        Processing status string — "success", "error", or "degraded".
    quality_passed:
        Whether the quality gate passed for this output.
    """

    user_id: str
    request_data: dict[str, Any]
    results: dict[str, Any]
    errors: list[str]
    status: str
    quality_passed: bool


# ─── LangGraph import with fallback ────────────────────────────────

try:
    from langgraph.graph import END, StateGraph
    from langgraph.graph.state import CompiledStateGraph

    _HAS_LANGGRAPH = True
except ImportError:
    _HAS_LANGGRAPH = False
    # Sentinel values used by the fallback
    END = "__end__"  # type: ignore[assignment]
    StateGraph = None  # type: ignore[assignment, misc]
    CompiledStateGraph = None  # type: ignore[assignment, misc]


# ─── Fallback sequential runner ─────────────────────────────────────


class _SequentialGraph:
    """Minimal fallback that runs node functions in registration order.

    This is used when langgraph is not installed. It mimics the
    ``CompiledStateGraph.invoke`` interface so coordinators work
    identically in either mode.
    """

    def __init__(self) -> None:
        self._nodes: list[tuple[str, Any]] = []

    def add_node(self, name: str, func: Any) -> None:  # noqa: ANN401
        self._nodes.append((name, func))

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run all nodes sequentially, threading state through each."""
        for _name, func in self._nodes:
            state = func(state)
        return state


# ─── Quality gate helper ────────────────────────────────────────────


def _run_quality_gate_node(state: CoordinatorState, system: str) -> CoordinatorState:
    """Run the quality gate validator for *system* on the current results.

    Mirrors the logic in ``BaseCoordinator._run_quality_gate`` but
    operates on the graph state dict directly.
    """
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    status = state.get("status", "success")
    quality_passed = True

    try:
        from alchymine.agents.quality.validators import run_quality_gate

        gate_result = run_quality_gate(results, system=system)
        quality_passed = gate_result.passed
    except ValueError:
        # No quality gate registered for this system — pass by default
        quality_passed = True
    except Exception as exc:
        logger.warning("Quality gate error for %s: %s", system, exc)
        quality_passed = True

    if not quality_passed:
        if status == "success":
            status = "degraded"
        errors = [*errors, f"Quality gate validation failed for {system}"]

    return {
        **state,
        "results": results,
        "errors": errors,
        "status": status,
        "quality_passed": quality_passed,
    }


def _compute_status(errors: list[str], data: dict[str, Any]) -> str:
    """Determine coordinator status from errors and data."""
    if errors and not data:
        return "error"
    if errors:
        return "degraded"
    return "success"


def _compute_status_with_baseline(
    errors: list[str],
    data: dict[str, Any],
    baseline_keys: int = 0,
) -> str:
    """Determine coordinator status when data has baseline keys (e.g. disclaimers)."""
    if errors and len(data) <= baseline_keys:
        return "degraded"
    if errors:
        return "degraded"
    return "success"


# ═══════════════════════════════════════════════════════════════════════
# Intelligence graph nodes
# ═══════════════════════════════════════════════════════════════════════


def _intelligence_numerology(state: CoordinatorState) -> CoordinatorState:
    """Numerology calculation node for the Intelligence graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from datetime import date as date_type

        from alchymine.engine.numerology import calculate_pythagorean_profile

        full_name = request_data.get("full_name", "")
        birth_date = request_data.get("birth_date")

        if full_name and birth_date:
            if isinstance(birth_date, str):
                birth_date = date_type.fromisoformat(birth_date)
            profile = calculate_pythagorean_profile(full_name, birth_date)
            results["numerology"] = {
                "life_path": profile.life_path,
                "expression": profile.expression,
                "soul_urge": profile.soul_urge,
                "personality": profile.personality,
                "personal_year": profile.personal_year,
                "personal_month": profile.personal_month,
            }
        else:
            errors.append("Intelligence: missing full_name or birth_date for numerology")
    except ImportError:
        errors.append("Intelligence: numerology engine not available")
    except Exception as exc:
        errors.append(f"Intelligence: numerology error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _intelligence_astrology(state: CoordinatorState) -> CoordinatorState:
    """Astrology calculation node for the Intelligence graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from datetime import date as date_type
        from datetime import time as time_type

        from alchymine.engine.astrology import calculate_natal_chart

        birth_date = request_data.get("birth_date")
        if birth_date:
            if isinstance(birth_date, str):
                birth_date = date_type.fromisoformat(birth_date)

            # Extract optional birth_time and birth_city for full chart
            birth_time = request_data.get("birth_time")
            if isinstance(birth_time, str) and birth_time:
                birth_time = time_type.fromisoformat(birth_time)
            elif not isinstance(birth_time, time_type):
                birth_time = None

            birth_city = request_data.get("birth_city")

            chart = calculate_natal_chart(
                birth_date,
                birth_time=birth_time,
                birth_city=birth_city,
            )
            results["astrology"] = chart
        else:
            errors.append("Intelligence: missing birth_date for astrology")
    except ImportError:
        errors.append("Intelligence: astrology engine not available")
    except Exception as exc:
        errors.append(f"Intelligence: astrology error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _intelligence_personality(state: CoordinatorState) -> CoordinatorState:
    """Personality (Big Five + attachment + enneagram) scoring node for the Intelligence graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.personality.big_five import score_big_five

        bf_responses = request_data.get("assessment_responses", {})
        # Filter to only Big Five items (bf_* keys)
        bf_items = {k: v for k, v in bf_responses.items() if k.startswith("bf_")}

        if len(bf_items) >= 20:
            scores = score_big_five(bf_items)
            personality: dict[str, Any] = {
                "big_five": {
                    "openness": scores.openness,
                    "conscientiousness": scores.conscientiousness,
                    "extraversion": scores.extraversion,
                    "agreeableness": scores.agreeableness,
                    "neuroticism": scores.neuroticism,
                },
                "attachment_style": None,
                "enneagram_type": None,
                "enneagram_wing": None,
            }

            # Score attachment style if items are present
            att_items = {k: v for k, v in bf_responses.items() if k.startswith("att_")}
            if att_items:
                try:
                    from alchymine.engine.personality.attachment import score_attachment

                    attachment = score_attachment(att_items)
                    personality["attachment_style"] = attachment.value
                except Exception as att_exc:
                    errors.append(f"Intelligence: attachment scoring error — {att_exc!s}")

            # Score enneagram type if items are present
            enn_items = {k: v for k, v in bf_responses.items() if k.startswith("enn_")}
            if enn_items:
                try:
                    from alchymine.engine.personality.enneagram import score_enneagram

                    primary_type, wing = score_enneagram(enn_items)
                    personality["enneagram_type"] = primary_type
                    personality["enneagram_wing"] = wing
                except Exception as enn_exc:
                    errors.append(f"Intelligence: enneagram scoring error — {enn_exc!s}")

            results["personality"] = personality
        else:
            errors.append(f"Intelligence: insufficient Big Five responses ({len(bf_items)}/20)")
    except ImportError:
        errors.append("Intelligence: personality engine not available")
    except Exception as exc:
        errors.append(f"Intelligence: personality error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _intelligence_archetype(state: CoordinatorState) -> CoordinatorState:
    """Archetype mapping node for the Intelligence graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))

    try:
        from alchymine.engine.archetype.mapper import map_archetype
        from alchymine.engine.profile import (
            AstrologyProfile,
            BigFiveScores,
            NumerologyProfile,
        )

        numerology_data = results.get("numerology")
        astrology_data = results.get("astrology")
        personality_data = results.get("personality")

        if numerology_data and astrology_data and personality_data:
            # Reconstruct profile objects from upstream node results
            numerology = NumerologyProfile(
                life_path=numerology_data["life_path"],
                expression=numerology_data["expression"],
                soul_urge=numerology_data["soul_urge"],
                personality=numerology_data["personality"],
                personal_year=numerology_data["personal_year"],
                personal_month=numerology_data["personal_month"],
                maturity=numerology_data.get("maturity"),
                is_master_number=numerology_data.get("is_master_number", False),
                chaldean_name=numerology_data.get("chaldean_name"),
                calculation_system=numerology_data.get("calculation_system", "pythagorean"),
            )
            astrology = AstrologyProfile(
                sun_sign=astrology_data["sun_sign"],
                sun_degree=astrology_data["sun_degree"],
                moon_sign=astrology_data.get("moon_sign", "Unknown"),
                moon_degree=astrology_data.get("moon_degree", 0.0),
                rising_sign=astrology_data.get("rising_sign"),
                rising_degree=astrology_data.get("rising_degree"),
                house_placements=astrology_data.get("house_placements"),
                current_transits=astrology_data.get("current_transits"),
                venus_retrograde=astrology_data.get("venus_retrograde", False),
                mercury_retrograde=astrology_data.get("mercury_retrograde", False),
            )
            bf_data = personality_data.get("big_five", personality_data)
            big_five = BigFiveScores(
                openness=bf_data["openness"],
                conscientiousness=bf_data["conscientiousness"],
                extraversion=bf_data["extraversion"],
                agreeableness=bf_data["agreeableness"],
                neuroticism=bf_data["neuroticism"],
            )

            archetype = map_archetype(numerology, astrology, big_five)
            results["archetype"] = {
                "primary": archetype.primary.value,
                "secondary": archetype.secondary.value if archetype.secondary else None,
                "shadow": archetype.shadow,
                "shadow_secondary": archetype.shadow_secondary,
                "light_qualities": archetype.light_qualities,
                "shadow_qualities": archetype.shadow_qualities,
            }
        else:
            missing = []
            if not numerology_data:
                missing.append("numerology")
            if not astrology_data:
                missing.append("astrology")
            if not personality_data:
                missing.append("personality")
            errors.append(f"Intelligence: archetype requires {', '.join(missing)} — skipped")
    except ImportError:
        errors.append("Intelligence: archetype engine not available")
    except Exception as exc:
        errors.append(f"Intelligence: archetype error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _intelligence_biorhythm(state: CoordinatorState) -> CoordinatorState:
    """Biorhythm calculation node for the Intelligence graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from datetime import date as date_type

        from alchymine.engine.biorhythm.calculator import calculate_biorhythm

        birth_date = request_data.get("birth_date")
        if birth_date:
            # Handle string dates
            if isinstance(birth_date, str):
                birth_date = date_type.fromisoformat(birth_date)
            today = date_type.today()
            bio = calculate_biorhythm(birth_date, today)
            results["biorhythm"] = {
                "physical": bio.physical,
                "emotional": bio.emotional,
                "intellectual": bio.intellectual,
                "physical_percentage": bio.physical_percentage,
                "emotional_percentage": bio.emotional_percentage,
                "intellectual_percentage": bio.intellectual_percentage,
                "days_alive": bio.days_alive,
                "is_physical_critical": bio.is_physical_critical,
                "is_emotional_critical": bio.is_emotional_critical,
                "is_intellectual_critical": bio.is_intellectual_critical,
                "target_date": bio.target_date.isoformat(),
                "evidence_rating": bio.evidence_rating,
                "methodology_note": bio.methodology_note,
            }
        else:
            errors.append("Intelligence: missing birth_date for biorhythm")
    except ImportError:
        errors.append("Intelligence: biorhythm engine not available")
    except Exception as exc:
        errors.append(f"Intelligence: biorhythm error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _intelligence_status(state: CoordinatorState) -> CoordinatorState:
    """Compute final status for the Intelligence graph."""
    results = state.get("results", {})
    errors = list(state.get("errors", []))
    status = _compute_status(errors, results)
    return {**state, "status": status}


def _intelligence_quality_gate(state: CoordinatorState) -> CoordinatorState:
    """Quality gate node for the Intelligence graph."""
    return _run_quality_gate_node(state, "intelligence")


# ═══════════════════════════════════════════════════════════════════════
# Healing graph nodes
# ═══════════════════════════════════════════════════════════════════════


def _healing_init(state: CoordinatorState) -> CoordinatorState:
    """Initialise healing results with mandatory disclaimers."""
    results = dict(state.get("results", {}))
    results["disclaimers"] = [
        "This is not medical advice. Please consult a qualified "
        "healthcare professional for medical concerns."
    ]
    return {**state, "results": results}


def _healing_crisis_detection(state: CoordinatorState) -> CoordinatorState:
    """Crisis detection node for the Healing graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.healing import detect_crisis

        user_text = request_data.get("text", "")
        if user_text:
            crisis = detect_crisis(user_text)
            results["crisis_flag"] = crisis is not None
            if crisis is not None:
                results["crisis_response"] = {
                    "severity": crisis.severity.value,
                    "resources": [{"name": r.name, "contact": r.contact} for r in crisis.resources],
                }
    except ImportError:
        errors.append("Healing: crisis detection not available")
    except Exception as exc:
        errors.append(f"Healing: crisis detection error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _healing_modality_matching(state: CoordinatorState) -> CoordinatorState:
    """Modality matching node for the Healing graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.healing import match_modalities

        archetype = request_data.get("archetype")
        intentions = request_data.get("intentions")
        intention = request_data.get("intention")
        archetype_secondary = request_data.get("archetype_secondary")
        big_five = request_data.get("big_five")

        # Prefer multi-intention list, fall back to single intention
        _intentions = (
            intentions if isinstance(intentions, list) else ([intention] if intention else None)
        )

        if archetype and big_five and _intentions:
            modalities = match_modalities(
                archetype,
                archetype_secondary,
                big_five,
                _intentions,
            )
            results["recommended_modalities"] = [
                {
                    "modality": m.modality,
                    "skill_trigger": m.skill_trigger,
                    "preference_score": m.preference_score,
                    "difficulty_level": m.difficulty_level.value
                    if hasattr(m.difficulty_level, "value")
                    else str(m.difficulty_level),
                }
                for m in modalities
            ]
    except ImportError:
        errors.append("Healing: modality engine not available")
    except Exception as exc:
        errors.append(f"Healing: modality matching error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _healing_status(state: CoordinatorState) -> CoordinatorState:
    """Compute final status for the Healing graph."""
    results = state.get("results", {})
    errors = list(state.get("errors", []))
    # Healing always has at least "disclaimers" key (1 baseline key)
    status = _compute_status_with_baseline(errors, results, baseline_keys=1)
    return {**state, "status": status}


def _healing_quality_gate(state: CoordinatorState) -> CoordinatorState:
    """Quality gate node for the Healing graph."""
    return _run_quality_gate_node(state, "healing")


# ═══════════════════════════════════════════════════════════════════════
# Wealth graph nodes
# ═══════════════════════════════════════════════════════════════════════


def _wealth_init(state: CoordinatorState) -> CoordinatorState:
    """Initialise wealth results with mandatory disclaimers."""
    results = dict(state.get("results", {}))
    results["disclaimers"] = [
        "This is not financial advice. Please consult a qualified "
        "financial advisor for personalised recommendations."
    ]
    return {**state, "results": results}


def _wealth_archetype(state: CoordinatorState) -> CoordinatorState:
    """Wealth archetype mapping node."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.wealth import map_wealth_archetype

        life_path = request_data.get("life_path")
        risk_tolerance = request_data.get("risk_tolerance", "moderate")
        archetype_primary = request_data.get("archetype_primary")

        if life_path is not None and archetype_primary:
            archetype = map_wealth_archetype(
                life_path,
                archetype_primary,
                risk_tolerance,
            )
            results["wealth_archetype"] = {
                "name": archetype.name,
                "description": archetype.description,
            }
    except ImportError:
        errors.append("Wealth: archetype engine not available")
    except Exception as exc:
        errors.append(f"Wealth: archetype error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _wealth_lever_prioritisation(state: CoordinatorState) -> CoordinatorState:
    """Lever prioritisation node for the Wealth graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.wealth import prioritize_levers

        life_path = request_data.get("life_path")
        risk_tolerance = request_data.get("risk_tolerance", "moderate")
        intentions = request_data.get("intentions")
        intention = request_data.get("intention")
        wealth_context = request_data.get("wealth_context")

        # Prefer multi-intention list, fall back to single intention
        _intentions = (
            intentions if isinstance(intentions, list) else ([intention] if intention else None)
        )

        if life_path is not None and _intentions:
            levers = prioritize_levers(
                wealth_context,
                risk_tolerance,
                _intentions,  # type: ignore[arg-type]
                life_path,
            )
            results["lever_priorities"] = [
                lev.value if hasattr(lev, "value") else str(lev) for lev in levers
            ]
    except ImportError:
        errors.append("Wealth: lever engine not available")
    except Exception as exc:
        errors.append(f"Wealth: lever prioritisation error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _wealth_calculations(state: CoordinatorState) -> CoordinatorState:
    """Add empty calculations placeholder for the Wealth graph."""
    results = dict(state.get("results", {}))
    results["calculations"] = {}
    return {**state, "results": results}


def _wealth_status(state: CoordinatorState) -> CoordinatorState:
    """Compute final status for the Wealth graph."""
    results = state.get("results", {})
    errors = list(state.get("errors", []))
    # Wealth always has disclaimers + calculations (2 baseline keys)
    status = _compute_status_with_baseline(errors, results, baseline_keys=2)
    return {**state, "status": status}


def _wealth_quality_gate(state: CoordinatorState) -> CoordinatorState:
    """Quality gate node for the Wealth graph."""
    return _run_quality_gate_node(state, "wealth")


# ═══════════════════════════════════════════════════════════════════════
# Creative graph nodes
# ═══════════════════════════════════════════════════════════════════════


def _creative_orientation(state: CoordinatorState) -> CoordinatorState:
    """Creative orientation node — derives orientation from life path."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.creative import derive_creative_orientation

        life_path = request_data.get("life_path")
        if life_path is not None:
            orientation = derive_creative_orientation(life_path)
            results["creative_orientation"] = orientation
    except ImportError:
        errors.append("Creative: orientation engine not available")
    except Exception as exc:
        errors.append(f"Creative: orientation error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _creative_strengths(state: CoordinatorState) -> CoordinatorState:
    """Creative strengths node — identifies strengths from Guilford scores."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.creative import identify_strengths

        guilford_scores = request_data.get("guilford_scores")
        if guilford_scores:
            strengths = identify_strengths(guilford_scores)
            results["strengths"] = strengths
    except ImportError:
        errors.append("Creative: style engine not available")
    except Exception as exc:
        errors.append(f"Creative: style analysis error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _creative_status(state: CoordinatorState) -> CoordinatorState:
    """Compute final status for the Creative graph."""
    results = state.get("results", {})
    errors = list(state.get("errors", []))
    status = _compute_status(errors, results)
    return {**state, "status": status}


def _creative_quality_gate(state: CoordinatorState) -> CoordinatorState:
    """Quality gate node for the Creative graph."""
    return _run_quality_gate_node(state, "creative")


# ═══════════════════════════════════════════════════════════════════════
# Perspective graph nodes
# ═══════════════════════════════════════════════════════════════════════


def _perspective_bias_detection(state: CoordinatorState) -> CoordinatorState:
    """Bias detection node for the Perspective graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.perspective import detect_biases

        reasoning_text = request_data.get("text", "")
        if reasoning_text:
            biases = detect_biases(reasoning_text)
            results["detected_biases"] = biases
    except ImportError:
        errors.append("Perspective: bias engine not available")
    except Exception as exc:
        errors.append(f"Perspective: bias detection error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _perspective_kegan_assessment(state: CoordinatorState) -> CoordinatorState:
    """Kegan stage assessment node for the Perspective graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.perspective import assess_kegan_stage

        responses = request_data.get("kegan_responses")
        if responses:
            stage = assess_kegan_stage(responses)
            results["kegan_stage"] = stage
    except ImportError:
        errors.append("Perspective: kegan engine not available")
    except Exception as exc:
        errors.append(f"Perspective: kegan assessment error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _perspective_decision_framework(state: CoordinatorState) -> CoordinatorState:
    """Decision framework node for the Perspective graph."""
    results = dict(state.get("results", {}))
    errors = list(state.get("errors", []))
    request_data = state.get("request_data", {})

    try:
        from alchymine.engine.perspective import pros_cons_analysis

        decision = request_data.get("decision")
        pros = request_data.get("pros", [])
        cons = request_data.get("cons", [])
        if decision:
            analysis = pros_cons_analysis(decision, pros, cons)
            results["decision_analysis"] = analysis
    except ImportError:
        errors.append("Perspective: framework engine not available")
    except Exception as exc:
        errors.append(f"Perspective: framework error — {exc!s}")

    return {**state, "results": results, "errors": errors}


def _perspective_status(state: CoordinatorState) -> CoordinatorState:
    """Compute final status for the Perspective graph."""
    results = state.get("results", {})
    errors = list(state.get("errors", []))
    status = _compute_status(errors, results)
    return {**state, "status": status}


def _perspective_quality_gate(state: CoordinatorState) -> CoordinatorState:
    """Quality gate node for the Perspective graph."""
    return _run_quality_gate_node(state, "perspective")


# ═══════════════════════════════════════════════════════════════════════
# Graph factory functions
# ═══════════════════════════════════════════════════════════════════════


def _build_sequential_fallback(
    nodes: list[tuple[str, Any]],
) -> _SequentialGraph:
    """Build a _SequentialGraph from a list of (name, func) pairs."""
    graph = _SequentialGraph()
    for name, func in nodes:
        graph.add_node(name, func)
    return graph


def build_intelligence_graph(
    *,
    include_quality_gate: bool = True,
) -> Any:  # noqa: ANN401
    """Build and compile the Intelligence system StateGraph.

    Node order: numerology -> astrology -> personality -> archetype -> biorhythm -> status [-> quality_gate] -> END

    Parameters
    ----------
    include_quality_gate:
        If True (default) the quality gate node is appended. Set to
        False when the coordinator's ``BaseCoordinator.process()``
        handles quality gating separately.

    Returns
    -------
    CompiledStateGraph | _SequentialGraph
        A compiled LangGraph graph, or a sequential fallback if
        langgraph is unavailable.
    """
    nodes: list[tuple[str, Any]] = [
        ("numerology", _intelligence_numerology),
        ("astrology", _intelligence_astrology),
        ("personality", _intelligence_personality),
        ("archetype", _intelligence_archetype),
        ("biorhythm", _intelligence_biorhythm),
        ("status", _intelligence_status),
    ]
    if include_quality_gate:
        nodes.append(("quality_gate", _intelligence_quality_gate))

    if not _HAS_LANGGRAPH:
        return _build_sequential_fallback(nodes)

    graph = StateGraph(CoordinatorState)
    for name, func in nodes:
        graph.add_node(name, func)
    graph.set_entry_point("numerology")
    graph.add_edge("numerology", "astrology")
    graph.add_edge("astrology", "personality")
    graph.add_edge("personality", "archetype")
    graph.add_edge("archetype", "biorhythm")
    graph.add_edge("biorhythm", "status")
    if include_quality_gate:
        graph.add_edge("status", "quality_gate")
        graph.add_edge("quality_gate", END)
    else:
        graph.add_edge("status", END)
    return graph.compile()


def build_healing_graph(
    *,
    include_quality_gate: bool = True,
) -> Any:  # noqa: ANN401
    """Build and compile the Healing system StateGraph.

    Node order: init -> crisis_detection -> modality_matching -> status [-> quality_gate] -> END

    Parameters
    ----------
    include_quality_gate:
        If True (default) the quality gate node is appended.

    Returns
    -------
    CompiledStateGraph | _SequentialGraph
        A compiled LangGraph graph, or a sequential fallback.
    """
    nodes: list[tuple[str, Any]] = [
        ("init", _healing_init),
        ("crisis_detection", _healing_crisis_detection),
        ("modality_matching", _healing_modality_matching),
        ("status", _healing_status),
    ]
    if include_quality_gate:
        nodes.append(("quality_gate", _healing_quality_gate))

    if not _HAS_LANGGRAPH:
        return _build_sequential_fallback(nodes)

    graph = StateGraph(CoordinatorState)
    for name, func in nodes:
        graph.add_node(name, func)
    graph.set_entry_point("init")
    graph.add_edge("init", "crisis_detection")
    graph.add_edge("crisis_detection", "modality_matching")
    graph.add_edge("modality_matching", "status")
    if include_quality_gate:
        graph.add_edge("status", "quality_gate")
        graph.add_edge("quality_gate", END)
    else:
        graph.add_edge("status", END)
    return graph.compile()


def build_wealth_graph(
    *,
    include_quality_gate: bool = True,
) -> Any:  # noqa: ANN401
    """Build and compile the Wealth system StateGraph.

    Node order: init -> archetype -> lever_prioritisation -> calculations -> status [-> quality_gate] -> END

    Parameters
    ----------
    include_quality_gate:
        If True (default) the quality gate node is appended.

    Returns
    -------
    CompiledStateGraph | _SequentialGraph
        A compiled LangGraph graph, or a sequential fallback.
    """
    nodes: list[tuple[str, Any]] = [
        ("init", _wealth_init),
        ("archetype", _wealth_archetype),
        ("lever_prioritisation", _wealth_lever_prioritisation),
        ("calculations", _wealth_calculations),
        ("status", _wealth_status),
    ]
    if include_quality_gate:
        nodes.append(("quality_gate", _wealth_quality_gate))

    if not _HAS_LANGGRAPH:
        return _build_sequential_fallback(nodes)

    graph = StateGraph(CoordinatorState)
    for name, func in nodes:
        graph.add_node(name, func)
    graph.set_entry_point("init")
    graph.add_edge("init", "archetype")
    graph.add_edge("archetype", "lever_prioritisation")
    graph.add_edge("lever_prioritisation", "calculations")
    graph.add_edge("calculations", "status")
    if include_quality_gate:
        graph.add_edge("status", "quality_gate")
        graph.add_edge("quality_gate", END)
    else:
        graph.add_edge("status", END)
    return graph.compile()


def build_creative_graph(
    *,
    include_quality_gate: bool = True,
) -> Any:  # noqa: ANN401
    """Build and compile the Creative system StateGraph.

    Node order: orientation -> strengths -> status [-> quality_gate] -> END

    Parameters
    ----------
    include_quality_gate:
        If True (default) the quality gate node is appended.

    Returns
    -------
    CompiledStateGraph | _SequentialGraph
        A compiled LangGraph graph, or a sequential fallback.
    """
    nodes: list[tuple[str, Any]] = [
        ("orientation", _creative_orientation),
        ("strengths", _creative_strengths),
        ("status", _creative_status),
    ]
    if include_quality_gate:
        nodes.append(("quality_gate", _creative_quality_gate))

    if not _HAS_LANGGRAPH:
        return _build_sequential_fallback(nodes)

    graph = StateGraph(CoordinatorState)
    for name, func in nodes:
        graph.add_node(name, func)
    graph.set_entry_point("orientation")
    graph.add_edge("orientation", "strengths")
    graph.add_edge("strengths", "status")
    if include_quality_gate:
        graph.add_edge("status", "quality_gate")
        graph.add_edge("quality_gate", END)
    else:
        graph.add_edge("status", END)
    return graph.compile()


def build_perspective_graph(
    *,
    include_quality_gate: bool = True,
) -> Any:  # noqa: ANN401
    """Build and compile the Perspective system StateGraph.

    Node order: bias_detection -> kegan_assessment -> decision_framework -> status [-> quality_gate] -> END

    Parameters
    ----------
    include_quality_gate:
        If True (default) the quality gate node is appended.

    Returns
    -------
    CompiledStateGraph | _SequentialGraph
        A compiled LangGraph graph, or a sequential fallback.
    """
    nodes: list[tuple[str, Any]] = [
        ("bias_detection", _perspective_bias_detection),
        ("kegan_assessment", _perspective_kegan_assessment),
        ("decision_framework", _perspective_decision_framework),
        ("status", _perspective_status),
    ]
    if include_quality_gate:
        nodes.append(("quality_gate", _perspective_quality_gate))

    if not _HAS_LANGGRAPH:
        return _build_sequential_fallback(nodes)

    graph = StateGraph(CoordinatorState)
    for name, func in nodes:
        graph.add_node(name, func)
    graph.set_entry_point("bias_detection")
    graph.add_edge("bias_detection", "kegan_assessment")
    graph.add_edge("kegan_assessment", "decision_framework")
    graph.add_edge("decision_framework", "status")
    if include_quality_gate:
        graph.add_edge("status", "quality_gate")
        graph.add_edge("quality_gate", END)
    else:
        graph.add_edge("status", END)
    return graph.compile()

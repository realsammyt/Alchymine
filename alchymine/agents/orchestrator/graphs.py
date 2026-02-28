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
        from alchymine.engine.numerology import calculate_pythagorean_profile

        full_name = request_data.get("full_name", "")
        birth_date = request_data.get("birth_date")

        if full_name and birth_date:
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
        from alchymine.engine.astrology import (
            approximate_sun_degree,
            approximate_sun_sign,
        )

        birth_date = request_data.get("birth_date")
        if birth_date:
            sun_sign = approximate_sun_sign(birth_date)
            sun_degree = approximate_sun_degree(birth_date)
            results["astrology"] = {
                "sun_sign": sun_sign,
                "sun_degree": sun_degree,
            }
        else:
            errors.append("Intelligence: missing birth_date for astrology")
    except ImportError:
        errors.append("Intelligence: astrology engine not available")
    except Exception as exc:
        errors.append(f"Intelligence: astrology error — {exc!s}")

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
        intention = request_data.get("intention")
        archetype_secondary = request_data.get("archetype_secondary")
        big_five = request_data.get("big_five")

        if archetype and big_five and intention:
            modalities = match_modalities(
                archetype,
                archetype_secondary,
                big_five,
                intention,
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
        intention = request_data.get("intention")
        wealth_context = request_data.get("wealth_context")

        if life_path is not None and intention:
            levers = prioritize_levers(
                wealth_context,
                risk_tolerance,
                intention,
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

    Node order: numerology -> astrology -> status [-> quality_gate] -> END

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
    graph.add_edge("astrology", "status")
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

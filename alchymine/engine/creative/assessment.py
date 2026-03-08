"""Creative assessment engine — Guilford scoring, Creative DNA, orientation.

All functions are deterministic (pure). No LLM calls.

Frameworks referenced:
- J. P. Guilford's Structure of Intellect model (1967) — divergent thinking
  components: fluency, flexibility, originality, elaboration, sensitivity,
  redefinition.
- Twyla Tharp's "Creative Habit" dimensions — structure vs. improvisation,
  collaboration vs. solitude, sensory mode, convergent vs. divergent thinking,
  peak creative time.
"""

from __future__ import annotations

from alchymine.engine.profile import CreativeDNA, GuilfordScores

# ─── Guilford Assessment ─────────────────────────────────────────────────

# Response keys expected for each Guilford component.
# Each key maps to a list of question IDs whose scores are averaged.
_GUILFORD_QUESTION_MAP: dict[str, list[str]] = {
    "fluency": ["guil_flu1", "guil_flu2", "guil_flu3"],
    "flexibility": ["guil_flex1", "guil_flex2", "guil_flex3"],
    "originality": ["guil_orig1", "guil_orig2", "guil_orig3"],
    "elaboration": ["guil_elab1", "guil_elab2", "guil_elab3"],
    "sensitivity": ["guil_sens1", "guil_sens2", "guil_sens3"],
    "redefinition": ["guil_redef1", "guil_redef2", "guil_redef3"],
}


def assess_guilford(responses: dict) -> GuilfordScores:
    """Score divergent thinking from assessment responses.

    Parameters
    ----------
    responses:
        Dictionary mapping question IDs to numeric scores (0-100).
        Expected keys follow the pattern ``{component}_{n}`` where
        component is one of: fluency, flexibility, originality,
        elaboration, sensitivity, redefinition and n is 1-3.

        Alternatively, responses can contain the component names directly
        (e.g., ``{"fluency": 75, "flexibility": 60, ...}``), in which case
        the values are used as-is.

    Returns
    -------
    GuilfordScores
        Pydantic model with scores clamped to [0, 100].
    """
    scores: dict[str, float] = {}

    for component, question_ids in _GUILFORD_QUESTION_MAP.items():
        # Check for direct component-level scores first
        if component in responses and not any(q in responses for q in question_ids):
            raw = float(responses[component])
            scores[component] = _clamp(raw, 0.0, 100.0)
        else:
            # Average across individual question scores
            values = [float(responses[q]) for q in question_ids if q in responses]
            if values:
                avg = sum(values) / len(values)
                scores[component] = _clamp(avg, 0.0, 100.0)
            else:
                scores[component] = 0.0

    return GuilfordScores(**scores)


# ─── Creative DNA Assessment ─────────────────────────────────────────────

# Question keys for each Creative DNA dimension.
_DNA_QUESTION_MAP: dict[str, list[str]] = {
    "structure_vs_improvisation": ["dna_structure_1", "dna_structure_2"],
    "collaboration_vs_solitude": ["dna_collab_1", "dna_collab_2"],
    "convergent_vs_divergent": ["dna_convergent_1", "dna_convergent_2"],
}

_VALID_SENSORY_MODES = {"visual", "verbal", "kinesthetic", "musical"}
_VALID_PEAK_TIMES = {"morning", "evening"}


def assess_creative_dna(responses: dict) -> CreativeDNA:
    """Derive Tharp-inspired creative preference dimensions from responses.

    Parameters
    ----------
    responses:
        Dictionary mapping question IDs to values.

        Continuous dimensions (0-1 scale):
        - ``dna_structure_1``, ``dna_structure_2`` — averaged for
          structure_vs_improvisation
        - ``dna_collab_1``, ``dna_collab_2`` — averaged for
          collaboration_vs_solitude
        - ``dna_convergent_1``, ``dna_convergent_2`` — averaged for
          convergent_vs_divergent

        Alternatively, the dimension names can be used directly
        (e.g., ``{"structure_vs_improvisation": 0.7, ...}``).

        Categorical:
        - ``primary_sensory_mode``: "visual" | "verbal" | "kinesthetic"
          | "musical" (default "visual")
        - ``creative_peak``: "morning" | "evening" (default "morning")

    Returns
    -------
    CreativeDNA
        Pydantic model with dimension values clamped to [0, 1].
    """
    dims: dict[str, float] = {}

    for dim, question_ids in _DNA_QUESTION_MAP.items():
        if dim in responses and not any(q in responses for q in question_ids):
            raw = float(responses[dim])
            dims[dim] = _clamp(raw, 0.0, 1.0)
        else:
            values = [float(responses[q]) for q in question_ids if q in responses]
            if values:
                dims[dim] = _clamp(sum(values) / len(values), 0.0, 1.0)
            else:
                dims[dim] = 0.5  # neutral default

    # Categorical dimensions
    sensory = str(responses.get("primary_sensory_mode", "visual")).lower()
    if sensory not in _VALID_SENSORY_MODES:
        sensory = "visual"

    peak = str(responses.get("creative_peak", "morning")).lower()
    if peak not in _VALID_PEAK_TIMES:
        peak = "morning"

    return CreativeDNA(
        structure_vs_improvisation=dims["structure_vs_improvisation"],
        collaboration_vs_solitude=dims["collaboration_vs_solitude"],
        convergent_vs_divergent=dims["convergent_vs_divergent"],
        primary_sensory_mode=sensory,
        creative_peak=peak,
    )


# ─── Creative Orientation from Life Path ──────────────────────────────────

# Mapping from Life Path number to creative orientation.
# Master numbers (11, 22, 33) have distinct orientations.
_LIFE_PATH_ORIENTATION: dict[int, str] = {
    1: "Pioneer Creator",
    2: "Collaborative Harmonizer",
    3: "Expressive Artist",
    4: "Structural Designer",
    5: "Experiential Explorer",
    6: "Nurturing Creator",
    7: "Contemplative Analyst",
    8: "Strategic Producer",
    9: "Universal Visionary",
    11: "Intuitive Innovator",
    22: "Master Builder",
    33: "Inspirational Teacher",
}


def derive_creative_orientation(life_path: int) -> str:
    """Map a Life Path number to a creative orientation label.

    Parameters
    ----------
    life_path:
        Life Path number (1-9, 11, 22, or 33).

    Returns
    -------
    str
        Human-readable creative orientation label.

    Raises
    ------
    ValueError
        If *life_path* is not a recognized value.
    """
    if life_path in _LIFE_PATH_ORIENTATION:
        return _LIFE_PATH_ORIENTATION[life_path]

    raise ValueError(f"Invalid life_path {life_path}. Must be 1-9, 11, 22, or 33.")


# ─── Helpers ──────────────────────────────────────────────────────────────


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the range [lo, hi]."""
    return max(lo, min(hi, value))

"""Style analysis — fingerprint generation, strengths, growth areas, mediums.

All functions are deterministic (pure). No LLM calls.

References:
- J. P. Guilford (1967), *The Nature of Human Intelligence*.
- Twyla Tharp (2003), *The Creative Habit*.
"""

from __future__ import annotations

from alchymine.engine.profile import CreativeDNA, GuilfordScores

# ─── Constants ────────────────────────────────────────────────────────────

# Human-readable labels for each Guilford component.
_GUILFORD_LABELS: dict[str, str] = {
    "fluency": "Idea Generation (Fluency)",
    "flexibility": "Adaptive Thinking (Flexibility)",
    "originality": "Original Thinking (Originality)",
    "elaboration": "Detail Development (Elaboration)",
    "sensitivity": "Problem Detection (Sensitivity)",
    "redefinition": "Repurposing Ability (Redefinition)",
}

# Map from Guilford component to recommended creative mediums.
_COMPONENT_MEDIUMS: dict[str, list[str]] = {
    "fluency": ["brainstorming workshops", "freewriting", "improv comedy"],
    "flexibility": ["mixed-media art", "cross-genre music", "interdisciplinary design"],
    "originality": ["experimental film", "avant-garde poetry", "conceptual art"],
    "elaboration": ["novel writing", "architectural design", "detailed illustration"],
    "sensitivity": ["documentary filmmaking", "investigative journalism", "social commentary art"],
    "redefinition": ["upcycling / found-object art", "remix music", "adaptive reuse design"],
}

# Map from sensory mode to recommended mediums.
_SENSORY_MEDIUMS: dict[str, list[str]] = {
    "visual": ["painting", "photography", "graphic design", "film"],
    "verbal": ["creative writing", "spoken word", "screenwriting", "podcasting"],
    "kinesthetic": ["dance", "sculpture", "ceramics", "woodworking"],
    "musical": ["songwriting", "music production", "sound design", "DJing"],
}

# Map from structure preference to mediums.
_STRUCTURE_MEDIUMS: dict[str, list[str]] = {
    "structured": ["architectural design", "technical writing", "classical music composition"],
    "improvisational": ["jazz improvisation", "improv comedy", "abstract painting"],
}


# ─── Public API ───────────────────────────────────────────────────────────


def generate_style_fingerprint(guilford: GuilfordScores, dna: CreativeDNA) -> dict:
    """Combine Guilford scores and Creative DNA into a unified style profile.

    Returns
    -------
    dict
        Keys:
        - ``guilford_summary``: dict of component → {"score", "label", "tier"}
        - ``dna_summary``: dict of dimension → description string
        - ``dominant_components``: list of top 3 Guilford component names
        - ``creative_style``: one-sentence style description
        - ``overall_score``: float (average of all Guilford components)
    """
    guilford_dict = _guilford_to_dict(guilford)

    # Build guilford summary
    guilford_summary: dict[str, dict] = {}
    for comp, score in guilford_dict.items():
        guilford_summary[comp] = {
            "score": score,
            "label": _GUILFORD_LABELS.get(comp, comp),
            "tier": _score_tier(score),
        }

    # Sort components by score descending
    sorted_components = sorted(guilford_dict, key=guilford_dict.get, reverse=True)  # type: ignore[arg-type]
    dominant = sorted_components[:3]

    # DNA summary
    dna_summary = {
        "work_style": _work_style_label(dna.structure_vs_improvisation),
        "social_mode": _social_mode_label(dna.collaboration_vs_solitude),
        "thinking_mode": _thinking_mode_label(dna.convergent_vs_divergent),
        "sensory_mode": dna.primary_sensory_mode,
        "creative_peak": dna.creative_peak,
    }

    # Overall score
    scores = list(guilford_dict.values())
    overall = sum(scores) / len(scores) if scores else 0.0

    # Creative style sentence
    style = _build_style_sentence(dominant, dna)

    return {
        "guilford_summary": guilford_summary,
        "dna_summary": dna_summary,
        "dominant_components": dominant,
        "creative_style": style,
        "overall_score": round(overall, 1),
    }


def identify_strengths(guilford: GuilfordScores) -> list[str]:
    """Return the top 3 creative strengths based on Guilford scores.

    Returns
    -------
    list[str]
        Up to 3 human-readable strength labels, ordered highest first.
    """
    guilford_dict = _guilford_to_dict(guilford)
    sorted_components = sorted(guilford_dict, key=guilford_dict.get, reverse=True)  # type: ignore[arg-type]

    strengths: list[str] = []
    for comp in sorted_components[:3]:
        score = guilford_dict[comp]
        if score > 0:
            strengths.append(_GUILFORD_LABELS[comp])
    return strengths


def identify_growth_areas(guilford: GuilfordScores) -> list[str]:
    """Return the bottom 3 areas for creative development.

    Returns
    -------
    list[str]
        Up to 3 human-readable growth area labels, ordered lowest first.
    """
    guilford_dict = _guilford_to_dict(guilford)
    sorted_components = sorted(guilford_dict, key=guilford_dict.get)  # type: ignore[arg-type]

    areas: list[str] = []
    for comp in sorted_components[:3]:
        score = guilford_dict[comp]
        if score < 100:
            areas.append(_GUILFORD_LABELS[comp])
    return areas


def suggest_mediums(dna: CreativeDNA, guilford: GuilfordScores) -> list[str]:
    """Recommend creative mediums based on DNA and Guilford profile.

    Combines recommendations from:
    - Top 2 Guilford components (skill-based mediums)
    - Primary sensory mode (sensory-based mediums)
    - Structure preference (work-style-based mediums)

    Returns
    -------
    list[str]
        Deduplicated list of recommended creative mediums (up to 8).
    """
    mediums: list[str] = []

    # Top 2 Guilford components
    guilford_dict = _guilford_to_dict(guilford)
    sorted_comps = sorted(guilford_dict, key=guilford_dict.get, reverse=True)  # type: ignore[arg-type]
    for comp in sorted_comps[:2]:
        mediums.extend(_COMPONENT_MEDIUMS.get(comp, [])[:2])

    # Sensory mode
    sensory_mediums = _SENSORY_MEDIUMS.get(dna.primary_sensory_mode, [])
    mediums.extend(sensory_mediums[:2])

    # Structure preference
    if dna.structure_vs_improvisation < 0.35:
        mediums.extend(_STRUCTURE_MEDIUMS["structured"][:1])
    elif dna.structure_vs_improvisation > 0.65:
        mediums.extend(_STRUCTURE_MEDIUMS["improvisational"][:1])

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for m in mediums:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    return unique[:8]


# ─── Helpers ──────────────────────────────────────────────────────────────


def _guilford_to_dict(g: GuilfordScores) -> dict[str, float]:
    """Convert GuilfordScores to a plain dict."""
    return {
        "fluency": g.fluency,
        "flexibility": g.flexibility,
        "originality": g.originality,
        "elaboration": g.elaboration,
        "sensitivity": g.sensitivity,
        "redefinition": g.redefinition,
    }


def _score_tier(score: float) -> str:
    """Classify a 0-100 score into a tier label."""
    if score >= 80:
        return "exceptional"
    if score >= 60:
        return "strong"
    if score >= 40:
        return "developing"
    if score >= 20:
        return "emerging"
    return "nascent"


def _work_style_label(value: float) -> str:
    """Human-readable label for the structure-improvisation axis."""
    if value < 0.3:
        return "highly structured"
    if value < 0.5:
        return "moderately structured"
    if value < 0.7:
        return "moderately improvisational"
    return "highly improvisational"


def _social_mode_label(value: float) -> str:
    """Human-readable label for the collaboration-solitude axis."""
    if value < 0.3:
        return "highly collaborative"
    if value < 0.5:
        return "moderately collaborative"
    if value < 0.7:
        return "moderately solitary"
    return "highly solitary"


def _thinking_mode_label(value: float) -> str:
    """Human-readable label for the convergent-divergent axis."""
    if value < 0.3:
        return "strongly convergent"
    if value < 0.5:
        return "moderately convergent"
    if value < 0.7:
        return "moderately divergent"
    return "strongly divergent"


def _build_style_sentence(dominant: list[str], dna: CreativeDNA) -> str:
    """Build a one-sentence creative style description."""
    if not dominant:
        return "Creative style not yet assessed."

    top = _GUILFORD_LABELS.get(dominant[0], dominant[0])
    work = _work_style_label(dna.structure_vs_improvisation)
    social = _social_mode_label(dna.collaboration_vs_solitude)
    sensory = dna.primary_sensory_mode

    return (
        f"A {work}, {social} creator whose greatest strength is "
        f"{top}, with a {sensory} sensory orientation."
    )

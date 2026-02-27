"""Collaboration matching — compatibility scoring and complementary strengths.

All functions are deterministic (pure). No LLM calls.
"""

from __future__ import annotations

from alchymine.engine.profile import CreativeDNA, GuilfordScores

# ─── Constants ────────────────────────────────────────────────────────────

# Human-readable labels for Guilford components.
_GUILFORD_LABELS: dict[str, str] = {
    "fluency": "Idea Generation (Fluency)",
    "flexibility": "Adaptive Thinking (Flexibility)",
    "originality": "Original Thinking (Originality)",
    "elaboration": "Detail Development (Elaboration)",
    "sensitivity": "Problem Detection (Sensitivity)",
    "redefinition": "Repurposing Ability (Redefinition)",
}


# ─── Public API ───────────────────────────────────────────────────────────


def compatibility_score(dna_a: CreativeDNA, dna_b: CreativeDNA) -> float:
    """Calculate creative compatibility between two people (0-1).

    Compatibility is highest when the pair shares a similar working style
    but has complementary thinking modes. The algorithm weights:

    - Same-direction preference on structure/improvisation: +weight
      (collaborators who share workspace habits work better together)
    - Complementary convergent/divergent thinking: +weight
      (one generates ideas, the other refines — a productive pairing)
    - Compatible social mode: +weight
      (both need to be open enough to collaboration)
    - Shared sensory mode: +bonus
      (shared creative language)
    - Same peak time: +bonus
      (practical scheduling compatibility)

    Parameters
    ----------
    dna_a, dna_b:
        CreativeDNA profiles for the two collaborators.

    Returns
    -------
    float
        Score between 0.0 and 1.0. Higher = more compatible.
    """
    score = 0.0

    # 1. Structure compatibility (weight: 0.25)
    #    Similar structure preferences → better collaboration
    structure_diff = abs(dna_a.structure_vs_improvisation - dna_b.structure_vs_improvisation)
    score += 0.25 * (1.0 - structure_diff)

    # 2. Convergent/divergent complementarity (weight: 0.25)
    #    Moderate difference is ideal (one divergent, one convergent)
    cd_diff = abs(dna_a.convergent_vs_divergent - dna_b.convergent_vs_divergent)
    # Optimal difference is ~0.5; score peaks there
    cd_complement = 1.0 - abs(cd_diff - 0.5) * 2.0
    score += 0.25 * max(0.0, cd_complement)

    # 3. Social mode compatibility (weight: 0.20)
    #    Both should lean collaborative (low values) for best pairing.
    #    Average of how collaborative each person is.
    collab_a = 1.0 - dna_a.collaboration_vs_solitude  # 1 = fully collaborative
    collab_b = 1.0 - dna_b.collaboration_vs_solitude
    social_compat = (collab_a + collab_b) / 2.0
    score += 0.20 * social_compat

    # 4. Shared sensory mode (weight: 0.15)
    if dna_a.primary_sensory_mode == dna_b.primary_sensory_mode:
        score += 0.15

    # 5. Same creative peak time (weight: 0.15)
    if dna_a.creative_peak == dna_b.creative_peak:
        score += 0.15

    return round(max(0.0, min(1.0, score)), 3)


def complementary_strengths(
    guilford_a: GuilfordScores,
    guilford_b: GuilfordScores,
) -> dict:
    """Identify what each collaborator brings to the partnership.

    For each Guilford component, the person with the higher score is
    designated as the lead for that area.

    Parameters
    ----------
    guilford_a, guilford_b:
        GuilfordScores for each collaborator.

    Returns
    -------
    dict
        Keys:
        - ``person_a_leads``: list of component labels where A is stronger
        - ``person_b_leads``: list of component labels where B is stronger
        - ``shared_strengths``: list of components where both score >= 60
        - ``shared_growth``: list of components where both score < 40
        - ``synergy_score``: float 0-1 indicating how well they complement
    """
    a_dict = _guilford_to_dict(guilford_a)
    b_dict = _guilford_to_dict(guilford_b)

    a_leads: list[str] = []
    b_leads: list[str] = []
    shared_strengths: list[str] = []
    shared_growth: list[str] = []

    complementarity_sum = 0.0
    component_count = 0

    for comp in a_dict:
        label = _GUILFORD_LABELS[comp]
        sa = a_dict[comp]
        sb = b_dict[comp]

        if sa > sb:
            a_leads.append(label)
        elif sb > sa:
            b_leads.append(label)
        # If equal, neither leads — falls through

        if sa >= 60 and sb >= 60:
            shared_strengths.append(label)
        if sa < 40 and sb < 40:
            shared_growth.append(label)

        # Complementarity: how well do their scores cover different areas?
        # A pair that covers all areas well has high synergy.
        combined = max(sa, sb)
        complementarity_sum += combined
        component_count += 1

    # Synergy: average of max(A, B) per component, normalized to 0-1
    synergy = (complementarity_sum / (component_count * 100.0)) if component_count > 0 else 0.0

    return {
        "person_a_leads": a_leads,
        "person_b_leads": b_leads,
        "shared_strengths": shared_strengths,
        "shared_growth": shared_growth,
        "synergy_score": round(synergy, 3),
    }


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

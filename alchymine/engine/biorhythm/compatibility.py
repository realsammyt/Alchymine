"""Biorhythm compatibility — compare two people's biorhythm cycles.

Computes per-cycle similarity and an overall synchronization percentage
between two individuals on a given target date.

Evidence rating: LOW
"""

from __future__ import annotations

from datetime import date

from alchymine.engine.biorhythm.calculator import (
    EVIDENCE_RATING,
    METHODOLOGY_NOTE,
    BiorhythmResult,
    calculate_biorhythm,
)


def _cycle_similarity(value_a: float, value_b: float) -> float:
    """Compute similarity between two cycle values as a percentage (0-100).

    Uses the complement of the absolute difference scaled to 0-100.
    When both values are identical, similarity is 100%.
    When they are maximally different (e.g., +1 vs -1), similarity is 0%.
    """
    # Max possible difference is 2.0 (from -1 to +1)
    diff = abs(value_a - value_b)
    return round((1.0 - diff / 2.0) * 100, 2)


def sync_percentage(result_a: BiorhythmResult, result_b: BiorhythmResult) -> float:
    """Calculate overall biorhythm synchronization between two results.

    Returns the average similarity across all three cycles as a percentage (0-100).
    """
    physical_sim = _cycle_similarity(result_a.physical, result_b.physical)
    emotional_sim = _cycle_similarity(result_a.emotional, result_b.emotional)
    intellectual_sim = _cycle_similarity(result_a.intellectual, result_b.intellectual)
    return round((physical_sim + emotional_sim + intellectual_sim) / 3.0, 2)


def biorhythm_compatibility(
    birth_date_a: date,
    birth_date_b: date,
    target_date: date,
) -> dict:
    """Compare two people's biorhythm cycles on a given date.

    Args:
        birth_date_a: Person A's date of birth.
        birth_date_b: Person B's date of birth.
        target_date: The date to compare biorhythms on.

    Returns:
        Dict with keys:
            - person_a: BiorhythmResult for person A
            - person_b: BiorhythmResult for person B
            - physical_similarity: float (0-100)
            - emotional_similarity: float (0-100)
            - intellectual_similarity: float (0-100)
            - overall_sync: float (0-100)
            - evidence_rating: str
            - methodology_note: str
    """
    result_a = calculate_biorhythm(birth_date_a, target_date)
    result_b = calculate_biorhythm(birth_date_b, target_date)

    physical_sim = _cycle_similarity(result_a.physical, result_b.physical)
    emotional_sim = _cycle_similarity(result_a.emotional, result_b.emotional)
    intellectual_sim = _cycle_similarity(result_a.intellectual, result_b.intellectual)

    return {
        "person_a": result_a,
        "person_b": result_b,
        "physical_similarity": physical_sim,
        "emotional_similarity": emotional_sim,
        "intellectual_similarity": intellectual_sim,
        "overall_sync": sync_percentage(result_a, result_b),
        "evidence_rating": EVIDENCE_RATING,
        "methodology_note": METHODOLOGY_NOTE,
    }

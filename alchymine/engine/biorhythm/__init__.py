"""Biorhythm engine — deterministic sine-wave cycle calculations.

Public API:
    calculate_biorhythm   — single-day calculation
    calculate_range       — multi-day range for charting
    find_critical_days    — zero-crossing detection
    find_peak_days        — maxima/minima detection
    biorhythm_compatibility — two-person comparison
    sync_percentage       — overall synchronization score
    BiorhythmResult       — result model

Constants:
    PHYSICAL_CYCLE, EMOTIONAL_CYCLE, INTELLECTUAL_CYCLE — cycle lengths
    CRITICAL_THRESHOLD    — zero-crossing tolerance
    EVIDENCE_RATING       — "LOW"
    METHODOLOGY_NOTE      — transparency disclosure

Evidence rating: LOW
Methodology note: Biorhythm theory is not supported by scientific consensus.
Results are provided for entertainment and self-reflection.
"""

from alchymine.engine.biorhythm.calculator import (
    CRITICAL_THRESHOLD,
    EMOTIONAL_CYCLE,
    EVIDENCE_RATING,
    INTELLECTUAL_CYCLE,
    METHODOLOGY_NOTE,
    PHYSICAL_CYCLE,
    BiorhythmResult,
    calculate_biorhythm,
)
from alchymine.engine.biorhythm.compatibility import (
    biorhythm_compatibility,
    sync_percentage,
)
from alchymine.engine.biorhythm.range_calc import (
    calculate_range,
    find_critical_days,
    find_peak_days,
)

__all__ = [
    "BiorhythmResult",
    "CRITICAL_THRESHOLD",
    "EMOTIONAL_CYCLE",
    "EVIDENCE_RATING",
    "INTELLECTUAL_CYCLE",
    "METHODOLOGY_NOTE",
    "PHYSICAL_CYCLE",
    "biorhythm_compatibility",
    "calculate_biorhythm",
    "calculate_range",
    "find_critical_days",
    "find_peak_days",
    "sync_percentage",
]

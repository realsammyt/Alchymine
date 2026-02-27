"""Healing modality engine — Phase 2 of Alchymine.

Public API:
    ModalityDefinition      — Frozen dataclass defining a healing modality
    MODALITY_REGISTRY       — Dict of all 15 modality definitions
    match_modalities        — Recommend modalities for a user profile
    BreathworkPattern       — Frozen dataclass defining a breathwork pattern
    BREATHWORK_PATTERNS     — Dict of all 6 breathwork patterns
    get_breathwork_pattern  — Select a breathwork pattern by difficulty/intention
"""

from .breathwork import BREATHWORK_PATTERNS, BreathworkPattern, get_breathwork_pattern
from .matcher import match_modalities
from .modalities import MODALITY_REGISTRY, ModalityDefinition

__all__ = [
    "BREATHWORK_PATTERNS",
    "BreathworkPattern",
    "MODALITY_REGISTRY",
    "ModalityDefinition",
    "get_breathwork_pattern",
    "match_modalities",
]

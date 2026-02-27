"""Healing modality engine — Phase 2 of Alchymine.

Public API:
    ModalityDefinition      — Frozen dataclass defining a healing modality
    MODALITY_REGISTRY       — Dict of all 15 modality definitions
    match_modalities        — Recommend modalities for a user profile
    BreathworkPattern       — Frozen dataclass defining a breathwork pattern
    BREATHWORK_PATTERNS     — Dict of all 6 breathwork patterns
    get_breathwork_pattern  — Select a breathwork pattern by difficulty/intention
    CrisisResponse          — Dataclass for crisis detection results
    CrisisSeverity          — Enum for crisis severity levels
    CRISIS_KEYWORDS         — List of crisis-related terms
    detect_crisis           — Scan text for crisis keywords
    get_crisis_resources    — Return standard crisis resources
    process_assessment      — Process intake assessment responses
"""

from .assessment import process_assessment
from .breathwork import BREATHWORK_PATTERNS, BreathworkPattern, get_breathwork_pattern
from .crisis import (
    CRISIS_KEYWORDS,
    CrisisResource,
    CrisisResponse,
    CrisisSeverity,
    detect_crisis,
    get_crisis_resources,
)
from .matcher import match_modalities
from .modalities import MODALITY_REGISTRY, ModalityDefinition

__all__ = [
    "BREATHWORK_PATTERNS",
    "BreathworkPattern",
    "CRISIS_KEYWORDS",
    "CrisisResource",
    "CrisisResponse",
    "CrisisSeverity",
    "MODALITY_REGISTRY",
    "ModalityDefinition",
    "detect_crisis",
    "get_breathwork_pattern",
    "get_crisis_resources",
    "match_modalities",
    "process_assessment",
]

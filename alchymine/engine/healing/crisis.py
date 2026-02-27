"""Crisis detection and response for the healing assessment pipeline.

Scans free-text responses for crisis-related keywords and returns
appropriate resources, severity levels, and mandatory disclaimers.
All healing outputs that touch user wellbeing must pass through
crisis detection before delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# ─── Severity levels ────────────────────────────────────────────────


class CrisisSeverity(StrEnum):
    """Severity tiers for crisis detection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


# ─── Crisis keywords grouped by severity ────────────────────────────

# Emergency-level keywords — immediate danger to life
_EMERGENCY_KEYWORDS: list[str] = [
    "suicidal",
    "suicide",
    "kill myself",
    "end my life",
    "want to die",
    "planning to die",
    "self-harm",
    "self harm",
    "cutting myself",
    "overdose",
    "hurt myself",
]

# High-severity keywords — serious safety concern
_HIGH_KEYWORDS: list[str] = [
    "abuse",
    "abused",
    "abusing",
    "domestic violence",
    "sexual assault",
    "rape",
    "trafficking",
    "stalking",
    "being beaten",
    "violent partner",
    "child abuse",
    "elder abuse",
]

# Medium-severity keywords — significant distress
_MEDIUM_KEYWORDS: list[str] = [
    "hopeless",
    "helpless",
    "worthless",
    "can't go on",
    "no reason to live",
    "severe anxiety",
    "panic attack",
    "eating disorder",
    "substance abuse",
    "addiction",
    "alcoholism",
    "relapse",
    "psychosis",
    "hallucinating",
    "voices in my head",
    "dissociating",
]

# Combined flat list for public access
CRISIS_KEYWORDS: list[str] = _EMERGENCY_KEYWORDS + _HIGH_KEYWORDS + _MEDIUM_KEYWORDS


# ─── Crisis resources ───────────────────────────────────────────────


@dataclass(frozen=True)
class CrisisResource:
    """A single crisis resource entry."""

    name: str
    contact: str
    description: str


_STANDARD_RESOURCES: tuple[CrisisResource, ...] = (
    CrisisResource(
        name="988 Suicide & Crisis Lifeline",
        contact="Call or text 988",
        description="Free, confidential 24/7 support for people in suicidal crisis or emotional distress.",
    ),
    CrisisResource(
        name="Crisis Text Line",
        contact="Text HOME to 741741",
        description="Free 24/7 crisis counseling via text message.",
    ),
    CrisisResource(
        name="National Domestic Violence Hotline",
        contact="1-800-799-7233",
        description="24/7 confidential support for victims of domestic violence.",
    ),
    CrisisResource(
        name="SAMHSA National Helpline",
        contact="1-800-662-4357",
        description=(
            "Free, confidential 24/7 treatment referral and information "
            "for substance use and mental health disorders."
        ),
    ),
    CrisisResource(
        name="Emergency Services",
        contact="Call 911",
        description="For immediate life-threatening emergencies.",
    ),
)

_STANDARD_DISCLAIMER: str = (
    "This is not a substitute for professional help. If you or someone you "
    "know is in immediate danger, please contact emergency services (911) or "
    "the 988 Suicide & Crisis Lifeline immediately."
)


# ─── CrisisResponse dataclass ───────────────────────────────────────


@dataclass(frozen=True)
class CrisisResponse:
    """Response object returned when crisis keywords are detected."""

    severity: CrisisSeverity
    matched_keywords: tuple[str, ...]
    resources: tuple[CrisisResource, ...]
    disclaimers: tuple[str, ...] = field(default=(_STANDARD_DISCLAIMER,))


# ─── Public API ─────────────────────────────────────────────────────


def get_crisis_resources() -> list[CrisisResource]:
    """Return the standard list of crisis resources.

    Always includes hotline numbers for suicide prevention, domestic
    violence, substance abuse, and emergency services.
    """
    return list(_STANDARD_RESOURCES)


def detect_crisis(text: str) -> CrisisResponse | None:
    """Scan free-text input for crisis-related keywords.

    Parameters
    ----------
    text:
        The user's free-text response to scan.

    Returns
    -------
    CrisisResponse | None
        A CrisisResponse with severity, matched keywords, resources,
        and disclaimers if any crisis keywords are found. Returns None
        if no crisis indicators are detected.

    The function performs case-insensitive matching. If multiple severity
    levels are matched, the highest severity takes precedence.
    """
    if not text or not text.strip():
        return None

    text_lower = text.lower()

    # Collect matches per severity
    emergency_matches: list[str] = []
    high_matches: list[str] = []
    medium_matches: list[str] = []

    for keyword in _EMERGENCY_KEYWORDS:
        if keyword in text_lower:
            emergency_matches.append(keyword)

    for keyword in _HIGH_KEYWORDS:
        if keyword in text_lower:
            high_matches.append(keyword)

    for keyword in _MEDIUM_KEYWORDS:
        if keyword in text_lower:
            medium_matches.append(keyword)

    all_matches = emergency_matches + high_matches + medium_matches

    if not all_matches:
        return None

    # Determine severity — highest takes precedence
    if emergency_matches:
        severity = CrisisSeverity.EMERGENCY
    elif high_matches:
        severity = CrisisSeverity.HIGH
    else:
        severity = CrisisSeverity.MEDIUM

    return CrisisResponse(
        severity=severity,
        matched_keywords=tuple(all_matches),
        resources=_STANDARD_RESOURCES,
        disclaimers=(_STANDARD_DISCLAIMER,),
    )

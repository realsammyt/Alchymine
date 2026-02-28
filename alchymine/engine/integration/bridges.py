"""Cross-system bridge engine — data flows between the five systems.

Each bridge maps insights from one system to actionable recommendations
in another. Bridges are deterministic and explainable — never LLM-generated.

The seven cross-system skills (XS-01..XS-07) from the PRD:
- XS-01: archetype-to-creative-style mapping
- XS-02: shadow-to-block-mapping
- XS-03: cycle-to-timing-mapping
- XS-04: wealth-creative-alignment
- XS-05: healing-to-perspective-sequencing
- XS-06: cross-system-coherence-check
- XS-07: user-profile-synthesis
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BridgeInsight:
    """A single cross-system insight."""

    source_system: str
    target_system: str
    bridge_type: str
    insight: str
    action: str
    confidence: float  # 0-1


@dataclass
class BridgeResult:
    """Result of a cross-system bridge analysis."""

    bridges: list[BridgeInsight] = field(default_factory=list)
    coherence_score: float = 0.0
    conflicts: list[str] = field(default_factory=list)


# ── XS-01: Archetype → Creative Style ─────────────────────────────

_ARCHETYPE_CREATIVE_MAP: dict[str, dict[str, str]] = {
    "Creator": {
        "style": "generative",
        "medium": "visual arts, writing, music composition",
        "strength": "original idea generation",
        "growth": "finishing and releasing work",
    },
    "Explorer": {
        "style": "experimental",
        "medium": "mixed media, travel writing, documentary",
        "strength": "cross-domain synthesis",
        "growth": "depth over breadth",
    },
    "Sage": {
        "style": "analytical",
        "medium": "essays, research, data visualization",
        "strength": "conceptual frameworks",
        "growth": "emotional expression",
    },
    "Hero": {
        "style": "narrative-driven",
        "medium": "storytelling, filmmaking, performance",
        "strength": "compelling structure",
        "growth": "vulnerability in work",
    },
    "Magician": {
        "style": "transformative",
        "medium": "digital art, interactive media, design",
        "strength": "vision and innovation",
        "growth": "practical execution",
    },
    "Ruler": {
        "style": "strategic",
        "medium": "architecture, systems design, curation",
        "strength": "organizing creative projects",
        "growth": "spontaneity and play",
    },
    "Caregiver": {
        "style": "nurturing",
        "medium": "teaching, memoir, community art",
        "strength": "empathetic storytelling",
        "growth": "creating for self vs. others",
    },
    "Innocent": {
        "style": "intuitive",
        "medium": "poetry, watercolor, folk art",
        "strength": "authentic simplicity",
        "growth": "embracing complexity",
    },
    "Jester": {
        "style": "playful",
        "medium": "comedy, satire, game design",
        "strength": "surprising perspective shifts",
        "growth": "depth beneath humor",
    },
    "Everyperson": {
        "style": "relatable",
        "medium": "blogging, crafts, photography",
        "strength": "accessible communication",
        "growth": "finding unique voice",
    },
    "Rebel": {
        "style": "disruptive",
        "medium": "street art, punk, protest art",
        "strength": "challenging conventions",
        "growth": "constructive alternatives",
    },
    "Lover": {
        "style": "sensory",
        "medium": "dance, fashion, culinary arts",
        "strength": "aesthetic sensitivity",
        "growth": "intellectual rigor",
    },
}


def archetype_to_creative_style(archetype: str) -> BridgeInsight:
    """XS-01: Map a Jungian archetype to creative style recommendations."""
    mapping = _ARCHETYPE_CREATIVE_MAP.get(archetype)
    if mapping is None:
        return BridgeInsight(
            source_system="intelligence",
            target_system="creative",
            bridge_type="archetype_to_creative",
            insight=f"Archetype '{archetype}' doesn't have a specific creative mapping.",
            action="Explore the Creative Assessment to discover your creative style.",
            confidence=0.3,
        )

    return BridgeInsight(
        source_system="intelligence",
        target_system="creative",
        bridge_type="archetype_to_creative",
        insight=(
            f"Your {archetype} archetype suggests a {mapping['style']} creative style. "
            f"Your strength is {mapping['strength']}, and your growth edge is {mapping['growth']}."
        ),
        action=f"Explore: {mapping['medium']}",
        confidence=0.75,
    )


# ── XS-02: Shadow → Creative Block ────────────────────────────────

_SHADOW_BLOCK_MAP: dict[str, dict[str, str]] = {
    "Creator": {
        "block_type": "perfectionism",
        "pattern": "Endless revision without releasing",
        "intervention": "Set a 'good enough' threshold and ship",
    },
    "Explorer": {
        "block_type": "distraction",
        "pattern": "Starting many projects, finishing none",
        "intervention": "Commit to one project for 30 days before exploring new ones",
    },
    "Sage": {
        "block_type": "analysis_paralysis",
        "pattern": "Over-researching instead of creating",
        "intervention": "Set a research cap (e.g., 2 hours) then create",
    },
    "Hero": {
        "block_type": "burnout",
        "pattern": "Pushing through exhaustion, ignoring rest needs",
        "intervention": "Schedule recovery days as non-negotiable",
    },
    "Magician": {
        "block_type": "imposter_syndrome",
        "pattern": "Feeling your work isn't transformative enough",
        "intervention": "Share work-in-progress to normalize imperfection",
    },
    "Ruler": {
        "block_type": "control",
        "pattern": "Micromanaging creative process, stifling spontaneity",
        "intervention": "Try freewriting or improvisational exercises",
    },
    "Caregiver": {
        "block_type": "self_neglect",
        "pattern": "Creating only for others, never for yourself",
        "intervention": "Dedicate one creative session per week to personal projects",
    },
    "Jester": {
        "block_type": "avoidance",
        "pattern": "Using humor to avoid vulnerable creative expression",
        "intervention": "Write or create one serious piece to explore depth",
    },
    "Rebel": {
        "block_type": "resistance",
        "pattern": "Rejecting all feedback as conformity pressure",
        "intervention": "Seek feedback from one trusted creative ally",
    },
    "Lover": {
        "block_type": "comparison",
        "pattern": "Comparing your work to others' finished pieces",
        "intervention": "Practice creating without viewing others' work for a week",
    },
}


def shadow_to_block_mapping(shadow_archetype: str) -> BridgeInsight:
    """XS-02: Map shadow archetype to likely creative block patterns."""
    mapping = _SHADOW_BLOCK_MAP.get(shadow_archetype)
    if mapping is None:
        return BridgeInsight(
            source_system="intelligence",
            target_system="creative",
            bridge_type="shadow_to_block",
            insight="No specific block pattern identified for this shadow archetype.",
            action="Take the Creative Block Diagnosis to identify your patterns.",
            confidence=0.3,
        )

    return BridgeInsight(
        source_system="intelligence",
        target_system="creative",
        bridge_type="shadow_to_block",
        insight=(
            f"Your {shadow_archetype} shadow may manifest as {mapping['block_type']}. "
            f"Pattern: {mapping['pattern']}"
        ),
        action=mapping["intervention"],
        confidence=0.7,
    )


# ── XS-03: Numerology Cycle → Timing ──────────────────────────────

_PERSONAL_YEAR_TIMING: dict[int, dict[str, str]] = {
    1: {"creative": "Start new creative projects", "wealth": "Launch new income streams"},
    2: {"creative": "Collaborate on creative work", "wealth": "Build partnerships"},
    3: {"creative": "Express freely, experiment widely", "wealth": "Network and promote"},
    4: {"creative": "Develop craft and technique", "wealth": "Build systems and foundations"},
    5: {"creative": "Break conventions, try new mediums", "wealth": "Diversify income sources"},
    6: {"creative": "Create for community and family", "wealth": "Focus on family wealth"},
    7: {"creative": "Deepen artistic practice solo", "wealth": "Research investments"},
    8: {"creative": "Monetize creative work", "wealth": "Scale and expand wealth"},
    9: {"creative": "Complete and release major works", "wealth": "Review and consolidate"},
}


def cycle_to_timing(personal_year: int) -> BridgeInsight:
    """XS-03: Map numerology personal year to timing recommendations."""
    year = personal_year if personal_year in _PERSONAL_YEAR_TIMING else (personal_year % 9 or 9)
    timing = _PERSONAL_YEAR_TIMING.get(year, {})

    actions = []
    if "creative" in timing:
        actions.append(f"Creative: {timing['creative']}")
    if "wealth" in timing:
        actions.append(f"Wealth: {timing['wealth']}")

    return BridgeInsight(
        source_system="intelligence",
        target_system="creative",
        bridge_type="cycle_to_timing",
        insight=f"Personal Year {personal_year}: This is a year for {', '.join(actions).lower()}.",
        action="; ".join(actions) if actions else "Follow your natural rhythm.",
        confidence=0.65,
    )


# ── XS-04: Wealth ↔ Creative Alignment ────────────────────────────


def wealth_creative_alignment(
    wealth_archetype: str,
    creative_style: str,
) -> BridgeInsight:
    """XS-04: Find alignment between wealth and creative approaches."""
    # Revenue stream suggestions based on creative style
    revenue_map: dict[str, str] = {
        "generative": "licensing, print-on-demand, commissions",
        "experimental": "grants, residencies, workshop facilitation",
        "analytical": "consulting, courses, publishing",
        "narrative-driven": "content creation, speaking, book deals",
        "transformative": "premium experiences, brand collaborations",
        "strategic": "creative direction, agency work, curation fees",
        "nurturing": "coaching, community memberships, teaching",
        "playful": "entertainment, brand partnerships, merchandise",
        "disruptive": "crowdfunding, limited editions, community patronage",
        "sensory": "luxury goods, experiential events, custom work",
        "intuitive": "artisanal goods, commissions, patron support",
        "relatable": "content creation, affiliate partnerships, courses",
    }

    streams = revenue_map.get(creative_style, "diverse revenue streams")

    return BridgeInsight(
        source_system="wealth",
        target_system="creative",
        bridge_type="wealth_creative_alignment",
        insight=(
            f"As a {wealth_archetype} wealth archetype with a {creative_style} creative style, "
            f"your most natural revenue streams are: {streams}."
        ),
        action=f"Explore monetization through {streams.split(',')[0].strip()}.",
        confidence=0.6,
    )


# ── XS-05: Healing → Perspective Sequencing ───────────────────────


def healing_to_perspective_sequence(
    healing_modality: str,
    kegan_stage: int,
) -> BridgeInsight:
    """XS-05: Sequence healing work before perspective expansion."""
    # Higher Kegan stages can handle more challenging reframes
    if kegan_stage <= 2:
        approach = "gentle exploration"
        sequence = "Start with grounding healing practices before any reframing work."
    elif kegan_stage == 3:
        approach = "supported inquiry"
        sequence = (
            "Use healing to build safety, then explore perspective shifts in a supportive context."
        )
    elif kegan_stage == 4:
        approach = "autonomous exploration"
        sequence = "Integrate healing insights with your own perspective-taking practice."
    else:
        approach = "meta-cognitive synthesis"
        sequence = "Use healing and perspective work interchangeably as complementary practices."

    return BridgeInsight(
        source_system="healing",
        target_system="perspective",
        bridge_type="healing_to_perspective",
        insight=(
            f"At Kegan stage {kegan_stage}, your readiness for perspective work is: {approach}. "
            f"{sequence}"
        ),
        action=f"Start with {healing_modality} before exploring cognitive reframing.",
        confidence=0.7,
    )


# ── XS-06: Cross-System Coherence ─────────────────────────────────


def check_coherence(
    active_recommendations: list[dict[str, str]],
) -> BridgeResult:
    """XS-06: Check for conflicts between active cross-system recommendations.

    Ensures no more than 3 active suggestions (per PRD) and resolves
    contradictory advice between systems.
    """
    conflicts: list[str] = []
    bridges: list[BridgeInsight] = []

    # Check for conflicting advice
    systems_advising_rest = []
    systems_advising_action = []

    for rec in active_recommendations:
        action = rec.get("action", "").lower()
        system = rec.get("system", "unknown")
        if any(w in action for w in ["rest", "pause", "recover", "ground", "slow"]):
            systems_advising_rest.append(system)
        if any(w in action for w in ["launch", "start", "push", "scale", "expand"]):
            systems_advising_action.append(system)

    if systems_advising_rest and systems_advising_action:
        conflicts.append(
            f"Conflict: {', '.join(systems_advising_rest)} recommend rest while "
            f"{', '.join(systems_advising_action)} recommend action. "
            f"Resolution: prioritize rest before taking action."
        )

    # Limit to 3 active suggestions (PRD requirement)
    if len(active_recommendations) > 3:
        conflicts.append(
            f"Too many active suggestions ({len(active_recommendations)}). "
            f"Maximum is 3 per session. Prioritize the top 3 by relevance."
        )

    # Calculate coherence score
    if not active_recommendations:
        coherence = 1.0
    elif conflicts:
        coherence = max(0.3, 1.0 - 0.2 * len(conflicts))
    else:
        coherence = 1.0

    return BridgeResult(
        bridges=bridges,
        coherence_score=coherence,
        conflicts=conflicts,
    )


# ── XS-07: User Profile Synthesis ─────────────────────────────────


def synthesize_profile(
    numerology: dict | None = None,
    archetype: dict | None = None,
    personality: dict | None = None,
    wealth_archetype: str | None = None,
    creative_style: str | None = None,
    kegan_stage: int | None = None,
) -> list[BridgeInsight]:
    """XS-07: Synthesize cross-system insights from the full user profile.

    Runs all applicable bridges and returns a unified list of insights.
    """
    insights: list[BridgeInsight] = []

    # XS-01: Archetype → Creative
    if archetype and archetype.get("primary"):
        insights.append(archetype_to_creative_style(archetype["primary"]))

    # XS-02: Shadow → Block
    if archetype and archetype.get("shadow"):
        insights.append(shadow_to_block_mapping(archetype["shadow"]))

    # XS-03: Cycle → Timing
    if numerology and numerology.get("personal_year"):
        insights.append(cycle_to_timing(numerology["personal_year"]))

    # XS-04: Wealth ↔ Creative
    if wealth_archetype and creative_style:
        insights.append(wealth_creative_alignment(wealth_archetype, creative_style))

    # XS-05: Healing → Perspective
    if kegan_stage is not None:
        modality = "breathwork"  # Default starting modality
        insights.append(healing_to_perspective_sequence(modality, kegan_stage))

    return insights

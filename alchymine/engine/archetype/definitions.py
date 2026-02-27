"""Complete Jungian archetype definitions for all 12 archetypes.

Each archetype definition includes light qualities, shadow qualities,
creative style, wealth tendency, healing affinity, communication style,
and leadership style. These definitions are the reference data used by
the mapping engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from alchymine.engine.profile import ArchetypeType


@dataclass(frozen=True)
class ArchetypeDefinition:
    """Full definition of a single Jungian archetype."""

    archetype: ArchetypeType
    light_qualities: tuple[str, ...]
    shadow_qualities: tuple[str, ...]
    creative_style: str
    wealth_tendency: str
    healing_affinity: tuple[str, ...]
    communication_style: str
    leadership_style: str
    shadow_label: str  # concise label for the primary shadow pattern


# ─── The 12 Archetype Definitions ──────────────────────────────────────


CREATOR = ArchetypeDefinition(
    archetype=ArchetypeType.CREATOR,
    light_qualities=(
        "Visionary imagination",
        "Craftsmanship",
        "Aesthetic sensitivity",
        "Innovation",
        "Self-expression",
    ),
    shadow_qualities=(
        "Perfectionism preventing completion",
        "Self-doubt about originality",
        "Creative narcissism",
        "Procrastination disguised as refinement",
    ),
    creative_style=(
        "Transforms ideas into tangible art; works through iterative craft, "
        "building layer upon layer until the inner vision is externalized"
    ),
    wealth_tendency=(
        "Invests in tools, education, and aesthetic experiences; "
        "may undervalue own work or oscillate between feast and famine"
    ),
    healing_affinity=("art therapy", "journaling", "movement", "sound healing"),
    communication_style="Expressive, metaphor-rich, visual storytelling",
    leadership_style="Leads by inspiring with original vision and creative courage",
    shadow_label="Perfectionism",
)

SAGE = ArchetypeDefinition(
    archetype=ArchetypeType.SAGE,
    light_qualities=(
        "Wisdom",
        "Philosophical inquiry",
        "Analytical depth",
        "Discernment",
        "Truth-seeking",
    ),
    shadow_qualities=(
        "Cynicism blocking risk-taking",
        "Analysis paralysis",
        "Intellectual elitism",
        "Detachment from embodied experience",
    ),
    creative_style=(
        "Pursues truth through philosophical inquiry; creates through research, "
        "synthesis, and the elegant articulation of complex ideas"
    ),
    wealth_tendency=(
        "Favours evidence-based investing; may over-research and miss "
        "time-sensitive opportunities due to need for certainty"
    ),
    healing_affinity=("meditation", "bibliotherapy", "contemplative practice", "breathwork"),
    communication_style="Precise, thoughtful, evidence-based, Socratic questioning",
    leadership_style="Leads through knowledge, mentorship, and strategic insight",
    shadow_label="Cynicism",
)

EXPLORER = ArchetypeDefinition(
    archetype=ArchetypeType.EXPLORER,
    light_qualities=(
        "Adventurousness",
        "Boundary-pushing",
        "Resourcefulness",
        "Independence",
        "Cultural curiosity",
    ),
    shadow_qualities=(
        "Restlessness preventing depth",
        "Commitment avoidance",
        "Chronic dissatisfaction with the present",
        "Escapism disguised as seeking",
    ),
    creative_style=(
        "Pushes boundaries through experimentation; creates by venturing "
        "into uncharted territory and cross-pollinating disciplines"
    ),
    wealth_tendency=(
        "Drawn to alternative and international investments; "
        "may scatter resources across too many ventures without follow-through"
    ),
    healing_affinity=("nature immersion", "adventure therapy", "breathwork", "movement"),
    communication_style="Energetic, story-driven, connecting disparate ideas",
    leadership_style="Leads by charting new paths and inspiring autonomy",
    shadow_label="Restlessness",
)

MYSTIC = ArchetypeDefinition(
    archetype=ArchetypeType.MYSTIC,
    light_qualities=(
        "Transcendent awareness",
        "Transformative vision",
        "Intuition",
        "Catalytic presence",
        "Spiritual depth",
    ),
    shadow_qualities=(
        "Inflation and grandiosity",
        "Spiritual bypassing",
        "Manipulation through charisma",
        "Disconnection from mundane reality",
    ),
    creative_style=(
        "Seeks transcendent experience; creates through channeling deeper "
        "currents, ritual, and the alchemical transformation of raw material"
    ),
    wealth_tendency=(
        "Attracted to impact investing and conscious capitalism; "
        "may neglect practical financial foundations for spiritual pursuits"
    ),
    healing_affinity=("meditation", "energy work", "breathwork", "plant medicine", "ritual"),
    communication_style="Evocative, symbolic, invitational, uses parable and metaphor",
    leadership_style="Leads through vision, transformation, and catalysing shifts",
    shadow_label="Grandiosity",
)

RULER = ArchetypeDefinition(
    archetype=ArchetypeType.RULER,
    light_qualities=(
        "Strategic mastery",
        "Organizational excellence",
        "Responsibility",
        "Stability-building",
        "Ambitious vision",
    ),
    shadow_qualities=(
        "Rigidity and control",
        "Authoritarianism",
        "Fear of chaos leading to micro-management",
        "Difficulty delegating",
    ),
    creative_style=(
        "Creates ambitious large-scale works; builds systems, empires, "
        "and enduring structures through disciplined execution"
    ),
    wealth_tendency=(
        "Excels at wealth accumulation and empire-building; "
        "may become overly controlling with resources or risk-averse"
    ),
    healing_affinity=("structured programs", "executive coaching", "somatic work", "breathwork"),
    communication_style="Commanding, clear, decisive, results-oriented",
    leadership_style="Leads through structure, accountability, and decisive authority",
    shadow_label="Rigidity",
)

LOVER = ArchetypeDefinition(
    archetype=ArchetypeType.LOVER,
    light_qualities=(
        "Emotional depth",
        "Passionate engagement",
        "Empathy",
        "Sensory richness",
        "Relational attunement",
    ),
    shadow_qualities=(
        "Co-dependency on validation",
        "Emotional overwhelm",
        "Boundary dissolution",
        "People-pleasing at the expense of self",
    ),
    creative_style=(
        "Creates through emotional depth; art emerges from the intensity "
        "of feeling, intimate connection, and the beauty of vulnerability"
    ),
    wealth_tendency=(
        "Generous and relational with money; may overspend on loved ones "
        "or struggle to negotiate fair compensation"
    ),
    healing_affinity=("art therapy", "somatic work", "couples work", "movement", "ritual"),
    communication_style="Warm, emotionally resonant, deeply personal, heart-centred",
    leadership_style="Leads through connection, inspiration, and emotional intelligence",
    shadow_label="Co-dependency",
)

HERO = ArchetypeDefinition(
    archetype=ArchetypeType.HERO,
    light_qualities=(
        "Courage",
        "Determination",
        "Resilience",
        "Protectiveness",
        "Inspirational drive",
    ),
    shadow_qualities=(
        "Competitive comparison",
        "Burnout from over-striving",
        "Win-at-all-costs mentality",
        "Inability to show vulnerability",
    ),
    creative_style=(
        "Inspires and challenges; creates works that push limits, "
        "confront obstacles, and demonstrate mastery through effort"
    ),
    wealth_tendency=(
        "High-energy wealth builder; may take excessive risks "
        "or tie self-worth to financial achievement"
    ),
    healing_affinity=("physical challenge", "breathwork", "movement", "martial arts"),
    communication_style="Direct, motivational, action-oriented, rallying",
    leadership_style="Leads from the front through courage, action, and personal example",
    shadow_label="Competitive comparison",
)

CAREGIVER = ArchetypeDefinition(
    archetype=ArchetypeType.CAREGIVER,
    light_qualities=(
        "Nurturing presence",
        "Community-building",
        "Generosity",
        "Loyalty",
        "Compassionate service",
    ),
    shadow_qualities=(
        "Self-neglect and martyrdom",
        "Enabling dependency in others",
        "Resentment from unreciprocated giving",
        "Difficulty receiving",
    ),
    creative_style=(
        "Nurturing community-building; creates through service, "
        "fostering others' growth, and building supportive environments"
    ),
    wealth_tendency=(
        "Prioritises security for family and community; "
        "may under-invest in personal wealth due to guilt about self-focus"
    ),
    healing_affinity=("group work", "nurturing practices", "nature immersion", "journaling"),
    communication_style="Warm, supportive, patient, attentive listening",
    leadership_style="Leads through service, empowerment, and creating safety",
    shadow_label="Self-neglect",
)

JESTER = ArchetypeDefinition(
    archetype=ArchetypeType.JESTER,
    light_qualities=(
        "Playfulness",
        "Subversive wit",
        "Joy cultivation",
        "Perspective-shifting",
        "Social ease",
    ),
    shadow_qualities=(
        "Avoidance of depth and seriousness",
        "Using humour as a deflection",
        "Fear of being seen as ordinary",
        "Sabotaging intimacy with jokes",
    ),
    creative_style=(
        "Creates through playfulness and subversion; uses humour, satire, "
        "and unexpected juxtapositions to reveal hidden truths"
    ),
    wealth_tendency=(
        "Unconventional financial strategies; may be overly casual "
        "about money or use humour to avoid financial planning"
    ),
    healing_affinity=("laughter therapy", "play therapy", "movement", "improvisation"),
    communication_style="Witty, irreverent, disarming, uses humour to illuminate",
    leadership_style="Leads by challenging norms, reducing tension, and fostering joy",
    shadow_label="Avoidance of depth",
)

INNOCENT = ArchetypeDefinition(
    archetype=ArchetypeType.INNOCENT,
    light_qualities=(
        "Optimism",
        "Wonder",
        "Faith",
        "Purity of vision",
        "Renewal capacity",
    ),
    shadow_qualities=(
        "Naivety and gullibility",
        "Denial of shadow or complexity",
        "Passivity disguised as trust",
        "Avoidance of conflict",
    ),
    creative_style=(
        "Creates from optimism and wonder; art emerges from beginner's mind, "
        "fresh perspectives, and the courage to see beauty in simplicity"
    ),
    wealth_tendency=(
        "Trusting with finances; may be vulnerable to scams or "
        "fail to protect wealth through inadequate due diligence"
    ),
    healing_affinity=("nature immersion", "guided meditation", "gentle yoga", "art therapy"),
    communication_style="Open, sincere, hopeful, emphasising possibility",
    leadership_style="Leads through trust, moral clarity, and infectious optimism",
    shadow_label="Naivety",
)

REBEL = ArchetypeDefinition(
    archetype=ArchetypeType.REBEL,
    light_qualities=(
        "Revolutionary courage",
        "Authenticity",
        "System disruption",
        "Liberation instinct",
        "Counter-cultural vision",
    ),
    shadow_qualities=(
        "Destruction without construction",
        "Rebellion for its own sake",
        "Alienation from community",
        "Self-destructive patterns",
    ),
    creative_style=(
        "Disrupts established forms; creates by breaking rules, "
        "challenging conventions, and forging radically new expressions"
    ),
    wealth_tendency=(
        "Drawn to disruption-based wealth (startups, crypto); "
        "may sabotage stable income out of anti-establishment instinct"
    ),
    healing_affinity=("somatic work", "breathwork", "movement", "expressive arts"),
    communication_style="Provocative, direct, challenging, unapologetic",
    leadership_style="Leads through disruption, radical honesty, and breaking barriers",
    shadow_label="Destruction without construction",
)

EVERYMAN = ArchetypeDefinition(
    archetype=ArchetypeType.EVERYMAN,
    light_qualities=(
        "Accessibility",
        "Relatability",
        "Belonging",
        "Egalitarian spirit",
        "Practical groundedness",
    ),
    shadow_qualities=(
        "Blandness from fear of standing out",
        "Suppression of unique gifts",
        "Conformity over authenticity",
        "Victim mentality",
    ),
    creative_style=(
        "Creates accessible, relatable work; art that speaks to the common "
        "human experience, democratising beauty and meaning"
    ),
    wealth_tendency=(
        "Steady, conventional financial approach; may avoid ambitious "
        "wealth goals out of fear of seeming greedy or standing out"
    ),
    healing_affinity=("group work", "community practices", "journaling", "walking meditation"),
    communication_style="Down-to-earth, inclusive, common-sense, unpretentious",
    leadership_style="Leads through consensus, inclusion, and shared ownership",
    shadow_label="Blandness from fear",
)


# ─── Registry ──────────────────────────────────────────────────────────

ARCHETYPE_DEFINITIONS: dict[ArchetypeType, ArchetypeDefinition] = {
    ArchetypeType.CREATOR: CREATOR,
    ArchetypeType.SAGE: SAGE,
    ArchetypeType.EXPLORER: EXPLORER,
    ArchetypeType.MYSTIC: MYSTIC,
    ArchetypeType.RULER: RULER,
    ArchetypeType.LOVER: LOVER,
    ArchetypeType.HERO: HERO,
    ArchetypeType.CAREGIVER: CAREGIVER,
    ArchetypeType.JESTER: JESTER,
    ArchetypeType.INNOCENT: INNOCENT,
    ArchetypeType.REBEL: REBEL,
    ArchetypeType.EVERYMAN: EVERYMAN,
}


# ─── Mapping tables ───────────────────────────────────────────────────

# Life Path number -> primary archetype tendency
LIFE_PATH_TO_ARCHETYPE: dict[int, ArchetypeType] = {
    1: ArchetypeType.HERO,
    2: ArchetypeType.CAREGIVER,
    3: ArchetypeType.CREATOR,
    4: ArchetypeType.RULER,
    5: ArchetypeType.EXPLORER,
    6: ArchetypeType.LOVER,
    7: ArchetypeType.SAGE,
    8: ArchetypeType.RULER,
    9: ArchetypeType.MYSTIC,
    11: ArchetypeType.MYSTIC,
    22: ArchetypeType.RULER,
    33: ArchetypeType.CAREGIVER,
}

# Zodiac signs grouped by element
FIRE_SIGNS: frozenset[str] = frozenset({"Aries", "Leo", "Sagittarius"})
EARTH_SIGNS: frozenset[str] = frozenset({"Taurus", "Virgo", "Capricorn"})
AIR_SIGNS: frozenset[str] = frozenset({"Gemini", "Libra", "Aquarius"})
WATER_SIGNS: frozenset[str] = frozenset({"Cancer", "Scorpio", "Pisces"})

# Element -> archetypes that get boosted
ELEMENT_ARCHETYPE_BOOSTS: dict[str, tuple[ArchetypeType, ...]] = {
    "fire": (ArchetypeType.HERO, ArchetypeType.EXPLORER),
    "earth": (ArchetypeType.RULER, ArchetypeType.CAREGIVER),
    "air": (ArchetypeType.SAGE, ArchetypeType.JESTER),
    "water": (ArchetypeType.LOVER, ArchetypeType.MYSTIC),
}


def get_element_for_sign(sign: str) -> str | None:
    """Return the element ('fire', 'earth', 'air', 'water') for a zodiac sign."""
    normalized = sign.strip().title()
    if normalized in FIRE_SIGNS:
        return "fire"
    if normalized in EARTH_SIGNS:
        return "earth"
    if normalized in AIR_SIGNS:
        return "air"
    if normalized in WATER_SIGNS:
        return "water"
    return None

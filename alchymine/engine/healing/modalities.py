"""Healing modality definitions and registry.

Each modality is defined as a frozen dataclass with metadata including
skill trigger, category, cultural traditions, contraindications, and
evidence level. The MODALITY_REGISTRY provides name-keyed access to
all 15 modalities in the Alchymine healing system.
"""

from __future__ import annotations

from dataclasses import dataclass

from alchymine.engine.profile import PracticeDifficulty


@dataclass(frozen=True)
class ModalityDefinition:
    """Immutable definition of a single healing modality."""

    name: str  # e.g., "breathwork"
    skill_trigger: str  # e.g., "/breathwork"
    category: str  # "somatic", "contemplative", "expressive", "nature", "relational"
    description: str  # Brief 1-2 sentence description
    contraindications: tuple[str, ...]  # e.g., ("severe asthma", "panic disorder")
    min_difficulty: PracticeDifficulty
    traditions: tuple[str, ...]  # Cultural traditions this modality draws from
    evidence_level: str  # "strong", "moderate", "emerging", "traditional"


# ─── The 15 Modality Definitions ─────────────────────────────────────


BREATHWORK = ModalityDefinition(
    name="breathwork",
    skill_trigger="/breathwork",
    category="somatic",
    description=(
        "Conscious breathing techniques that regulate the autonomic nervous "
        "system, reduce stress, and cultivate present-moment awareness."
    ),
    contraindications=("severe asthma", "panic disorder", "uncontrolled epilepsy"),
    min_difficulty=PracticeDifficulty.FOUNDATION,
    traditions=("Pranayama (Yogic)", "Tummo (Tibetan)", "Holotropic (Western)"),
    evidence_level="strong",
)

COHERENCE_MEDITATION = ModalityDefinition(
    name="coherence_meditation",
    skill_trigger="/coherence",
    category="contemplative",
    description=(
        "Heart-brain coherence practice combining rhythmic breathing with "
        "positive emotional focus to synchronise cardiac and neural rhythms."
    ),
    contraindications=("acute psychosis", "severe dissociative disorder"),
    min_difficulty=PracticeDifficulty.FOUNDATION,
    traditions=("HeartMath (Western)", "Metta (Buddhist)", "Hesychasm (Christian)"),
    evidence_level="strong",
)

LANGUAGE_AWARENESS = ModalityDefinition(
    name="language_awareness",
    skill_trigger="/language",
    category="contemplative",
    description=(
        "Practices that reveal how habitual language patterns shape perception, "
        "emotion, and identity, enabling conscious linguistic reframing."
    ),
    contraindications=("active speech therapy for trauma-related mutism",),
    min_difficulty=PracticeDifficulty.DEVELOPING,
    traditions=(
        "General Semantics (Korzybski)",
        "NLP (Western)",
        "Buddhist Right Speech",
    ),
    evidence_level="moderate",
)

RESILIENCE_TRAINING = ModalityDefinition(
    name="resilience_training",
    skill_trigger="/resilience",
    category="somatic",
    description=(
        "Structured practices building psychological and physiological resilience "
        "through graded stress exposure, recovery protocols, and adaptability drills."
    ),
    contraindications=("acute PTSD without clinical supervision", "active suicidal ideation"),
    min_difficulty=PracticeDifficulty.DEVELOPING,
    traditions=(
        "Stoic philosophy (Greco-Roman)",
        "Stress inoculation (Western clinical)",
        "Bushido (Japanese)",
    ),
    evidence_level="strong",
)

CONSCIOUSNESS_JOURNEY = ModalityDefinition(
    name="consciousness_journey",
    skill_trigger="/consciousness",
    category="contemplative",
    description=(
        "Guided exploration of expanded states of consciousness through "
        "meditation, visualisation, and contemplative inquiry without substances."
    ),
    contraindications=(
        "schizophrenia",
        "bipolar disorder (unmedicated)",
        "severe dissociative disorder",
    ),
    min_difficulty=PracticeDifficulty.ESTABLISHED,
    traditions=(
        "Vipassana (Buddhist)",
        "Sufi dhikr (Islamic)",
        "Contemplative prayer (Christian)",
        "Yoga Nidra (Yogic)",
    ),
    evidence_level="moderate",
)

SOUND_HEALING = ModalityDefinition(
    name="sound_healing",
    skill_trigger="/sound",
    category="somatic",
    description=(
        "Therapeutic use of sound frequencies, vibration, and music to "
        "promote relaxation, neural entrainment, and emotional release."
    ),
    contraindications=("sound-triggered epilepsy", "severe hyperacusis"),
    min_difficulty=PracticeDifficulty.FOUNDATION,
    traditions=(
        "Nada Yoga (Indian)",
        "Singing bowls (Tibetan)",
        "Sound bath (Western)",
        "Icaros (Amazonian)",
    ),
    evidence_level="moderate",
)

SOMATIC_PRACTICE = ModalityDefinition(
    name="somatic_practice",
    skill_trigger="/somatic",
    category="somatic",
    description=(
        "Body-centred awareness practices that release stored tension, "
        "process embodied emotion, and restore nervous system regulation."
    ),
    contraindications=(
        "recent major surgery",
        "acute physical injury at practice site",
    ),
    min_difficulty=PracticeDifficulty.DEVELOPING,
    traditions=(
        "Somatic Experiencing (Levine)",
        "Feldenkrais (Western)",
        "Qigong (Chinese)",
        "Yoga (Indian)",
    ),
    evidence_level="strong",
)

SLEEP_HEALING = ModalityDefinition(
    name="sleep_healing",
    skill_trigger="/sleep",
    category="somatic",
    description=(
        "Protocols for improving sleep quality through guided relaxation, "
        "sleep hygiene practices, and pre-sleep contemplative routines."
    ),
    contraindications=("untreated sleep apnoea requiring CPAP",),
    min_difficulty=PracticeDifficulty.FOUNDATION,
    traditions=(
        "Yoga Nidra (Yogic)",
        "CBT-I (Western clinical)",
        "Traditional Chinese Medicine sleep practices",
    ),
    evidence_level="strong",
)

NATURE_HEALING = ModalityDefinition(
    name="nature_healing",
    skill_trigger="/nature",
    category="nature",
    description=(
        "Structured engagement with natural environments to restore attention, "
        "reduce cortisol, and cultivate ecological awareness and connection."
    ),
    contraindications=("severe agoraphobia", "anaphylactic environmental allergies"),
    min_difficulty=PracticeDifficulty.FOUNDATION,
    traditions=(
        "Shinrin-yoku (Japanese forest bathing)",
        "Aboriginal walkabout (Indigenous Australian)",
        "Ecotherapy (Western)",
    ),
    evidence_level="strong",
)

PNI_MAPPING = ModalityDefinition(
    name="pni_mapping",
    skill_trigger="/pni",
    category="somatic",
    description=(
        "Psychoneuroimmunology-informed practices mapping the connections "
        "between mental states, neural pathways, and immune function for "
        "targeted mind-body interventions."
    ),
    contraindications=(
        "active autoimmune flare without medical supervision",
        "immunosuppressive therapy without physician clearance",
    ),
    min_difficulty=PracticeDifficulty.ADVANCED,
    traditions=(
        "Psychoneuroimmunology (Western clinical)",
        "Ayurveda mind-body typology (Indian)",
        "Traditional Chinese Medicine (Chinese)",
    ),
    evidence_level="emerging",
)

GRIEF_HEALING = ModalityDefinition(
    name="grief_healing",
    skill_trigger="/grief",
    category="relational",
    description=(
        "Structured grief processing that honours loss through ritual, "
        "community witnessing, and graduated emotional integration."
    ),
    contraindications=(
        "complicated grief with active suicidal ideation",
        "bereavement within 48 hours (crisis protocol instead)",
    ),
    min_difficulty=PracticeDifficulty.ESTABLISHED,
    traditions=(
        "Worden's grief tasks (Western clinical)",
        "Dia de los Muertos (Mexican)",
        "Sitting shiva (Jewish)",
        "Keening (Celtic)",
    ),
    evidence_level="strong",
)

WATER_HEALING = ModalityDefinition(
    name="water_healing",
    skill_trigger="/water",
    category="nature",
    description=(
        "Therapeutic engagement with water in its many forms — bathing, "
        "immersion, flotation, and water contemplation — for nervous system "
        "regulation and emotional cleansing."
    ),
    contraindications=(
        "aquaphobia (severe)",
        "open wounds or active skin infections",
        "uncontrolled epilepsy near water",
    ),
    min_difficulty=PracticeDifficulty.DEVELOPING,
    traditions=(
        "Onsen (Japanese)",
        "Mikveh (Jewish)",
        "Hydrotherapy (Western naturopathic)",
        "River ceremony (various Indigenous)",
    ),
    evidence_level="moderate",
)

COMMUNITY_HEALING = ModalityDefinition(
    name="community_healing",
    skill_trigger="/community",
    category="relational",
    description=(
        "Group-based healing practices that leverage shared experience, "
        "collective witnessing, and relational repair for transformation."
    ),
    contraindications=(
        "severe social anxiety disorder (unmanaged)",
        "active paranoid ideation",
    ),
    min_difficulty=PracticeDifficulty.DEVELOPING,
    traditions=(
        "Ubuntu (Southern African)",
        "Talking circles (Indigenous North American)",
        "Group therapy (Western clinical)",
        "Sangha (Buddhist)",
    ),
    evidence_level="moderate",
)

EXPRESSIVE_HEALING = ModalityDefinition(
    name="expressive_healing",
    skill_trigger="/expressive",
    category="expressive",
    description=(
        "Creative arts-based healing through visual art, movement, music, "
        "writing, and dramatic expression to access and integrate "
        "pre-verbal and embodied experience."
    ),
    contraindications=(
        "acute psychosis with disorganised expression",
        "severe perfectionism triggering self-harm (clinical assessment needed)",
    ),
    min_difficulty=PracticeDifficulty.DEVELOPING,
    traditions=(
        "Art therapy (Western clinical)",
        "Butoh (Japanese)",
        "Bibliotherapy (Western)",
        "Drum circle (West African / global)",
    ),
    evidence_level="strong",
)

CONTEMPLATIVE_INQUIRY = ModalityDefinition(
    name="contemplative_inquiry",
    skill_trigger="/inquiry",
    category="contemplative",
    description=(
        "Advanced self-inquiry practices that investigate the nature of "
        "consciousness, identity, and meaning through structured "
        "contemplative questioning."
    ),
    contraindications=(
        "active depersonalisation/derealisation disorder",
        "acute existential crisis with suicidal ideation",
    ),
    min_difficulty=PracticeDifficulty.ADVANCED,
    traditions=(
        "Atma Vichara (Advaita Vedanta)",
        "Koan practice (Zen Buddhist)",
        "Socratic method (Greco-Roman)",
        "Ignatian discernment (Jesuit)",
    ),
    evidence_level="traditional",
)


# ─── Registry ────────────────────────────────────────────────────────


MODALITY_REGISTRY: dict[str, ModalityDefinition] = {
    "breathwork": BREATHWORK,
    "coherence_meditation": COHERENCE_MEDITATION,
    "language_awareness": LANGUAGE_AWARENESS,
    "resilience_training": RESILIENCE_TRAINING,
    "consciousness_journey": CONSCIOUSNESS_JOURNEY,
    "sound_healing": SOUND_HEALING,
    "somatic_practice": SOMATIC_PRACTICE,
    "sleep_healing": SLEEP_HEALING,
    "nature_healing": NATURE_HEALING,
    "pni_mapping": PNI_MAPPING,
    "grief_healing": GRIEF_HEALING,
    "water_healing": WATER_HEALING,
    "community_healing": COMMUNITY_HEALING,
    "expressive_healing": EXPRESSIVE_HEALING,
    "contemplative_inquiry": CONTEMPLATIVE_INQUIRY,
}


# ─── Category helpers ────────────────────────────────────────────────


VALID_CATEGORIES: frozenset[str] = frozenset(
    {"somatic", "contemplative", "expressive", "nature", "relational"}
)

VALID_EVIDENCE_LEVELS: frozenset[str] = frozenset({"strong", "moderate", "emerging", "traditional"})


def get_modalities_by_category(category: str) -> list[ModalityDefinition]:
    """Return all modalities in the given category."""
    return [m for m in MODALITY_REGISTRY.values() if m.category == category]


def get_modalities_by_difficulty(
    difficulty: PracticeDifficulty,
) -> list[ModalityDefinition]:
    """Return all modalities at or below the given difficulty level."""
    order = list(PracticeDifficulty)
    max_idx = order.index(difficulty)
    return [m for m in MODALITY_REGISTRY.values() if order.index(m.min_difficulty) <= max_idx]

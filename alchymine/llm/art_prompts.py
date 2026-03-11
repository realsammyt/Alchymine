"""Generative art prompt builders for Alchymine reports.

Builds personalized image generation prompts from user profile data,
mapping archetypes, zodiac signs, and Big Five traits to visual imagery.
"""

from __future__ import annotations

from enum import StrEnum

# ── System presets ───────────────────────────────────────────────────────────


class ArtSystem(StrEnum):
    """The five Alchymine system pillars, each with its own visual style."""

    INTELLIGENCE = "intelligence"
    HEALING = "healing"
    WEALTH = "wealth"
    CREATIVE = "creative"
    PERSPECTIVE = "perspective"


STYLE_PRESETS: dict[str, str] = {
    ArtSystem.INTELLIGENCE: (
        "luminous neural networks, soft blue light, crystalline mind-maps, "
        "intricate geometry, clarity, focused energy, cosmic intelligence"
    ),
    ArtSystem.HEALING: (
        "gentle emerald light, flowing water, botanical elements, warm amber glow, "
        "soft healing energy, sacred geometry, serene sanctuary"
    ),
    ArtSystem.WEALTH: (
        "golden abundance, rich textures, architectural grandeur, flowing rivers of gold, "
        "prosperity symbols, deep amber and jade, generational legacy"
    ),
    ArtSystem.CREATIVE: (
        "vibrant colors, expressive brushstrokes, dynamic composition, layered textures, "
        "artistic inspiration, vivid imagination unleashed, creative fire"
    ),
    ArtSystem.PERSPECTIVE: (
        "wide horizon vistas, multiple vanishing points, layered dimensions, "
        "philosophical depth, cosmic scale, expanded awareness, infinite possibility"
    ),
}

# ── Archetype → visual motif ─────────────────────────────────────────────────

_ARCHETYPE_MOTIFS: dict[str, str] = {
    "the visionary": "ethereal light beams piercing clouds, distant horizon, prophetic imagery",
    "the alchemist": "swirling transformation, lead becoming gold, mystical laboratory, change",
    "the explorer": "uncharted territories, compass rose, ancient maps, adventurous spirit",
    "the creator": "hands shaping clay, painterly swirls, raw creative energy emerging",
    "the sage": "ancient library, deep wisdom, starlit contemplation, scholarly light",
    "the hero": "rising sun, triumphant stance, golden armor, strength and purpose",
    "the caregiver": "warm embrace, nurturing light, community, flowing compassion",
    "the rebel": "breaking chains, electric energy, disruption, bold contrast",
    "the lover": "rose petals, warm crimson light, heart-centered radiance, deep connection",
    "the magician": "sacred geometry, mystical symbols, transformation energy, cosmic power",
    "the ruler": "crown of light, vast domain, order from chaos, dignified authority",
    "the innocent": "golden meadow, soft dawn light, pure beginnings, childlike wonder",
}

# ── Zodiac sign → elemental themes ──────────────────────────────────────────

_ZODIAC_ELEMENTS: dict[str, str] = {
    # Fire signs
    "aries": "fierce flames, warrior energy, rams, crimson and gold, bold dawn",
    "leo": "solar radiance, golden mane, regal fire, sun-drenched savanna",
    "sagittarius": "archer's arrow, purple dusk, philosophical flame, centaur silhouette",
    # Earth signs
    "taurus": "lush green meadows, earth tones, abundant flowers, grounded solidity",
    "virgo": "precise geometry, harvest wheat, soft greens, analytical clarity",
    "capricorn": "mountain peaks, stone and ice, stoic endurance, cool grey dawn",
    # Air signs
    "gemini": "swirling winds, dual reflections, mercury light, quick silver energy",
    "libra": "balanced scales, soft rose light, harmony, elegant symmetry",
    "aquarius": "electric blue currents, futuristic vision, humanitarian light waves",
    # Water signs
    "cancer": "moonlit ocean, silver tides, protective shell, nurturing currents",
    "scorpio": "deep abyss, dark water with luminous depths, transformation, phoenix",
    "pisces": "iridescent ocean depths, dreamlike currents, flowing imagination, sea-light",
}

# ── Big Five trait → mood/atmosphere ────────────────────────────────────────


def _openness_mood(openness: float) -> str:
    if openness >= 75:
        return "surreal and imaginative, dreamlike abstraction, vivid creative atmosphere"
    if openness >= 50:
        return "balanced curiosity, gentle exploration, open and inviting"
    return "grounded and structured, classical composition, serene calm"


def _conscientiousness_mood(conscientiousness: float) -> str:
    if conscientiousness >= 70:
        return "precise detail, ordered elegance, meticulous refinement"
    if conscientiousness >= 40:
        return "balanced structure and flow"
    return "spontaneous energy, organic flow, natural imperfection"


def _extraversion_mood(extraversion: float) -> str:
    if extraversion >= 70:
        return "dynamic energy, vibrant social light, radiant warmth"
    if extraversion >= 40:
        return "comfortable presence, measured warmth"
    return "contemplative solitude, quiet depth, introspective shadows"


# ── Main builder ─────────────────────────────────────────────────────────────


def build_report_hero_prompt(profile: dict) -> str:
    """Build a personalized art prompt for a report hero image.

    Parameters
    ----------
    profile:
        User profile dict. Recognized keys (all optional):

        - ``archetype`` — e.g. ``"The Visionary"``
        - ``zodiac_sign`` — e.g. ``"Pisces"``
        - ``big_five`` — dict with keys ``openness``, ``conscientiousness``,
          ``extraversion`` (float 0–100)
        - ``system`` — one of the :class:`ArtSystem` values

    Returns
    -------
    str
        A rich natural-language prompt for Gemini image generation.
    """
    parts: list[str] = []

    # System style preset
    system_key = str(profile.get("system", "")).lower()
    if system_key in STYLE_PRESETS:
        parts.append(STYLE_PRESETS[system_key])

    # Archetype visual motif
    archetype = str(profile.get("archetype", "")).lower()
    for key, motif in _ARCHETYPE_MOTIFS.items():
        if key in archetype:
            parts.append(motif)
            break

    # Zodiac elemental theme
    zodiac = str(profile.get("zodiac_sign", "")).lower()
    if zodiac in _ZODIAC_ELEMENTS:
        parts.append(_ZODIAC_ELEMENTS[zodiac])

    # Big Five mood
    big_five = profile.get("big_five", {})
    if isinstance(big_five, dict):
        openness = float(big_five.get("openness", 50))
        conscientiousness = float(big_five.get("conscientiousness", 50))
        extraversion = float(big_five.get("extraversion", 50))
        parts.append(_openness_mood(openness))
        parts.append(_conscientiousness_mood(conscientiousness))
        parts.append(_extraversion_mood(extraversion))

    # Fallback when no profile data matched
    if not parts:
        parts.append("luminous personal journey, transformational energy, cosmic tapestry")

    # Universal quality markers
    parts.append(
        "cinematic lighting, ultra-detailed, 8k resolution, award-winning digital art, "
        "no text, no watermarks, full-bleed composition"
    )

    return ", ".join(parts)

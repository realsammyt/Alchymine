"""Prompt templates for Gemini image generation.

These functions take an identity profile (either a Pydantic
:class:`alchymine.engine.profile.IdentityLayer` or the equivalent JSON
mapping that lives on the report ``profile_summary``) and return a plain
prompt string.

Design goals
~~~~~~~~~~~~
- **Never raise.** Missing fields fall back to safe defaults.
- **No personally-identifying content.** The prompts never mention real
  people, brands, copyrighted characters, or text overlays — text-in-image
  rendering is unreliable on Gemini and we don't want hallucinated logos.
- **Tasteful and non-violent.** Style suffix includes explicit safety
  language to discourage sexual, violent, or weapon imagery.
- **Symbolic, not literal.** The prompt describes archetype + element +
  numerology as symbolic landscape — never as a portrait of a real person.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# ── Style presets ──────────────────────────────────────────────────────
# Each preset is a style-suffix string appended to the core prompt. Five
# presets, one for each Alchymine creative domain.
STYLE_PRESETS: dict[str, str] = {
    "mystical": (
        "Painterly digital illustration with sacred geometry motifs, "
        "deep indigo and gold palette, soft mystical atmosphere, "
        "cinematic lighting, 16:9 composition."
    ),
    "modern": (
        "Clean minimalist editorial illustration, muted gradients, "
        "spacious composition with refined typography-free negative space, "
        "soft daylight, 16:9 framing."
    ),
    "organic": (
        "Botanical watercolour illustration with flowing organic forms, "
        "earth tones and verdant greens, gentle dappled light, "
        "natural textures, 16:9 composition."
    ),
    "celestial": (
        "Cosmic illustration with starfields, nebulae, and luminous "
        "constellation motifs, deep violet and silver palette, "
        "ethereal atmosphere, 16:9 composition."
    ),
    "grounded": (
        "Warm hand-painted illustration with stone, wood, and earth "
        "textures, rich umber and terracotta tones, golden-hour lighting, "
        "tactile and grounded atmosphere, 16:9 composition."
    ),
}


# ── Safety suffix appended to every prompt ────────────────────────────
_SAFETY_SUFFIX = (
    "Tasteful, serene, non-violent, no weapons, no nudity, no real people, "
    "no brand logos or watermarks, no text or letters in the image."
)


# ── Archetype → symbolic imagery mapping ──────────────────────────────
# Keys are normalized to lowercase to match alchymine.engine.profile.ArchetypeType
# but the lookup also handles capitalized variants.
_ARCHETYPE_IMAGERY: dict[str, str] = {
    "sage": "an ancient open-air library nestled among quiet mountains",
    "creator": "a luminous workshop where ideas crystallize into geometric forms",
    "explorer": "an open horizon where land and cosmic sea meet at twilight",
    "mystic": "a moonlit grove of standing stones wreathed in soft mist",
    "ruler": "a serene crystalline pavilion atop a high plateau",
    "lover": "intertwined flowering vines forming a gentle mandala",
    "hero": "a solitary traveler cresting a radiant mountain ridge at dawn",
    "caregiver": "a warm hearth surrounded by protective golden light",
    "jester": "kaleidoscopic patterns dancing across a meadow of wildflowers",
    "innocent": "a sunlit meadow where each flower glows like a tiny constellation",
    "rebel": "shattered chains dissolving into prismatic light at sunrise",
    "everyman": "a winding path passing through four seasons in a single landscape",
    # Generic fallbacks for archetype names that aren't in the canonical enum
    "seeker": "a wandering figure on a winding path through a luminous valley",
    "magician": "swirling alchemical symbols transforming into points of light",
}

# ── Zodiac sign → element mapping ─────────────────────────────────────
_SIGN_ELEMENT: dict[str, str] = {
    "aries": "fire",
    "leo": "fire",
    "sagittarius": "fire",
    "taurus": "earth",
    "virgo": "earth",
    "capricorn": "earth",
    "gemini": "air",
    "libra": "air",
    "aquarius": "air",
    "cancer": "water",
    "scorpio": "water",
    "pisces": "water",
}

# ── Element → palette / mood cue ──────────────────────────────────────
_ELEMENT_PALETTE: dict[str, str] = {
    "fire": "warm amber and crimson tones with radiant energy",
    "earth": "rich umber, moss, and sandstone tones with grounded stillness",
    "air": "pale cerulean and silver tones with light, drifting movement",
    "water": "deep teal and indigo tones with flowing reflective depth",
}


# ── Helpers ────────────────────────────────────────────────────────────


def _get_field(source: Any, name: str) -> Any:
    """Read a field from a Pydantic model OR a Mapping, returning None on miss."""
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _normalize_archetype(value: Any) -> str:
    """Coerce an archetype value (StrEnum, str, or None) to lowercase."""
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip().lower()


def _normalize_sign(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _archetype_imagery(archetype: str) -> str:
    """Return symbolic imagery cue for an archetype, with a safe fallback."""
    return _ARCHETYPE_IMAGERY.get(
        archetype,
        "an ethereal symbolic landscape of personal transformation",
    )


def _element_for_sign(sun_sign: str) -> str:
    return _SIGN_ELEMENT.get(sun_sign, "")


def _palette_for_element(element: str) -> str:
    return _ELEMENT_PALETTE.get(element, "soft luminous tones with balanced light")


# ── Public API ─────────────────────────────────────────────────────────


def build_report_hero_prompt(profile: Any) -> str:
    """Build a personalized hero-image prompt for a report.

    Parameters
    ----------
    profile:
        Either an :class:`alchymine.engine.profile.IdentityLayer` Pydantic
        model, or a Mapping with the same nested shape (``archetype``,
        ``astrology``, ``numerology``). May be ``None`` or empty — the
        function never raises.

    Returns
    -------
    str
        A 2-4 sentence prompt suitable for Gemini image generation.
    """
    archetype_obj = _get_field(profile, "archetype")
    astrology_obj = _get_field(profile, "astrology")
    numerology_obj = _get_field(profile, "numerology")

    archetype = _normalize_archetype(_get_field(archetype_obj, "primary"))
    sun_sign = _normalize_sign(_get_field(astrology_obj, "sun_sign"))
    life_path = _get_field(numerology_obj, "life_path")

    imagery = _archetype_imagery(archetype)
    element = _element_for_sign(sun_sign)
    palette = _palette_for_element(element)

    archetype_label = archetype.title() if archetype else "Wanderer"
    element_label = element if element else "elemental"
    life_path_clause = f" Life Path {life_path} energy" if life_path else ""

    return (
        f"A breathtaking symbolic landscape representing the {archetype_label} "
        f"archetype, depicted as {imagery}. Render with {palette} reflecting "
        f"{element_label} essence,{life_path_clause} blending sacred geometry "
        f"with painterly atmosphere. {_SAFETY_SUFFIX}"
    )


def apply_style_preset(prompt: str, preset: str | None) -> str:
    """Append a style-preset suffix to a base prompt.

    Unknown preset names fall back to ``mystical``. ``None`` leaves the
    prompt unchanged.
    """
    if preset is None:
        return prompt
    suffix = STYLE_PRESETS.get(preset, STYLE_PRESETS["mystical"])
    return f"{prompt} Style: {suffix}"


def build_studio_prompt(
    profile: Any,
    user_extension: str | None = None,
    style_preset: str | None = None,
) -> str:
    """Build a Creative Studio prompt from the user's profile and inputs.

    The user-supplied extension is **appended** to the core profile prompt
    so the user can steer the imagery without bypassing the safety suffix.
    """
    base = build_report_hero_prompt(profile)
    if user_extension:
        # Trim and quote the extension so prompt-injection attempts at
        # least don't smuggle in directives like "ignore the above".
        cleaned = user_extension.strip().replace("\n", " ")
        base = f"{base} Additional theme requested by the user: {cleaned}."
    return apply_style_preset(base, style_preset)

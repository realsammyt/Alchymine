"""Build a compact natural-language summary of a user's profile.

The Growth Assistant chat endpoint injects this string into the system
prompt so that every reply is grounded in the user's actual data
(numerology Life Path, sun sign, archetype, top Big Five traits, etc.)
without leaking the entire JSON profile into the LLM context.

The builder is deliberately tolerant of missing fields — early users may
only have completed the intake step, and later users may have all five
layers populated.  When no profile is available the function returns an
empty string and the chat endpoint falls back to a generic system prompt.
"""

from __future__ import annotations

from typing import Any

from alchymine.engine.profile import UserProfile


def build_user_context(profile: UserProfile | None) -> str:
    """Return a short natural-language paragraph describing the user.

    Parameters
    ----------
    profile:
        A populated :class:`UserProfile` instance, or ``None`` if the
        caller has no profile available.

    Returns
    -------
    str
        A multi-line string starting with ``[User Profile Summary]`` and
        listing the most relevant identity data, or an empty string when
        no profile is supplied.
    """
    if profile is None:
        return ""

    lines: list[str] = ["[User Profile Summary]"]

    # Intake basics — name and primary intention.
    intake = profile.intake
    if intake is not None:
        if getattr(intake, "full_name", None):
            lines.append(f"- Name: {intake.full_name}")
        intention = getattr(intake, "intention", None)
        if intention is not None:
            intention_str = intention.value if hasattr(intention, "value") else str(intention)
            lines.append(f"- Primary intention: {intention_str}")

    # Identity layer — numerology, astrology, archetype, personality.
    identity = profile.identity
    if identity is not None:
        num = identity.numerology
        if num is not None:
            master = " (master number)" if num.is_master_number else ""
            lines.append(
                f"- Life Path: {num.life_path}{master}, "
                f"Expression: {num.expression}, "
                f"Personal Year: {num.personal_year}"
            )

        astro = identity.astrology
        if astro is not None:
            astro_parts = [f"Sun {astro.sun_sign}", f"Moon {astro.moon_sign}"]
            if astro.rising_sign:
                astro_parts.append(f"Rising {astro.rising_sign}")
            lines.append(f"- Astrology: {', '.join(astro_parts)}")

        arch = identity.archetype
        if arch is not None:
            primary = arch.primary.value if hasattr(arch.primary, "value") else str(arch.primary)
            arch_line = f"- Primary archetype: {primary}"
            if arch.shadow:
                arch_line += f" (shadow: {arch.shadow})"
            lines.append(arch_line)

        pers = identity.personality
        if pers is not None and pers.big_five is not None:
            top_traits = _top_big_five_traits(pers.big_five)
            if top_traits:
                lines.append(
                    "- Big Five top traits: "
                    + ", ".join(f"{name} ({score:.0f})" for name, score in top_traits)
                )
            attachment = pers.attachment_style
            if attachment is not None:
                attach_str = attachment.value if hasattr(attachment, "value") else str(attachment)
                lines.append(f"- Attachment style: {attach_str}")

        if identity.strengths_map:
            top_strengths = list(identity.strengths_map)[:5]
            lines.append(f"- Top strengths: {', '.join(top_strengths)}")

    # Active plan day — useful so the coach knows where they are in the journey.
    if profile.active_plan_day is not None:
        lines.append(f"- Active plan day: {profile.active_plan_day}/90")

    # If we only emitted the header, treat it as no useful context.
    if len(lines) == 1:
        return ""

    return "\n".join(lines)


def _top_big_five_traits(big_five: Any, n: int = 2) -> list[tuple[str, float]]:
    """Return the top *n* Big Five traits as ``(name, score)`` pairs.

    Sorted descending by score.  Names use the standard psychology
    ordering: openness, conscientiousness, extraversion, agreeableness,
    neuroticism.
    """
    pairs = [
        ("openness", float(big_five.openness)),
        ("conscientiousness", float(big_five.conscientiousness)),
        ("extraversion", float(big_five.extraversion)),
        ("agreeableness", float(big_five.agreeableness)),
        ("neuroticism", float(big_five.neuroticism)),
    ]
    pairs.sort(key=lambda kv: kv[1], reverse=True)
    return pairs[:n]

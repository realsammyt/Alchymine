"""Context builder for the Growth Assistant.

Extracts key user profile facts from a report result dict and formats
them into a compact context block that can be injected into the first
message of a chat session.
"""

from __future__ import annotations


def build_user_context(report_result: dict | None) -> str:
    """Build a compact user-profile context string from report result data.

    Extracts numerology, astrology, archetype, and Big Five personality
    fields from the report's ``profile_summary.identity`` sub-dict and
    formats them as a short bullet list prefixed with
    ``[User Profile Summary]``.

    Parameters
    ----------
    report_result:
        The top-level report result dict (e.g. ``Report.result`` from the
        database), or ``None`` / empty dict if no report is available.

    Returns
    -------
    str
        A multiline context block, or an empty string if no data is present.
    """
    if not report_result:
        return ""

    lines: list[str] = ["[User Profile Summary]"]
    summary = report_result.get("profile_summary", {})
    identity = summary.get("identity", {})

    if not identity:
        return "\n".join(lines)

    num = identity.get("numerology", {})
    if num:
        lines.append(f"- Life Path: {num.get('life_path')}, Expression: {num.get('expression')}")

    astro = identity.get("astrology", {})
    if astro:
        lines.append(f"- Sun: {astro.get('sun_sign')}, Moon: {astro.get('moon_sign')}")

    arch = identity.get("archetype", {})
    if arch:
        lines.append(f"- Primary Archetype: {arch.get('primary')}")

    pers = identity.get("personality", {})
    if pers and pers.get("big_five"):
        bf = pers["big_five"]
        lines.append(
            f"- Big Five: O={bf.get('openness', 0):.0f} "
            f"C={bf.get('conscientiousness', 0):.0f} "
            f"E={bf.get('extraversion', 0):.0f}"
        )

    return "\n".join(lines)

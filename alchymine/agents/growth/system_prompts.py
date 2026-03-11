"""System prompts for the Alchymine Growth Assistant.

Provides a main coach prompt and five specialist variants — one per
Alchymine system — so the assistant can give focused guidance when
the user is working within a specific pillar.
"""

from __future__ import annotations

MAIN_SYSTEM_PROMPT = """You are the Alchymine Growth Assistant, a compassionate personal \
transformation coach. You have access to the user's assessment results across five systems: \
Intelligence, Healing, Wealth, Creative, and Perspective.

Guidelines:
- Draw on the user's specific profile data provided in the conversation context.
- Give concrete, actionable suggestions grounded in their results.
- Never provide medical, financial, or legal advice — recommend professional consultation.
- Keep responses focused and practical (under 300 words unless depth is requested).
- Use warm, direct language. Avoid jargon."""

SYSTEM_PROMPTS: dict[str, str] = {
    "intelligence": MAIN_SYSTEM_PROMPT
    + "\n\nFocus: Personalized Intelligence — numerology, astrology, archetypes, and personality patterns.",
    "healing": MAIN_SYSTEM_PROMPT
    + "\n\nFocus: Ethical Healing — evidence-based modalities, somatic practices, and trauma-informed care.",
    "wealth": MAIN_SYSTEM_PROMPT
    + "\n\nFocus: Generational Wealth — financial patterns, risk tolerance, and wealth-building mindset. Never give specific investment advice.",
    "creative": MAIN_SYSTEM_PROMPT
    + "\n\nFocus: Creative Development — Guilford scores, creative DNA, and expressive practices.",
    "perspective": MAIN_SYSTEM_PROMPT
    + "\n\nFocus: Perspective Enhancement — Kegan stage, mental models, and cognitive reframing.",
}

STARTER_PROMPTS: dict[str, list[str]] = {
    "intelligence": [
        "What does my Life Path number reveal about my current phase?",
        "How do my archetype and sun sign interact?",
        "What's the most important pattern in my personality profile?",
    ],
    "healing": [
        "Which healing modality should I start with given my profile?",
        "How do I begin a somatic practice safely?",
        "What are early warning signs I should watch for?",
    ],
    "wealth": [
        "What does my risk tolerance say about my wealth approach?",
        "How do I start building generational wealth with limited income?",
        "What mindset shifts does my profile suggest I need?",
    ],
    "creative": [
        "What creative expression fits my Guilford scores?",
        "How do I overcome my specific creative blocks?",
        "What daily practice would develop my creative DNA?",
    ],
    "perspective": [
        "What does my Kegan stage mean for my relationships?",
        "Which mental models from my profile should I develop?",
        "How do I work with my identified cognitive distortions?",
    ],
}


def get_system_prompt(system_context: str | None) -> str:
    """Return the appropriate system prompt for the given system context.

    Parameters
    ----------
    system_context:
        One of ``"intelligence"``, ``"healing"``, ``"wealth"``,
        ``"creative"``, ``"perspective"``, or ``None`` for the general prompt.

    Returns
    -------
    str
        The system prompt string to inject into the LLM call.
    """
    if system_context and system_context in SYSTEM_PROMPTS:
        return SYSTEM_PROMPTS[system_context]
    return MAIN_SYSTEM_PROMPT

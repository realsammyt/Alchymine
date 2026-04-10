"""Growth Assistant agent package.

Provides the system prompts and context builder used by the Growth
Assistant chat endpoint (``alchymine/api/routers/chat.py``).  The
Growth Assistant is a per-user AI coach that draws on the unified
:class:`alchymine.engine.profile.UserProfile` to give grounded,
non-judgemental guidance across all five Alchymine systems.
"""

from alchymine.agents.growth.context_builder import build_user_context
from alchymine.agents.growth.system_prompts import (
    MAIN_COACH_PROMPT,
    SYSTEM_PROMPTS,
    build_system_prompt,
    get_system_prompt,
)

__all__ = [
    "MAIN_COACH_PROMPT",
    "SYSTEM_PROMPTS",
    "build_system_prompt",
    "build_user_context",
    "get_system_prompt",
]

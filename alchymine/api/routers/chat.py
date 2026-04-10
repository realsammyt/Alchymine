"""Growth Assistant chat endpoint — SSE streaming with persisted history.

Provides ``POST /api/v1/chat``: an authenticated endpoint that accepts a
single user message, persists it, streams the LLM reply back to the
client as Server-Sent Events, and persists the full assistant reply
when streaming completes.

Safety: the user input is run through the same prompt-injection /
harmful-content patterns used by ``alchymine/api/routers/streaming.py``
before any LLM call is made.  Blocked content returns HTTP 400 with no
LLM round-trip.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.agents.growth.system_prompts import build_system_prompt
from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.llm.client import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Safety patterns (mirrored from streaming.py) ──────────────────────


_BLOCKED_PATTERNS = [
    # Prompt injection
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)",
    r"you\s+are\s+now\s+in\s+",
    r"system\s*:\s*",
    # Harmful intent
    r"(how\s+to\s+)?(make|create|build)\s+(a\s+)?(bomb|weapon|explosive)",
    r"(how\s+to\s+)?(harm|hurt|kill|poison)",
]


# ─── Scope enforcement (off-topic / token-burn protection) ─────────────
#
# The Growth Assistant is a personal transformation coach, not a
# general-purpose LLM.  Off-topic requests (code generation, translation,
# homework lookups, arbitrary summarization) are rejected BEFORE calling
# the LLM so we do not burn API tokens on out-of-scope work.
#
# These patterns are deliberately conservative — they target clear
# abuse cases and must not catch legitimate coaching questions.  The
# test suite (tests/api/test_chat.py::TestChatScopeEnforcement) pins
# both rejection AND allowance cases so regressions in either
# direction are caught.

_OFF_TOPIC_PATTERNS = [
    # Programming-language code generation
    (
        r"\b(write|generate|create|give\s+me|show\s+me|build)\b[^.]{0,60}"
        r"\b(python|javascript|typescript|java|c\+\+|ruby|rust|bash|shell|sql|html|css|php)\s+"
        r"(code|script|function|program|class|method|query|snippet)"
    ),
    # Generic code/program/script request
    (
        r"\b(write|generate|create)\s+(me\s+)?(a\s+|an\s+|some\s+)?"
        r"(script|program|code\s+snippet|regex|regular\s+expression)\b"
    ),
    # Debug / fix / explain external code
    (
        r"\b(debug|fix)\s+(?:\w+\s+){0,3}"
        r"(code|function|script|error|bug|program|stack\s*trace)\b"
    ),
    r"\bexplain\s+(?:\w+\s+){0,3}(code|function|snippet|regex|sql|algorithm)\b",
    # Translation of arbitrary content to another spoken language
    (
        r"\btranslate\b[^.]{0,40}\b(to|into|in)\s+"
        r"(spanish|french|german|chinese|japanese|korean|russian|italian|portuguese|"
        r"arabic|hindi|mandarin|dutch|swedish|polish|turkish|latin|greek)\b"
    ),
    # Math / equation solving
    (
        r"\bsolve\b[^.]{0,40}\b"
        r"(equation|math\s+problem|integral|derivative|calculus|algebra|for\s+x\b)"
    ),
    # Essay / paper / homework writing for external topics
    (
        r"\bwrite\s+(me\s+)?(a|an)\s+"
        r"(essay|research\s+paper|report|thesis|book\s+report)\s+(on|about|for)\s+"
    ),
    # Do my X (school / taxes / admin tasks)
    r"\bdo\s+my\s+(homework|assignment|taxes|essay|report)\b",
    # Pure general-knowledge lookups
    (
        r"\bwhat\s+is\s+the\s+"
        r"(capital|population|gdp|currency|official\s+language|national\s+anthem)\s+of\b"
    ),
    # Summarization of arbitrary external content
    # (note: "summarize my journey" stays legit — this requires an explicit
    # third-party noun like article/document/paper)
    (
        r"\bsummar(ize|ise)\s+(this|the\s+following)\s+"
        r"(article|text|document|passage|paper|book|pdf|email|transcript)"
    ),
]


_OFF_TOPIC_MESSAGE = (
    "The Growth Assistant is focused on personal transformation coaching "
    "(healing, wealth mindset, creative development, perspective work, "
    "intelligence insights). For coding, translation, homework, or general "
    "research, please use a general-purpose assistant. This keeps the "
    "conversation in scope and reduces unnecessary token usage."
)


def _check_content_safety(text: str) -> str | None:
    """Return an error message if *text* matches a blocked pattern, else ``None``."""
    lower = text.lower()
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, lower):
            return "Content flagged by safety filter"
    return None


def _check_on_topic(text: str) -> str | None:
    """Return an error message if *text* is clearly off-topic, else ``None``.

    Runs BEFORE any LLM call so out-of-scope requests never reach Claude.
    """
    lower = text.lower()
    for pattern in _OFF_TOPIC_PATTERNS:
        if re.search(pattern, lower):
            return _OFF_TOPIC_MESSAGE
    return None


# Valid system keys — keep aligned with SYSTEM_PROMPTS in
# alchymine/agents/growth/system_prompts.py.
_VALID_SYSTEM_KEYS = {"intelligence", "healing", "wealth", "creative", "perspective"}


# ─── Request model ─────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """POST /api/v1/chat request body."""

    message: str = Field(..., min_length=1, max_length=2000, description="User chat message")
    system_key: str | None = Field(
        None,
        description=(
            "Optional system scope: intelligence | healing | wealth | "
            "creative | perspective.  None defaults to the general coach."
        ),
    )


# ─── Streaming generator ───────────────────────────────────────────────


async def _chat_event_stream(
    *,
    user_id: str,
    message: str,
    system_key: str | None,
    session: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Stream LLM reply chunks as SSE ``data:`` frames.

    Persists the user message before streaming starts and the full
    assistant message after the stream completes.  Each LLM chunk is
    additionally checked against the safety patterns; the stream is
    truncated and a sentinel emitted if blocked content is detected
    in the model's output.
    """
    # Persist the user message before any LLM round-trip so it's never lost.
    await repository.save_chat_message(
        session,
        user_id=user_id,
        role="user",
        content=message,
        system_key=system_key,
    )
    await session.commit()

    # We don't have a UserProfile loader hooked up here yet — the chat
    # endpoint accepts a system_key for now and the system prompt is
    # selected without per-user context interpolation.  Sprint 5 will
    # wire profile context end-to-end.
    system_prompt = build_system_prompt(system_key, None)

    client = LLMClient()
    full_reply: list[str] = []
    blocked = False

    try:
        async for chunk in client.stream_generate(
            prompt=message,
            system_prompt=system_prompt,
        ):
            full_reply.append(chunk)
            if _check_content_safety("".join(full_reply)) is not None:
                # The model produced something that trips the same safety
                # filter we apply to user input.  Truncate the stream and
                # emit an explicit error frame.
                logger.warning("Chat output blocked by safety filter for user %s", user_id)
                blocked = True
                yield "event: error\ndata: Response blocked by safety filter\n\n"
                break
            yield f"data: {chunk}\n\n"
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Chat streaming failed: %s", exc)
        yield "event: error\ndata: Streaming failed\n\n"

    # Persist the assistant message even when truncated — the partial
    # reply (or the empty string) is part of the conversation history.
    assistant_text = "".join(full_reply)
    if blocked:
        assistant_text = "[response blocked by safety filter]"
    await repository.save_chat_message(
        session,
        user_id=user_id,
        role="assistant",
        content=assistant_text,
        system_key=system_key,
    )
    await session.commit()

    yield "event: done\ndata: \n\n"


# ─── Endpoint ──────────────────────────────────────────────────────────


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream a Growth Assistant chat reply via Server-Sent Events.

    Safety: the user message is checked against the blocked-pattern list
    before any LLM call.  Blocked input returns HTTP 400.

    The response is a ``text/event-stream`` where each LLM chunk is
    delivered as a ``data:`` frame and the stream terminates with an
    ``event: done`` sentinel.

    Both the user message and the full assistant reply are persisted to
    the ``chat_messages`` table for the authenticated user.
    """
    safety_message = _check_content_safety(request.message)
    if safety_message:
        raise HTTPException(status_code=400, detail=safety_message)

    off_topic_message = _check_on_topic(request.message)
    if off_topic_message:
        raise HTTPException(status_code=400, detail=off_topic_message)

    if request.system_key is not None and request.system_key not in _VALID_SYSTEM_KEYS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown system_key {request.system_key!r}. Valid: {sorted(_VALID_SYSTEM_KEYS)}"
            ),
        )

    user_id = current_user["sub"]

    # Ensure the user row exists so the FK constraint on chat_messages
    # is satisfied.  In production the user always exists (auth requires
    # a real account); in tests with the auth dependency overridden we
    # may need to create the test user on demand.
    await _ensure_user_exists(session, user_id)

    return StreamingResponse(
        _chat_event_stream(
            user_id=user_id,
            message=request.message,
            system_key=request.system_key,
            session=session,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _ensure_user_exists(session: AsyncSession, user_id: str) -> None:
    """Create a placeholder ``users`` row if one does not already exist.

    The auth dependency populates ``current_user["sub"]`` from a verified
    JWT, so the user is *known* even if their row hasn't been written
    yet (e.g. very early in the onboarding flow).  Creating an empty
    user row is safe and idempotent.
    """
    from sqlalchemy import select

    from alchymine.db.models import User

    existing = await session.execute(select(User).where(User.id == user_id))
    if existing.scalar_one_or_none() is not None:
        return
    session.add(User(id=user_id))
    await session.flush()
    await session.commit()

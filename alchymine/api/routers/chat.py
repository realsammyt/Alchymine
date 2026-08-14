"""Growth Assistant chat endpoint — SSE streaming with persisted history.

Provides ``POST /api/v1/chat``: an authenticated endpoint that accepts a
single user message, persists it, streams the LLM reply back to the
client as Server-Sent Events, and persists the full assistant reply
when streaming completes.

Safety: the user input is run through prompt-injection and
harmful-content patterns before any LLM call is made.  Blocked content
returns HTTP 400 with no LLM round-trip.

This is the only streaming LLM surface.  The old ``/stream/narrative``
proxy, which took an arbitrary prompt and had no frontend caller, was
removed rather than capped.

Guardrails added in Sprint 5 (#165):
- **History cap**: 200 user messages per user per system_key.  Beyond
  that, new messages are rejected with HTTP 429 and a friendly message
  asking the user to start a fresh conversation.
- **Per-user rate limit**: 10 messages per minute per user, enforced
  with a simple in-memory sliding-window counter (no Redis needed).

The ``practice`` scope (epic #251, slice 5) adds three things nobody
else on this endpoint has, and nothing anybody else on it loses:

- ``detect_crisis`` on the way in, answering high and emergency
  disclosures with resources instead of a coaching reply.
- ``check_text`` on the way out, on a cadence inside the streaming loop.
- A deterministic practice-context block appended to the *user message*,
  never the system prompt.

Removing ``"practice"`` from ``_VALID_SYSTEM_KEYS`` is the kill switch,
and it is worth being exact about what it kills.  The scope 422s, so
there is no LLM call, no ethics gate and no context builder, and the
other five scopes are untouched.  The crisis gate is the deliberate
exception: it reads ``PRACTICE_SYSTEM_KEY`` directly and runs *before*
the validity check, so a crisis-severity message on a killed scope
still receives resources rather than a 422.  That ordering is the point
of the gate.  Answering somebody in crisis with a schema error because
an operator disabled a feature would be the one failure mode this path
exists to prevent, and the resource stream costs nothing to serve.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.agents.growth.practice_context import build_practice_context
from alchymine.agents.growth.system_prompts import build_system_prompt
from alchymine.agents.quality.ethics_check import (
    ViolationCategory,
    ViolationSeverity,
    check_text,
)
from alchymine.api.auth import Account, get_current_user
from alchymine.api.deps import get_db_session
from alchymine.api.entitlements import require_chat
from alchymine.config import get_settings
from alchymine.db import repository
from alchymine.db.usage_counters import CostCeilingExceeded
from alchymine.engine.healing.crisis import CrisisResponse, CrisisSeverity, detect_crisis
from alchymine.llm.attribution import set_request_id
from alchymine.llm.client import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Safety patterns ───────────────────────────────────────────────────


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


# Valid system keys — must equal ``set(SYSTEM_PROMPTS)`` in
# alchymine/agents/growth/system_prompts.py.  A literal rather than a
# derived set, deliberately: removing a key here 422s that scope and
# leaves every other one untouched, which is the kill switch for the
# practice scope.  ``tests/api/test_chat_practice_scope.py`` pins the
# equality so the two literals cannot drift apart in the meantime.
#
# The crisis gate survives the kill switch by design — see the module
# docstring and ``TestKillSwitch``.  Everything else the scope has does
# not.
PRACTICE_SYSTEM_KEY = "practice"

_VALID_SYSTEM_KEYS = {
    "intelligence",
    "healing",
    "wealth",
    "creative",
    "perspective",
    PRACTICE_SYSTEM_KEY,
}


# ─── Practice-scope safety gates ──────────────────────────────────────
#
# The practice scope is the first chat surface wired to the real ethics
# and crisis gates.  The other five keep the local regex they have always
# had; adopting these across five live surfaces changes behaviour on all
# of them and deserves its own PR and regression pass (follow-up filed
# with the epic close-out).

# check_text over the whole accumulation is O(n²) across a reply, so it
# runs on a cadence rather than per chunk, plus once when the stream ends.
_ETHICS_CHECK_EVERY = 8

# The categories a partial reply can be judged on.  MISSING_DISCLAIMER is
# excluded on purpose: mid-stream, "no disclaimer yet" is a property of
# every reply that has not finished, and truncating on it guarantees the
# disclaimer never arrives.  It is excluded at the end-of-stream check too,
# because blocking a whole practice answer for saying "meditation" without
# the word "professional" would refuse more good replies than bad ones.
# Appending a disclaimer instead of blocking is the right fix and is a
# follow-up, not a gate this slice can safely widen.
_BLOCKING_CATEGORIES = frozenset(
    {
        ViolationCategory.FATALISTIC_LANGUAGE.value,
        ViolationCategory.DIAGNOSTIC_LANGUAGE.value,
        ViolationCategory.DARK_PATTERNS.value,
        ViolationCategory.CULTURAL_INSENSITIVITY.value,
        ViolationCategory.FINANCIAL_ADVICE.value,
    }
)

# Warnings do not truncate a live reply.  "will never" is a WARNING and
# is ordinary English; error and critical are the tiers that describe
# actual harm.
_BLOCKING_SEVERITIES = frozenset({ViolationSeverity.ERROR.value, ViolationSeverity.CRITICAL.value})


def run_safety_gates(
    system_key: str | None,
    text: str,
    *,
    check_ethics: bool = False,
) -> str | None:
    """Return a block reason for *text*, or ``None`` to let it through.

    The blocked-pattern regex runs for every scope, exactly as it did
    before this function existed.  ``check_text`` runs only for the
    practice scope and only when *check_ethics* is set, which the
    streaming loop does on its cadence.

    ``context="healing"`` is reused rather than adding a ``"practice"``
    context: it is the strictest existing coaching branch, and a
    first-class context is deferred to the gate rollout across the other
    scopes.
    """
    reason = _check_content_safety(text)
    if reason is not None:
        return reason

    if not check_ethics or system_key != PRACTICE_SYSTEM_KEY:
        return None

    result = check_text(text, context="healing")
    for violation in result.violations:
        if (
            violation.category in _BLOCKING_CATEGORIES
            and violation.severity in _BLOCKING_SEVERITIES
        ):
            return "Content flagged by safety filter"
    return None


def crisis_for(system_key: str | None, message: str) -> CrisisResponse | None:
    """Return the crisis response *message* warrants on this scope, if any.

    Practice only, and only at high or emergency severity.  Medium
    severity is ordinary coaching material ("I had a panic attack before
    my morning practice"); handing that user a hotline list instead of a
    conversation would be the wrong kind of careful.
    """
    if system_key != PRACTICE_SYSTEM_KEY:
        return None
    crisis = detect_crisis(message)
    if crisis is None:
        return None
    if crisis.severity not in (CrisisSeverity.HIGH, CrisisSeverity.EMERGENCY):
        return None
    return crisis


def _crisis_frames(crisis: CrisisResponse) -> list[str]:
    """Render the crisis response as one line per SSE ``data:`` frame.

    One line per frame because a ``data:`` field cannot carry a newline,
    and the client concatenates the values it receives.  So the copy is
    written to read as continuous prose rather than as a list.
    """
    parts = [
        "Before anything about practice: what you have written matters more than "
        "today's protocol, and there are people available right now who are "
        "better placed than I am to sit with it.",
    ]
    parts.extend(
        f"{resource.name}: {resource.contact}. {resource.description}"
        for resource in crisis.resources
    )
    parts.extend(crisis.disclaimers)
    parts.append("I'll be here when you want to come back to the practice side of things.")
    return parts


# ─── History cap ──────────────────────────────────────────────────────
#
# Limits the total number of *user* messages a single user can send
# per system_key.  This prevents runaway conversations from exhausting
# the LLM token budget.  The cap is per-system, so a user can send
# 200 messages in healing *and* 200 in wealth independently.

HISTORY_CAP = 200

_HISTORY_CAP_MESSAGE = (
    "You've reached the 200-message limit for this coaching topic. "
    "Please start a fresh conversation to continue. This limit exists "
    "to keep your coaching sessions focused and effective."
)


# ─── Per-user chat rate limiter (in-memory sliding window) ───────────
#
# Simple approach: keep a deque of timestamps per user; reject when
# more than ``_RATE_LIMIT_MAX`` entries fall within the last
# ``_RATE_LIMIT_WINDOW`` seconds.  No Redis, no persistence.

_RATE_LIMIT_MAX = 10  # messages per window
_RATE_LIMIT_WINDOW = 60.0  # seconds

# {user_id: [timestamp, ...]} — timestamps older than the window are
# lazily pruned on each request.
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

_RATE_LIMIT_MESSAGE = (
    "You're sending messages too quickly. Please wait a moment before "
    "trying again (limit: 10 messages per minute)."
)


def _check_rate_limit(user_id: str) -> str | None:
    """Return an error message if the user has exceeded the chat rate limit."""
    now = time.monotonic()
    cutoff = now - _RATE_LIMIT_WINDOW
    timestamps = _rate_limit_store[user_id]
    # Prune expired entries.
    _rate_limit_store[user_id] = [t for t in timestamps if t > cutoff]
    if len(_rate_limit_store[user_id]) >= _RATE_LIMIT_MAX:
        return _RATE_LIMIT_MESSAGE
    _rate_limit_store[user_id].append(now)
    return None


def reset_chat_rate_limit(user_id: str | None = None) -> None:
    """Clear rate-limit state — used by test fixtures.

    When ``user_id`` is ``None``, all entries are cleared.
    """
    if user_id is None:
        _rate_limit_store.clear()
    else:
        _rate_limit_store.pop(user_id, None)


# ─── Request model ─────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """POST /api/v1/chat request body."""

    message: str = Field(..., min_length=1, max_length=2000, description="User chat message")
    system_key: str | None = Field(
        None,
        description=(
            "Optional system scope: intelligence | healing | wealth | "
            "creative | perspective | practice.  None defaults to the "
            "general coach."
        ),
    )


class ChatHistoryItem(BaseModel):
    """Single message in the chat history response."""

    id: str
    role: str
    content: str
    system_key: str | None
    created_at: str  # ISO 8601


# ─── Streaming generator ───────────────────────────────────────────────


# Both stream responses send these.  ``X-Accel-Buffering`` is what stops
# nginx holding chunks back until the reply is complete.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def _chat_event_stream(
    *,
    user_id: str,
    message: str,
    system_key: str | None,
    session: AsyncSession,
    ephemeral: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream LLM reply chunks as SSE ``data:`` frames.

    Persists the user message before streaming starts and the full
    assistant message after the stream completes.  Each LLM chunk is
    additionally checked against the safety patterns; the stream is
    truncated and a sentinel emitted if blocked content is detected
    in the model's output.

    When *ephemeral* is ``True``, neither the user message nor the
    assistant reply is written to the database.  Safety checks and scope
    enforcement still run because they protect the LLM call, not the DB.
    """
    # Persist the user message before any LLM round-trip so it's never lost.
    user_message_id: str | None = None
    if not ephemeral:
        user_row = await repository.save_chat_message(
            session,
            user_id=user_id,
            role="user",
            content=message,
            system_key=system_key,
        )
        user_message_id = user_row.id
        await session.commit()

    # The ledger row for this turn names the message that caused it, so
    # per-scope cost is an exact join against chat_messages.system_key
    # rather than a correlation over timestamps.
    #
    # Only when there *is* a message to name.  An ephemeral turn persists
    # nothing, so it has no id to point at and stays out of that join —
    # but it keeps the HTTP request id ``get_current_account`` put there,
    # which is the only handle anybody has on it in the logs.  Clearing
    # it would trade one form of attribution for none.
    if user_message_id is not None:
        set_request_id(user_message_id)

    # We don't have a UserProfile loader hooked up here yet — the chat
    # endpoint accepts a system_key for now and the system prompt is
    # selected without per-user context interpolation.  Sprint 5 will
    # wire profile context end-to-end.
    system_prompt = build_system_prompt(system_key, None)

    # The practice block rides on the user message, never the system
    # prompt: the assembled system prompt is the cacheable stable prefix
    # of every chat turn, and this block changes daily.  Only ``message``
    # is persisted, so the assembly never enters the history either.
    prompt = message
    if system_key == PRACTICE_SYSTEM_KEY:
        practice_block = await build_practice_context(session, user_id)
        if practice_block:
            prompt = f"{practice_block}\n\n{message}"

    client = LLMClient()
    full_reply: list[str] = []
    blocked = False
    unavailable = False

    try:
        chunk_count = 0
        async for chunk in client.stream_generate(
            prompt=prompt,
            system_prompt=system_prompt,
            # Chat is the only surface that names its own model. It heads
            # the fallback chain rather than replacing it, so a 529 still
            # escalates instead of failing. Report narratives pass nothing
            # and keep the Sonnet-first chain.
            model=get_settings().llm_chat_model,
        ):
            full_reply.append(chunk)
            chunk_count += 1
            reason = run_safety_gates(
                system_key,
                "".join(full_reply),
                check_ethics=chunk_count % _ETHICS_CHECK_EVERY == 0,
            )
            if reason is not None:
                # The model produced something that trips the same safety
                # filter we apply to user input.  Truncate the stream and
                # emit an explicit error frame.
                logger.warning("Chat output blocked by safety filter for user %s", user_id)
                blocked = True
                yield "event: error\ndata: Response blocked by safety filter\n\n"
                break
            yield f"data: {chunk}\n\n"

        # Once at the end, so a violation inside the last few chunks is
        # not missed by the cadence.  It cannot unsend what already
        # streamed, but it still keeps the violation out of the history.
        if not blocked and system_key == PRACTICE_SYSTEM_KEY:
            if run_safety_gates(system_key, "".join(full_reply), check_ethics=True) is not None:
                logger.warning("Chat output blocked by safety filter for user %s", user_id)
                blocked = True
                yield "event: error\ndata: Response blocked by safety filter\n\n"
    except CostCeilingExceeded:
        # The response already started, so there is no status code left to
        # set — the state ships as an error frame the client renders. Text
        # only: the user does not need our meter names or scope ids.
        unavailable = True
        yield (
            "event: error\n"
            "data: The assistant is taking a short break while we catch up on "
            "demand. Please try again later.\n\n"
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Chat streaming failed: %s", exc)
        yield "event: error\ndata: Streaming failed\n\n"

    # Persist the assistant message even when truncated — the partial
    # reply (or the empty string) is part of the conversation history.
    # Skip persistence entirely when running in ephemeral mode.
    if not ephemeral:
        assistant_text = "".join(full_reply)
        if blocked:
            assistant_text = "[response blocked by safety filter]"
        elif unavailable:
            assistant_text = "[assistant temporarily unavailable]"
        await repository.save_chat_message(
            session,
            user_id=user_id,
            role="assistant",
            content=assistant_text,
            system_key=system_key,
        )
        await session.commit()

    yield "event: done\ndata: \n\n"


async def _crisis_event_stream(
    *,
    user_id: str,
    message: str,
    system_key: str | None,
    crisis: CrisisResponse,
    session: AsyncSession,
    ephemeral: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream crisis resources instead of a coaching reply.

    No LLM client is constructed, so this path makes no model call and
    writes no ledger row.  It is a 200 with a normal stream rather than
    a 400: a refusal status at that moment reads as "you did something
    wrong", and the client would render it as an error banner instead of
    a message.

    The turn is still persisted, respecting *ephemeral*.  A conversation
    that silently drops the hardest thing a user has typed is worse than
    one that keeps it, and the user message is committed *before* the
    first frame goes out for exactly that reason: a client that closes
    the tab mid-stream would otherwise roll the whole turn back, which
    is the case where keeping it matters most.
    """
    logger.info("Crisis gate engaged on the practice scope (severity=%s)", crisis.severity)

    frames = _crisis_frames(crisis)
    reply = " ".join(frames)

    # Committed up front, matching _chat_event_stream, so a disconnect
    # cannot take it with it.
    if not ephemeral:
        await repository.save_chat_message(
            session,
            user_id=user_id,
            role="user",
            content=message,
            system_key=system_key,
        )
        await session.commit()

    for part in frames:
        # Trailing space: the client concatenates data values without a
        # separator, and a data field cannot carry a newline.
        yield f"data: {part} \n\n"

    if not ephemeral:
        await repository.save_chat_message(
            session,
            user_id=user_id,
            role="assistant",
            content=reply,
            system_key=system_key,
        )
        await session.commit()

    yield "event: done\ndata: \n\n"


# ─── Endpoint ──────────────────────────────────────────────────────────


@router.post("/chat")
async def chat(
    request: ChatRequest,
    ephemeral: bool = Query(False, description="Skip message persistence"),
    account: Account = Depends(require_chat),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream a Growth Assistant chat reply via Server-Sent Events.

    The plan gate is a dependency, so it resolves before the
    ``StreamingResponse`` is constructed and a refusal is still a real
    402 or 429.  Once the stream opens there is no status code left to
    set, and a quota state buried in an ``event: error`` frame reads as
    a successful request to every layer above the parser.

    Safety: the user message is checked against the blocked-pattern list
    before any LLM call.  Blocked input returns HTTP 400.

    The response is a ``text/event-stream`` where each LLM chunk is
    delivered as a ``data:`` frame and the stream terminates with an
    ``event: done`` sentinel.

    Both the user message and the full assistant reply are persisted to
    the ``chat_messages`` table for the authenticated user.  Pass
    ``?ephemeral=true`` to skip persistence entirely (useful for
    one-off queries that should not appear in history).
    """
    user_id = account.user_id

    # Before every other check, because most of them would answer a
    # crisis disclosure with a refusal.  "kill" and "hurt" are in the
    # blocked-pattern list, so "I want to kill myself" would otherwise
    # return HTTP 400 "content flagged by safety filter" to somebody who
    # has just said the hardest thing they can say.
    #
    # This also skips the rate limit and the history cap, deliberately.
    # Both of them refuse, and neither has a refusal worth sending at
    # this moment.  The path makes no LLM call and writes no ledger row,
    # so there is no spend to cap; the request-level RateLimitMiddleware
    # still bounds the volume.  The plan gate above is the exception it
    # cannot escape: it is a dependency, so a free account is refused
    # before the handler runs at all.
    crisis = crisis_for(request.system_key, request.message)
    if crisis is not None:
        await _ensure_user_exists(session, user_id)
        return StreamingResponse(
            _crisis_event_stream(
                user_id=user_id,
                message=request.message,
                system_key=request.system_key,
                crisis=crisis,
                session=session,
                ephemeral=ephemeral,
            ),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

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

    # ── Per-user rate limit (in-memory, 10 msg/min) ──────────────────
    rate_limit_msg = _check_rate_limit(user_id)
    if rate_limit_msg:
        raise HTTPException(status_code=429, detail=rate_limit_msg)

    # Ensure the user row exists so the FK constraint on chat_messages
    # is satisfied.  In production the user always exists (auth requires
    # a real account); in tests with the auth dependency overridden we
    # may need to create the test user on demand.
    await _ensure_user_exists(session, user_id)

    # ── History cap (200 user messages per system_key) ───────────────
    # Skip when ephemeral — there is no point counting rows we won't write.
    if not ephemeral:
        msg_count = await repository.count_user_chat_messages(
            session,
            user_id=user_id,
            system_key=request.system_key,
        )
        if msg_count >= HISTORY_CAP:
            raise HTTPException(status_code=429, detail=_HISTORY_CAP_MESSAGE)

    return StreamingResponse(
        _chat_event_stream(
            user_id=user_id,
            message=request.message,
            system_key=request.system_key,
            session=session,
            ephemeral=ephemeral,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/chat/history")
async def chat_history(
    system_key: str | None = Query(
        None,
        description=(
            "Filter by system scope. Pass one of: intelligence, healing, "
            "wealth, creative, perspective, practice. Omit for all messages."
        ),
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum messages to return"),
    q: str | None = Query(None, description="Search message content"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatHistoryItem]:
    """Return persisted chat history for the authenticated user.

    Messages are returned in chronological (oldest-first) order so the
    frontend can display them from top to bottom.  The ``limit`` caps
    the result set — the *most recent* N messages are fetched and then
    reversed into chronological order by the repository layer.

    When ``system_key`` is provided, only messages scoped to that system
    are returned.  When omitted, all messages regardless of system scope
    are included.

    When ``q`` is provided, only messages whose content contains the
    search term (case-insensitive) are returned.  Because the ``content``
    column is encrypted (EncryptedString), SQL-level filtering is not
    possible; the search is applied in Python after the DB query returns
    decrypted values.
    """
    if system_key is not None and system_key not in _VALID_SYSTEM_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown system_key {system_key!r}. Valid: {sorted(_VALID_SYSTEM_KEYS)}",
        )

    user_id = current_user["sub"]
    rows = await repository.get_chat_history(
        session,
        user_id=user_id,
        system_key=system_key,
        limit=limit,
    )

    # Apply content search filter in Python (content is encrypted, cannot
    # filter in SQL).
    messages = list(rows)
    if q:
        q_lower = q.lower()
        messages = [m for m in messages if q_lower in m.content.lower()]

    return [
        ChatHistoryItem(
            id=row.id,
            role=row.role,
            content=row.content,
            system_key=row.system_key,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in messages
    ]


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

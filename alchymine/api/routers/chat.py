"""Growth Assistant chat endpoint — SSE streaming with history.

POST /api/v1/chat  — accepts a message and optional system context,
streams the assistant reply as Server-Sent Events, and persists both
the user message and the full assistant reply to the chat_messages table.

GET /api/v1/chat/history — returns the last 50 messages for the
current user as a JSON list.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.agents.growth.context_builder import build_user_context
from alchymine.agents.growth.system_prompts import get_system_prompt
from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.llm.client import LLMClient

router = APIRouter()

_MAX_HISTORY_MESSAGES = 200

_BLOCKED_PATTERNS = [
    # Prompt injection
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)",
    r"you\s+are\s+now\s+in\s+",
    r"system\s*:\s*",
    # Harmful intent
    r"(how\s+to\s+)?(make|create|build)\s+(a\s+)?(bomb|weapon|explosive)",
    r"(how\s+to\s+)?(harm|hurt|kill|poison)",
]


def _is_safe(text: str) -> bool:
    """Return True if the text passes all safety pattern checks."""
    lower = text.lower()
    return not any(re.search(p, lower) for p in _BLOCKED_PATTERNS)


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    system_context: str | None = Field(default=None, max_length=32)
    report_result: dict | None = Field(default=None)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    system_context: str | None
    created_at: str


async def _chat_stream(
    user_id: str,
    request: ChatRequest,
    session: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted chunks and persist the conversation to DB."""
    history = await repository.get_chat_history(session, user_id, limit=20)
    await repository.save_chat_message(
        session, user_id, "user", request.message, request.system_context
    )
    await session.commit()

    context_block = build_user_context(request.report_result)

    # Build message list for context — inject profile block into first message
    messages: list[dict] = []
    for i, msg in enumerate(history):
        content = (
            f"{context_block}\n\n{msg.content}".strip() if i == 0 and context_block else msg.content
        )
        messages.append({"role": msg.role, "content": content})

    # Current user message (with context if no history yet)
    current_content = (
        f"{context_block}\n\n{request.message}".strip()
        if context_block and not history
        else request.message
    )
    messages.append({"role": "user", "content": current_content})

    system_prompt = get_system_prompt(request.system_context)
    client = LLMClient()

    full_reply: list[str] = []
    async for chunk in client.stream_generate(
        prompt=current_content,
        system_prompt=system_prompt,
    ):
        full_reply.append(chunk)
        yield f"data: {chunk}\n\n"

    await repository.save_chat_message(
        session, user_id, "assistant", "".join(full_reply), request.system_context
    )
    await session.commit()
    yield "event: done\ndata: \n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream a Growth Assistant response as Server-Sent Events.

    Accepts a user message and an optional system context key.  The
    last 20 chat messages are loaded to provide conversational continuity.
    Both the user message and the assembled assistant reply are persisted.

    Returns a ``text/event-stream`` response ending with ``event: done``.
    """
    if not _is_safe(request.message):
        raise HTTPException(status_code=400, detail="Content flagged by safety filter")

    user_id: str = current_user["sub"]

    # Guard against runaway history
    history = await repository.get_chat_history(session, user_id, limit=_MAX_HISTORY_MESSAGES + 1)
    if len(history) >= _MAX_HISTORY_MESSAGES:
        raise HTTPException(
            status_code=429,
            detail="Chat history limit reached. Start a new session.",
        )

    return StreamingResponse(
        _chat_stream(user_id, request, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/history")
async def get_history(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageOut]:
    """Return the last 50 chat messages for the current user (oldest-first)."""
    user_id: str = current_user["sub"]
    msgs = await repository.get_chat_history(session, user_id)
    return [
        ChatMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            system_context=m.system_context,
            created_at=m.created_at.isoformat(),
        )
        for m in msgs
    ]

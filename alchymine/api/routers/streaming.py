"""Streaming LLM response endpoints.

Provides Server-Sent Events (SSE) endpoints for streaming narrative
generation from the LLM backend. Responses are sent as ``text/event-stream``
with individual ``data:`` frames for each chunk.
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from alchymine.api.auth import get_current_user
from alchymine.llm.client import LLMClient

router = APIRouter()

_BLOCKED_PATTERNS = [
    # Prompt injection
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)",
    r"you\s+are\s+now\s+in\s+",
    r"system\s*:\s*",
    # Harmful intent
    r"(how\s+to\s+)?(make|create|build)\s+(a\s+)?(bomb|weapon|explosive)",
    r"(how\s+to\s+)?(harm|hurt|kill|poison)",
]


def _check_content_safety(text: str) -> str | None:
    """Return error message if content is unsafe, None if OK."""
    lower = text.lower()
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, lower):
            return "Content flagged by safety filter"
    return None


async def _narrative_event_stream(
    prompt: str,
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted chunks from the LLM streaming backend.

    Each chunk is sent as ``data: <text>\\n\\n``.  When the stream is
    complete a ``event: done\\ndata: \\n\\n`` sentinel is emitted.

    Parameters
    ----------
    prompt:
        The user prompt to send to the LLM.
    system_prompt:
        Optional system-level instructions.
    """
    client = LLMClient()
    async for chunk in client.stream_generate(
        prompt=prompt,
        system_prompt=system_prompt,
    ):
        yield f"data: {chunk}\n\n"

    yield "event: done\ndata: \n\n"


@router.get("/stream/narrative")
async def stream_narrative(
    prompt: str = Query(..., max_length=2000, description="The prompt to generate a narrative for"),
    system_prompt: str = Query(
        "", max_length=2000, description="Optional system-level instructions"
    ),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream a narrative LLM response as Server-Sent Events.

    Returns a ``text/event-stream`` response where each chunk of the
    generated narrative is delivered as a ``data:`` event.  The stream
    ends with an ``event: done`` sentinel.

    This endpoint supports all configured LLM backends (Claude, Ollama)
    with automatic fallback.  When no backend is available the fallback
    message is streamed word-by-word.
    """
    for text in (prompt, system_prompt):
        safety_message = _check_content_safety(text)
        if safety_message:
            raise HTTPException(status_code=400, detail=safety_message)
    return StreamingResponse(
        _narrative_event_stream(prompt, system_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

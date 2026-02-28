"""Streaming LLM response endpoints.

Provides Server-Sent Events (SSE) endpoints for streaming narrative
generation from the LLM backend. Responses are sent as ``text/event-stream``
with individual ``data:`` frames for each chunk.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from alchymine.llm.client import LLMClient

router = APIRouter()


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
    prompt: str = Query(..., description="The prompt to generate a narrative for"),
    system_prompt: str = Query("", description="Optional system-level instructions"),
) -> StreamingResponse:
    """Stream a narrative LLM response as Server-Sent Events.

    Returns a ``text/event-stream`` response where each chunk of the
    generated narrative is delivered as a ``data:`` event.  The stream
    ends with an ``event: done`` sentinel.

    This endpoint supports all configured LLM backends (Claude, Ollama)
    with automatic fallback.  When no backend is available the fallback
    message is streamed word-by-word.
    """
    return StreamingResponse(
        _narrative_event_stream(prompt, system_prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

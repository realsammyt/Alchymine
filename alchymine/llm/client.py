"""Unified LLM client with Claude API primary and Ollama fallback.

The client tries Claude first. If unavailable (no API key, network error),
it falls back to a local Ollama instance. If neither is available, it
returns a graceful degradation response.

Environment Variables:
    ANTHROPIC_API_KEY: Claude API key (optional — enables Claude backend)
    OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)
    OLLAMA_MODEL: Ollama model name (default: llama3.2)
    LLM_BACKEND: Force a specific backend ("claude", "ollama", "none")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from alchymine.config import get_settings
from alchymine.db.usage_counters import METER_LLM_CALLS, CostCeilingExceeded
from alchymine.llm.cost_guard import charge_paid_call
from alchymine.llm.ledger import record_usage

logger = logging.getLogger(__name__)

# How long the streaming path waits for the accumulated final message before
# giving up and recording an estimate. On a normal completion the stream is
# already drained and this returns immediately; after a client disconnect the
# upstream response may never drain, and an unbounded await there would hang
# the generator's finalization until the 90-second client timeout.
_FINAL_MESSAGE_TIMEOUT_SECONDS = 5.0

# Rough characters-per-token used only when the exact usage is unreachable.
_CHARS_PER_TOKEN = 4


def _usage_int(usage: Any, field_name: str) -> int:
    """Read one integer usage field, defaulting to 0.

    The two cache fields are absent on older SDK responses, and a test
    double may carry anything at all. Anything that is not a plain int
    reads as 0 rather than propagating into the cost arithmetic.
    """
    value = getattr(usage, field_name, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


class LLMBackend(StrEnum):
    """Available LLM backends."""

    CLAUDE = "claude"
    OLLAMA = "ollama"
    NONE = "none"


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM generation call.

    Attributes
    ----------
    text:
        The generated text content.
    backend:
        Which backend produced this response.
    model:
        The model name used.
    input_tokens:
        Approximate input token count (0 if unknown).
    output_tokens:
        Approximate output token count (0 if unknown).
    """

    text: str
    backend: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


# ── OllamaClient ────────────────────────────────────────────────────────


@dataclass
class OllamaModelInfo:
    """Information about an available Ollama model.

    Attributes
    ----------
    name:
        The model identifier (e.g., ``llama3.2``).
    size:
        Model size in bytes (0 if unknown).
    digest:
        Model digest hash.
    modified_at:
        ISO timestamp of last modification.
    """

    name: str
    size: int = 0
    digest: str = ""
    modified_at: str = ""


class OllamaClient:
    """Client for a local Ollama instance.

    Provides non-streaming and streaming generation, model listing,
    and health-check methods. All HTTP calls use ``httpx``.

    Parameters
    ----------
    base_url:
        Ollama server URL (default from settings).
    default_model:
        Default model to use if not specified per call.
    timeout:
        HTTP timeout in seconds.
    """

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str = "llama3.2",
        timeout: float = 10.0,
    ) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.ollama_base_url
        self._default_model = default_model
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        """Return the configured Ollama base URL."""
        return self._base_url

    @property
    def default_model(self) -> str:
        """Return the configured default model name."""
        return self._default_model

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using the Ollama REST API.

        Parameters
        ----------
        prompt:
            The user prompt / data to process.
        model:
            Model name (uses default if not provided).
        system_prompt:
            Optional system instructions.
        max_tokens:
            Maximum output tokens.
        temperature:
            Sampling temperature.

        Returns
        -------
        LLMResponse
            The generated text and metadata.
        """
        import httpx

        model = model or self._default_model
        url = f"{self._base_url}/api/generate"
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            text=data.get("response", ""),
            backend=LLMBackend.OLLAMA.value,
            model=model,
        )

    async def stream_generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream text from the Ollama REST API.

        Yields chunks as they arrive from the Ollama streaming endpoint.

        Parameters
        ----------
        prompt:
            The user prompt / data to process.
        model:
            Model name (uses default if not provided).
        system_prompt:
            Optional system instructions.
        max_tokens:
            Maximum output tokens.
        temperature:
            Sampling temperature.

        Yields
        ------
        str
            Text chunks from the model.
        """
        import httpx

        model = model or self._default_model
        url = f"{self._base_url}/api/generate"
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
                    if data.get("done", False):
                        break

    async def list_models(self) -> list[OllamaModelInfo]:
        """List locally available Ollama models.

        Calls ``GET /api/tags`` on the Ollama server.

        Returns
        -------
        list[OllamaModelInfo]
            Available models with metadata.
        """
        import httpx

        url = f"{self._base_url}/api/tags"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        models: list[OllamaModelInfo] = []
        for m in data.get("models", []):
            models.append(
                OllamaModelInfo(
                    name=m.get("name", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at", ""),
                )
            )
        return models

    async def is_available(self) -> bool:
        """Check if the Ollama server is reachable and healthy.

        Returns
        -------
        bool
            True if the server responded successfully, False otherwise.
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self._base_url)
                return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False


# ── Unified LLM Client ──────────────────────────────────────────────────


@dataclass
class _StreamState:
    """Tracks which backend was used during a streaming call."""

    backend_used: str = LLMBackend.NONE.value
    _field_order: list[str] = field(default_factory=list)


class LLMClient:
    """Unified LLM client with automatic fallback.

    Tries backends in order: Claude -> Ollama -> graceful degradation.
    """

    def __init__(self) -> None:
        forced = os.environ.get("LLM_BACKEND", "").lower()
        self._forced_backend: LLMBackend | None = None
        if forced in ("claude", "ollama", "none"):
            self._forced_backend = LLMBackend(forced)

        settings = get_settings()
        self._anthropic_key = settings.anthropic_api_key
        self._ollama_url = settings.ollama_base_url
        self._ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        self._ollama_client = OllamaClient(
            base_url=self._ollama_url,
            default_model=self._ollama_model,
        )
        self._last_backend: str = LLMBackend.NONE.value

        # Log backend configuration at init so worker logs confirm what's active
        key_status = "SET" if self._anthropic_key else "NOT SET"
        logger.info(
            "[LLM] Client initialized — ANTHROPIC_API_KEY=%s, forced_backend=%s, ollama=%s",
            key_status,
            self._forced_backend or "auto",
            self._ollama_url,
        )

    @property
    def last_backend(self) -> str:
        """Return the backend used for the most recent call."""
        return self._last_backend

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using the best available backend.

        Parameters
        ----------
        system_prompt:
            System instructions for the model.
        user_prompt:
            The user message / data to process.
        max_tokens:
            Maximum output tokens.
        temperature:
            Sampling temperature (0.0 = deterministic, 1.0 = creative).

        Returns
        -------
        LLMResponse
            The generated text and metadata.
        """
        if self._forced_backend == LLMBackend.NONE:
            self._last_backend = LLMBackend.NONE.value
            return self._fallback_response()

        import time as _time

        # Try Claude first
        if self._forced_backend in (None, LLMBackend.CLAUDE) and self._anthropic_key:
            try:
                logger.info(
                    "[LLM] Sending request to Claude (max_tokens=%d, temp=%.1f)",
                    max_tokens,
                    temperature,
                )
                t0 = _time.monotonic()
                result = await self._generate_claude(
                    system_prompt, user_prompt, max_tokens, temperature
                )
                elapsed = _time.monotonic() - t0
                self._last_backend = LLMBackend.CLAUDE.value
                logger.info(
                    "[LLM] Claude response received in %.1fs — model=%s, in=%d tok, out=%d tok",
                    elapsed,
                    result.model,
                    result.input_tokens,
                    result.output_tokens,
                )
                return result
            except CostCeilingExceeded:
                # Not a backend failure. Falling through to Ollama (or to
                # the canned fallback text) would hand the user a made-up
                # answer while the real state is "spending is capped".
                raise
            except Exception as exc:
                logger.warning("[LLM] Claude API failed: %s — trying Ollama fallback", exc)

        # Try Ollama
        if self._forced_backend in (None, LLMBackend.OLLAMA):
            try:
                logger.info("[LLM] Sending request to Ollama at %s", self._ollama_url)
                t0 = _time.monotonic()
                result = await self._generate_ollama(
                    system_prompt, user_prompt, max_tokens, temperature
                )
                elapsed = _time.monotonic() - t0
                self._last_backend = LLMBackend.OLLAMA.value
                logger.info("[LLM] Ollama response received in %.1fs", elapsed)
                return result
            except Exception as exc:
                logger.warning("[LLM] Ollama failed: %s", exc)

        # Graceful degradation
        logger.warning("[LLM] All backends exhausted — returning static fallback response")
        self._last_backend = LLMBackend.NONE.value
        return self._fallback_response()

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response chunks using the best available backend.

        For mock/testing: yields prompt words one at a time.
        For real usage: streams from Claude API or Ollama.

        Parameters
        ----------
        prompt:
            The user prompt / data to process.
        system_prompt:
            Optional system instructions.
        max_tokens:
            Maximum output tokens.
        temperature:
            Sampling temperature.

        Yields
        ------
        str
            Text chunks from the model.
        """
        if self._forced_backend == LLMBackend.NONE:
            self._last_backend = LLMBackend.NONE.value
            # Yield words of the fallback message one at a time
            fallback_text = self._fallback_response().text
            for word in fallback_text.split():
                yield word + " "
            return

        # Try Claude streaming first
        if self._forced_backend in (None, LLMBackend.CLAUDE) and self._anthropic_key:
            try:
                self._last_backend = LLMBackend.CLAUDE.value
                logger.info("Streaming LLM response via Claude backend")
                async for chunk in self._stream_claude(
                    prompt, system_prompt, max_tokens, temperature
                ):
                    yield chunk
                return
            except CostCeilingExceeded:
                # See generate(): a tripped breaker is not a backend outage.
                raise
            except Exception as exc:
                logger.warning("Claude streaming failed, trying Ollama fallback: %s", exc)

        # Try Ollama streaming
        if self._forced_backend in (None, LLMBackend.OLLAMA):
            try:
                self._last_backend = LLMBackend.OLLAMA.value
                logger.info("Streaming LLM response via Ollama backend")
                async for chunk in self._ollama_client.stream_generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ):
                    yield chunk
                return
            except Exception as exc:
                logger.warning("Ollama streaming failed: %s", exc)

        # Graceful degradation
        self._last_backend = LLMBackend.NONE.value
        fallback_text = self._fallback_response().text
        for word in fallback_text.split():
            yield word + " "

    # Model fallback chain, walked on 529 (overloaded): Sonnet, then Haiku.
    # Both hops go down in price. Opus used to sit on the end as a "last
    # resort", which meant a provider-side overload silently upgraded every
    # request to the most expensive model available — the opposite of what a
    # fallback should do. It could come back as a plan-gated option once
    # there is an entitlement to gate on; User has no plan field today, so
    # there is nothing to check.
    CLAUDE_MODELS = [
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ]

    async def _stream_claude(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream text from the Claude API using server-sent events.

        Tries each model in CLAUDE_MODELS until one succeeds.
        """
        import anthropic

        # Charged once per request, not once per fallback attempt: the
        # retries below exist because a model was overloaded, and the user
        # asked for one answer.
        await charge_paid_call()

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key, timeout=90.0)
        last_exc: Exception | None = None

        for model in self.CLAUDE_MODELS:
            try:
                delivered_chars = 0
                async with client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    try:
                        async for text in stream.text_stream:
                            delivered_chars += len(text)
                            yield text
                    finally:
                        # The ONLY recording site for this call. It runs on
                        # every exit path — normal completion, client
                        # disconnect (GeneratorExit at the yield above), or
                        # an exception — so it can neither double-record the
                        # common case nor miss the rare one. A capture placed
                        # after the loop would silently lose the cost of every
                        # stream the browser walked away from.
                        await _record_stream_usage(
                            stream=stream,
                            model=model,
                            system_prompt=system_prompt,
                            prompt=prompt,
                            delivered_chars=delivered_chars,
                        )
                return  # Success — stop trying models
            except anthropic.APIStatusError as exc:
                if exc.status_code == 529:  # overloaded
                    logger.warning("Claude model %s overloaded, trying next fallback", model)
                    last_exc = exc
                    continue
                raise  # Other API errors (auth, bad request) — don't retry
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                logger.warning("Claude model %s unavailable: %s, trying next fallback", model, exc)
                last_exc = exc
                continue

        if last_exc:
            raise last_exc

    async def _generate_claude(  # noqa: C901
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Generate text using the Claude API.

        Tries each model in CLAUDE_MODELS until one succeeds.
        """
        import anthropic

        # See _stream_claude: one charge per request, not per fallback hop.
        await charge_paid_call()

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key, timeout=90.0)
        last_exc: Exception | None = None

        for model in self.CLAUDE_MODELS:
            try:
                logger.info("[LLM] Trying Claude model: %s", model)
                response = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text

                input_tokens = _usage_int(response.usage, "input_tokens")
                output_tokens = _usage_int(response.usage, "output_tokens")
                # The two cache fields are read here and nowhere else. Pricing
                # only input and output would under-count every cached call
                # once prompt caching is switched on.
                cache_read = _usage_int(response.usage, "cache_read_input_tokens")
                cache_creation = _usage_int(response.usage, "cache_creation_input_tokens")

                logger.info(
                    "[LLM] Claude model %s succeeded — %d input tokens, %d output tokens",
                    model,
                    input_tokens,
                    output_tokens,
                )
                # ``model`` is the one that actually served: the 529 walk can
                # move the request onto a cheaper model, and pricing has to
                # follow it rather than what was asked for.
                await record_usage(
                    meter=METER_LLM_CALLS,
                    provider="anthropic",
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_input_tokens=cache_read,
                    cache_creation_input_tokens=cache_creation,
                )
                return LLMResponse(
                    text=text,
                    backend=LLMBackend.CLAUDE.value,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except anthropic.APIStatusError as exc:
                if exc.status_code == 529:  # overloaded
                    logger.warning("Claude model %s overloaded, trying next fallback", model)
                    last_exc = exc
                    continue
                raise
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                logger.warning("Claude model %s unavailable: %s, trying next fallback", model, exc)
                last_exc = exc
                continue

        if last_exc:
            raise last_exc
        raise RuntimeError("No Claude models available")

    async def _generate_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Generate text using the OllamaClient."""
        return await self._ollama_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @staticmethod
    def _fallback_response() -> LLMResponse:
        """Return a graceful degradation response when no LLM is available."""
        return LLMResponse(
            text=(
                "Narrative generation is currently unavailable. "
                "Your report contains all deterministic calculations "
                "and data. Narrative interpretations will be available "
                "when an LLM backend is configured."
            ),
            backend=LLMBackend.NONE.value,
            model="none",
        )


async def _record_stream_usage(
    *,
    stream: Any,
    model: str,
    system_prompt: str,
    prompt: str,
    delivered_chars: int,
) -> None:
    """Write the ledger row for one streamed Claude call.

    Called from exactly one place: the ``finally`` inside ``_stream_claude``.

    ``get_final_message()`` returns the accumulated message after
    ``message_stop``, and its usage carries all four token fields. On a
    normal completion the stream is already drained, so the await returns
    immediately with exact numbers — this is the only place in the codebase
    that can learn what a streamed reply cost.

    After a disconnect the stream is usually torn down and that call cannot
    complete, so the fallback records an estimate from characters sent and
    delivered. An estimate is a floor rather than a measurement, which is
    what ``estimated=True`` says to whoever reads the ledger later; the
    alternative is losing the cost of a call we were charged for.

    Never raises. It runs inside a ``finally`` during generator finalization,
    where an exception would replace whatever was already unwinding.
    """
    final: Any = None
    try:
        final = await asyncio.wait_for(
            stream.get_final_message(), timeout=_FINAL_MESSAGE_TIMEOUT_SECONDS
        )
    except Exception as exc:
        logger.info(
            "[LLM] Exact usage unavailable for streamed call on %s (%s) — recording an estimate",
            model,
            exc,
        )

    try:
        usage = getattr(final, "usage", None)
        if usage is not None:
            await record_usage(
                meter=METER_LLM_CALLS,
                provider="anthropic",
                model=model,
                input_tokens=_usage_int(usage, "input_tokens"),
                output_tokens=_usage_int(usage, "output_tokens"),
                cache_read_input_tokens=_usage_int(usage, "cache_read_input_tokens"),
                cache_creation_input_tokens=_usage_int(usage, "cache_creation_input_tokens"),
            )
            return

        await record_usage(
            meter=METER_LLM_CALLS,
            provider="anthropic",
            model=model,
            input_tokens=(len(system_prompt) + len(prompt)) // _CHARS_PER_TOKEN,
            output_tokens=delivered_chars // _CHARS_PER_TOKEN,
            estimated=True,
        )
    except Exception:
        # record_usage swallows its own failures; anything reaching here is
        # unexpected, and a broken ledger must not truncate a delivered reply.
        logger.exception("[LLM] Failed to record usage for a streamed call on %s", model)

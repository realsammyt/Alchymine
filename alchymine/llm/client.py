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

import json
import logging
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from enum import StrEnum

from alchymine.config import get_settings

logger = logging.getLogger(__name__)


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
                logger.info("[LLM] Sending request to Claude (max_tokens=%d, temp=%.1f)", max_tokens, temperature)
                t0 = _time.monotonic()
                result = await self._generate_claude(
                    system_prompt, user_prompt, max_tokens, temperature
                )
                elapsed = _time.monotonic() - t0
                self._last_backend = LLMBackend.CLAUDE.value
                logger.info(
                    "[LLM] Claude response received in %.1fs — model=%s, in=%d tok, out=%d tok",
                    elapsed, result.model, result.input_tokens, result.output_tokens,
                )
                return result
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

    # Model fallback chain: Sonnet (fast/cheap) → Haiku (backup) → Opus (last resort)
    CLAUDE_MODELS = [
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
        "claude-opus-4-6",
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

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key, timeout=90.0)
        last_exc: Exception | None = None

        for model in self.CLAUDE_MODELS:
            try:
                async with client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
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

    async def _generate_claude(
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

                logger.info(
                    "[LLM] Claude model %s succeeded — %d input tokens, %d output tokens",
                    model, response.usage.input_tokens, response.usage.output_tokens,
                )
                return LLMResponse(
                    text=text,
                    backend=LLMBackend.CLAUDE.value,
                    model=model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
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

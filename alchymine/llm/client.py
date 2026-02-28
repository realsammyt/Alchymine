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

import logging
import os
from dataclasses import dataclass
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


class LLMClient:
    """Unified LLM client with automatic fallback.

    Tries backends in order: Claude → Ollama → graceful degradation.
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
            return self._fallback_response()

        # Try Claude first
        if self._forced_backend in (None, LLMBackend.CLAUDE) and self._anthropic_key:
            try:
                return await self._generate_claude(
                    system_prompt, user_prompt, max_tokens, temperature
                )
            except Exception as exc:
                logger.warning("Claude API failed, trying Ollama fallback: %s", exc)

        # Try Ollama
        if self._forced_backend in (None, LLMBackend.OLLAMA):
            try:
                return await self._generate_ollama(
                    system_prompt, user_prompt, max_tokens, temperature
                )
            except Exception as exc:
                logger.warning("Ollama failed: %s", exc)

        # Graceful degradation
        return self._fallback_response()

    async def _generate_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Generate text using the Claude API."""
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        model = "claude-sonnet-4-20250514"

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

        return LLMResponse(
            text=text,
            backend=LLMBackend.CLAUDE.value,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def _generate_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Generate text using a local Ollama instance."""
        import httpx

        url = f"{self._ollama_url}/api/generate"
        payload = {
            "model": self._ollama_model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            text=data.get("response", ""),
            backend=LLMBackend.OLLAMA.value,
            model=self._ollama_model,
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

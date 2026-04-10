"""Gemini image generation client.

Wraps the optional ``google-genai`` SDK to call a Gemini image-generation
model. Designed to degrade gracefully when the API key is missing or the
SDK is not installed: every public method returns ``None`` instead of
raising. This lets the API layer return ``204 No Content`` so the
frontend can render an on-brand placeholder.

Environment variables (read from :class:`alchymine.config.Settings`):

- ``GEMINI_API_KEY``  — Google AI API key (optional)
- ``GEMINI_MODEL``    — Image generation model id (default: gemini-2.0-flash-preview-image-generation)

Notes
-----
- Installation of ``google-genai`` is **optional**::

    pip install "alchymine[gemini]"

- The SDK is imported lazily at module load time. If the import fails,
  ``_genai`` is set to ``None`` and every client instance reports
  ``is_available == False``.
- All network errors are caught, logged, and converted to ``None`` —
  this client never raises from ``generate_image``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from alchymine.config import get_settings

logger = logging.getLogger(__name__)

# ── Lazy SDK import ────────────────────────────────────────────────────
# Importing google-genai is optional. We attempt the import once at
# module load. If it fails, ``_genai`` stays ``None`` and the client
# reports unavailable, but ``alchymine.llm.gemini`` itself stays
# importable so the API router and tests can still load.
try:
    from google import genai as _genai  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised on environments without the SDK
    _genai = None  # type: ignore[assignment]


@dataclass(frozen=True)
class GeminiImageResult:
    """A single successful image generation result.

    Attributes
    ----------
    image_bytes:
        Raw image bytes (already decoded — no base64 wrapper).
    mime_type:
        IANA mime type, typically ``image/png``.
    prompt:
        The exact text prompt sent to the model.
    model:
        The Gemini model id that produced the image.
    generated_at:
        UTC timestamp at which the result was returned.
    """

    image_bytes: bytes
    mime_type: str
    prompt: str
    model: str
    generated_at: datetime


# Module-level guard so we only emit the "disabled" log line once per
# process even if many client instances are constructed.
_disabled_log_emitted = False


def _log_disabled_once(reason: str) -> None:
    global _disabled_log_emitted
    if not _disabled_log_emitted:
        logger.info("Gemini client disabled: %s", reason)
        _disabled_log_emitted = True


class GeminiClient:
    """Async client wrapping ``google-genai`` image generation.

    Parameters
    ----------
    api_key:
        Google AI API key. If ``None`` or empty the client is disabled.
    model:
        The Gemini image-generation model id.
    """

    def __init__(self, api_key: str | None, model: str) -> None:
        self._api_key = api_key or ""
        self._model = model
        self._client: Any = None

        if not self._api_key:
            _log_disabled_once("API key not configured")
            self._available = False
            return

        if _genai is None:
            _log_disabled_once("google-genai SDK not installed")
            self._available = False
            return

        try:
            self._client = _genai.Client(api_key=self._api_key)
        except Exception as exc:  # pragma: no cover - SDK init rarely fails
            logger.warning("Gemini client init failed: %s", exc)
            self._available = False
            return

        self._available = True
        logger.info("Gemini client initialized (model=%s)", self._model)

    @property
    def is_available(self) -> bool:
        """Return True iff the client can make API calls."""
        return self._available

    @property
    def model(self) -> str:
        """Return the configured Gemini model id."""
        return self._model

    async def generate_image(self, prompt: str) -> GeminiImageResult | None:
        """Generate one image from a text prompt.

        Returns
        -------
        GeminiImageResult | None
            The result on success, or ``None`` if the client is unavailable,
            the API call failed, or the response contained no image data.
            **Never raises.**
        """
        if not self._available or self._client is None or _genai is None:
            return None

        try:
            from google.genai import types  # type: ignore[import-not-found]
        except ImportError:  # pragma: no cover
            return None

        # Strict default safety settings — block low-severity content and above
        # for the four standard harm categories.
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ]

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    safety_settings=safety_settings,
                ),
            )
        except Exception as exc:
            logger.warning("Gemini image generation failed: %s", exc)
            return None

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is None:
                    continue
                data = getattr(inline, "data", None)
                if not data:
                    continue
                # Some SDK versions return base64 strings, others return raw
                # bytes. Normalize to bytes.
                if isinstance(data, str):
                    import base64

                    try:
                        image_bytes = base64.b64decode(data)
                    except (ValueError, TypeError):
                        logger.warning("Gemini returned non-decodable image payload")
                        return None
                else:
                    image_bytes = bytes(data)

                mime_type = getattr(inline, "mime_type", None) or "image/png"
                return GeminiImageResult(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    prompt=prompt,
                    model=self._model,
                    generated_at=datetime.now(UTC),
                )

        logger.warning("Gemini response had no image parts")
        return None


@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    """Return a process-wide cached :class:`GeminiClient` singleton.

    Reads ``gemini_api_key`` and ``gemini_model`` from settings. Use
    :meth:`functools.lru_cache.cache_clear` on this function in tests
    that need to swap the settings.
    """
    settings = get_settings()
    return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)

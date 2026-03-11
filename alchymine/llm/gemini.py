"""Gemini image generation client.

Uses the google-genai SDK to call Gemini 2.0 Flash image generation.
Returns None gracefully when GEMINI_API_KEY is not set or when the
google-genai SDK is not installed.

Environment Variables:
    GEMINI_API_KEY: Google AI API key (optional — disables art generation when absent)
    ART_CACHE_DIR: Directory for caching generated images (default: /tmp/alchymine_art)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from alchymine.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"

# Attempt to import the google-genai SDK. The client degrades gracefully if
# the package is not installed.
try:
    import google.genai as genai  # type: ignore[import]
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ImageResult:
    """Result from a Gemini image generation call.

    Attributes
    ----------
    data_b64:
        Base-64 encoded image bytes returned by the API.
    mime_type:
        MIME type of the image (e.g. ``"image/png"``).
    prompt_used:
        The prompt that produced this image.
    """

    data_b64: str
    mime_type: str
    prompt_used: str


class GeminiClient:
    """Client for Gemini image generation.

    Wraps the google-genai SDK with graceful degradation — returns ``None``
    when the API key is absent or when the SDK is not installed.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: str = settings.gemini_api_key

    @property
    def is_available(self) -> bool:
        """Return True when the API key is configured and the SDK is installed."""
        return bool(self._api_key) and genai is not None

    async def generate_image(self, prompt: str) -> ImageResult | None:
        """Generate an image from *prompt* using Gemini.

        Parameters
        ----------
        prompt:
            Natural-language description of the image to generate.

        Returns
        -------
        ImageResult | None
            The generated image result, or ``None`` when generation is
            unavailable (no API key, SDK missing, or API error).
        """
        if not self.is_available:
            logger.debug("[Gemini] Image generation unavailable (no API key or SDK missing)")
            return None

        try:
            client = genai.Client(api_key=self._api_key)
            response = await client.aio.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            for candidate in response.candidates or []:
                for part in candidate.content.parts or []:
                    inline = getattr(part, "inline_data", None)
                    if inline is not None:
                        return ImageResult(
                            data_b64=inline.data,
                            mime_type=inline.mime_type,
                            prompt_used=prompt,
                        )

            logger.warning("[Gemini] Response contained no image parts for prompt: %r", prompt[:80])
            return None

        except Exception as exc:
            logger.warning("[Gemini] Image generation failed: %s", exc)
            return None

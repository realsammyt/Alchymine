"""Filesystem storage for Gemini-generated images.

Images are written under ``ART_CACHE_DIR/<user_id>/<image_id>.<ext>``.
This module is intentionally tiny and synchronous — image writes happen
inside async request handlers via ``run_in_threadpool`` if a worker
needs to avoid blocking the loop, but the typical request shape is
sequential and small enough that direct writes are fine.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from alchymine.config import get_settings

logger = logging.getLogger(__name__)


_MIME_EXT: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
}


def get_art_cache_root() -> Path:
    """Resolve the art cache directory to an absolute :class:`~pathlib.Path`."""
    raw = get_settings().art_cache_dir
    p = Path(raw)
    if not p.is_absolute():
        # Resolve relative paths against the current working directory at
        # runtime — for the API process this is the project root.
        p = Path(os.getcwd()) / p
    return p


def _ext_for_mime(mime_type: str) -> str:
    return _MIME_EXT.get(mime_type.lower(), "png")


def write_image(user_id: str, image_id: str, image_bytes: bytes, mime_type: str) -> str:
    """Persist bytes for a single generated image.

    Returns the path *relative* to the art cache root, suitable for
    storing in the ``generated_images.file_path`` column.
    """
    root = get_art_cache_root()
    user_dir = root / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    ext = _ext_for_mime(mime_type)
    rel_path = f"{user_id}/{image_id}.{ext}"
    abs_path = root / rel_path
    abs_path.write_bytes(image_bytes)
    logger.info("Wrote generated image: %s (%d bytes)", rel_path, len(image_bytes))
    return rel_path


def read_image(file_path: str) -> bytes | None:
    """Read raw bytes for a stored image, returning ``None`` on miss."""
    root = get_art_cache_root()
    abs_path = root / file_path
    try:
        return abs_path.read_bytes()
    except (FileNotFoundError, OSError) as exc:
        logger.warning("Generated image not found at %s: %s", abs_path, exc)
        return None

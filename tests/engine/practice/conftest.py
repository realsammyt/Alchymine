"""Fixtures for building throwaway practice packs on disk.

Every loader test needs a pack directory, and the interesting cases are
one-field mutations of a valid pack. These helpers keep the mutation
visible at the call site instead of buried in twenty lines of YAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def practice_dict(slug: str = "alpha", **overrides: Any) -> dict[str, Any]:
    """Return a schema-valid practice mapping, with *overrides* applied.

    The prose is deliberately bland: it has to pass the load-time
    ``check_text`` gate, so a fixture that trips an ethics pattern would
    fail tests for a reason that has nothing to do with what they assert.
    """
    base: dict[str, Any] = {
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "order": 1,
        "summary": "A short line about the practice.",
        "purposes": ["self-knowledge"],
        "category": "reflection",
        "builds_on": [],
        "related": [],
        "use_when": ["You want to try something small."],
        "description": "Sit down and write one sentence about how today went.",
        "expected_shift": "You have one written sentence you did not have before.",
        "applications": ["Before you start the working day."],
        "daily_prompts": [
            "What is one thing to watch for today?",
            "What are you noticing right now?",
            "What did you notice today?",
        ],
        "self_check": {
            "failure_mode": "It turns into a chore you tick off.",
            "question": "Did writing it down change anything?",
        },
        "scaffold_note": "Let it go once the noticing happens on its own.",
        "duration_minutes": 5,
        "evidence_rating": "D",
        "contraindications": [],
        "tags": [],
        "featured": False,
    }
    base.update(overrides)
    return base


def manifest_dict(pack_id: str = "test-pack", **overrides: Any) -> dict[str, Any]:
    """Return a schema-valid pack manifest mapping, with *overrides* applied."""
    base: dict[str, Any] = {
        "schema_version": "2.0",
        "pack_id": pack_id,
        "title": "Test Pack",
        "summary": "A pack used by tests.",
        "version": "1.0.0",
        "license": "CC-BY-NC-SA-4.0",
        "attribution": "Alchymine Contributors",
        "source_url": None,
        "bundled": False,
    }
    base.update(overrides)
    return base


def write_pack(
    container: Path,
    pack_id: str = "test-pack",
    practices: list[dict[str, Any]] | None = None,
    **manifest_overrides: Any,
) -> Path:
    """Write ``<container>/<pack_id>/`` as a pack directory and return *container*.

    *container* is what ``PRACTICE_PACK_DIRS`` points at: a directory
    holding one subdirectory per pack.
    """
    if practices is None:
        practices = [practice_dict()]

    pack_dir = container / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    manifest = manifest_dict(pack_id, **manifest_overrides)
    (pack_dir / "pack.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    for practice in practices:
        (pack_dir / f"{practice['slug']}.yaml").write_text(
            yaml.safe_dump(practice, sort_keys=False), encoding="utf-8"
        )
    return container

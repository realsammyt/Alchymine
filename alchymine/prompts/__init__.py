"""Prompt template management for Alchymine narrative generation.

All prompt templates are version-controlled YAML files that define
how engine outputs are transformed into human-readable narratives.
Every template must pass ethics validation before use.
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent
TEMPLATES_DIR = PROMPTS_DIR / "templates"

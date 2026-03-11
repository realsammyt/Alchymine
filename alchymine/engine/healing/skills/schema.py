"""Pydantic model for a single healing skill definition loaded from YAML."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealingSkill(BaseModel):
    """A single healing skill loaded from a YAML file."""

    id: str
    modality: str
    title: str
    duration_minutes: int
    difficulty: str
    instructions: list[str]
    contraindications: list[str] = Field(default_factory=list)
    traditions: list[str] = Field(default_factory=list)
    evidence_level: str = "traditional"
    tags: list[str] = Field(default_factory=list)

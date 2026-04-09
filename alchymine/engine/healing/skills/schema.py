"""Pydantic schema for healing skill YAML definitions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from alchymine.engine.healing.modalities import MODALITY_REGISTRY

# Source of truth: the 15 modality keys from the existing healing engine.
ALLOWED_MODALITIES: frozenset[str] = frozenset(MODALITY_REGISTRY.keys())

EvidenceRating = Literal["A", "B", "C", "D"]


class SkillDefinition(BaseModel):
    """A single healing skill loaded from YAML.

    Evidence rating scale:
        A — Strong RCT / meta-analytic support
        B — Multiple controlled studies, moderate effect sizes
        C — Limited / observational evidence, plausible mechanism
        D — Traditional, anecdotal, or contemplative practice (not RCT-tested)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1, description="Unique slug, lowercase-with-dashes")
    modality: str = Field(..., description="One of the 15 healing modality keys")
    title: str = Field(..., min_length=1, description="Display name")
    description: str = Field(..., min_length=1)
    steps: list[str] = Field(..., min_length=1)
    evidence_rating: EvidenceRating
    contraindications: list[str] = Field(default_factory=list)
    duration_minutes: int = Field(..., gt=0)

    @field_validator("name")
    @classmethod
    def _validate_name_slug(cls, v: str) -> str:
        if v != v.lower():
            raise ValueError("name must be lowercase")
        if " " in v or "_" in v:
            raise ValueError("name must use dashes (not spaces or underscores)")
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("name must contain only [a-z0-9-]")
        return v

    @field_validator("modality")
    @classmethod
    def _validate_modality(cls, v: str) -> str:
        if v not in ALLOWED_MODALITIES:
            raise ValueError(
                f"unknown modality '{v}'. Must be one of: {sorted(ALLOWED_MODALITIES)}"
            )
        return v

    @field_validator("steps")
    @classmethod
    def _validate_steps_nonempty(cls, v: list[str]) -> list[str]:
        if any(not s.strip() for s in v):
            raise ValueError("steps must not contain empty strings")
        return v

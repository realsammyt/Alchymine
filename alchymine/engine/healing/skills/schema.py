"""Pydantic schema for healing skill YAML definitions."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from alchymine.engine.healing.modalities import MODALITY_REGISTRY

# Source of truth: the 15 modality keys from the existing healing engine.
ALLOWED_MODALITIES: frozenset[str] = frozenset(MODALITY_REGISTRY.keys())

EvidenceRating = Literal["A", "B", "C", "D"]

# Defaults for content Alchymine wrote. They match the bundled practice
# pack manifest verbatim, so a later migration onto pack schema v2 is a
# move rather than a re-decision.
BUNDLED_LICENSE: Final = "CC-BY-NC-SA-4.0"
BUNDLED_ATTRIBUTION: Final = "Alchymine Contributors"

# Field names the loader requires an external skill to declare for
# itself. Named here, next to the defaults, because the defaults are
# exactly what makes an undeclared external skill dangerous: it would
# otherwise ship third-party content under Alchymine's own terms.
LICENSING_FIELDS: Final[tuple[str, ...]] = ("license", "attribution")


class SkillDefinition(BaseModel):
    """A single healing skill loaded from YAML.

    Evidence rating scale:
        A — Strong RCT / meta-analytic support
        B — Multiple controlled studies, moderate effect sizes
        C — Limited / observational evidence, plausible mechanism
        D — Traditional, anecdotal, or contemplative practice (not RCT-tested)

    Licensing metadata (``license``, ``attribution``, ``source_url``,
    ``bundled``) uses the same field names and rules as the practice-pack
    manifest, ``engine/practice/schema.py:PackManifest``. Defaults cover
    bundled content; the loader requires an external directory's skills to
    declare their own. ``extra="forbid"`` stays: a silently accepted typo
    in a licensed third-party file is worse than a loud failure.
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
    license: str = Field(default=BUNDLED_LICENSE, min_length=1)
    attribution: str = Field(default=BUNDLED_ATTRIBUTION, min_length=1)
    source_url: str | None = None
    bundled: bool = Field(
        default=True,
        description="True only for skills shipped in this repository",
    )

    @field_validator("license", "attribution")
    @classmethod
    def _reject_blank_licensing(cls, v: str, info: ValidationInfo) -> str:
        # min_length=1 passes on whitespace, which is the shape a
        # half-filled template arrives in.
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return v

    @field_validator("source_url")
    @classmethod
    def _validate_source_url_scheme(cls, v: str | None) -> str | None:
        # The UI will render this as a link, so anything but http(s) is a
        # click-to-XSS vector from an external skill directory.
        if v is not None and not v.startswith(("https://", "http://")):
            raise ValueError("source_url must use http:// or https://")
        return v

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

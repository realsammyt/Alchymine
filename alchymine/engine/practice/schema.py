"""Pydantic schema for practice-pack YAML, version 2.0.

Two models rather than one. ``PackManifest`` carries the licensing
metadata a mounted external pack has to declare; ``PracticeDefinition``
carries the practice itself. The healing loader put everything on a
single frozen ``extra="forbid"`` model, which is why license fields
cannot be added to a healing skill YAML today.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .purposes import VALID_PURPOSES

SCHEMA_VERSION: Final = "2.0"


class PracticeCategory(StrEnum):
    """What kind of activity a practice is. The safety-class dimension."""

    REFLECTION = "reflection"
    ATTENTION = "attention"
    SOMATIC = "somatic"
    RELATIONAL = "relational"
    ENACTMENT = "enactment"


ACCEPTED_CATEGORIES: Final[frozenset[str]] = frozenset(c.value for c in PracticeCategory)

_SCREENING_REASON: Final = (
    "{label} practices need screening questions, contraindication review and a "
    "supervision model that this schema does not carry. Alchymine does not ship them."
)

# Named individually so the failure message says why, rather than "not a
# valid enumeration member". The exclusion is enforced by the engine, not
# by editorial vigilance.
REJECTED_CATEGORIES: Final[MappingProxyType[str, str]] = MappingProxyType(
    {
        "state-induction": _SCREENING_REASON.format(label="State-induction"),
        "breath-retention": _SCREENING_REASON.format(label="Breath-retention"),
        "fasting": _SCREENING_REASON.format(label="Fasting"),
        "cold-immersion": _SCREENING_REASON.format(label="Cold-immersion"),
        "sensory-deprivation": _SCREENING_REASON.format(label="Sensory-deprivation"),
        "substance": _SCREENING_REASON.format(label="Substance"),
    }
)

EvidenceRating = Literal["A", "B", "C", "D"]

# Field names whose text is read by a human and therefore passes the
# load-time ethics gate. Kept here, next to the model, so a new prose
# field is one edit away from being gated.
PROSE_FIELDS: Final[tuple[str, ...]] = (
    "summary",
    "description",
    "expected_shift",
    "scaffold_note",
    "use_when",
    "applications",
    "daily_prompts",
)


def _validate_slug(value: str, field: str) -> str:
    """Shared slug rule: lowercase ``[a-z0-9-]``, no spaces or underscores."""
    if value != value.lower():
        raise ValueError(f"{field} must be lowercase")
    if " " in value or "_" in value:
        raise ValueError(f"{field} must use dashes (not spaces or underscores)")
    if not all(c.isalnum() or c == "-" for c in value):
        raise ValueError(f"{field} must contain only [a-z0-9-]")
    return value


class PackManifest(BaseModel):
    """``pack.yaml`` — one per pack directory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["2.0"]
    pack_id: str = Field(..., min_length=1, description="Unique across all mounted dirs")
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1, description="The pack's own content version")
    license: str = Field(..., min_length=1)
    attribution: str = Field(..., min_length=1)
    source_url: str | None = None
    bundled: bool = False

    @field_validator("pack_id")
    @classmethod
    def _validate_pack_id(cls, v: str) -> str:
        return _validate_slug(v, "pack_id")

    @field_validator("source_url")
    @classmethod
    def _validate_source_url_scheme(cls, v: str | None) -> str | None:
        # The UI will render this as a link; anything but http(s) is a
        # click-to-XSS vector from a third-party pack (javascript: etc.).
        if v is not None and not v.startswith(("https://", "http://")):
            raise ValueError("source_url must use http:// or https://")
        return v


class SelfCheck(BaseModel):
    """The reflective question that closes a practice.

    Never a verdict and never scored: a scored self-check is a diagnosis
    by another name, so the question mark is a schema constraint.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    failure_mode: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)

    @field_validator("question")
    @classmethod
    def _must_be_a_question(cls, v: str) -> str:
        if not v.strip().endswith("?"):
            raise ValueError(
                "self_check question must end with '?'. A self-check asks the user "
                "something; it never tells them what is true about them."
            )
        return v


class PracticeDefinition(BaseModel):
    """A single practice loaded from one YAML file.

    Evidence rating scale (identical to the healing skills scale, so one
    rating vocabulary covers both loaders):
        A — Strong RCT / meta-analytic support
        B — Multiple controlled studies, moderate effect sizes
        C — Limited / observational evidence, plausible mechanism
        D — Traditional, anecdotal, or contemplative practice (not RCT-tested)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(..., min_length=1, description="Unique within the pack")
    title: str = Field(..., min_length=1)
    order: int = Field(..., ge=0, description="Display order within the pack")
    summary: str = Field(..., min_length=1)
    purposes: list[str] = Field(..., min_length=1, max_length=3)
    category: str = Field(..., description="See PracticeCategory and REJECTED_CATEGORIES")
    builds_on: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    use_when: list[str] = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    expected_shift: str = Field(..., min_length=1)
    applications: list[str] = Field(..., min_length=1)
    daily_prompts: list[str] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly 3, positionally morning / day / evening",
    )
    self_check: SelfCheck
    scaffold_note: str = Field(..., min_length=1)
    duration_minutes: int = Field(..., gt=0, le=120)
    evidence_rating: EvidenceRating
    contraindications: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    featured: bool = False

    @field_validator("slug")
    @classmethod
    def _validate_slug_field(cls, v: str) -> str:
        return _validate_slug(v, "slug")

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str) -> str:
        # Rejected set FIRST, so a screened-out category fails with the
        # reason rather than with a generic enumeration error.
        if v in REJECTED_CATEGORIES:
            raise ValueError(REJECTED_CATEGORIES[v])
        if v not in ACCEPTED_CATEGORIES:
            raise ValueError(
                f"unknown category '{v}'. Must be one of: {sorted(ACCEPTED_CATEGORIES)}"
            )
        return v

    @field_validator("purposes")
    @classmethod
    def _validate_purposes(cls, v: list[str]) -> list[str]:
        for purpose in v:
            if purpose not in VALID_PURPOSES:
                raise ValueError(
                    f"unknown purpose '{purpose}'. Must be one of: {sorted(VALID_PURPOSES)}"
                )
        if len(set(v)) != len(v):
            raise ValueError(f"duplicate purpose in {v}")
        return v

    @field_validator("builds_on", "related")
    @classmethod
    def _validate_edge_slugs(cls, v: list[str]) -> list[str]:
        for slug in v:
            _validate_slug(slug, "edge slug")
        if len(set(v)) != len(v):
            raise ValueError(f"duplicate edge in {v}")
        return v

    @field_validator("use_when", "applications", "daily_prompts", "contraindications", "tags")
    @classmethod
    def _no_blank_entries(cls, v: list[str]) -> list[str]:
        if any(not entry.strip() for entry in v):
            raise ValueError("list entries must not be empty or whitespace")
        return v

    @property
    def primary_purpose(self) -> str:
        """The first declared purpose, denormalized onto every log row."""
        return self.purposes[0]

    def prose(self) -> str:
        """Return every human-read text field, joined for the ethics gate."""
        parts: list[str] = []
        for name in PROSE_FIELDS:
            value = getattr(self, name)
            if isinstance(value, list):
                parts.extend(value)
            else:
                parts.append(value)
        parts.append(self.self_check.failure_mode)
        parts.append(self.self_check.question)
        return "\n".join(parts)

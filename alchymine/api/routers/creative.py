"""Creative Forge API endpoints.

Endpoints for Guilford divergent thinking assessment, style fingerprint
generation, and project suggestions. All calculations are deterministic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.creative import (
    assess_guilford,
    generate_style_fingerprint,
    identify_growth_areas,
    identify_strengths,
    suggest_mediums,
    suggest_projects,
)
from alchymine.engine.profile import CreativeDNA, GuilfordScores

router = APIRouter()


# --- Request / Response models -----------------------------------------------


class GuilfordAssessmentRequest(BaseModel):
    """Request to run a Guilford divergent thinking assessment."""

    responses: dict = Field(
        ...,
        description=(
            "Assessment responses. Either component-level scores "
            "(e.g., {'fluency': 75, 'flexibility': 60, ...}) or individual "
            "question scores (e.g., {'fluency_1': 80, 'fluency_2': 70, ...})."
        ),
    )


class GuilfordScoresResponse(BaseModel):
    """Guilford assessment scores response."""

    fluency: float
    flexibility: float
    originality: float
    elaboration: float
    sensitivity: float
    redefinition: float
    evidence_level: str = Field(default="strong")
    calculation_type: str = Field(default="deterministic")
    methodology: str = Field(
        default="Guilford SOI divergent thinking scores. All calculations are deterministic averages of assessment responses.",
    )


class StyleFingerprintRequest(BaseModel):
    """Request to generate a style fingerprint."""

    guilford_scores: GuilfordScores = Field(..., description="Guilford divergent thinking scores")
    creative_dna: CreativeDNA = Field(..., description="Tharp-inspired creative preferences")
    life_path: int | None = Field(None, ge=1, le=33, description="Optional Life Path number")


class StyleFingerprintResponse(BaseModel):
    """Style fingerprint response."""

    guilford_summary: dict
    dna_summary: dict
    dominant_components: list[str]
    creative_style: str
    overall_score: float
    strengths: list[str]
    growth_areas: list[str]
    recommended_mediums: list[str]
    evidence_level: str = Field(default="strong")
    calculation_type: str = Field(default="hybrid")
    methodology: str = Field(
        default="Style fingerprint combines Guilford divergent thinking scores with Tharp-inspired Creative DNA. All scoring is deterministic; style classification uses rule-based mapping.",
    )


class ProjectSuggestRequest(BaseModel):
    """Request to suggest creative projects."""

    orientation: str = Field(..., description="Creative orientation (e.g., 'Expressive Artist')")
    strengths: list[str] = Field(..., description="Dominant Guilford component names")
    medium_affinities: list[str] = Field(
        default_factory=list, description="Preferred creative mediums"
    )
    skill_level: str = Field(
        "beginner", description="Skill level: beginner, intermediate, or advanced"
    )


class ProjectResponse(BaseModel):
    """A single project suggestion."""

    title: str
    description: str
    type: str
    medium: str
    skill_level: str


class ProjectListResponse(BaseModel):
    """List of project suggestions."""

    projects: list[ProjectResponse]
    total: int
    orientation: str


# --- Endpoints ----------------------------------------------------------------


@router.post("/creative/assessment")
async def run_guilford_assessment(
    request: GuilfordAssessmentRequest,
    current_user: dict = Depends(get_current_user),
) -> GuilfordScoresResponse:
    """Run a Guilford divergent thinking assessment.

    Scores six components of divergent thinking from assessment responses.
    All calculations are deterministic.
    """
    try:
        scores = assess_guilford(request.responses)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return GuilfordScoresResponse(
        fluency=scores.fluency,
        flexibility=scores.flexibility,
        originality=scores.originality,
        elaboration=scores.elaboration,
        sensitivity=scores.sensitivity,
        redefinition=scores.redefinition,
    )


@router.post("/creative/style")
async def get_style_fingerprint(
    request: StyleFingerprintRequest,
    current_user: dict = Depends(get_current_user),
) -> StyleFingerprintResponse:
    """Generate a combined creative style fingerprint.

    Merges Guilford scores and Creative DNA into a unified style profile
    with strengths, growth areas, and medium recommendations.
    """
    fingerprint = generate_style_fingerprint(
        guilford=request.guilford_scores,
        dna=request.creative_dna,
    )

    strengths = identify_strengths(request.guilford_scores)
    growth_areas = identify_growth_areas(request.guilford_scores)
    mediums = suggest_mediums(
        dna=request.creative_dna,
        guilford=request.guilford_scores,
    )

    return StyleFingerprintResponse(
        guilford_summary=fingerprint["guilford_summary"],
        dna_summary=fingerprint["dna_summary"],
        dominant_components=fingerprint["dominant_components"],
        creative_style=fingerprint["creative_style"],
        overall_score=fingerprint["overall_score"],
        strengths=strengths,
        growth_areas=growth_areas,
        recommended_mediums=mediums,
    )


@router.post("/creative/projects")
async def suggest_creative_projects(
    request: ProjectSuggestRequest,
    current_user: dict = Depends(get_current_user),
) -> ProjectListResponse:
    """Suggest creative projects based on style and skill level.

    Uses the dominant Guilford components and skill level to generate
    relevant project ideas from the project template database.
    """
    # Build a minimal style dict for the suggest_projects function
    style = {
        "dominant_components": request.strengths,
    }

    projects = suggest_projects(style=style, skill_level=request.skill_level)

    project_responses = [
        ProjectResponse(
            title=p["title"],
            description=p["description"],
            type=p["type"],
            medium=p["medium"],
            skill_level=p["skill_level"],
        )
        for p in projects
    ]

    return ProjectListResponse(
        projects=project_responses,
        total=len(project_responses),
        orientation=request.orientation,
    )

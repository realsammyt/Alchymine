"""Perspective Prism API endpoints.

Endpoints for decision frameworks (pros/cons, weighted matrix),
cognitive bias detection, and Kegan developmental stage assessment.
All calculations are deterministic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.perspective import (
    assess_kegan_stage,
    detect_biases,
    growth_pathway,
    pros_cons_analysis,
    stage_description,
    suggest_debiasing,
    weighted_decision_matrix,
)

router = APIRouter()


# --- Request / Response models -----------------------------------------------


class ProsConsRequest(BaseModel):
    """Request for pros/cons analysis."""

    decision: str = Field(..., min_length=1, description="The option/decision being evaluated")
    factors: dict = Field(
        ...,
        description=(
            "Dict with 'pros' and 'cons' keys, each a list of strings. "
            "Example: {'pros': ['low cost', 'fast'], 'cons': ['risky']}"
        ),
    )


class ProsConsResponse(BaseModel):
    """Pros/cons analysis response."""

    option: str
    pros: list[dict]
    cons: list[dict]
    pro_count: int
    con_count: int
    balance_score: float
    assessment: str
    methodology: str


class WeightedMatrixRequest(BaseModel):
    """Request for weighted decision matrix."""

    options: list[str] = Field(..., min_length=1, description="Options to evaluate")
    criteria: list[dict] = Field(
        ...,
        min_length=1,
        description=(
            "List of criterion dicts with keys: name (str), weight (float), "
            "scores (dict mapping option name to score 0-10)"
        ),
    )


class WeightedMatrixResponse(BaseModel):
    """Weighted decision matrix response."""

    ranked_options: list[dict]
    criteria_breakdown: list[dict]
    methodology: str


class BiasDetectRequest(BaseModel):
    """Request to detect cognitive biases in text."""

    text: str = Field(..., min_length=1, description="Reasoning text to analyse for biases")


class BiasDetectResponse(BaseModel):
    """Cognitive bias detection response."""

    biases_detected: list[dict]
    total: int
    disclaimer: str = Field(
        default=(
            "Bias detection is a reflective aid, not a diagnostic tool. "
            "Identifying a bias pattern does not mean your reasoning is wrong."
        )
    )
    evidence_level: str = Field(default="moderate")
    calculation_type: str = Field(default="deterministic")
    methodology: str = Field(
        default="Pattern-based detection against a catalog of 20 cognitive biases from Kahneman, Tversky, and Ariely. Results include confidence scores and academic attributions.",
    )


class KeganAssessRequest(BaseModel):
    """Request for Kegan developmental stage assessment."""

    responses: dict = Field(
        ...,
        description=(
            "Dict mapping dimension keys to scores (1-5). Valid keys: "
            "self_awareness, perspective_taking, relationship_to_authority, "
            "conflict_tolerance, systems_thinking. At least 2 required."
        ),
    )


class KeganAssessResponse(BaseModel):
    """Kegan stage assessment response."""

    stage: str
    stage_number: int
    name: str
    description: str
    strengths: list[str]
    growth_edges: list[str]
    growth_practices: list[str]
    supportive_environments: list[str]
    encouragement: str
    methodology: str
    evidence_level: str = Field(default="strong")
    calculation_type: str = Field(default="ai-assisted")


# --- Endpoints ----------------------------------------------------------------


@router.post("/perspective/frameworks/pros-cons")
async def analyze_pros_cons(
    request: ProsConsRequest,
    current_user: dict = Depends(get_current_user),
) -> ProsConsResponse:
    """Run a structured pros/cons analysis with balance scoring.

    Deterministic calculation of balance score and qualitative assessment.
    """
    pros = request.factors.get("pros", [])
    cons = request.factors.get("cons", [])

    if not isinstance(pros, list) or not isinstance(cons, list):
        raise HTTPException(
            status_code=400,
            detail="factors must contain 'pros' and 'cons' as lists of strings",
        )

    try:
        result = pros_cons_analysis(
            option=request.decision,
            pros=pros,
            cons=cons,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return ProsConsResponse(**result)


@router.post("/perspective/frameworks/weighted-matrix")
async def analyze_weighted_matrix(
    request: WeightedMatrixRequest,
    current_user: dict = Depends(get_current_user),
) -> WeightedMatrixResponse:
    """Run a weighted decision matrix analysis.

    Scores options against weighted criteria using multi-criteria
    decision analysis. All calculations are deterministic.
    """
    try:
        result = weighted_decision_matrix(
            options=request.options,
            criteria=request.criteria,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return WeightedMatrixResponse(**result)


@router.post("/perspective/biases/detect")
async def detect_cognitive_biases(
    request: BiasDetectRequest,
    current_user: dict = Depends(get_current_user),
) -> BiasDetectResponse:
    """Detect potential cognitive biases in reasoning text.

    Uses keyword/phrase pattern matching against a catalog of 20 common
    cognitive biases. Results include matched phrases, confidence levels,
    and academic attributions.
    """
    detected = detect_biases(request.text)

    # Enrich each detected bias with debiasing strategies
    for bias in detected:
        try:
            debiasing = suggest_debiasing(bias["bias_type"])
            bias["strategies"] = debiasing["strategies"]
            bias["reframe"] = debiasing["reframe"]
        except ValueError:
            bias["strategies"] = []
            bias["reframe"] = ""

    return BiasDetectResponse(
        biases_detected=detected,
        total=len(detected),
    )


@router.post("/perspective/kegan/assess")
async def assess_kegan(
    request: KeganAssessRequest,
    current_user: dict = Depends(get_current_user),
) -> KeganAssessResponse:
    """Assess developmental stage using Kegan's framework.

    Uses a scored questionnaire mapping to determine which of the five
    Kegan stages best matches the user's responses. All calculations
    are deterministic.
    """
    try:
        stage = assess_kegan_stage(request.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    desc = stage_description(stage)
    pathway = growth_pathway(stage)

    return KeganAssessResponse(
        stage=stage.value,
        stage_number=desc["stage_number"],
        name=desc["name"],
        description=desc["description"],
        strengths=desc["strengths"],
        growth_edges=desc["growth_edges"],
        growth_practices=pathway["practices"],
        supportive_environments=pathway["supportive_environments"],
        encouragement=pathway["encouragement"],
        methodology=desc["methodology"],
    )

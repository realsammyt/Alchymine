"""Personality Assessment API endpoints.

Endpoints for Big Five (mini-IPIP), Attachment Style, and Enneagram
assessments. All scoring is deterministic — no LLM calls.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.personality import (
    ENNEAGRAM_TYPES,
    score_attachment,
    score_big_five,
    score_enneagram,
)

router = APIRouter()


# --- Request / Response models -----------------------------------------------


class BigFiveRequest(BaseModel):
    """Request for Big Five (mini-IPIP) personality assessment.

    Expects 20 responses keyed as bf_e1..bf_e4 (extraversion),
    bf_a1..bf_a4 (agreeableness), bf_c1..bf_c4 (conscientiousness),
    bf_n1..bf_n4 (neuroticism), bf_o1..bf_o4 (openness).
    Each value is an integer 1-5.
    """

    responses: dict[str, int] = Field(
        ..., description="Mapping of question_id -> raw score (1-5). 20 items required."
    )


class BigFiveResponse(BaseModel):
    """Big Five personality trait scores (0-100 scale)."""

    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float


class AttachmentRequest(BaseModel):
    """Request for attachment style assessment.

    Expects 4 responses keyed as att_closeness, att_abandonment,
    att_trust, att_self_reliance. Each value is an integer 1-5.
    """

    responses: dict[str, int] = Field(
        ..., description="Mapping of question_id -> raw score (1-5). 4 items required."
    )


class AttachmentResponse(BaseModel):
    """Attachment style assessment result."""

    attachment_style: str = Field(
        ...,
        description="One of: secure, anxious, avoidant, disorganized, anxious-secure, avoidant-secure",
    )


class EnneagramRequest(BaseModel):
    """Request for Enneagram type assessment.

    Expects 9 responses keyed as enn_1..enn_9.
    Each value is an integer 1-5 (resonance rating).
    """

    responses: dict[str, int] = Field(
        ..., description="Mapping of question_id -> raw score (1-5). 9 items required."
    )


class EnneagramResponse(BaseModel):
    """Enneagram type assessment result."""

    primary_type: int = Field(..., ge=1, le=9, description="Primary Enneagram type (1-9)")
    primary_name: str = Field(..., description="Name of primary type (e.g., 'Reformer')")
    wing: int = Field(..., ge=1, le=9, description="Wing type (1-9)")
    wing_name: str = Field(..., description="Name of wing type")


# --- Endpoints ----------------------------------------------------------------


@router.post("/personality/big-five")
async def assess_big_five(
    request: BigFiveRequest,
    current_user: dict = Depends(get_current_user),
) -> BigFiveResponse:
    """Score a mini-IPIP Big Five personality assessment.

    Accepts 20 Likert-scale responses (1-5) and returns trait scores
    on a 0-100 scale. Deterministic scoring with reverse-coded items.
    """
    try:
        scores = score_big_five(request.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return BigFiveResponse(
        openness=scores.openness,
        conscientiousness=scores.conscientiousness,
        extraversion=scores.extraversion,
        agreeableness=scores.agreeableness,
        neuroticism=scores.neuroticism,
    )


@router.post("/personality/attachment")
async def assess_attachment(
    request: AttachmentRequest,
    current_user: dict = Depends(get_current_user),
) -> AttachmentResponse:
    """Score an attachment style assessment.

    Accepts 4 Likert-scale responses (1-5) and returns the classified
    attachment style. Deterministic threshold-based classification.
    """
    try:
        style = score_attachment(request.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return AttachmentResponse(attachment_style=style.value)


@router.post("/personality/enneagram")
async def assess_enneagram(
    request: EnneagramRequest,
    current_user: dict = Depends(get_current_user),
) -> EnneagramResponse:
    """Score an Enneagram type assessment.

    Accepts 9 Likert-scale responses (1-5) and returns the primary type
    and wing. Deterministic scoring with tie-breaking by lower type number.
    """
    try:
        primary, wing = score_enneagram(request.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return EnneagramResponse(
        primary_type=primary,
        primary_name=ENNEAGRAM_TYPES[primary],
        wing=wing,
        wing_name=ENNEAGRAM_TYPES[wing],
    )

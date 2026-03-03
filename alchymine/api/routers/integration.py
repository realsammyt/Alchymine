"""Cross-system integration API endpoints.

Provides access to cross-system bridge insights, coherence checks,
and profile synthesis. These endpoints connect the five Alchymine
systems through deterministic mapping logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.integration.bridges import (
    BridgeInsight,
    archetype_to_creative_style,
    check_coherence,
    cycle_to_timing,
    healing_to_perspective_sequence,
    shadow_to_block_mapping,
    synthesize_profile,
    wealth_creative_alignment,
)

router = APIRouter()


# ── Request / Response models ──────────────────────────────────────


class BridgeInsightResponse(BaseModel):
    """A single cross-system insight."""

    source_system: str
    target_system: str
    bridge_type: str
    insight: str
    action: str
    confidence: float


class ArchetypeCreativeRequest(BaseModel):
    archetype: str = Field(..., description="Primary Jungian archetype")


class ShadowBlockRequest(BaseModel):
    shadow_archetype: str = Field(..., description="Shadow archetype name")


class CycleTimingRequest(BaseModel):
    personal_year: int = Field(..., ge=1, le=9, description="Numerology personal year (1-9)")


class WealthCreativeRequest(BaseModel):
    wealth_archetype: str = Field(..., description="Wealth archetype name")
    creative_style: str = Field(..., description="Creative style (e.g., generative, analytical)")


class HealingPerspectiveRequest(BaseModel):
    healing_modality: str = Field(default="breathwork", description="Current healing modality")
    kegan_stage: int = Field(..., ge=1, le=5, description="Kegan developmental stage (1-5)")


class CoherenceRequest(BaseModel):
    active_recommendations: list[dict[str, str]] = Field(
        ..., description="List of active recommendations with 'system' and 'action' keys"
    )


class CoherenceResponse(BaseModel):
    coherence_score: float
    conflicts: list[str]


class ProfileSynthesisRequest(BaseModel):
    numerology: dict | None = None
    archetype: dict | None = None
    personality: dict | None = None
    wealth_archetype: str | None = None
    creative_style: str | None = None
    kegan_stage: int | None = None


def _insight_to_response(insight: BridgeInsight) -> BridgeInsightResponse:
    return BridgeInsightResponse(
        source_system=insight.source_system,
        target_system=insight.target_system,
        bridge_type=insight.bridge_type,
        insight=insight.insight,
        action=insight.action,
        confidence=insight.confidence,
    )


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/integration/archetype-creative")
async def get_archetype_creative(
    request: ArchetypeCreativeRequest,
    current_user: dict = Depends(get_current_user),
) -> BridgeInsightResponse:
    """XS-01: Map archetype to creative style recommendations."""
    insight = archetype_to_creative_style(request.archetype)
    return _insight_to_response(insight)


@router.post("/integration/shadow-block")
async def get_shadow_block(
    request: ShadowBlockRequest,
    current_user: dict = Depends(get_current_user),
) -> BridgeInsightResponse:
    """XS-02: Map shadow archetype to creative block patterns."""
    insight = shadow_to_block_mapping(request.shadow_archetype)
    return _insight_to_response(insight)


@router.post("/integration/cycle-timing")
async def get_cycle_timing(
    request: CycleTimingRequest,
    current_user: dict = Depends(get_current_user),
) -> BridgeInsightResponse:
    """XS-03: Map numerology cycle to timing recommendations."""
    insight = cycle_to_timing(request.personal_year)
    return _insight_to_response(insight)


@router.post("/integration/wealth-creative")
async def get_wealth_creative(
    request: WealthCreativeRequest,
    current_user: dict = Depends(get_current_user),
) -> BridgeInsightResponse:
    """XS-04: Find wealth-creative alignment."""
    insight = wealth_creative_alignment(request.wealth_archetype, request.creative_style)
    return _insight_to_response(insight)


@router.post("/integration/healing-perspective")
async def get_healing_perspective(
    request: HealingPerspectiveRequest,
    current_user: dict = Depends(get_current_user),
) -> BridgeInsightResponse:
    """XS-05: Sequence healing before perspective work."""
    insight = healing_to_perspective_sequence(request.healing_modality, request.kegan_stage)
    return _insight_to_response(insight)


@router.post("/integration/coherence")
async def check_system_coherence(
    request: CoherenceRequest,
    current_user: dict = Depends(get_current_user),
) -> CoherenceResponse:
    """XS-06: Check coherence across active system recommendations."""
    result = check_coherence(request.active_recommendations)
    return CoherenceResponse(
        coherence_score=result.coherence_score,
        conflicts=result.conflicts,
    )


@router.post("/integration/synthesize")
async def synthesize_user_profile(
    request: ProfileSynthesisRequest,
    current_user: dict = Depends(get_current_user),
) -> list[BridgeInsightResponse]:
    """XS-07: Synthesize cross-system insights from user profile."""
    insights = synthesize_profile(
        numerology=request.numerology,
        archetype=request.archetype,
        personality=request.personality,
        wealth_archetype=request.wealth_archetype,
        creative_style=request.creative_style,
        kegan_stage=request.kegan_stage,
    )
    return [_insight_to_response(i) for i in insights]

"""Wealth Engine API endpoints.

Phase 2 endpoints for wealth archetype profiling, lever prioritization,
and 90-day activation plan generation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from alchymine.api.auth import get_current_user
from alchymine.engine.profile import (
    ArchetypeType,
    Intention,
    RiskTolerance,
    WealthContext,
)
from alchymine.engine.wealth.archetype import (
    WealthArchetype,
    get_wealth_archetype_scores,
    map_wealth_archetype,
)
from alchymine.engine.wealth.export import plan_to_csv
from alchymine.engine.wealth.levers import prioritize_levers
from alchymine.engine.wealth.plan import ActivationPlan, generate_activation_plan

router = APIRouter()


# ─── Request / Response models ───────────────────────────────────────────


class WealthProfileRequest(BaseModel):
    """Request to calculate a wealth archetype from intake data."""

    life_path: int = Field(..., ge=1, le=33, description="Life Path number (1-9, 11, 22, 33)")
    archetype_primary: ArchetypeType = Field(..., description="Primary Jungian archetype")
    risk_tolerance: RiskTolerance = Field(
        RiskTolerance.MODERATE, description="Financial risk tolerance"
    )


class WealthProfileResponse(BaseModel):
    """Wealth archetype profile response."""

    wealth_archetype: str
    description: str
    primary_levers: list[str]
    strengths: list[str]
    blind_spots: list[str]
    recommended_actions: list[str]
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Raw scores for all 8 wealth archetypes (for transparency)",
    )
    evidence_level: str = Field(
        default="strong",
        description="Evidence quality rating: strong | moderate | emerging | traditional",
    )
    calculation_type: str = Field(
        default="deterministic",
        description="How the result was produced: deterministic | ai-assisted | hybrid",
    )
    methodology: str = Field(
        default="Wealth archetype mapping uses deterministic scoring from Life Path number and Jungian archetype cross-reference. No financial data is sent to any LLM.",
    )


class WealthPlanRequest(BaseModel):
    """Request to generate a 90-day activation plan."""

    life_path: int = Field(..., ge=1, le=33, description="Life Path number")
    archetype_primary: ArchetypeType = Field(..., description="Primary Jungian archetype")
    risk_tolerance: RiskTolerance = Field(RiskTolerance.MODERATE)
    intention: Intention | None = Field(None, description="Primary intention (backward compat)")
    intentions: list[Intention] | None = Field(
        None, min_length=1, max_length=3, description="Life intentions (1-3)"
    )
    wealth_context: WealthContext | None = Field(None, description="Optional financial context")

    def resolved_intentions(self) -> list[Intention]:
        """Return the consolidated intention list."""
        if self.intentions:
            return list(self.intentions)
        if self.intention:
            return [self.intention]
        return [Intention.MONEY]


class PlanPhaseResponse(BaseModel):
    """A single phase in the activation plan."""

    name: str
    days: list[int] = Field(..., description="[start_day, end_day]")
    focus_lever: str
    actions: list[str]
    milestones: list[str]


class WealthPlanResponse(BaseModel):
    """Complete 90-day activation plan response."""

    wealth_archetype: str
    phases: list[PlanPhaseResponse]
    daily_habits: list[str]
    weekly_reviews: list[str]
    evidence_level: str = Field(default="strong")
    calculation_type: str = Field(default="deterministic")
    methodology: str = Field(
        default="90-day plan uses deterministic action templates matched to lever priorities and risk tolerance. All content is pre-written, not LLM-generated.",
    )


class LeverRequest(BaseModel):
    """Request to get lever priorities."""

    life_path: int = Field(..., ge=1, le=33, description="Life Path number")
    risk_tolerance: RiskTolerance = Field(RiskTolerance.MODERATE)
    intention: Intention | None = Field(None, description="Primary intention (backward compat)")
    intentions: list[Intention] | None = Field(
        None, min_length=1, max_length=3, description="Life intentions (1-3)"
    )
    wealth_context: WealthContext | None = None

    def resolved_intentions(self) -> list[Intention]:
        """Return the consolidated intention list."""
        if self.intentions:
            return list(self.intentions)
        if self.intention:
            return [self.intention]
        return [Intention.MONEY]


class LeverResponse(BaseModel):
    """Ordered lever priorities response."""

    levers: list[str] = Field(..., description="Wealth levers ordered by priority")


# ─── Helper converters ───────────────────────────────────────────────────


def _archetype_to_response(
    archetype: WealthArchetype,
    scores: dict[str, float],
) -> WealthProfileResponse:
    """Convert a WealthArchetype to an API response."""
    return WealthProfileResponse(
        wealth_archetype=archetype.name,
        description=archetype.description,
        primary_levers=[lever.value for lever in archetype.primary_levers],
        strengths=list(archetype.strengths),
        blind_spots=list(archetype.blind_spots),
        recommended_actions=list(archetype.recommended_actions),
        scores=scores,
    )


def _plan_to_response(plan: ActivationPlan) -> WealthPlanResponse:
    """Convert an ActivationPlan to an API response."""
    phases = [
        PlanPhaseResponse(
            name=phase.name,
            days=list(phase.days),
            focus_lever=phase.focus_lever.value,
            actions=list(phase.actions),
            milestones=list(phase.milestones),
        )
        for phase in plan.phases
    ]
    return WealthPlanResponse(
        wealth_archetype=plan.wealth_archetype,
        phases=phases,
        daily_habits=list(plan.daily_habits),
        weekly_reviews=list(plan.weekly_reviews),
    )


# ─── Endpoints ───────────────────────────────────────────────────────────


@router.post("/wealth/profile")
async def calculate_wealth_profile(
    request: WealthProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> WealthProfileResponse:
    """Calculate a wealth archetype from intake data.

    Uses the deterministic wealth archetype mapping engine to score all 8
    wealth archetypes and return the best match with transparency scores.
    """
    archetype = map_wealth_archetype(
        life_path=request.life_path,
        archetype_primary=request.archetype_primary,
        risk_tolerance=request.risk_tolerance,
    )

    scores = get_wealth_archetype_scores(
        life_path=request.life_path,
        archetype_primary=request.archetype_primary,
        risk_tolerance=request.risk_tolerance,
    )

    return _archetype_to_response(archetype, scores)


@router.post("/wealth/plan")
async def generate_wealth_plan(
    request: WealthPlanRequest,
    current_user: dict = Depends(get_current_user),
) -> WealthPlanResponse:
    """Generate a 90-day wealth activation plan.

    Combines wealth archetype mapping, lever prioritization, and plan
    generation into a single endpoint. All calculations are deterministic.
    """
    archetype = map_wealth_archetype(
        life_path=request.life_path,
        archetype_primary=request.archetype_primary,
        risk_tolerance=request.risk_tolerance,
    )

    levers = prioritize_levers(
        wealth_context=request.wealth_context,
        risk_tolerance=request.risk_tolerance,
        intentions=request.resolved_intentions(),
        life_path=request.life_path,
    )

    plan = generate_activation_plan(
        wealth_archetype=archetype,
        lever_priorities=levers,
        risk_tolerance=request.risk_tolerance,
    )

    return _plan_to_response(plan)


@router.post("/wealth/levers")
async def get_lever_priorities(
    request: LeverRequest,
    current_user: dict = Depends(get_current_user),
) -> LeverResponse:
    """Get wealth lever priorities for a user.

    Returns all 5 wealth levers (EARN, KEEP, GROW, PROTECT, TRANSFER)
    ordered by priority based on the user's context.
    """
    levers = prioritize_levers(
        wealth_context=request.wealth_context,
        risk_tolerance=request.risk_tolerance,
        intentions=request.resolved_intentions(),
        life_path=request.life_path,
    )

    return LeverResponse(levers=[lever.value for lever in levers])


@router.post("/wealth/plan/export")
async def export_wealth_plan_csv(
    request: WealthPlanRequest,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Export a 90-day wealth activation plan as a downloadable CSV.

    Generates the same deterministic plan as ``POST /wealth/plan`` but
    returns it as a CSV file for independent verification and task tracking.
    """
    archetype = map_wealth_archetype(
        life_path=request.life_path,
        archetype_primary=request.archetype_primary,
        risk_tolerance=request.risk_tolerance,
    )

    levers = prioritize_levers(
        wealth_context=request.wealth_context,
        risk_tolerance=request.risk_tolerance,
        intentions=request.resolved_intentions(),
        life_path=request.life_path,
    )

    plan = generate_activation_plan(
        wealth_archetype=archetype,
        lever_priorities=levers,
        risk_tolerance=request.risk_tolerance,
    )

    csv_content = plan_to_csv(plan)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="alchymine-wealth-plan.csv"',
        },
    )

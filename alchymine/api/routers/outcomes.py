"""Outcome tracking API endpoints.

Provides endpoints for recording milestones, logging activities,
and calculating progress summaries across all five Alchymine systems.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from alchymine.outcomes.tracker import (
    MilestoneRecord,
    OutcomeSummary,
    calculate_outcome_summary,
    get_milestones,
    record_activity,
    record_milestone,
)

router = APIRouter()


# ── Request models ──────────────────────────────────────────────────────


class MilestoneRequest(BaseModel):
    """Request to record a milestone."""

    user_id: str = Field(..., description="User identifier")
    system: str = Field(
        ..., description="System: identity | healing | wealth | creative | perspective"
    )
    name: str = Field(..., min_length=1, max_length=200, description="Milestone name")
    completed: bool = Field(True, description="Whether the milestone is completed")
    notes: str | None = Field(None, max_length=1000, description="Optional notes")


class ActivityRequest(BaseModel):
    """Request to log an activity event."""

    user_id: str = Field(..., description="User identifier")
    system: str = Field(..., description="System name")
    activity_type: str = Field(
        ..., description="Activity type: session | assessment | practice | review"
    )
    detail: str = Field("", max_length=500, description="Optional detail")


class MilestoneListResponse(BaseModel):
    """List of milestone records."""

    milestones: list[MilestoneRecord]
    total: int


# ── Endpoints ───────────────────────────────────────────────────────────


@router.post("/outcomes/milestones", status_code=201)
async def create_milestone(req: MilestoneRequest) -> MilestoneRecord:
    """Record a milestone completion or creation.

    Milestones represent significant achievements within any of the
    five Alchymine systems. They contribute to the overall progress score.
    """
    return record_milestone(
        user_id=req.user_id,
        system=req.system,
        name=req.name,
        completed=req.completed,
        notes=req.notes,
    )


@router.get("/outcomes/milestones")
async def list_milestones(
    user_id: str = Query(..., description="User ID"),
    system: str | None = Query(None, description="Optional system filter"),
) -> MilestoneListResponse:
    """List milestones for a user, optionally filtered by system."""
    records = get_milestones(user_id, system)
    return MilestoneListResponse(milestones=records, total=len(records))


@router.post("/outcomes/activity", status_code=201)
async def log_activity(req: ActivityRequest) -> dict[str, str]:
    """Log a user activity event for engagement tracking.

    Activities are lightweight events (sessions, assessments, practices)
    that contribute to the user's engagement score in their outcome summary.
    """
    record_activity(
        user_id=req.user_id,
        system=req.system,
        activity_type=req.activity_type,
        detail=req.detail,
    )
    return {"status": "recorded"}


@router.get("/outcomes/summary/{user_id}")
async def get_outcome_summary(
    user_id: str,
    journal_count: int = Query(0, ge=0, description="Number of journal entries"),
    active_plan_day: int | None = Query(None, ge=0, le=90, description="Current plan day"),
) -> OutcomeSummary:
    """Calculate a cross-system outcome summary for a user.

    The overall score is a weighted composite:
    - 40%: Milestone completion across all systems
    - 30%: Engagement frequency (activity events)
    - 20%: System breadth (number of systems used)
    - 10%: Journaling consistency

    All calculations are deterministic and auditable.
    """
    return calculate_outcome_summary(
        user_id=user_id,
        journal_count=journal_count,
        active_plan_day=active_plan_day,
    )

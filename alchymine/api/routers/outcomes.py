"""Outcome tracking API endpoints.

Provides endpoints for recording milestones, logging activities,
calculating progress summaries, and querying outcome metrics
across all five Alchymine systems.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from alchymine.outcomes.tracker import (
    MilestoneRecord,
    OutcomeSummary,
    calculate_outcome_summary,
    get_milestones,
    get_outcome_tracker,
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


class MetricRecordRequest(BaseModel):
    """Request to record an outcome metric."""

    user_id: str = Field(..., description="User identifier")
    system: str = Field(
        ..., description="System: identity | healing | wealth | creative | perspective"
    )
    metric_name: str = Field(..., min_length=1, max_length=200, description="Metric name")
    value: float = Field(..., description="Numeric value of the measurement")
    period: str = Field("weekly", description="Reporting period: weekly | monthly")


class MilestoneListResponse(BaseModel):
    """List of milestone records."""

    milestones: list[MilestoneRecord]
    total: int


class MetricResponse(BaseModel):
    """A single metric data point returned by the API."""

    user_id: str
    system: str
    metric_name: str
    value: float
    timestamp: str
    period: str


class MetricsListResponse(BaseModel):
    """List of metric records."""

    metrics: list[MetricResponse]
    total: int


class TrendResponse(BaseModel):
    """Trend analysis result for a system."""

    system: str
    direction: str
    metric_trends: dict[str, str]
    sample_size: int


class ProgressSummaryResponse(BaseModel):
    """Overall progress summary across all systems."""

    user_id: str
    total_metrics_recorded: int
    systems_tracked: list[str]
    trends: dict[str, str]
    correlations: list[dict[str, Any]]
    outcome_summary: OutcomeSummary | None = None
    generated_at: str


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


# ── Outcome Metric Endpoints ────────────────────────────────────────────


@router.post("/outcomes/record", status_code=201)
async def record_outcome_metric(req: MetricRecordRequest) -> MetricResponse:
    """Record an outcome metric measurement.

    Metrics are quantitative data points that track user progress
    within each system over time (e.g., engagement scores, practice
    completion rates, growth indicators).

    All metric data is deterministic and auditable.
    """
    tracker = get_outcome_tracker()
    metric = tracker.record_metric(
        user_id=req.user_id,
        system=req.system,
        metric_name=req.metric_name,
        value=req.value,
        period=req.period,
    )
    return MetricResponse(
        user_id=metric.user_id,
        system=metric.system,
        metric_name=metric.metric_name,
        value=metric.value,
        timestamp=metric.timestamp,
        period=metric.period,
    )


@router.get("/outcomes/{user_id}/metrics")
async def get_user_metrics(
    user_id: str,
    system: str | None = Query(None, description="Optional system filter"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
) -> MetricsListResponse:
    """Query outcome metrics for a user.

    Supports optional filtering by system and date range.
    Returns metrics sorted by timestamp (ascending).
    """
    tracker = get_outcome_tracker()
    metrics = tracker.get_metrics(
        user_id=user_id,
        system=system,
        start_date=start_date,
        end_date=end_date,
    )
    return MetricsListResponse(
        metrics=[
            MetricResponse(
                user_id=m.user_id,
                system=m.system,
                metric_name=m.metric_name,
                value=m.value,
                timestamp=m.timestamp,
                period=m.period,
            )
            for m in metrics
        ],
        total=len(metrics),
    )


@router.get("/outcomes/{user_id}/trends")
async def get_user_trends(
    user_id: str,
    system: str = Query(..., description="System to analyze"),
) -> TrendResponse:
    """Calculate trend analysis for a user's metrics in a specific system.

    Compares the average of the first half of data points to the second
    half to determine if the user is improving, stable, or declining.

    All calculations are deterministic and auditable.
    """
    tracker = get_outcome_tracker()
    trend = tracker.calculate_trends(user_id=user_id, system=system)
    return TrendResponse(
        system=trend.system,
        direction=trend.direction,
        metric_trends=trend.metric_trends,
        sample_size=trend.sample_size,
    )


@router.get("/outcomes/{user_id}/summary")
async def get_user_progress_summary(
    user_id: str,
    journal_count: int = Query(0, ge=0, description="Number of journal entries"),
    active_plan_day: int | None = Query(None, ge=0, le=90, description="Current plan day"),
) -> ProgressSummaryResponse:
    """Generate a comprehensive progress summary across all systems.

    Combines metric data, trend analysis, cross-system correlations,
    and the existing outcome summary into a single view.

    All calculations are deterministic and auditable.
    """
    tracker = get_outcome_tracker()
    summary = tracker.get_progress_summary(
        user_id=user_id,
        journal_count=journal_count,
        active_plan_day=active_plan_day,
    )
    return ProgressSummaryResponse(
        user_id=summary.user_id,
        total_metrics_recorded=summary.total_metrics_recorded,
        systems_tracked=summary.systems_tracked,
        trends=summary.trends,
        correlations=summary.correlations,
        outcome_summary=summary.outcome_summary,
        generated_at=summary.generated_at,
    )

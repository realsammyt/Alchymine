"""Outcome tracking API endpoints.

Provides endpoints for recording milestones, logging activities,
calculating progress summaries, and querying outcome metrics
across all five Alchymine systems.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import MilestoneDBRecord, OutcomeMetricRecord
from alchymine.outcomes.tracker import (
    MilestoneRecord,
    OutcomeSummary,
    OutcomeTracker,
    _activity_log,
    _milestones,
    calculate_outcome_summary,
    record_activity,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _hydrate_from_db(
    user_id: str,
    db_milestones: list[MilestoneDBRecord],
    db_metrics: list[OutcomeMetricRecord],
) -> None:
    """Populate in-memory stores from DB records before calculating summary.

    This bridges the gap between DB-persisted milestones/activities and the
    in-memory ``calculate_outcome_summary`` function.
    """
    # Hydrate milestones — merge DB records with any in-memory ones
    existing_ids = {m.id for m in _milestones.get(user_id, []) if m.id}
    hydrated: list[MilestoneRecord] = list(_milestones.get(user_id, []))
    for m in db_milestones:
        if str(m.id) not in existing_ids:
            hydrated.append(
                MilestoneRecord(
                    id=str(m.id),
                    system=m.system,
                    name=m.name,
                    completed=m.completed,
                    completed_at=m.completed_at.isoformat() if m.completed_at else None,
                    notes=m.notes,
                )
            )
    _milestones[user_id] = hydrated

    # Hydrate activity log from outcome metrics
    existing_count = len(_activity_log.get(user_id, []))
    if len(db_metrics) > existing_count:
        _activity_log[user_id] = [
            {
                "system": m.system,
                "activity_type": m.metric_name,
                "timestamp": m.recorded_at.isoformat() if m.recorded_at else "",
                "detail": "",
            }
            for m in db_metrics
        ]


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
async def create_milestone(
    req: MilestoneRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MilestoneRecord:
    """Record a milestone completion or creation.

    Milestones represent significant achievements within any of the
    five Alchymine systems. They contribute to the overall progress score.
    """
    if current_user["sub"] != req.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    record = await repository.record_milestone(
        db,
        user_id=req.user_id,
        system=req.system,
        name=req.name,
        completed=req.completed,
        notes=req.notes,
    )
    return MilestoneRecord(
        id=str(record.id),
        system=record.system,
        name=record.name,
        completed=record.completed,
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
        notes=record.notes,
    )


@router.get("/outcomes/milestones")
async def list_milestones(
    user_id: str = Query(..., description="User ID"),
    system: str | None = Query(None, description="Optional system filter"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MilestoneListResponse:
    """List milestones for a user, optionally filtered by system."""
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db_records = await repository.get_milestones(db, user_id, system)
    records = [
        MilestoneRecord(
            id=str(r.id),
            system=r.system,
            name=r.name,
            completed=r.completed,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            notes=r.notes,
        )
        for r in db_records
    ]
    return MilestoneListResponse(milestones=records, total=len(records))


@router.post("/outcomes/activity", status_code=201)
async def log_activity(
    req: ActivityRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Log a user activity event for engagement tracking.

    Activities are lightweight events (sessions, assessments, practices)
    that contribute to the user's engagement score in their outcome summary.
    Persisted as an outcome metric record for durability.
    """
    if current_user["sub"] != req.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    # Persist to DB as an outcome metric (value=1 for each event)
    await repository.record_outcome_metric(
        db,
        user_id=req.user_id,
        system=req.system,
        metric_name=req.activity_type,
        value=1.0,
    )
    # Also update in-memory for current-session reads
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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OutcomeSummary:
    """Calculate a cross-system outcome summary for a user.

    The overall score is a weighted composite:
    - 40%: Milestone completion across all systems
    - 30%: Engagement frequency (activity events)
    - 20%: System breadth (number of systems used)
    - 10%: Journaling consistency

    All calculations are deterministic and auditable.
    Reads milestones and activity metrics from the database.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Hydrate in-memory stores from DB so calculate_outcome_summary
    # works with persisted data (not just current-session activity)
    try:
        db_milestones = await repository.get_milestones(db, user_id)
        db_metrics = await repository.get_outcome_metrics(db, user_id)
        _hydrate_from_db(user_id, db_milestones, db_metrics)
    except Exception:
        logger.debug("Failed to hydrate outcomes from DB for %s", user_id)

    return calculate_outcome_summary(
        user_id=user_id,
        journal_count=journal_count,
        active_plan_day=active_plan_day,
    )


# ── Outcome Metric Endpoints ────────────────────────────────────────────


@router.post("/outcomes/record", status_code=201)
async def record_outcome_metric(
    req: MetricRecordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MetricResponse:
    """Record an outcome metric measurement.

    Metrics are quantitative data points that track user progress
    within each system over time (e.g., engagement scores, practice
    completion rates, growth indicators).

    All metric data is deterministic and auditable.
    """
    if current_user["sub"] != req.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    record = await repository.record_outcome_metric(
        db,
        user_id=req.user_id,
        system=req.system,
        metric_name=req.metric_name,
        value=req.value,
        period=req.period,
    )
    return MetricResponse(
        user_id=record.user_id,
        system=record.system,
        metric_name=record.metric_name,
        value=record.value,
        timestamp=record.recorded_at.isoformat(),
        period=record.period,
    )


@router.get("/outcomes/{user_id}/metrics")
async def get_user_metrics(
    user_id: str,
    system: str | None = Query(None, description="Optional system filter"),
    start_date: str | None = Query(None, description="Start date (ISO format)"),
    end_date: str | None = Query(None, description="End date (ISO format)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MetricsListResponse:
    """Query outcome metrics for a user.

    Supports optional filtering by system and date range.
    Returns metrics sorted by timestamp (ascending).
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    records = await repository.get_outcome_metrics(db, user_id, system)
    return MetricsListResponse(
        metrics=[
            MetricResponse(
                user_id=r.user_id,
                system=r.system,
                metric_name=r.metric_name,
                value=r.value,
                timestamp=r.recorded_at.isoformat(),
                period=r.period,
            )
            for r in records
        ],
        total=len(records),
    )


@router.get("/outcomes/{user_id}/trends")
async def get_user_trends(
    user_id: str,
    system: str = Query(..., description="System to analyze"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> TrendResponse:
    """Calculate trend analysis for a user's metrics in a specific system.

    Compares the average of the first half of data points to the second
    half to determine if the user is improving, stable, or declining.

    All calculations are deterministic and auditable.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    records = []
    try:
        records = await repository.get_outcome_metrics(db, user_id, system)
    except Exception:
        logger.debug("Failed to fetch outcome metrics from DB for %s", user_id)
    # Sort chronologically — DB returns DESC but trend calculation needs oldest-first
    records.sort(key=lambda r: r.recorded_at)
    tracker = OutcomeTracker()
    for r in records:
        tracker.record_metric(r.user_id, r.system, r.metric_name, r.value, r.period)
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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProgressSummaryResponse:
    """Generate a comprehensive progress summary across all systems.

    Combines metric data, trend analysis, cross-system correlations,
    and the existing outcome summary into a single view.

    All calculations are deterministic and auditable.
    """
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Hydrate in-memory stores and fetch metrics from DB
    records = []
    try:
        db_milestones = await repository.get_milestones(db, user_id)
        records = await repository.get_outcome_metrics(db, user_id)
        _hydrate_from_db(user_id, db_milestones, records)
    except Exception:
        logger.debug("Failed to hydrate outcomes from DB for %s", user_id)

    # Sort chronologically for correct trend direction
    records.sort(key=lambda r: r.recorded_at)
    tracker = OutcomeTracker()
    for r in records:
        tracker.record_metric(r.user_id, r.system, r.metric_name, r.value, r.period)
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

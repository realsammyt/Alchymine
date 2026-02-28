"""Outcome tracker — measures user progress across all five systems.

Provides deterministic scoring based on user engagement, milestone
completion, and self-reported metrics. All calculations are transparent
and auditable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# ── Models ──────────────────────────────────────────────────────────────


class MilestoneRecord(BaseModel):
    """A single milestone completion record."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    system: str = Field(
        ..., description="System: identity | healing | wealth | creative | perspective"
    )
    name: str = Field(..., description="Milestone name")
    completed: bool = Field(False)
    completed_at: str | None = None
    notes: str | None = None


class SystemProgress(BaseModel):
    """Progress summary for a single system."""

    system: str
    engagement_score: float = Field(0.0, ge=0, le=100, description="0-100 engagement level")
    milestones_total: int = 0
    milestones_completed: int = 0
    completion_pct: float = Field(0.0, ge=0, le=100)
    active_days: int = 0
    last_activity: str | None = None


class OutcomeSummary(BaseModel):
    """Cross-system outcome summary for a user."""

    user_id: str
    overall_score: float = Field(0.0, ge=0, le=100)
    systems: list[SystemProgress] = Field(default_factory=list)
    total_milestones: int = 0
    completed_milestones: int = 0
    total_journal_entries: int = 0
    active_plan_day: int | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── In-memory stores ───────────────────────────────────────────────────

_milestones: dict[str, list[MilestoneRecord]] = {}
"""user_id -> list of milestone records."""

_activity_log: dict[str, list[dict[str, Any]]] = {}
"""user_id -> list of activity events."""


# ── Public API ──────────────────────────────────────────────────────────


def record_milestone(
    user_id: str,
    system: str,
    name: str,
    completed: bool = True,
    notes: str | None = None,
) -> MilestoneRecord:
    """Record a milestone event for a user.

    Parameters
    ----------
    user_id:
        The user's unique identifier.
    system:
        Which system this milestone belongs to.
    name:
        Human-readable milestone name.
    completed:
        Whether the milestone is completed.
    notes:
        Optional user notes about this milestone.

    Returns
    -------
    MilestoneRecord
        The created record.
    """
    record = MilestoneRecord(
        system=system,
        name=name,
        completed=completed,
        completed_at=datetime.now(UTC).isoformat() if completed else None,
        notes=notes,
    )

    if user_id not in _milestones:
        _milestones[user_id] = []
    _milestones[user_id].append(record)

    # Also log activity
    _log_activity(user_id, system, "milestone", name)

    return record


def record_activity(
    user_id: str,
    system: str,
    activity_type: str,
    detail: str = "",
) -> None:
    """Record a general activity event for engagement tracking.

    Parameters
    ----------
    user_id:
        The user's unique identifier.
    system:
        Which system this activity belongs to.
    activity_type:
        Type of activity (e.g., 'session', 'assessment', 'practice').
    detail:
        Optional detail string.
    """
    _log_activity(user_id, system, activity_type, detail)


def get_milestones(
    user_id: str,
    system: str | None = None,
) -> list[MilestoneRecord]:
    """Get all milestones for a user, optionally filtered by system.

    Parameters
    ----------
    user_id:
        The user's unique identifier.
    system:
        Optional system filter.

    Returns
    -------
    list[MilestoneRecord]
        Matching milestone records.
    """
    records = _milestones.get(user_id, [])
    if system:
        records = [r for r in records if r.system == system]
    return records


def calculate_outcome_summary(
    user_id: str,
    journal_count: int = 0,
    active_plan_day: int | None = None,
) -> OutcomeSummary:
    """Calculate a cross-system outcome summary.

    The overall score is a weighted composite:
    - 40% milestone completion across all systems
    - 30% engagement (activity frequency)
    - 20% system breadth (how many systems used)
    - 10% journaling consistency

    Parameters
    ----------
    user_id:
        The user's unique identifier.
    journal_count:
        Number of journal entries (from journal store).
    active_plan_day:
        Current day in 90-day plan if applicable.

    Returns
    -------
    OutcomeSummary
        The computed summary with per-system breakdowns.
    """
    all_milestones = _milestones.get(user_id, [])
    activities = _activity_log.get(user_id, [])

    # Group milestones by system
    systems_data: dict[str, dict[str, Any]] = {}
    for ms in all_milestones:
        if ms.system not in systems_data:
            systems_data[ms.system] = {"total": 0, "completed": 0}
        systems_data[ms.system]["total"] += 1
        if ms.completed:
            systems_data[ms.system]["completed"] += 1

    # Group activities by system
    activity_by_system: dict[str, list[dict[str, Any]]] = {}
    for act in activities:
        sys = act["system"]
        if sys not in activity_by_system:
            activity_by_system[sys] = []
        activity_by_system[sys].append(act)

    # Build per-system progress
    all_systems = set(list(systems_data.keys()) + list(activity_by_system.keys()))
    system_progress: list[SystemProgress] = []

    for sys_name in sorted(all_systems):
        ms_data = systems_data.get(sys_name, {"total": 0, "completed": 0})
        sys_activities = activity_by_system.get(sys_name, [])

        # Active days = unique dates with activity
        active_dates = {a["timestamp"][:10] for a in sys_activities}

        # Engagement score: activities per day scaled to 100
        engagement = min(100.0, len(sys_activities) * 10.0)

        # Completion percentage
        comp_pct = (
            (ms_data["completed"] / ms_data["total"] * 100.0) if ms_data["total"] > 0 else 0.0
        )

        last_act = max((a["timestamp"] for a in sys_activities), default=None)

        system_progress.append(
            SystemProgress(
                system=sys_name,
                engagement_score=round(engagement, 1),
                milestones_total=ms_data["total"],
                milestones_completed=ms_data["completed"],
                completion_pct=round(comp_pct, 1),
                active_days=len(active_dates),
                last_activity=last_act,
            )
        )

    # Calculate overall score
    total_ms = sum(s.milestones_total for s in system_progress)
    completed_ms = sum(s.milestones_completed for s in system_progress)

    milestone_score = (completed_ms / total_ms * 100.0) if total_ms > 0 else 0.0
    engagement_score = (
        sum(s.engagement_score for s in system_progress) / len(system_progress)
        if system_progress
        else 0.0
    )
    breadth_score = min(100.0, len(all_systems) * 20.0)  # 5 systems = 100
    journal_score = min(100.0, journal_count * 10.0)

    overall = (
        milestone_score * 0.40
        + engagement_score * 0.30
        + breadth_score * 0.20
        + journal_score * 0.10
    )

    return OutcomeSummary(
        user_id=user_id,
        overall_score=round(min(100.0, overall), 1),
        systems=system_progress,
        total_milestones=total_ms,
        completed_milestones=completed_ms,
        total_journal_entries=journal_count,
        active_plan_day=active_plan_day,
    )


# ── Internal helpers ────────────────────────────────────────────────────


def _log_activity(
    user_id: str,
    system: str,
    activity_type: str,
    detail: str = "",
) -> None:
    """Append an activity event to the user's log."""
    if user_id not in _activity_log:
        _activity_log[user_id] = []
    _activity_log[user_id].append(
        {
            "system": system,
            "type": activity_type,
            "detail": detail,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )

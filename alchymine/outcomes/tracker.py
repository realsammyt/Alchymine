"""Outcome tracker — measures user progress across all five systems.

Provides deterministic scoring based on user engagement, milestone
completion, and self-reported metrics. All calculations are transparent
and auditable.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
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


# ── Outcome Metric Models ─────────────────────────────────────────────


class MetricPeriod(StrEnum):
    """Supported measurement periods."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TrendDirection(StrEnum):
    """Trend direction for a metric time series."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class OutcomeMetric:
    """A single outcome measurement data point.

    Attributes
    ----------
    user_id:
        The user this metric belongs to.
    system:
        Which system (identity, healing, wealth, creative, perspective).
    metric_name:
        Name of the metric being tracked.
    value:
        Numeric value of the measurement.
    timestamp:
        When the measurement was taken.
    period:
        The reporting period (weekly or monthly).
    """

    user_id: str
    system: str
    metric_name: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    period: str = MetricPeriod.WEEKLY


@dataclass
class OutcomeSnapshot:
    """A point-in-time snapshot of all metrics for a user.

    Attributes
    ----------
    user_id:
        The user this snapshot belongs to.
    timestamp:
        When the snapshot was taken.
    metrics:
        Dictionary of system -> list of metric values.
    """

    user_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metrics: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass
class TrendResult:
    """Result of trend calculation for a system.

    Attributes
    ----------
    system:
        The system this trend applies to.
    direction:
        Whether the trend is improving, stable, or declining.
    metric_trends:
        Per-metric trend details.
    sample_size:
        Number of data points used in the calculation.
    """

    system: str
    direction: str
    metric_trends: dict[str, str] = field(default_factory=dict)
    sample_size: int = 0


@dataclass
class CorrelationResult:
    """Cross-system correlation result.

    Attributes
    ----------
    system_a:
        First system in the pair.
    system_b:
        Second system in the pair.
    correlation:
        Pearson-like correlation coefficient (-1 to 1).
    strength:
        Human-readable strength label.
    """

    system_a: str
    system_b: str
    correlation: float
    strength: str


class ProgressSummary(BaseModel):
    """Overall progress summary across all systems."""

    user_id: str
    total_metrics_recorded: int = 0
    systems_tracked: list[str] = Field(default_factory=list)
    trends: dict[str, str] = Field(default_factory=dict)
    correlations: list[dict[str, Any]] = Field(default_factory=list)
    outcome_summary: OutcomeSummary | None = None
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class OutcomeTracker:
    """Tracks outcome metrics across all five systems.

    Uses in-memory storage for metric data. Provides time-series
    querying, trend analysis, and cross-system correlation.

    All calculations are deterministic and auditable.
    """

    def __init__(self) -> None:
        self._metrics: list[OutcomeMetric] = []

    @property
    def metrics_store(self) -> list[OutcomeMetric]:
        """Expose the metrics store for testing purposes."""
        return self._metrics

    def record_metric(
        self,
        user_id: str,
        system: str,
        metric_name: str,
        value: float,
        period: str = MetricPeriod.WEEKLY,
        timestamp: str | None = None,
    ) -> OutcomeMetric:
        """Store a new outcome metric measurement.

        Parameters
        ----------
        user_id:
            The user's unique identifier.
        system:
            Which system (identity, healing, wealth, creative, perspective).
        metric_name:
            Name of the metric being tracked.
        value:
            Numeric value of the measurement.
        period:
            The reporting period (weekly or monthly).
        timestamp:
            Optional ISO-format timestamp. If not provided, uses current time.

        Returns
        -------
        OutcomeMetric
            The recorded metric.
        """
        metric = OutcomeMetric(
            user_id=user_id,
            system=system,
            metric_name=metric_name,
            value=value,
            period=period,
        )
        if timestamp is not None:
            metric.timestamp = timestamp
        self._metrics.append(metric)
        return metric

    def get_metrics(
        self,
        user_id: str,
        system: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[OutcomeMetric]:
        """Query metrics with optional time-range and system filters.

        Parameters
        ----------
        user_id:
            The user's unique identifier.
        system:
            Optional system filter.
        start_date:
            Optional ISO-format start date (inclusive).
        end_date:
            Optional ISO-format end date (inclusive).

        Returns
        -------
        list[OutcomeMetric]
            Matching metric records, sorted by timestamp.
        """
        results = [m for m in self._metrics if m.user_id == user_id]

        if system:
            results = [m for m in results if m.system == system]

        if start_date:
            results = [m for m in results if m.timestamp >= start_date]

        if end_date:
            # Include the entire end date by comparing with next day
            results = [m for m in results if m.timestamp[:10] <= end_date[:10]]

        return sorted(results, key=lambda m: m.timestamp)

    def calculate_trends(
        self,
        user_id: str,
        system: str,
    ) -> TrendResult:
        """Compute trend direction for a given system's metrics.

        Uses the simple approach of comparing the average of the first
        half of data points against the second half. This is fully
        deterministic and transparent.

        Parameters
        ----------
        user_id:
            The user's unique identifier.
        system:
            The system to analyze.

        Returns
        -------
        TrendResult
            The computed trend with per-metric breakdown.
        """
        metrics = self.get_metrics(user_id, system=system)

        if len(metrics) < 2:
            return TrendResult(
                system=system,
                direction=TrendDirection.STABLE,
                sample_size=len(metrics),
            )

        # Group by metric name
        by_name: dict[str, list[float]] = {}
        for m in metrics:
            if m.metric_name not in by_name:
                by_name[m.metric_name] = []
            by_name[m.metric_name].append(m.value)

        metric_trends: dict[str, str] = {}
        directions: list[str] = []

        for name, values in by_name.items():
            if len(values) < 2:
                metric_trends[name] = TrendDirection.STABLE
                directions.append(TrendDirection.STABLE)
                continue

            mid = len(values) // 2
            first_half_avg = statistics.mean(values[:mid]) if mid > 0 else values[0]
            second_half_avg = statistics.mean(values[mid:])

            # Use a 5% threshold to determine meaningful change
            if first_half_avg == 0:
                pct_change = 0.0 if second_half_avg == 0 else 100.0
            else:
                pct_change = ((second_half_avg - first_half_avg) / abs(first_half_avg)) * 100

            if pct_change > 5.0:
                direction = TrendDirection.IMPROVING
            elif pct_change < -5.0:
                direction = TrendDirection.DECLINING
            else:
                direction = TrendDirection.STABLE

            metric_trends[name] = direction
            directions.append(direction)

        # Overall direction: majority vote
        improving_count = directions.count(TrendDirection.IMPROVING)
        declining_count = directions.count(TrendDirection.DECLINING)

        if improving_count > declining_count:
            overall = TrendDirection.IMPROVING
        elif declining_count > improving_count:
            overall = TrendDirection.DECLINING
        else:
            overall = TrendDirection.STABLE

        return TrendResult(
            system=system,
            direction=overall,
            metric_trends=metric_trends,
            sample_size=len(metrics),
        )

    def cross_system_correlation(
        self,
        user_id: str,
    ) -> list[CorrelationResult]:
        """Find correlations between systems based on metric trends.

        Computes a simplified correlation by comparing average metric
        values across systems. This is deterministic and does not
        require external statistical libraries.

        Parameters
        ----------
        user_id:
            The user's unique identifier.

        Returns
        -------
        list[CorrelationResult]
            Pairwise correlation results between systems.
        """
        metrics = [m for m in self._metrics if m.user_id == user_id]

        # Group average values by system
        system_avgs: dict[str, float] = {}
        system_values: dict[str, list[float]] = {}
        for m in metrics:
            if m.system not in system_values:
                system_values[m.system] = []
            system_values[m.system].append(m.value)

        for sys_name, values in system_values.items():
            system_avgs[sys_name] = statistics.mean(values)

        systems = sorted(system_avgs.keys())
        results: list[CorrelationResult] = []

        for i, sys_a in enumerate(systems):
            for sys_b in systems[i + 1 :]:
                # Simplified correlation: compare normalized averages
                vals_a = system_values[sys_a]
                vals_b = system_values[sys_b]

                # Use minimum length for fair comparison
                min_len = min(len(vals_a), len(vals_b))
                if min_len < 2:
                    correlation = 0.0
                else:
                    correlation = self._simple_correlation(vals_a[:min_len], vals_b[:min_len])

                strength = self._correlation_strength(correlation)
                results.append(
                    CorrelationResult(
                        system_a=sys_a,
                        system_b=sys_b,
                        correlation=round(correlation, 3),
                        strength=strength,
                    )
                )

        return results

    def get_progress_summary(
        self,
        user_id: str,
        journal_count: int = 0,
        active_plan_day: int | None = None,
    ) -> ProgressSummary:
        """Generate an overall progress summary across all systems.

        Combines metric data, trend analysis, correlations, and the
        existing outcome summary into a single comprehensive view.

        Parameters
        ----------
        user_id:
            The user's unique identifier.
        journal_count:
            Number of journal entries.
        active_plan_day:
            Current day in 90-day plan.

        Returns
        -------
        ProgressSummary
            The comprehensive progress summary.
        """
        user_metrics = [m for m in self._metrics if m.user_id == user_id]
        systems_tracked = sorted({m.system for m in user_metrics})

        # Calculate trends for each system
        trends: dict[str, str] = {}
        for system in systems_tracked:
            trend = self.calculate_trends(user_id, system)
            trends[system] = trend.direction

        # Calculate cross-system correlations
        correlations = self.cross_system_correlation(user_id)
        corr_dicts = [
            {
                "system_a": c.system_a,
                "system_b": c.system_b,
                "correlation": c.correlation,
                "strength": c.strength,
            }
            for c in correlations
        ]

        # Include the existing outcome summary
        outcome = calculate_outcome_summary(
            user_id, journal_count=journal_count, active_plan_day=active_plan_day
        )

        return ProgressSummary(
            user_id=user_id,
            total_metrics_recorded=len(user_metrics),
            systems_tracked=systems_tracked,
            trends=trends,
            correlations=corr_dicts,
            outcome_summary=outcome,
        )

    @staticmethod
    def _simple_correlation(xs: list[float], ys: list[float]) -> float:
        """Compute a simple Pearson correlation coefficient.

        Parameters
        ----------
        xs:
            First data series.
        ys:
            Second data series (same length as xs).

        Returns
        -------
        float
            Correlation coefficient in range [-1, 1].
        """
        n = len(xs)
        if n < 2:
            return 0.0

        mean_x = statistics.mean(xs)
        mean_y = statistics.mean(ys)

        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
        denom_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
        denom_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5

        if denom_x == 0 or denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    @staticmethod
    def _correlation_strength(r: float) -> str:
        """Classify correlation strength from coefficient.

        Parameters
        ----------
        r:
            Pearson correlation coefficient.

        Returns
        -------
        str
            Human-readable strength label.
        """
        abs_r = abs(r)
        if abs_r >= 0.7:
            return "strong"
        elif abs_r >= 0.4:
            return "moderate"
        elif abs_r >= 0.2:
            return "weak"
        else:
            return "negligible"


# ── Shared OutcomeTracker instance ────────────────────────────────────

_outcome_tracker = OutcomeTracker()
"""Module-level OutcomeTracker instance for use by API routes."""


def get_outcome_tracker() -> OutcomeTracker:
    """Return the shared OutcomeTracker instance."""
    return _outcome_tracker


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

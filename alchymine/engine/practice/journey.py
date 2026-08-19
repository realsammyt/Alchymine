"""The journey series: what the user actually did, day by day.

One pure fold from bounded practice-log rows to a fixed-length window,
so the page that renders it has nothing to compute and nothing to guess.
Deterministic: no clock read, no randomness, no LLM. The same rows on
the same day produce the same series, which is what lets the chart be
answerable from the practice log the user can already read.

Two rules here are load-bearing and easy to get wrong.

A skip is not a smaller success. Only completions count toward practice,
the same rule :func:`~alchymine.engine.practice.ecology.summarize_practice`
applies, because a chart that counted skips would tell somebody they
practiced on a day they did not.

A loop lands on the day of the practice it closed, never the day it was
written. ``practice_log.day_key`` is the user's local day; the derived
``outcome_metrics`` row is stamped in UTC. Folding on the UTC stamp
would put an evening loop in Auckland one column to the right of the
practice it belongs to, every time.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Final

from .purposes import PURPOSE_ORDER

# The window the caller may ask for, in days. The floor is a week
# because a shorter window is the rhythm display, which already exists.
# The ceiling bounds the read: the query behind this is scoped by
# ``day_key >= start``, and without a ceiling a client could ask for the
# user's whole history and grow the response without limit.
JOURNEY_WINDOW_MIN: Final[int] = 7
JOURNEY_WINDOW_MAX: Final[int] = 90
JOURNEY_WINDOW_DEFAULT: Final[int] = 30

# Two decimals. The mean of a handful of small integers is otherwise a
# repeating binary fraction, and a value that renders as 0.6666666666666666
# in one build and 0.67 in the next is a diff nobody asked for.
_SHIFT_PRECISION: Final[int] = 2


def loop_shift_value(capacity_delta: int | None) -> float:
    """The number one closed loop contributes to the recorded shift.

    ``capacity_delta`` is the user's own read on whether the capacity
    moved, and it is optional: most loops are saved without one. When
    it is absent the practice still happened, and that is worth 1.0
    rather than 0.0.

    This is the same rule the derived ``outcome_metrics`` row is written
    under. It lives in one place so the two cannot drift: if they did,
    the journey and the dashboard would report different numbers for the
    same event and neither would be wrong on its own terms.
    """
    return float(capacity_delta) if capacity_delta is not None else 1.0


@dataclass(frozen=True)
class JourneyRow:
    """One practice-log row, with the loop that closed on it if there is one.

    Carries no user-authored text. ``reflection``, ``self_check_response``
    and the integration ``note`` are encrypted at rest and are not read
    to build a chart, so nothing the user wrote is decrypted on this
    path.
    """

    day_key: str
    primary_purpose: str
    status: str
    has_loop: bool = False
    capacity_delta: int | None = None


@dataclass(frozen=True)
class JourneyDayPoint:
    """One column of the chart.

    ``average_shift`` is ``None`` rather than 0.0 on a day with no
    loops. Zero is a real self-report meaning "nothing moved", and a day
    nobody wrote about is not that.
    """

    day_key: str
    completed: int
    purposes: tuple[str, ...]
    loops: int
    average_shift: float | None


@dataclass(frozen=True)
class JourneySeries:
    """The whole window, plus the figures that describe it.

    ``by_purpose`` is zero-filled across all five purposes so a caller
    has one shape to render rather than a map that grows as the user
    broadens. Every count here is window-scoped; the all-time anchors
    are read separately, because they are the one thing a window cannot
    tell you.
    """

    start_day: str
    end_day: str
    window_days: int
    days: tuple[JourneyDayPoint, ...]
    by_purpose: dict[str, int] = field(default_factory=dict)
    days_practiced: int = 0
    total_completed: int = 0
    total_loops: int = 0


@dataclass
class _DayBucket:
    """Mutable accumulator for one day, folded into a point at the end."""

    completed: int = 0
    purposes: set[str] = field(default_factory=set)
    shifts: list[float] = field(default_factory=list)


def _parse_day(value: str) -> date | None:
    """Parse a ``YYYY-MM-DD`` key, or ``None`` if it is not one.

    A row whose day cannot be read is dropped rather than raised on. The
    column is validated at write time, so this only fires on data that
    predates the validation or arrived around it, and a chart that
    refuses to render is worse than a chart missing one bar.
    """
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def build_journey_series(
    rows: Iterable[JourneyRow], *, today: str, window_days: int
) -> JourneySeries:
    """Fold *rows* into the ``window_days`` ending on *today*.

    The result always has exactly ``window_days`` entries, oldest first,
    zero-filled. A day with nothing on it is a gap in the chart, not a
    missing column: without the fill, every later day would slide left
    and the axis would stop meaning anything.

    Rows outside the window are ignored rather than clamped into the
    edges. The caller already bounds the query, so these are only the
    stragglers a day boundary lets through.

    Raises
    ------
    ValueError
        If *window_days* is outside :data:`JOURNEY_WINDOW_MIN` to
        :data:`JOURNEY_WINDOW_MAX`, or *today* is not a calendar date.
        Both are the caller's to validate; failing loudly here keeps a
        bad window from silently becoming a default one.
    """
    if not JOURNEY_WINDOW_MIN <= window_days <= JOURNEY_WINDOW_MAX:
        raise ValueError(
            f"window_days must be between {JOURNEY_WINDOW_MIN} and {JOURNEY_WINDOW_MAX}"
        )
    end = _parse_day(today)
    if end is None:
        raise ValueError("today must be a calendar date in YYYY-MM-DD form")

    window = [end - timedelta(days=offset) for offset in range(window_days - 1, -1, -1)]
    buckets: dict[date, _DayBucket] = {day: _DayBucket() for day in window}
    by_purpose = dict.fromkeys(PURPOSE_ORDER, 0)

    for row in rows:
        day = _parse_day(row.day_key)
        bucket = buckets.get(day) if day is not None else None
        if bucket is None:
            continue
        if row.status == "completed":
            bucket.completed += 1
            bucket.purposes.add(row.primary_purpose)
            if row.primary_purpose in by_purpose:
                by_purpose[row.primary_purpose] += 1
        if row.has_loop:
            bucket.shifts.append(loop_shift_value(row.capacity_delta))

    points = tuple(
        JourneyDayPoint(
            day_key=day.isoformat(),
            completed=buckets[day].completed,
            # Fixed order rather than insertion order, so the same day's
            # chips render identically whatever order the query returned.
            purposes=tuple(p for p in PURPOSE_ORDER if p in buckets[day].purposes),
            loops=len(buckets[day].shifts),
            average_shift=(
                round(sum(buckets[day].shifts) / len(buckets[day].shifts), _SHIFT_PRECISION)
                if buckets[day].shifts
                else None
            ),
        )
        for day in window
    )

    return JourneySeries(
        start_day=window[0].isoformat(),
        end_day=window[-1].isoformat(),
        window_days=window_days,
        days=points,
        by_purpose=by_purpose,
        days_practiced=sum(1 for point in points if point.completed > 0),
        total_completed=sum(point.completed for point in points),
        total_loops=sum(point.loops for point in points),
    )

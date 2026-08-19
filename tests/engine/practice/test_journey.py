"""Tests for the journey series: the deterministic fold behind /journey.

The page this feeds is a record of what the user actually did, so the
properties worth naming are the ones that would quietly misreport it:

- The window is exactly ``window_days`` long and zero-filled, so a day
  with nothing on it is a gap in the chart rather than a missing column
  that shifts every later day left.
- Only completions count as practice. A skip is not a smaller success,
  it is a different thing, and counting it would tell the user they
  practiced on a day they did not.
- A loop counts on the day of the practice it closed, not the day it was
  written. The practice day is the user's local day; the write is
  stamped in UTC, and mixing the two would put an evening loop in
  Auckland on the wrong column.
- An absent self-report reads as 1.0, the same value the derived
  outcome row carries. If the two rules ever disagreed, the journey and
  the dashboard would show different numbers for one event.
"""

from __future__ import annotations

import pytest

from alchymine.engine.practice.journey import (
    JOURNEY_WINDOW_DEFAULT,
    JOURNEY_WINDOW_MAX,
    JOURNEY_WINDOW_MIN,
    JourneyRow,
    build_journey_series,
    loop_shift_value,
)

TODAY = "2026-08-18"


def row(
    day_key: str,
    *,
    purpose: str = "steadiness",
    status: str = "completed",
    has_loop: bool = False,
    capacity_delta: int | None = None,
) -> JourneyRow:
    return JourneyRow(
        day_key=day_key,
        primary_purpose=purpose,
        status=status,
        has_loop=has_loop,
        capacity_delta=capacity_delta,
    )


# ── The window ───────────────────────────────────────────────────────


def test_window_is_zero_filled_and_oldest_first() -> None:
    series = build_journey_series([], today=TODAY, window_days=7)

    assert len(series.days) == 7
    assert series.days[0].day_key == "2026-08-12"
    assert series.days[-1].day_key == TODAY
    assert series.start_day == "2026-08-12"
    assert series.end_day == TODAY
    assert all(day.completed == 0 for day in series.days)


def test_empty_history_reports_zero_rather_than_nothing() -> None:
    series = build_journey_series([], today=TODAY, window_days=30)

    assert series.total_completed == 0
    assert series.total_loops == 0
    assert series.days_practiced == 0
    assert series.by_purpose == {
        "self-knowledge": 0,
        "steadiness": 0,
        "stewardship": 0,
        "expression": 0,
        "reframing": 0,
    }


def test_rows_outside_the_window_are_ignored() -> None:
    series = build_journey_series([row("2026-07-01"), row(TODAY)], today=TODAY, window_days=7)

    assert series.total_completed == 1
    assert series.days[-1].completed == 1


def test_an_unparseable_day_is_dropped_rather_than_raised() -> None:
    series = build_journey_series([row("not-a-day"), row(TODAY)], today=TODAY, window_days=7)

    assert series.total_completed == 1


# ── What counts as practice ──────────────────────────────────────────


def test_only_completions_count_as_practice() -> None:
    series = build_journey_series(
        [
            row(TODAY, status="completed"),
            row(TODAY, status="skipped"),
            row(TODAY, status="started"),
        ],
        today=TODAY,
        window_days=7,
    )

    assert series.days[-1].completed == 1
    assert series.total_completed == 1
    assert series.days_practiced == 1


def test_two_completions_on_one_day_are_one_practiced_day() -> None:
    series = build_journey_series([row(TODAY), row(TODAY)], today=TODAY, window_days=7)

    assert series.days[-1].completed == 2
    assert series.days_practiced == 1


def test_purposes_are_distinct_and_in_fixed_order() -> None:
    series = build_journey_series(
        [
            row(TODAY, purpose="reframing"),
            row(TODAY, purpose="self-knowledge"),
            row(TODAY, purpose="reframing"),
        ],
        today=TODAY,
        window_days=7,
    )

    assert series.days[-1].purposes == ("self-knowledge", "reframing")


def test_by_purpose_counts_completions_inside_the_window() -> None:
    series = build_journey_series(
        [
            row(TODAY, purpose="steadiness"),
            row("2026-08-17", purpose="steadiness"),
            row("2026-08-16", purpose="expression"),
            row("2026-08-16", purpose="expression", status="skipped"),
        ],
        today=TODAY,
        window_days=7,
    )

    assert series.by_purpose["steadiness"] == 2
    assert series.by_purpose["expression"] == 1
    assert series.by_purpose["stewardship"] == 0


def test_a_purpose_no_pack_declares_does_not_invent_a_key() -> None:
    series = build_journey_series([row(TODAY, purpose="levitation")], today=TODAY, window_days=7)

    assert "levitation" not in series.by_purpose
    assert series.total_completed == 1


# ── Loops and the recorded shift ─────────────────────────────────────


def test_a_loop_lands_on_the_day_of_the_practice_it_closed() -> None:
    series = build_journey_series(
        [row("2026-08-15", has_loop=True, capacity_delta=2)],
        today=TODAY,
        window_days=7,
    )

    landed = {day.day_key: day.loops for day in series.days if day.loops}
    assert landed == {"2026-08-15": 1}
    assert series.total_loops == 1


def test_an_absent_self_report_reads_as_one() -> None:
    assert loop_shift_value(None) == 1.0
    assert loop_shift_value(0) == 0.0
    assert loop_shift_value(-2) == -2.0


def test_average_shift_is_the_mean_of_the_days_loops() -> None:
    series = build_journey_series(
        [
            row(TODAY, has_loop=True, capacity_delta=2),
            row(TODAY, has_loop=True, capacity_delta=-1),
        ],
        today=TODAY,
        window_days=7,
    )

    assert series.days[-1].average_shift == 0.5


def test_a_day_without_loops_has_no_average_rather_than_zero() -> None:
    series = build_journey_series([row(TODAY)], today=TODAY, window_days=7)

    assert series.days[-1].loops == 0
    assert series.days[-1].average_shift is None


def test_average_shift_is_rounded_so_the_wire_value_is_stable() -> None:
    series = build_journey_series(
        [
            row(TODAY, has_loop=True, capacity_delta=1),
            row(TODAY, has_loop=True, capacity_delta=1),
            row(TODAY, has_loop=True, capacity_delta=0),
        ],
        today=TODAY,
        window_days=7,
    )

    assert series.days[-1].average_shift == 0.67


def test_a_loop_on_a_skipped_practice_still_counts_as_a_loop() -> None:
    # The user wrote something about what happened. It happened.
    series = build_journey_series(
        [row(TODAY, status="skipped", has_loop=True, capacity_delta=1)],
        today=TODAY,
        window_days=7,
    )

    assert series.days[-1].completed == 0
    assert series.days[-1].loops == 1


# ── Window bounds ────────────────────────────────────────────────────


def test_window_bounds_are_ordered_and_the_default_sits_between_them() -> None:
    assert JOURNEY_WINDOW_MIN < JOURNEY_WINDOW_DEFAULT < JOURNEY_WINDOW_MAX


@pytest.mark.parametrize("window", [0, -1, JOURNEY_WINDOW_MAX + 1])
def test_an_out_of_range_window_is_refused(window: int) -> None:
    with pytest.raises(ValueError):
        build_journey_series([], today=TODAY, window_days=window)


def test_the_fold_is_deterministic() -> None:
    rows = [
        row("2026-08-16", purpose="expression", has_loop=True, capacity_delta=1),
        row(TODAY, purpose="steadiness"),
        row("2026-08-14", purpose="reframing", status="skipped"),
    ]

    first = build_journey_series(rows, today=TODAY, window_days=30)
    second = build_journey_series(list(reversed(rows)), today=TODAY, window_days=30)

    assert first == second

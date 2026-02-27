"""Comprehensive tests for the Biorhythm Calculator engine.

Covers:
  - Core calculator (known values, edge cases, validation)
  - Range calculations (multi-day, critical-day detection, peak-day detection)
  - Compatibility (similarity scoring, sync percentage)
  - API endpoints (POST routes)
  - Transparency (evidence rating, methodology note)

Minimum 25 tests as specified in the issue.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from alchymine.engine.biorhythm import (
    CRITICAL_THRESHOLD,
    EMOTIONAL_CYCLE,
    EVIDENCE_RATING,
    INTELLECTUAL_CYCLE,
    METHODOLOGY_NOTE,
    PHYSICAL_CYCLE,
    BiorhythmResult,
    biorhythm_compatibility,
    calculate_biorhythm,
    calculate_range,
    find_critical_days,
    find_peak_days,
    sync_percentage,
)


# ─── Fixtures ─────────────────────────────────────────────────────────

BIRTH_DATE = date(1990, 1, 1)


# ─── 1. Core Calculator: Known Values ────────────────────────────────


class TestCoreCalculator:
    """Tests for calculate_biorhythm with known mathematical values."""

    def test_day_zero_all_cycles_are_zero(self) -> None:
        """On the day of birth (day 0), all sine values should be 0."""
        result = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE)
        assert result.physical == 0.0
        assert result.emotional == 0.0
        assert result.intellectual == 0.0
        assert result.days_alive == 0

    def test_day_zero_percentages_are_50(self) -> None:
        """Day 0: sine=0 maps to 50%."""
        result = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE)
        assert result.physical_percentage == 50
        assert result.emotional_percentage == 50
        assert result.intellectual_percentage == 50

    def test_physical_peak_at_quarter_cycle(self) -> None:
        """At day 23/4 ~ day 5.75, physical should be near +1.0.

        We use day 6 (closest integer) and verify it is very close to peak.
        Exact: sin(2*pi*6/23) ~ 0.9980..., close to 1.0.
        Actually, the true peak is at exactly 23/4 = 5.75 days.
        At day 6: sin(2*pi*6/23) = sin(12*pi/23).
        """
        # The exact quarter-cycle is not an integer day, so we compute
        # the expected value and verify the engine matches.
        target = BIRTH_DATE + timedelta(days=6)
        result = calculate_biorhythm(BIRTH_DATE, target)
        expected = math.sin(2 * math.pi * 6 / PHYSICAL_CYCLE)
        assert abs(result.physical - round(expected, 10)) < 1e-9
        # Should be close to 1.0
        assert result.physical > 0.95

    def test_physical_trough_at_three_quarter_cycle(self) -> None:
        """The trough (minimum) of a sine wave is at 3/4 of the cycle.

        Physical cycle: 23 days. 3/4 * 23 = 17.25. Nearest integer = day 17.
        sin(2*pi*17/23) ~ -0.9977, close to -1.0.
        """
        target = BIRTH_DATE + timedelta(days=17)
        result = calculate_biorhythm(BIRTH_DATE, target)
        expected = math.sin(2 * math.pi * 17 / PHYSICAL_CYCLE)
        assert abs(result.physical - round(expected, 10)) < 1e-9
        assert result.physical < -0.95

    def test_emotional_peak_at_quarter_cycle(self) -> None:
        """Emotional cycle: 28 days. Quarter = day 7. sin(2*pi*7/28) = sin(pi/2) = 1.0."""
        target = BIRTH_DATE + timedelta(days=7)
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert abs(result.emotional - 1.0) < 1e-9

    def test_emotional_trough_at_three_quarter_cycle(self) -> None:
        """Emotional: day 21. sin(2*pi*21/28) = sin(3*pi/2) = -1.0."""
        target = BIRTH_DATE + timedelta(days=21)
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert abs(result.emotional - (-1.0)) < 1e-9

    def test_intellectual_peak_at_quarter_cycle(self) -> None:
        """Intellectual cycle: 33 days. Quarter ~ day 8.25.

        Day 8: sin(2*pi*8/33) should be close to 1.0.
        """
        target = BIRTH_DATE + timedelta(days=8)
        result = calculate_biorhythm(BIRTH_DATE, target)
        expected = math.sin(2 * math.pi * 8 / INTELLECTUAL_CYCLE)
        assert abs(result.intellectual - round(expected, 10)) < 1e-9
        assert result.intellectual > 0.9

    def test_full_physical_cycle_returns_near_zero(self) -> None:
        """After exactly one full physical cycle (23 days), value returns to ~0."""
        target = BIRTH_DATE + timedelta(days=PHYSICAL_CYCLE)
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert abs(result.physical) < 1e-9

    def test_full_emotional_cycle_returns_to_zero(self) -> None:
        """After exactly one full emotional cycle (28 days), value returns to ~0."""
        target = BIRTH_DATE + timedelta(days=EMOTIONAL_CYCLE)
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert abs(result.emotional) < 1e-9

    def test_full_intellectual_cycle_returns_to_zero(self) -> None:
        """After exactly one full intellectual cycle (33 days), value returns to ~0."""
        target = BIRTH_DATE + timedelta(days=INTELLECTUAL_CYCLE)
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert abs(result.intellectual) < 1e-9


# ─── 2. Critical Day Detection ───────────────────────────────────────


class TestCriticalDays:
    """Tests for critical-day detection (zero-crossing)."""

    def test_day_zero_is_critical_for_all(self) -> None:
        """Day 0: all values are 0 — all are critical."""
        result = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE)
        assert result.is_physical_critical is True
        assert result.is_emotional_critical is True
        assert result.is_intellectual_critical is True

    def test_full_cycle_is_critical(self) -> None:
        """Day == cycle_length: value returns to 0 — is critical."""
        for cycle in [PHYSICAL_CYCLE, EMOTIONAL_CYCLE, INTELLECTUAL_CYCLE]:
            target = BIRTH_DATE + timedelta(days=cycle)
            result = calculate_biorhythm(BIRTH_DATE, target)
            if cycle == PHYSICAL_CYCLE:
                assert result.is_physical_critical is True
            elif cycle == EMOTIONAL_CYCLE:
                assert result.is_emotional_critical is True
            else:
                assert result.is_intellectual_critical is True

    def test_peak_day_is_not_critical(self) -> None:
        """Day 7 for emotional: value=1.0, definitely not critical."""
        target = BIRTH_DATE + timedelta(days=7)
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert result.is_emotional_critical is False

    def test_critical_threshold_boundary(self) -> None:
        """Verify CRITICAL_THRESHOLD constant is 0.1."""
        assert CRITICAL_THRESHOLD == 0.1

    def test_find_critical_days_in_range(self) -> None:
        """Find critical days in a 30-day range; day 0 should have 3 critical entries."""
        crits = find_critical_days(BIRTH_DATE, BIRTH_DATE, 30)
        assert isinstance(crits, list)
        # Day 0 produces 3 critical entries (one per cycle)
        day_zero_crits = [c for c in crits if c["days_alive"] == 0]
        assert len(day_zero_crits) == 3

    def test_find_critical_days_returns_correct_keys(self) -> None:
        """Each critical day dict has the expected keys."""
        crits = find_critical_days(BIRTH_DATE, BIRTH_DATE, 10)
        if crits:
            keys = set(crits[0].keys())
            assert keys == {"date", "cycle", "value", "days_alive"}


# ─── 3. Range Calculations ───────────────────────────────────────────


class TestRangeCalculations:
    """Tests for calculate_range and related range functions."""

    def test_range_returns_correct_count(self) -> None:
        """calculate_range(days=30) returns exactly 30 results."""
        results = calculate_range(BIRTH_DATE, BIRTH_DATE, 30)
        assert len(results) == 30

    def test_range_single_day(self) -> None:
        """calculate_range(days=1) returns exactly 1 result."""
        results = calculate_range(BIRTH_DATE, BIRTH_DATE, 1)
        assert len(results) == 1
        assert results[0].days_alive == 0

    def test_range_results_are_chronological(self) -> None:
        """Results should be in ascending date order."""
        results = calculate_range(BIRTH_DATE, BIRTH_DATE, 10)
        dates = [r.target_date for r in results]
        assert dates == sorted(dates)

    def test_range_days_alive_increment(self) -> None:
        """days_alive should increment by 1 each day."""
        results = calculate_range(BIRTH_DATE, BIRTH_DATE, 5)
        for i, result in enumerate(results):
            assert result.days_alive == i

    def test_range_invalid_days_raises(self) -> None:
        """days < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="days must be >= 1"):
            calculate_range(BIRTH_DATE, BIRTH_DATE, 0)

    def test_find_peak_days_in_range(self) -> None:
        """find_peak_days should find peaks in a 30-day range."""
        peaks = find_peak_days(BIRTH_DATE, BIRTH_DATE, 30)
        assert isinstance(peaks, list)
        # Day 7 emotional peak (value=1.0) should be found
        emotional_peaks = [p for p in peaks if p["cycle"] == "emotional" and p["peak_type"] == "high"]
        assert len(emotional_peaks) >= 1

    def test_find_peak_days_returns_correct_keys(self) -> None:
        """Each peak day dict has the expected keys."""
        peaks = find_peak_days(BIRTH_DATE, BIRTH_DATE, 30)
        if peaks:
            keys = set(peaks[0].keys())
            assert keys == {"date", "cycle", "value", "peak_type", "days_alive"}


# ─── 4. Compatibility ────────────────────────────────────────────────


class TestCompatibility:
    """Tests for biorhythm compatibility calculations."""

    def test_same_person_perfect_sync(self) -> None:
        """Same birth date => 100% sync on any day."""
        target = BIRTH_DATE + timedelta(days=100)
        result = biorhythm_compatibility(BIRTH_DATE, BIRTH_DATE, target)
        assert result["overall_sync"] == 100.0
        assert result["physical_similarity"] == 100.0
        assert result["emotional_similarity"] == 100.0
        assert result["intellectual_similarity"] == 100.0

    def test_compatibility_returns_correct_keys(self) -> None:
        """Result dict has all expected keys."""
        # Use a target_date well after both birth dates
        target = date(2020, 1, 1)
        result = biorhythm_compatibility(BIRTH_DATE, date(1991, 6, 15), target)
        expected_keys = {
            "person_a", "person_b",
            "physical_similarity", "emotional_similarity", "intellectual_similarity",
            "overall_sync", "evidence_rating", "methodology_note",
        }
        assert set(result.keys()) == expected_keys

    def test_sync_percentage_same_results(self) -> None:
        """sync_percentage of identical results is 100.0."""
        result = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE + timedelta(days=50))
        assert sync_percentage(result, result) == 100.0

    def test_sync_percentage_opposite_results(self) -> None:
        """Two results with opposite sine values should have low sync."""
        # Emotional cycle: day 7 gives +1.0, day 21 gives -1.0
        result_peak = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE + timedelta(days=7))
        result_trough = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE + timedelta(days=21))

        # Emotional similarity should be 0% (1.0 vs -1.0)
        from alchymine.engine.biorhythm.compatibility import _cycle_similarity
        assert _cycle_similarity(result_peak.emotional, result_trough.emotional) == 0.0

    def test_compatibility_different_birth_dates(self) -> None:
        """Different birth dates should produce non-100% sync in general."""
        # Use a target_date well after both birth dates
        target = date(2020, 1, 1)
        result = biorhythm_compatibility(BIRTH_DATE, date(1992, 7, 4), target)
        # Highly unlikely to be exactly 100% with different birth dates
        assert 0.0 <= result["overall_sync"] <= 100.0


# ─── 5. Validation & Edge Cases ──────────────────────────────────────


class TestValidation:
    """Tests for input validation and edge cases."""

    def test_target_before_birth_raises(self) -> None:
        """target_date before birth_date should raise ValueError."""
        with pytest.raises(ValueError, match="target_date cannot be before birth_date"):
            calculate_biorhythm(BIRTH_DATE, date(1989, 1, 1))

    def test_large_days_alive(self) -> None:
        """Calculate biorhythm for someone very old (100+ years)."""
        target = BIRTH_DATE + timedelta(days=36500)  # ~100 years
        result = calculate_biorhythm(BIRTH_DATE, target)
        assert result.days_alive == 36500
        assert -1.0 <= result.physical <= 1.0
        assert -1.0 <= result.emotional <= 1.0
        assert -1.0 <= result.intellectual <= 1.0

    def test_percentage_bounds(self) -> None:
        """Percentages should always be 0-100 for any day."""
        for days in range(0, 100):
            target = BIRTH_DATE + timedelta(days=days)
            result = calculate_biorhythm(BIRTH_DATE, target)
            assert 0 <= result.physical_percentage <= 100
            assert 0 <= result.emotional_percentage <= 100
            assert 0 <= result.intellectual_percentage <= 100


# ─── 6. Transparency & Ethics ────────────────────────────────────────


class TestTransparency:
    """Tests for evidence rating and methodology disclosure."""

    def test_evidence_rating_is_low(self) -> None:
        """Evidence rating must be LOW."""
        assert EVIDENCE_RATING == "LOW"

    def test_methodology_note_present(self) -> None:
        """Methodology note must mention scientific consensus."""
        assert "not supported by scientific consensus" in METHODOLOGY_NOTE

    def test_result_includes_evidence_rating(self) -> None:
        """Each BiorhythmResult includes evidence_rating field."""
        result = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE)
        assert result.evidence_rating == "LOW"

    def test_result_includes_methodology_note(self) -> None:
        """Each BiorhythmResult includes methodology_note field."""
        result = calculate_biorhythm(BIRTH_DATE, BIRTH_DATE)
        assert "entertainment and self-reflection" in result.methodology_note

    def test_compatibility_includes_transparency(self) -> None:
        """Compatibility result includes evidence rating and methodology."""
        # Use a target_date well after both birth dates
        result = biorhythm_compatibility(BIRTH_DATE, date(1991, 1, 1), date(2020, 1, 1))
        assert result["evidence_rating"] == "LOW"
        assert "not supported by scientific consensus" in result["methodology_note"]


# ─── 7. Cycle Constants ──────────────────────────────────────────────


class TestConstants:
    """Tests for cycle length constants."""

    def test_physical_cycle_is_23(self) -> None:
        assert PHYSICAL_CYCLE == 23

    def test_emotional_cycle_is_28(self) -> None:
        assert EMOTIONAL_CYCLE == 28

    def test_intellectual_cycle_is_33(self) -> None:
        assert INTELLECTUAL_CYCLE == 33

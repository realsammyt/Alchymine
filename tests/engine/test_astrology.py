"""Tests for astrological chart engine."""

from __future__ import annotations

from datetime import date

from alchymine.engine.astrology import (
    approximate_sun_degree,
    approximate_sun_sign,
    calculate_natal_chart,
)


class TestSunSign:
    """Tests for approximate sun sign calculation."""

    def test_pisces(self) -> None:
        assert approximate_sun_sign(date(1992, 3, 15)) == "Pisces"

    def test_aries(self) -> None:
        assert approximate_sun_sign(date(1990, 4, 5)) == "Aries"

    def test_cancer(self) -> None:
        assert approximate_sun_sign(date(1990, 7, 4)) == "Cancer"

    def test_capricorn_december(self) -> None:
        assert approximate_sun_sign(date(1995, 12, 25)) == "Capricorn"

    def test_capricorn_january(self) -> None:
        assert approximate_sun_sign(date(2000, 1, 5)) == "Capricorn"

    def test_aquarius(self) -> None:
        assert approximate_sun_sign(date(2000, 2, 1)) == "Aquarius"

    def test_leo(self) -> None:
        assert approximate_sun_sign(date(1988, 8, 10)) == "Leo"

    def test_scorpio(self) -> None:
        assert approximate_sun_sign(date(1999, 11, 5)) == "Scorpio"

    def test_boundary_aries_start(self) -> None:
        """March 21 is Aries."""
        assert approximate_sun_sign(date(2000, 3, 21)) == "Aries"

    def test_boundary_pisces_end(self) -> None:
        """March 20 is still Pisces."""
        assert approximate_sun_sign(date(2000, 3, 20)) == "Pisces"


class TestSunDegree:
    """Tests for approximate sun degree calculation."""

    def test_returns_float(self) -> None:
        result = approximate_sun_degree(date(1992, 3, 15))
        assert isinstance(result, float)

    def test_degree_range(self) -> None:
        """Degree should always be 0-360."""
        for month in range(1, 13):
            degree = approximate_sun_degree(date(2000, month, 15))
            assert 0 <= degree < 360

    def test_pisces_date_near_360(self) -> None:
        """March 15 is 5 days before equinox, so ~355 degrees."""
        degree = approximate_sun_degree(date(1992, 3, 15))
        assert 350 < degree < 360 or 0 <= degree < 5

    def test_june_near_90(self) -> None:
        """Around June 20 should be near 90 degrees (Cancer)."""
        degree = approximate_sun_degree(date(2000, 6, 20))
        assert 80 < degree < 100


class TestNatalChart:
    """Tests for full natal chart calculation."""

    def test_returns_dict(self) -> None:
        result = calculate_natal_chart(date(1992, 3, 15))
        assert isinstance(result, dict)

    def test_has_required_keys(self) -> None:
        result = calculate_natal_chart(date(1992, 3, 15))
        assert "sun_sign" in result
        assert "sun_degree" in result
        assert "moon_sign" in result
        assert "moon_degree" in result
        assert "birth_date" in result

    def test_sun_sign_is_pisces(self) -> None:
        result = calculate_natal_chart(date(1992, 3, 15))
        assert result["sun_sign"] == "Pisces"

    def test_moon_sign_is_string(self) -> None:
        result = calculate_natal_chart(date(1992, 3, 15))
        assert isinstance(result["moon_sign"], str)
        assert len(result["moon_sign"]) > 0

    def test_without_birth_time_no_rising(self) -> None:
        result = calculate_natal_chart(date(1992, 3, 15))
        assert result["rising_sign"] is None

    def test_deterministic(self) -> None:
        a = calculate_natal_chart(date(1992, 3, 15))
        b = calculate_natal_chart(date(1992, 3, 15))
        assert a["sun_sign"] == b["sun_sign"]
        assert a["sun_degree"] == b["sun_degree"]
        assert a["moon_sign"] == b["moon_sign"]

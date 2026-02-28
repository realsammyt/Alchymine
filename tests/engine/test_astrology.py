"""Tests for astrological chart engine.

Covers:
- Sun sign approximation (including cusp dates, all 12 signs)
- Sun degree approximation
- Moon sign approximation
- Natal chart calculation (with and without birth time/location)
- Rising sign / Ascendant calculation
- House system calculations (Placidus, Koch, Equal, Whole Sign)
- Aspect calculations (all major and minor types)
- Orb tolerance calculations
- Transit aspect detection
- Edge cases (cusp dates, midnight births, southern hemisphere)
- Determinism
"""

from __future__ import annotations

from datetime import date, time

import pytest

from alchymine.engine.astrology import (
    MAJOR_ASPECTS,
    Aspect,
    AspectType,
    HouseSystem,
    TransitAspect,
    angular_separation,
    approximate_ascendant,
    approximate_planet_longitude,
    approximate_sun_degree,
    approximate_sun_sign,
    aspect_strength,
    calculate_aspects,
    calculate_house_cusps,
    calculate_natal_chart,
    calculate_transit_aspects,
    filter_aspects_by_type,
    find_aspect,
    get_current_positions,
    get_transit_overlay,
    normalize_angle,
    summarize_transits,
)
from alchymine.engine.astrology.transits import PLANET_ELEMENTS

# ═══════════════════════════════════════════════════════════════════════════
# Sun Sign Tests
# ═══════════════════════════════════════════════════════════════════════════


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

    def test_taurus(self) -> None:
        assert approximate_sun_sign(date(2005, 5, 1)) == "Taurus"

    def test_gemini(self) -> None:
        assert approximate_sun_sign(date(2010, 6, 10)) == "Gemini"

    def test_virgo(self) -> None:
        assert approximate_sun_sign(date(1985, 9, 10)) == "Virgo"

    def test_libra(self) -> None:
        assert approximate_sun_sign(date(1978, 10, 5)) == "Libra"

    def test_sagittarius(self) -> None:
        assert approximate_sun_sign(date(2020, 12, 1)) == "Sagittarius"

    def test_boundary_taurus_start(self) -> None:
        """April 20 is Taurus."""
        assert approximate_sun_sign(date(2000, 4, 20)) == "Taurus"

    def test_boundary_taurus_before(self) -> None:
        """April 19 is still Aries."""
        assert approximate_sun_sign(date(2000, 4, 19)) == "Aries"

    def test_cusp_capricorn_aquarius(self) -> None:
        """January 20 is Aquarius."""
        assert approximate_sun_sign(date(2000, 1, 20)) == "Aquarius"

    def test_cusp_capricorn_aquarius_before(self) -> None:
        """January 19 is still Capricorn."""
        assert approximate_sun_sign(date(2000, 1, 19)) == "Capricorn"


# ═══════════════════════════════════════════════════════════════════════════
# Sun Degree Tests
# ═══════════════════════════════════════════════════════════════════════════


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

    def test_september_near_180(self) -> None:
        """Around September 22 should be near 180 degrees (Libra)."""
        degree = approximate_sun_degree(date(2000, 9, 22))
        assert 170 < degree < 195

    def test_december_near_270(self) -> None:
        """Around December 21 should be near 270 degrees (Capricorn)."""
        degree = approximate_sun_degree(date(2000, 12, 21))
        assert 260 < degree < 280

    def test_vernal_equinox_near_zero(self) -> None:
        """March 20 should be near 0 degrees."""
        degree = approximate_sun_degree(date(2000, 3, 20))
        assert degree < 2 or degree > 358


# ═══════════════════════════════════════════════════════════════════════════
# Natal Chart Tests
# ═══════════════════════════════════════════════════════════════════════════


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

    def test_with_birth_time_and_city(self) -> None:
        """Birth time + known city should produce rising sign."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            birth_time=time(14, 30),
            birth_city="New York",
        )
        assert result["rising_sign"] is not None
        assert result["rising_degree"] is not None

    def test_with_birth_time_and_coordinates(self) -> None:
        """Birth time + lat/lon should produce rising sign."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            birth_time=time(14, 30),
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert result["rising_sign"] is not None
        assert result["rising_degree"] is not None

    def test_with_birth_time_no_location_no_rising(self) -> None:
        """Birth time alone (no location) should not produce rising sign."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            birth_time=time(14, 30),
        )
        assert result["rising_sign"] is None

    def test_includes_planetary_positions(self) -> None:
        """Approximate chart should include planetary positions."""
        result = calculate_natal_chart(date(1992, 3, 15))
        assert "planetary_positions" in result
        positions = result["planetary_positions"]
        assert "Sun" in positions
        assert "Moon" in positions
        assert "Mars" in positions

    def test_includes_aspects_by_default(self) -> None:
        """Natal chart should include aspects by default."""
        result = calculate_natal_chart(date(1992, 3, 15))
        assert "aspects" in result
        assert isinstance(result["aspects"], list)

    def test_aspects_can_be_disabled(self) -> None:
        """Aspects can be turned off."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            include_aspects=False,
        )
        assert result["aspects"] == []

    def test_house_cusps_with_location(self) -> None:
        """House cusps should be present when location is provided."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            birth_time=time(14, 30),
            birth_city="London",
        )
        assert result["house_cusps"] is not None
        assert len(result["house_cusps"]) == 12

    def test_house_placements_with_location(self) -> None:
        """House placements should be present when cusps are available."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            birth_time=time(14, 30),
            birth_city="Tokyo",
        )
        assert result["house_placements"] is not None
        placements = result["house_placements"]
        for planet, house in placements.items():
            assert 1 <= house <= 12, f"{planet} in house {house}"

    def test_unknown_city_no_rising(self) -> None:
        """Unknown city without lat/lon should not crash, just no rising."""
        result = calculate_natal_chart(
            date(1992, 3, 15),
            birth_time=time(14, 30),
            birth_city="Smalltown Nowhere",
        )
        assert result["rising_sign"] is None


# ═══════════════════════════════════════════════════════════════════════════
# Angle Utility Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAngleUtilities:
    """Tests for normalize_angle and angular_separation."""

    def test_normalize_positive(self) -> None:
        assert normalize_angle(370.0) == 10.0

    def test_normalize_negative(self) -> None:
        assert normalize_angle(-10.0) == 350.0

    def test_normalize_zero(self) -> None:
        assert normalize_angle(0.0) == 0.0

    def test_normalize_360(self) -> None:
        assert normalize_angle(360.0) == 0.0

    def test_normalize_large(self) -> None:
        assert normalize_angle(720.5) == 0.5

    def test_separation_same_point(self) -> None:
        assert angular_separation(100.0, 100.0) == 0.0

    def test_separation_opposite(self) -> None:
        assert angular_separation(10.0, 190.0) == 180.0

    def test_separation_across_zero(self) -> None:
        assert angular_separation(350.0, 10.0) == 20.0

    def test_separation_symmetric(self) -> None:
        """angular_separation(a, b) == angular_separation(b, a)."""
        assert angular_separation(30.0, 150.0) == angular_separation(150.0, 30.0)

    def test_separation_max_180(self) -> None:
        """Separation should never exceed 180."""
        for d in range(0, 360, 15):
            sep = angular_separation(0, float(d))
            assert 0 <= sep <= 180


# ═══════════════════════════════════════════════════════════════════════════
# Aspect Calculation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAspectDetection:
    """Tests for finding aspects between two positions."""

    def test_exact_conjunction(self) -> None:
        result = find_aspect(100.0, 100.0)
        assert result is not None
        assert result.aspect_type == AspectType.CONJUNCTION
        assert result.orb == 0.0

    def test_exact_opposition(self) -> None:
        result = find_aspect(10.0, 190.0)
        assert result is not None
        assert result.aspect_type == AspectType.OPPOSITION
        assert result.orb == 0.0

    def test_exact_trine(self) -> None:
        result = find_aspect(0.0, 120.0)
        assert result is not None
        assert result.aspect_type == AspectType.TRINE
        assert result.orb == 0.0

    def test_exact_square(self) -> None:
        result = find_aspect(45.0, 135.0)
        assert result is not None
        assert result.aspect_type == AspectType.SQUARE
        assert result.orb == 0.0

    def test_exact_sextile(self) -> None:
        result = find_aspect(30.0, 90.0)
        assert result is not None
        assert result.aspect_type == AspectType.SEXTILE
        assert result.orb == 0.0

    def test_exact_quincunx(self) -> None:
        result = find_aspect(0.0, 150.0)
        assert result is not None
        assert result.aspect_type == AspectType.QUINCUNX
        assert result.orb == 0.0

    def test_exact_semi_sextile(self) -> None:
        result = find_aspect(0.0, 30.0)
        assert result is not None
        assert result.aspect_type == AspectType.SEMI_SEXTILE
        assert result.orb == 0.0

    def test_exact_semi_square(self) -> None:
        result = find_aspect(0.0, 45.0)
        assert result is not None
        assert result.aspect_type == AspectType.SEMI_SQUARE
        assert result.orb == 0.0

    def test_exact_sesquiquadrate(self) -> None:
        result = find_aspect(0.0, 135.0)
        assert result is not None
        assert result.aspect_type == AspectType.SESQUIQUADRATE
        assert result.orb == 0.0

    def test_conjunction_within_orb(self) -> None:
        result = find_aspect(100.0, 105.0)
        assert result is not None
        assert result.aspect_type == AspectType.CONJUNCTION
        assert result.orb == pytest.approx(5.0, abs=0.01)

    def test_opposition_within_orb(self) -> None:
        result = find_aspect(10.0, 185.0)
        assert result is not None
        assert result.aspect_type == AspectType.OPPOSITION
        assert result.orb == pytest.approx(5.0, abs=0.01)

    def test_trine_within_orb(self) -> None:
        result = find_aspect(0.0, 117.0)
        assert result is not None
        assert result.aspect_type == AspectType.TRINE
        assert result.orb == pytest.approx(3.0, abs=0.01)

    def test_square_within_orb(self) -> None:
        result = find_aspect(0.0, 86.0)
        assert result is not None
        assert result.aspect_type == AspectType.SQUARE
        assert result.orb == pytest.approx(4.0, abs=0.01)

    def test_no_aspect_out_of_orb(self) -> None:
        """Two positions with no close aspect angle."""
        result = find_aspect(0.0, 25.0)
        assert result is None

    def test_aspect_across_zero(self) -> None:
        """Aspect detection works across the 0/360 boundary."""
        # 358 and 2 are 4 degrees apart, within conjunction orb of 8
        result = find_aspect(358.0, 2.0)
        assert result is not None
        assert result.aspect_type == AspectType.CONJUNCTION
        assert result.orb == pytest.approx(4.0, abs=0.01)

    def test_custom_orbs(self) -> None:
        """Custom orb tolerances are respected."""
        tight_orbs = {a: 1.0 for a in AspectType}
        result = find_aspect(0.0, 5.0, orbs=tight_orbs)
        assert result is None  # 5 degree orb exceeds 1 degree tolerance

    def test_restrict_to_major_aspects_only(self) -> None:
        """Only check major aspects when specified."""
        result = find_aspect(0.0, 30.0, aspect_types=MAJOR_ASPECTS)
        # 30 degrees is a semi-sextile (minor), should not match as major
        assert result is None

    def test_conjunction_at_zero_boundary(self) -> None:
        """Conjunction near 0/360 degrees."""
        result = find_aspect(1.0, 359.0)
        assert result is not None
        assert result.aspect_type == AspectType.CONJUNCTION
        assert result.orb == pytest.approx(2.0, abs=0.01)


class TestCalculateAspects:
    """Tests for calculating aspects between multiple planetary positions."""

    def test_basic_aspects(self) -> None:
        positions = {
            "Sun": 0.0,
            "Moon": 120.0,  # trine to Sun
            "Mars": 90.0,  # square to Sun, semi-square to Moon (120-90=30 -> semi-sextile)
        }
        aspects = calculate_aspects(positions)
        assert len(aspects) > 0

    def test_aspects_sorted_by_orb(self) -> None:
        positions = {
            "Sun": 0.0,
            "Moon": 120.5,  # trine to Sun (0.5 orb)
            "Mars": 92.0,  # square to Sun (2.0 orb)
        }
        aspects = calculate_aspects(positions)
        orbs = [a.orb for a in aspects]
        assert orbs == sorted(orbs)

    def test_major_only(self) -> None:
        positions = {
            "Sun": 0.0,
            "Moon": 30.0,  # semi-sextile (minor)
            "Mars": 120.0,  # trine (major)
        }
        aspects = calculate_aspects(positions, include_minor=False)
        for a in aspects:
            assert a.aspect_type in MAJOR_ASPECTS

    def test_no_self_aspects(self) -> None:
        """A planet should not aspect itself."""
        positions = {"Sun": 50.0, "Moon": 50.0}
        aspects = calculate_aspects(positions)
        # Sun conjunct Moon is valid; no self-aspects
        for a in aspects:
            assert a.planet1 != a.planet2

    def test_all_planets_produce_aspects(self) -> None:
        """A full chart with 10 planets should produce multiple aspects."""
        positions = {
            "Sun": 0.0,
            "Moon": 120.0,
            "Mercury": 5.0,
            "Venus": 60.0,
            "Mars": 180.0,
            "Jupiter": 90.0,
            "Saturn": 270.0,
            "Uranus": 45.0,
            "Neptune": 150.0,
            "Pluto": 240.0,
        }
        aspects = calculate_aspects(positions)
        assert len(aspects) >= 5

    def test_empty_positions(self) -> None:
        """Empty positions dict should return no aspects."""
        aspects = calculate_aspects({})
        assert aspects == []

    def test_single_planet(self) -> None:
        """Single planet should return no aspects."""
        aspects = calculate_aspects({"Sun": 100.0})
        assert aspects == []


class TestAspectStrength:
    """Tests for aspect strength calculation."""

    def test_exact_aspect(self) -> None:
        assert aspect_strength(0.0, 8.0) == 1.0

    def test_half_orb(self) -> None:
        assert aspect_strength(4.0, 8.0) == 0.5

    def test_full_orb(self) -> None:
        assert aspect_strength(8.0, 8.0) == 0.0

    def test_strength_range(self) -> None:
        """Strength should always be 0-1."""
        for orb in [0, 1, 2, 3, 4, 5, 6, 7, 8]:
            s = aspect_strength(float(orb), 8.0)
            assert 0.0 <= s <= 1.0

    def test_zero_max_orb_exact(self) -> None:
        assert aspect_strength(0.0, 0.0) == 1.0

    def test_zero_max_orb_nonexact(self) -> None:
        assert aspect_strength(1.0, 0.0) == 0.0


class TestFilterAspects:
    """Tests for filtering aspects by type."""

    def test_major_only_filter(self) -> None:
        aspects = [
            Aspect("Sun", "Moon", AspectType.TRINE, 120.0, 120.0, 0.0),
            Aspect("Sun", "Mars", AspectType.SEMI_SEXTILE, 30.0, 30.0, 0.0),
        ]
        filtered = filter_aspects_by_type(aspects, major_only=True)
        assert len(filtered) == 1
        assert filtered[0].aspect_type == AspectType.TRINE

    def test_minor_only_filter(self) -> None:
        aspects = [
            Aspect("Sun", "Moon", AspectType.TRINE, 120.0, 120.0, 0.0),
            Aspect("Sun", "Mars", AspectType.SEMI_SEXTILE, 30.0, 30.0, 0.0),
        ]
        filtered = filter_aspects_by_type(aspects, minor_only=True)
        assert len(filtered) == 1
        assert filtered[0].aspect_type == AspectType.SEMI_SEXTILE

    def test_both_flags_returns_empty(self) -> None:
        aspects = [
            Aspect("Sun", "Moon", AspectType.TRINE, 120.0, 120.0, 0.0),
        ]
        filtered = filter_aspects_by_type(aspects, major_only=True, minor_only=True)
        assert filtered == []


# ═══════════════════════════════════════════════════════════════════════════
# Rising Sign / Ascendant Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRisingSign:
    """Tests for approximate ascendant calculation."""

    def test_returns_sign_and_degree(self) -> None:
        sign, degree = approximate_ascendant(date(1992, 3, 15), time(14, 30), 40.7128, -74.0060)
        assert isinstance(sign, str)
        assert isinstance(degree, float)
        assert 0 <= degree < 360

    def test_rising_sign_is_valid_zodiac(self) -> None:
        valid_signs = {
            "Aries",
            "Taurus",
            "Gemini",
            "Cancer",
            "Leo",
            "Virgo",
            "Libra",
            "Scorpio",
            "Sagittarius",
            "Capricorn",
            "Aquarius",
            "Pisces",
        }
        sign, _ = approximate_ascendant(date(2000, 6, 21), time(6, 0), 51.5074, -0.1278)
        assert sign in valid_signs

    def test_rising_deterministic(self) -> None:
        a = approximate_ascendant(date(1990, 1, 1), time(12, 0), 40.0, -74.0)
        b = approximate_ascendant(date(1990, 1, 1), time(12, 0), 40.0, -74.0)
        assert a == b

    def test_different_times_different_rising(self) -> None:
        """Different birth times should (usually) give different ascendants."""
        _, d1 = approximate_ascendant(date(2000, 6, 21), time(6, 0), 40.0, -74.0)
        _, d2 = approximate_ascendant(date(2000, 6, 21), time(18, 0), 40.0, -74.0)
        assert d1 != d2

    def test_midnight_birth(self) -> None:
        """Midnight birth should not crash."""
        sign, degree = approximate_ascendant(date(2000, 1, 1), time(0, 0), 40.7128, -74.0060)
        assert isinstance(sign, str)
        assert 0 <= degree < 360

    def test_noon_birth(self) -> None:
        """Noon birth should not crash."""
        sign, degree = approximate_ascendant(date(2000, 1, 1), time(12, 0), 40.7128, -74.0060)
        assert isinstance(sign, str)
        assert 0 <= degree < 360

    def test_southern_hemisphere(self) -> None:
        """Southern hemisphere (negative latitude) should work."""
        sign, degree = approximate_ascendant(
            date(2000, 6, 21),
            time(8, 0),
            -33.8688,
            151.2093,  # Sydney
        )
        assert isinstance(sign, str)
        assert 0 <= degree < 360

    def test_equator(self) -> None:
        """Birth near the equator should work."""
        sign, degree = approximate_ascendant(date(2000, 6, 21), time(6, 0), 0.0, 0.0)
        assert isinstance(sign, str)
        assert 0 <= degree < 360

    def test_rising_changes_with_location(self) -> None:
        """Different locations at same time should give different ascendants."""
        _, d1 = approximate_ascendant(
            date(2000, 6, 21),
            time(12, 0),
            40.7128,
            -74.0060,  # New York
        )
        _, d2 = approximate_ascendant(
            date(2000, 6, 21),
            time(12, 0),
            35.6762,
            139.6503,  # Tokyo
        )
        assert d1 != d2

    def test_high_latitude(self) -> None:
        """High latitude (e.g., Stockholm) should not crash."""
        sign, degree = approximate_ascendant(
            date(2000, 6, 21),
            time(12, 0),
            59.3293,
            18.0686,  # Stockholm
        )
        assert isinstance(sign, str)
        assert 0 <= degree < 360


# ═══════════════════════════════════════════════════════════════════════════
# House System Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHouseSystems:
    """Tests for house cusp calculations."""

    def test_equal_houses_30_degree_spacing(self) -> None:
        """Equal houses should have exactly 30 degree intervals."""
        cusps = calculate_house_cusps(15.0, HouseSystem.EQUAL)
        for i in range(12):
            expected = (15.0 + i * 30) % 360
            assert cusps[i] == pytest.approx(expected, abs=0.01)

    def test_whole_sign_houses(self) -> None:
        """Whole Sign houses start at the beginning of the Ascendant's sign."""
        # Ascendant at 15 Aries (15 degrees) -> first house starts at 0 degrees
        cusps = calculate_house_cusps(15.0, HouseSystem.WHOLE_SIGN)
        assert cusps[0] == 0.0  # Start of Aries
        assert cusps[1] == 30.0  # Start of Taurus
        assert cusps[6] == 180.0  # Start of Libra

    def test_twelve_cusps_returned(self) -> None:
        """All house systems should return exactly 12 cusps."""
        for system in HouseSystem:
            cusps = calculate_house_cusps(100.0, system)
            assert len(cusps) == 12, f"{system.value} returned {len(cusps)} cusps"

    def test_cusps_in_range(self) -> None:
        """All cusps should be in [0, 360)."""
        for system in HouseSystem:
            cusps = calculate_house_cusps(200.0, system)
            for i, cusp in enumerate(cusps):
                assert 0 <= cusp < 360, f"{system.value} cusp {i + 1} = {cusp}"

    def test_placidus_first_cusp_is_ascendant(self) -> None:
        """Placidus first cusp should be the Ascendant."""
        cusps = calculate_house_cusps(123.45, HouseSystem.PLACIDUS)
        assert cusps[0] == pytest.approx(123.45, abs=0.01)

    def test_koch_first_cusp_is_ascendant(self) -> None:
        """Koch first cusp should be the Ascendant."""
        cusps = calculate_house_cusps(50.0, HouseSystem.KOCH)
        assert cusps[0] == pytest.approx(50.0, abs=0.01)

    def test_equal_first_cusp_is_ascendant(self) -> None:
        """Equal first cusp should be the Ascendant."""
        cusps = calculate_house_cusps(200.0, HouseSystem.EQUAL)
        assert cusps[0] == pytest.approx(200.0, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# Transit Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanetaryPositions:
    """Tests for approximate planetary position calculations."""

    def test_all_planets_available(self) -> None:
        """All major planets should be in PLANET_ELEMENTS."""
        expected = [
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Jupiter",
            "Saturn",
            "Uranus",
            "Neptune",
            "Pluto",
        ]
        for planet in expected:
            assert planet in PLANET_ELEMENTS

    def test_planet_longitude_range(self) -> None:
        """All planet longitudes should be in [0, 360)."""
        for planet in PLANET_ELEMENTS:
            degree = approximate_planet_longitude(planet, date(2024, 6, 21))
            assert 0 <= degree < 360, f"{planet} = {degree}"

    def test_planet_longitude_deterministic(self) -> None:
        """Same inputs should give same outputs."""
        d = date(2020, 1, 1)
        a = approximate_planet_longitude("Mars", d)
        b = approximate_planet_longitude("Mars", d)
        assert a == b

    def test_unknown_planet_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown planet"):
            approximate_planet_longitude("Krypton", date(2024, 1, 1))

    def test_get_current_positions_returns_all(self) -> None:
        positions = get_current_positions(target_date=date(2024, 1, 1))
        assert len(positions) == 10
        for planet, degree in positions.items():
            assert 0 <= degree < 360

    def test_get_current_positions_subset(self) -> None:
        positions = get_current_positions(
            target_date=date(2024, 1, 1),
            planets=["Sun", "Moon"],
        )
        assert len(positions) == 2
        assert "Sun" in positions
        assert "Moon" in positions

    def test_sun_position_near_june_solstice(self) -> None:
        """Sun near June 21 should be around 90 degrees (Cancer)."""
        degree = approximate_planet_longitude("Sun", date(2024, 6, 21))
        assert 80 < degree < 100

    def test_outer_planets_move_slowly(self) -> None:
        """Outer planets should barely move in 30 days."""
        d1 = approximate_planet_longitude("Neptune", date(2024, 1, 1))
        d2 = approximate_planet_longitude("Neptune", date(2024, 1, 31))
        diff = abs(d2 - d1)
        assert diff < 1.0  # Neptune moves ~0.6 deg/month


class TestTransitAspects:
    """Tests for transit overlay calculations."""

    def test_transit_aspects_returns_list(self) -> None:
        natal = {"Sun": 0.0, "Moon": 120.0}
        aspects = calculate_transit_aspects(natal, transit_date=date(2024, 6, 21))
        assert isinstance(aspects, list)

    def test_transit_aspect_structure(self) -> None:
        natal = {"Sun": 0.0, "Moon": 120.0, "Mars": 90.0}
        aspects = calculate_transit_aspects(natal, transit_date=date(2024, 1, 15))
        for ta in aspects:
            assert isinstance(ta, TransitAspect)
            assert isinstance(ta.transit_planet, str)
            assert isinstance(ta.natal_planet, str)
            assert 0 <= ta.transit_degree < 360
            assert 0 <= ta.natal_degree < 360

    def test_transit_aspects_sorted_by_orb(self) -> None:
        natal = {"Sun": 0.0, "Moon": 90.0, "Venus": 180.0}
        aspects = calculate_transit_aspects(natal, transit_date=date(2024, 3, 20))
        orbs = [ta.aspect.orb for ta in aspects]
        assert orbs == sorted(orbs)

    def test_transit_overlay_full(self) -> None:
        natal = {"Sun": 100.0, "Moon": 220.0}
        overlay = get_transit_overlay(natal, transit_date=date(2024, 6, 21))
        assert "transit_positions" in overlay
        assert "transit_aspects" in overlay
        assert "summary" in overlay
        assert "transit_date" in overlay
        assert overlay["transit_date"] == date(2024, 6, 21)

    def test_transit_overlay_positions_complete(self) -> None:
        natal = {"Sun": 50.0}
        overlay = get_transit_overlay(natal, transit_date=date(2024, 1, 1))
        assert len(overlay["transit_positions"]) == 10

    def test_transit_deterministic(self) -> None:
        natal = {"Sun": 0.0, "Moon": 120.0}
        a = calculate_transit_aspects(natal, transit_date=date(2024, 6, 21))
        b = calculate_transit_aspects(natal, transit_date=date(2024, 6, 21))
        assert len(a) == len(b)
        for ta_a, ta_b in zip(a, b):
            assert ta_a.transit_planet == ta_b.transit_planet
            assert ta_a.natal_planet == ta_b.natal_planet
            assert ta_a.aspect.orb == ta_b.aspect.orb


class TestSummarizeTransits:
    """Tests for transit summary generation."""

    def test_summary_format(self) -> None:
        aspects = [
            TransitAspect(
                transit_planet="Jupiter",
                natal_planet="Sun",
                transit_degree=120.0,
                natal_degree=0.0,
                aspect=Aspect(
                    "T.Jupiter",
                    "N.Sun",
                    AspectType.TRINE,
                    120.0,
                    120.0,
                    0.5,
                ),
            ),
        ]
        summary = summarize_transits(aspects)
        assert "Jupiter -> Sun" in summary
        assert "trine" in summary["Jupiter -> Sun"]

    def test_empty_summary(self) -> None:
        summary = summarize_transits([])
        assert summary == {}


# ═══════════════════════════════════════════════════════════════════════════
# Edge Case Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case tests for the astrology engine."""

    def test_leap_year_date(self) -> None:
        """February 29 on a leap year should work."""
        sign = approximate_sun_sign(date(2000, 2, 29))
        assert sign == "Pisces"

    def test_new_years_day(self) -> None:
        """January 1 should be Capricorn."""
        assert approximate_sun_sign(date(2024, 1, 1)) == "Capricorn"

    def test_december_31(self) -> None:
        """December 31 should be Capricorn."""
        assert approximate_sun_sign(date(2024, 12, 31)) == "Capricorn"

    def test_very_old_date(self) -> None:
        """Calculation should work for dates far in the past."""
        sign = approximate_sun_sign(date(1900, 6, 15))
        assert sign == "Gemini"

    def test_future_date(self) -> None:
        """Calculation should work for future dates."""
        sign = approximate_sun_sign(date(2050, 9, 15))
        assert sign == "Virgo"

    def test_natal_chart_determinism_full(self) -> None:
        """Full chart with all options should be deterministic."""
        kwargs = {
            "birth_date": date(1985, 7, 4),
            "birth_time": time(3, 15),
            "birth_city": "New York",
            "include_aspects": True,
            "include_minor_aspects": True,
        }
        a = calculate_natal_chart(**kwargs)
        b = calculate_natal_chart(**kwargs)
        assert a["sun_sign"] == b["sun_sign"]
        assert a["rising_sign"] == b["rising_sign"]
        assert a["aspects"] == b["aspects"]

    def test_aspect_at_exactly_max_orb(self) -> None:
        """An aspect right at the maximum orb boundary should be included."""
        # Conjunction with 8 degree orb
        result = find_aspect(0.0, 8.0)
        assert result is not None
        assert result.aspect_type == AspectType.CONJUNCTION

    def test_aspect_just_beyond_max_orb(self) -> None:
        """An aspect just beyond the max orb should not be found."""
        tight_orbs = {a: 2.0 for a in AspectType}
        result = find_aspect(0.0, 122.1, orbs=tight_orbs)
        # 122.1 is 2.1 degrees from 120 (trine), beyond 2.0 orb
        assert result is None

    def test_midnight_birth_rising(self) -> None:
        """Midnight birth with location should compute rising."""
        result = calculate_natal_chart(
            date(2000, 1, 1),
            birth_time=time(0, 0, 0),
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert result["rising_sign"] is not None

    def test_southern_hemisphere_chart(self) -> None:
        """Full chart for southern hemisphere location."""
        result = calculate_natal_chart(
            date(1990, 12, 15),
            birth_time=time(22, 45),
            latitude=-33.8688,  # Sydney
            longitude=151.2093,
        )
        assert result["rising_sign"] is not None
        assert result["house_cusps"] is not None

    def test_all_house_systems_work(self) -> None:
        """All four house systems should produce valid cusps."""
        for system in HouseSystem:
            result = calculate_natal_chart(
                date(1990, 6, 15),
                birth_time=time(14, 0),
                latitude=40.0,
                longitude=-74.0,
                house_system=system,
            )
            assert result["house_cusps"] is not None
            assert len(result["house_cusps"]) == 12

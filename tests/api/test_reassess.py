"""Tests for reassess endpoint helpers and configuration.

Covers:
- ``_extract_identity_enrichment`` correctly reading nested JSON columns
- ``_VALID_REASSESS_SYSTEMS`` containing "intelligence"

Note: These are pure-function unit tests — no database, no HTTP client, no
async fixtures needed.  The import guard below patches ``get_settings``
before the API module chain loads so that a local ``.env`` with stale
production keys does not break test collection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ─── Import guard ──────────────────────────────────────────────────────
# ``alchymine.api.auth`` calls ``get_settings()`` at module-import time.
# Patch the cached singleton before importing anything from the API layer
# so that a local .env containing extra/stale keys does not cause a
# pydantic ValidationError during collection.

_fake_settings = MagicMock()
_fake_settings.jwt_secret_key = "test-secret-key-minimum-32-characters-long"  # noqa: S105
_fake_settings.jwt_algorithm = "HS256"
_fake_settings.access_token_expire_minutes = 30
_fake_settings.refresh_token_expire_days = 7

with patch("alchymine.config.get_settings", return_value=_fake_settings):
    from alchymine.api.routers.profile import (
        _VALID_REASSESS_SYSTEMS,
        _extract_identity_enrichment,
    )


# ─── Helpers ──────────────────────────────────────────────────────────


def _make_identity(**kwargs: object) -> MagicMock:
    """Return a mock IdentityProfile instance with the given column values."""
    identity = MagicMock()
    # Default all JSON columns to None so tests are explicit about what is set
    identity.numerology = None
    identity.astrology = None
    identity.archetype = None
    identity.personality = None
    for key, val in kwargs.items():
        setattr(identity, key, val)
    return identity


# ─── _extract_identity_enrichment ─────────────────────────────────────


def test_extract_archetype_primary_and_secondary() -> None:
    """Extracts archetype_primary and archetype_secondary from archetype JSON."""
    identity = _make_identity(
        archetype={"primary": "Sage", "secondary": "Explorer", "tertiary": "Ruler"}
    )
    result = _extract_identity_enrichment(identity)

    assert result["archetype"] == "Sage"
    assert result["archetype_primary"] == "Sage"
    assert result["archetype_secondary"] == "Explorer"


def test_extract_big_five_as_full_personality_dict() -> None:
    """Extracts big_five as the entire personality dict, not a sub-key."""
    personality = {"big_five": {"openness": 0.8, "conscientiousness": 0.7}, "mbti": "INFJ"}
    identity = _make_identity(personality=personality)
    result = _extract_identity_enrichment(identity)

    # big_five should be the full personality column, not just personality["big_five"]
    assert result["big_five"] == personality
    assert result["big_five"]["big_five"]["openness"] == 0.8


def test_extract_life_path_from_numerology() -> None:
    """Extracts life_path from the numerology JSON column."""
    identity = _make_identity(numerology={"life_path": 7, "expression": 3, "soul_urge": 5})
    result = _extract_identity_enrichment(identity)

    assert result["life_path"] == 7
    # expression and soul_urge are not extracted as top-level keys
    assert "expression" not in result


def test_extract_returns_empty_dict_when_all_columns_are_none() -> None:
    """Returns an empty dict when all identity columns are None."""
    identity = _make_identity(
        numerology=None,
        astrology=None,
        archetype=None,
        personality=None,
    )
    result = _extract_identity_enrichment(identity)

    assert result == {}


def test_extract_astrology_signs() -> None:
    """Extracts sun_sign, moon_sign, rising_sign from astrology JSON."""
    identity = _make_identity(
        astrology={
            "sun_sign": "Pisces",
            "moon_sign": "Scorpio",
            "rising_sign": "Libra",
            "chart_type": "tropical",
        }
    )
    result = _extract_identity_enrichment(identity)

    assert result["astrology"]["sun_sign"] == "Pisces"
    assert result["sun_sign"] == "Pisces"
    assert result["moon_sign"] == "Scorpio"
    assert result["rising_sign"] == "Libra"


def test_extract_partial_astrology_omits_missing_signs() -> None:
    """Missing sign keys are not inserted into the result."""
    identity = _make_identity(astrology={"sun_sign": "Aries"})
    result = _extract_identity_enrichment(identity)

    assert result["sun_sign"] == "Aries"
    assert "moon_sign" not in result
    assert "rising_sign" not in result


def test_extract_archetype_without_secondary() -> None:
    """archetype_secondary is omitted when the secondary key is absent."""
    identity = _make_identity(archetype={"primary": "Hero"})
    result = _extract_identity_enrichment(identity)

    assert result["archetype_primary"] == "Hero"
    assert "archetype_secondary" not in result


# ─── _VALID_REASSESS_SYSTEMS ───────────────────────────────────────────


def test_intelligence_in_valid_reassess_systems() -> None:
    """'intelligence' must be in _VALID_REASSESS_SYSTEMS."""
    assert "intelligence" in _VALID_REASSESS_SYSTEMS


@pytest.mark.parametrize("system", ["creative", "wealth", "perspective", "healing"])
def test_existing_systems_still_in_valid_reassess_systems(system: str) -> None:
    """All previously-valid systems remain in _VALID_REASSESS_SYSTEMS."""
    assert system in _VALID_REASSESS_SYSTEMS

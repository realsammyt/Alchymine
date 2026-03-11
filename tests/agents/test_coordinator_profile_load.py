"""Tests that HealingCoordinator pre-loads identity profile from DB."""
import sys
import types
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from alchymine.agents.orchestrator.coordinator import HealingCoordinator


def _make_fake_identity():
    fake_identity = MagicMock()
    fake_identity.numerology = {"life_path": 7}
    fake_identity.archetype = {"primary": "Alchemist", "secondary": "Sage"}
    fake_identity.personality = {
        "big_five": {"openness": 72, "conscientiousness": 65,
                     "extraversion": 45, "agreeableness": 78, "neuroticism": 38},
        "attachment_style": "secure",
    }
    fake_identity.astrology = {"sun_sign": "Aries"}
    fake_identity.strengths_map = None
    return fake_identity


def _fake_extract_identity_enrichment(identity):
    """Mirrors _extract_identity_enrichment for test isolation."""
    result = {}
    numerology = getattr(identity, "numerology", None) or {}
    if numerology:
        life_path = numerology.get("life_path")
        if life_path is not None:
            result["life_path"] = life_path
    archetype = getattr(identity, "archetype", None) or {}
    if archetype:
        result["archetype"] = archetype
        primary = archetype.get("primary")
        if primary is not None:
            result["archetype_primary"] = primary
        secondary = archetype.get("secondary")
        if secondary is not None:
            result["archetype_secondary"] = secondary
    personality = getattr(identity, "personality", None)
    if personality is not None:
        result["big_five"] = personality
    astrology = getattr(identity, "astrology", None) or {}
    if astrology:
        result["astrology"] = astrology
        for key in ("sun_sign", "moon_sign", "rising_sign"):
            val = astrology.get(key)
            if val is not None:
                result[key] = val
    return result


def _stub_profile_module():
    """Return a stub for alchymine.api.routers.profile with our test extractor."""
    stub = types.ModuleType("alchymine.api.routers.profile")
    stub._extract_identity_enrichment = _fake_extract_identity_enrichment
    return stub


class TestHealingProfilePreload:
    @pytest.mark.asyncio
    async def test_merges_identity_into_request_data(self):
        fake_identity = _make_fake_identity()
        coordinator = HealingCoordinator()
        request_data = {"intentions": ["health"]}

        stub = _stub_profile_module()
        with patch.object(coordinator, "_load_identity_profile",
                          new_callable=AsyncMock, return_value=fake_identity), \
             patch.dict(sys.modules, {"alchymine.api.routers.profile": stub}), \
             patch.object(coordinator, "_invoke_graph",
                          return_value=MagicMock(
                              system="healing", status="success", data={},
                              errors=[], quality_passed=True)):
            result = await coordinator.process("test-user", request_data)

        assert request_data.get("archetype_primary") == "Alchemist"
        assert request_data.get("big_five") is not None
        assert request_data.get("life_path") == 7

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_request_data(self):
        fake_identity = _make_fake_identity()
        coordinator = HealingCoordinator()
        request_data = {"intentions": ["health"], "archetype_primary": "Sage",
                        "big_five": {"openness": 90}}

        stub = _stub_profile_module()
        with patch.object(coordinator, "_load_identity_profile",
                          new_callable=AsyncMock, return_value=fake_identity), \
             patch.dict(sys.modules, {"alchymine.api.routers.profile": stub}), \
             patch.object(coordinator, "_invoke_graph",
                          return_value=MagicMock(
                              system="healing", status="success", data={},
                              errors=[], quality_passed=True)):
            await coordinator.process("test-user", request_data)

        # Caller-supplied values must not be overwritten
        assert request_data["archetype_primary"] == "Sage"
        assert request_data["big_five"] == {"openness": 90}

    @pytest.mark.asyncio
    async def test_graceful_when_no_identity_profile(self):
        coordinator = HealingCoordinator()
        request_data = {"intentions": ["health"]}

        with patch.object(coordinator, "_load_identity_profile",
                          new_callable=AsyncMock, return_value=None), \
             patch.object(coordinator, "_invoke_graph",
                          return_value=MagicMock(
                              system="healing", status="success", data={},
                              errors=[], quality_passed=True)):
            result = await coordinator.process("test-user", request_data)

        assert result.status in ("success", "degraded")

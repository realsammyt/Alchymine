"""Unit tests for the cross-system bridges registry."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from alchymine.engine.bridges import (
    BRIDGE_REGISTRY,
    Bridge,
    BridgeNotFoundError,
    get_bridge,
    list_bridges,
    list_bridges_from,
    list_bridges_to,
)
from alchymine.engine.bridges.registry import VALID_SYSTEMS

EXPECTED_IDS = ("XS-01", "XS-02", "XS-03", "XS-04", "XS-05", "XS-06", "XS-07")


# ─────────────────────────────────────────────────────────────────────────
# Registry composition
# ─────────────────────────────────────────────────────────────────────────


class TestRegistryComposition:
    def test_registry_has_all_seven_bridges(self) -> None:
        assert len(BRIDGE_REGISTRY) == 7
        assert set(BRIDGE_REGISTRY.keys()) == set(EXPECTED_IDS)

    def test_bridge_ids_are_unique(self) -> None:
        ids = [b.id for b in BRIDGE_REGISTRY.values()]
        assert len(ids) == len(set(ids))

    def test_dict_key_matches_bridge_id_field(self) -> None:
        for key, bridge in BRIDGE_REGISTRY.items():
            assert key == bridge.id

    def test_source_systems_are_valid(self) -> None:
        for bridge in BRIDGE_REGISTRY.values():
            assert bridge.source_system in VALID_SYSTEMS, (
                f"{bridge.id} has invalid source_system={bridge.source_system!r}"
            )

    def test_target_systems_are_valid(self) -> None:
        for bridge in BRIDGE_REGISTRY.values():
            assert bridge.target_system in VALID_SYSTEMS, (
                f"{bridge.id} has invalid target_system={bridge.target_system!r}"
            )

    def test_source_and_target_differ(self) -> None:
        for bridge in BRIDGE_REGISTRY.values():
            assert bridge.source_system != bridge.target_system, (
                f"{bridge.id} has source==target ({bridge.source_system})"
            )

    def test_every_bridge_has_nonempty_metadata(self) -> None:
        for bridge in BRIDGE_REGISTRY.values():
            assert bridge.name.strip(), f"{bridge.id} has empty name"
            assert bridge.description.strip(), f"{bridge.id} has empty description"
            assert len(bridge.insight_keys) >= 1, f"{bridge.id} has no insight_keys"

    def test_insight_keys_is_a_tuple(self) -> None:
        # Frozen dataclass + tuple makes the entry effectively immutable.
        for bridge in BRIDGE_REGISTRY.values():
            assert isinstance(bridge.insight_keys, tuple)


# ─────────────────────────────────────────────────────────────────────────
# get_bridge
# ─────────────────────────────────────────────────────────────────────────


class TestGetBridge:
    def test_get_bridge_returns_known_id(self) -> None:
        bridge = get_bridge("XS-01")
        assert bridge.id == "XS-01"
        assert bridge.source_system == "healing"
        assert bridge.target_system == "perspective"

    def test_get_bridge_raises_on_unknown_id(self) -> None:
        with pytest.raises(BridgeNotFoundError):
            get_bridge("XS-99")

    def test_get_bridge_raises_on_empty_string(self) -> None:
        with pytest.raises(BridgeNotFoundError):
            get_bridge("")


# ─────────────────────────────────────────────────────────────────────────
# list_bridges* helpers
# ─────────────────────────────────────────────────────────────────────────


class TestListBridges:
    def test_list_bridges_returns_seven(self) -> None:
        bridges = list_bridges()
        assert len(bridges) == 7

    def test_list_bridges_returns_stable_order(self) -> None:
        bridges = list_bridges()
        ids = tuple(b.id for b in bridges)
        assert ids == EXPECTED_IDS

    def test_list_bridges_returns_tuple(self) -> None:
        bridges = list_bridges()
        assert isinstance(bridges, tuple)

    def test_list_bridges_from_filters_correctly(self) -> None:
        healing_sources = list_bridges_from("healing")
        # XS-01 (healing→perspective) and XS-06 (healing→creative)
        assert {b.id for b in healing_sources} == {"XS-01", "XS-06"}
        for b in healing_sources:
            assert b.source_system == "healing"

    def test_list_bridges_from_unknown_returns_empty(self) -> None:
        assert list_bridges_from("not-a-system") == ()

    def test_list_bridges_to_filters_correctly(self) -> None:
        healing_targets = list_bridges_to("healing")
        # XS-02 (intelligence→healing), XS-03 (wealth→healing),
        # XS-04 (creative→healing)
        assert {b.id for b in healing_targets} == {"XS-02", "XS-03", "XS-04"}
        for b in healing_targets:
            assert b.target_system == "healing"

    def test_list_bridges_to_unknown_returns_empty(self) -> None:
        assert list_bridges_to("not-a-system") == ()

    def test_list_bridges_from_preserves_id_order(self) -> None:
        bridges = list_bridges_from("intelligence")
        ids = [b.id for b in bridges]
        assert ids == sorted(ids)


# ─────────────────────────────────────────────────────────────────────────
# Frozenness
# ─────────────────────────────────────────────────────────────────────────


class TestBridgeIsFrozen:
    def test_bridge_attributes_cannot_be_mutated(self) -> None:
        bridge = get_bridge("XS-01")
        with pytest.raises(FrozenInstanceError):
            bridge.name = "Hacked"  # type: ignore[misc]

    def test_cannot_add_new_attribute(self) -> None:
        bridge = get_bridge("XS-01")
        with pytest.raises(FrozenInstanceError):
            bridge.foo = "bar"  # type: ignore[attr-defined]

    def test_bridge_dataclass_is_frozen_class_level(self) -> None:
        # Sanity: instantiating a fresh Bridge and trying to mutate it
        # should also raise.
        b = Bridge(
            id="XS-XX",
            name="Test",
            source_system="healing",
            target_system="creative",
            description="d",
            insight_keys=("k",),
        )
        with pytest.raises(FrozenInstanceError):
            b.id = "XS-YY"  # type: ignore[misc]

"""Cross-system bridges API endpoints — public reference data, no auth required.

Exposes the seven cross-system bridges (XS-01..XS-07) declared in
:mod:`alchymine.engine.bridges.registry`.  Bridges are static reference
data, so the registry is injected via a FastAPI dependency to make the
endpoints trivially testable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from alchymine.engine.bridges import (
    BRIDGE_REGISTRY,
    Bridge,
    BridgeId,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────
# Response model
# ─────────────────────────────────────────────────────────────────────────


class BridgeResponse(BaseModel):
    """Wire-format representation of a :class:`Bridge`.

    FastAPI cannot serialize frozen dataclasses without help, so we mirror
    the dataclass fields here and convert via :meth:`from_bridge`.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable bridge identifier, e.g. 'XS-01'")
    name: str = Field(..., description="Short human-readable title")
    source_system: str = Field(..., description="Producing pillar")
    target_system: str = Field(..., description="Consuming pillar")
    description: str = Field(..., description="What insight flows from source to target")
    insight_keys: list[str] = Field(
        ..., description="Source-system field names surfaced in the target"
    )

    @classmethod
    def from_bridge(cls, bridge: Bridge) -> BridgeResponse:
        return cls(
            id=bridge.id,
            name=bridge.name,
            source_system=bridge.source_system,
            target_system=bridge.target_system,
            description=bridge.description,
            insight_keys=list(bridge.insight_keys),
        )


# ─────────────────────────────────────────────────────────────────────────
# Dependency
# ─────────────────────────────────────────────────────────────────────────


def get_bridge_registry() -> dict[BridgeId, Bridge]:
    """FastAPI dependency that returns the in-memory bridge registry.

    Kept as a thin wrapper so tests can override it via
    ``app.dependency_overrides`` if needed.
    """
    return BRIDGE_REGISTRY


# ─────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────


@router.get("/bridges")
async def list_bridges_endpoint(
    source: str | None = Query(None, description="Filter by source_system"),
    target: str | None = Query(None, description="Filter by target_system"),
    registry: dict[BridgeId, Bridge] = Depends(get_bridge_registry),
) -> list[BridgeResponse]:
    """List all cross-system bridges, optionally filtered by source/target.

    Filters are independent and may be combined.  An unknown system value
    simply yields an empty list (not a 400).  Results are returned in
    stable id order (XS-01 first).
    """
    bridges: list[Bridge] = [registry[bid] for bid in sorted(registry.keys())]
    if source is not None:
        bridges = [b for b in bridges if b.source_system == source]
    if target is not None:
        bridges = [b for b in bridges if b.target_system == target]
    return [BridgeResponse.from_bridge(b) for b in bridges]


@router.get("/bridges/{bridge_id}")
async def get_bridge_endpoint(
    bridge_id: str,
    registry: dict[BridgeId, Bridge] = Depends(get_bridge_registry),
) -> BridgeResponse:
    """Return a single bridge by id, or 404 if not found."""
    bridge = registry.get(bridge_id)  # type: ignore[call-overload]
    if bridge is None:
        raise HTTPException(status_code=404, detail=f"Bridge not found: {bridge_id}")
    return BridgeResponse.from_bridge(bridge)

"""Cross-system bridges sub-package.

Defines the 7 cross-system insight bridges (XS-01..XS-07) that describe
how data and insights flow between Alchymine's five pillars
(intelligence, healing, wealth, creative, perspective).

Bridges are pure in-code reference data — frozen dataclasses kept in a
module-level registry. There is no DB persistence and no I/O involved.
"""

from .registry import (
    BRIDGE_REGISTRY,
    Bridge,
    BridgeId,
    BridgeNotFoundError,
    get_bridge,
    list_bridges,
    list_bridges_from,
    list_bridges_to,
)

__all__ = [
    "BRIDGE_REGISTRY",
    "Bridge",
    "BridgeId",
    "BridgeNotFoundError",
    "get_bridge",
    "list_bridges",
    "list_bridges_from",
    "list_bridges_to",
]

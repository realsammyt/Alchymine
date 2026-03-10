"""Canonical intention-to-system mapping.

Single source of truth for which user intentions (career, love, purpose,
money, health, family, business, legacy) map to which Alchymine systems
(intelligence, healing, wealth, creative, perspective).

Three consumers use this data in different ways:

- **Orchestrator routing** (``intent.py``): uses
  :data:`INTENTION_PRIMARY_SYSTEMS` to decide which coordinators to
  invoke for a given set of user intentions.
- **Spiral adaptive routing** (``router.py``): uses
  :data:`INTENTION_WEIGHTS` to score and rank all five systems for
  personalised recommendations.
- **Synthesis filtering** (``synthesis.py``): uses
  :data:`INTENTION_SYSTEM_RELEVANCE` to prioritise coordinator results
  by relevance when generating guided-session output.

All three data structures live here so that adding a new intention or
adjusting system affinities only requires changes in one file.
"""

from __future__ import annotations

# ── Constants ──────────────────────────────────────────────────────────

SYSTEMS = ("intelligence", "healing", "wealth", "creative", "perspective")

# ── Intention weights (Spiral router) ──────────────────────────────────
#
# Each intention maps to a dict of {system: weight}.  Weights express
# relative affinity (higher = more relevant).  Every system appears in
# every intention so the router can rank all five.

INTENTION_WEIGHTS: dict[str, dict[str, float]] = {
    "career": {
        "intelligence": 30,
        "perspective": 30,
        "wealth": 20,
        "creative": 15,
        "healing": 5,
    },
    "love": {
        "healing": 35,
        "intelligence": 25,
        "perspective": 20,
        "creative": 15,
        "wealth": 5,
    },
    "purpose": {
        "perspective": 35,
        "intelligence": 25,
        "creative": 20,
        "healing": 15,
        "wealth": 5,
    },
    "money": {
        "wealth": 40,
        "perspective": 20,
        "intelligence": 20,
        "creative": 15,
        "healing": 5,
    },
    "health": {
        "healing": 40,
        "intelligence": 20,
        "perspective": 15,
        "creative": 15,
        "wealth": 10,
    },
    "family": {
        "wealth": 25,
        "healing": 25,
        "perspective": 20,
        "intelligence": 20,
        "creative": 10,
    },
    "business": {
        "wealth": 30,
        "creative": 25,
        "perspective": 20,
        "intelligence": 15,
        "healing": 10,
    },
    "legacy": {
        "wealth": 30,
        "perspective": 25,
        "intelligence": 20,
        "creative": 15,
        "healing": 10,
    },
    "creative": {
        "creative": 40,
        "intelligence": 20,
        "perspective": 20,
        "healing": 10,
        "wealth": 10,
    },
}

# ── Primary systems per intention (orchestrator routing) ──────────────
#
# The curated subset of systems that should be activated when a user
# selects a given intention in the report flow.  Used by
# ``intent.intentions_to_systems()`` to decide which coordinators run.
#
# Order matters: the first system listed is the most relevant.

INTENTION_PRIMARY_SYSTEMS: dict[str, list[str]] = {
    "career": ["intelligence", "perspective"],
    "love": ["intelligence", "healing"],
    "purpose": ["intelligence", "creative", "perspective"],
    "money": ["wealth", "intelligence"],
    "health": ["healing", "intelligence"],
    "family": ["healing", "perspective"],
    "business": ["wealth", "creative"],
    "legacy": ["wealth", "perspective", "creative"],
    "creative": ["creative", "intelligence"],
}

# ── System relevance for synthesis filtering ──────────────────────────
#
# Maps keywords (including synonyms for the 8 canonical intentions)
# to ordered lists of the top-3 most relevant systems.  Synthesis
# uses substring matching (``keyword in intent_text``) to look up
# priorities, so keywords like "healing" and "health" have separate
# entries.
#
# Order matters: systems earlier in the list are ranked higher during
# guided-session synthesis.

INTENTION_SYSTEM_RELEVANCE: dict[str, list[str]] = {
    "healing": ["healing", "perspective", "intelligence"],
    "health": ["healing", "perspective", "intelligence"],
    "wellness": ["healing", "perspective", "intelligence"],
    "money": ["wealth", "creative", "intelligence"],
    "wealth": ["wealth", "creative", "intelligence"],
    "financial": ["wealth", "creative", "intelligence"],
    "career": ["wealth", "creative", "perspective"],
    "creativity": ["creative", "intelligence", "perspective"],
    "art": ["creative", "intelligence", "perspective"],
    "writing": ["creative", "intelligence", "perspective"],
    "decision": ["perspective", "intelligence", "wealth"],
    "growth": ["perspective", "healing", "intelligence"],
    "self-discovery": ["intelligence", "perspective", "healing"],
    "purpose": ["intelligence", "creative", "perspective"],
    "relationships": ["perspective", "healing", "intelligence"],
    "spirituality": ["intelligence", "healing", "perspective"],
}

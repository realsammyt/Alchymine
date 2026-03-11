# Profile-First Healing Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the healing narrative pipeline so it reads intelligence data from the persisted DB profile instead of fragile runtime enrichment, and give users the ability to complete or update specific assessment sections without repeating the entire 67-question assessment.

**Architecture:** The HealingCoordinator will pre-load the user's IdentityProfile from the database before invoking the healing graph, making it independent of runtime orchestrator enrichment order. The assessment page will accept a `sections` query parameter to show only specific question categories. The report page will show actionable guidance for missing sections instead of silently hiding them.

**Tech Stack:** Python 3.11+ (FastAPI, SQLAlchemy, LangGraph), Next.js 15 (App Router, React 18, TypeScript), PostgreSQL

---

## File Map

### Backend — Modified

| File                                           | Responsibility                                                                     |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| `alchymine/agents/orchestrator/coordinator.py` | HealingCoordinator pre-loads identity profile from DB                              |
| `alchymine/agents/orchestrator/graphs.py`      | Remove fallback defaults, add `missing_prerequisites` reporting                    |
| `alchymine/api/routers/profile.py`             | Fix reassess enrichment, add completeness endpoint, add "intelligence" to reassess |
| `alchymine/api/routers/reports.py`             | Return `missing_sections` in report response                                       |

### Backend — New

| File                                    | Responsibility                                     |
| --------------------------------------- | -------------------------------------------------- |
| `alchymine/api/schemas/completeness.py` | Pydantic models for completeness endpoint response |

### Frontend — Modified

| File                                                  | Responsibility                                                |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| `alchymine/web/src/app/discover/assessment/page.tsx`  | Accept `?sections=` query param, filter questions             |
| `alchymine/web/src/app/discover/report/[id]/page.tsx` | Show guidance for missing sections                            |
| `alchymine/web/src/app/profile/page.tsx`              | Show section completeness status + retake buttons             |
| `alchymine/web/src/lib/api.ts`                        | Add `getCompleteness()` and `reassessSection()` API functions |

### Tests — New/Modified

| File                                            | Responsibility                                 |
| ----------------------------------------------- | ---------------------------------------------- |
| `tests/agents/test_graphs.py`                   | Update healing tests for missing_prerequisites |
| `tests/agents/test_coordinator_profile_load.py` | HealingCoordinator DB integration tests        |
| `tests/api/test_profile_completeness.py`        | Completeness endpoint tests                    |
| `tests/api/test_reassess.py`                    | Fix/add reassess endpoint tests                |

---

## Chunk 1: Backend — Profile-First Healing Pipeline

### Task 1: Fix reassess endpoint identity enrichment

The reassess endpoint at `alchymine/api/routers/profile.py:370-375` has a bug: it reads `getattr(user.identity, "life_path", None)` and `getattr(user.identity, "big_five", None)`, but `IdentityProfile` model stores these inside JSON columns (`numerology`, `personality`), not as top-level attributes. The enrichment silently returns None for all three keys.

**Files:**

- Modify: `alchymine/api/routers/profile.py:370-375`
- Test: `tests/api/test_reassess.py`

- [ ] **Step 1: Write failing test for reassess enrichment**

```python
# tests/api/test_reassess.py
"""Tests for the reassess endpoint's identity data enrichment."""

import pytest

from alchymine.api.routers.profile import _extract_identity_enrichment


class TestIdentityEnrichment:
    """_extract_identity_enrichment extracts nested values from IdentityProfile."""

    def test_extracts_archetype_primary(self) -> None:
        """Extracts primary archetype string from archetype JSON column."""

        class FakeIdentity:
            numerology = {"life_path": 7}
            astrology = {"sun_sign": "Aries"}
            archetype = {"primary": "Alchemist", "secondary": "Sage"}
            personality = {
                "big_five": {
                    "openness": 72,
                    "conscientiousness": 65,
                    "extraversion": 45,
                    "agreeableness": 78,
                    "neuroticism": 38,
                },
                "attachment_style": "secure",
            }
            strengths_map = None

        result = _extract_identity_enrichment(FakeIdentity())
        assert result["archetype"] == "Alchemist"
        assert result["archetype_secondary"] == "Sage"

    def test_extracts_big_five_as_personality_dict(self) -> None:
        """Extracts full personality dict for big_five key."""

        class FakeIdentity:
            numerology = None
            astrology = None
            archetype = None
            personality = {
                "big_five": {"openness": 72, "conscientiousness": 65,
                             "extraversion": 45, "agreeableness": 78,
                             "neuroticism": 38},
                "attachment_style": "secure",
            }
            strengths_map = None

        result = _extract_identity_enrichment(FakeIdentity())
        assert result["big_five"]["big_five"]["openness"] == 72
        assert result["big_five"]["attachment_style"] == "secure"

    def test_extracts_life_path_from_numerology(self) -> None:
        """Extracts life_path from nested numerology JSON."""

        class FakeIdentity:
            numerology = {"life_path": 7, "expression": 3}
            astrology = None
            archetype = None
            personality = None
            strengths_map = None

        result = _extract_identity_enrichment(FakeIdentity())
        assert result["life_path"] == 7

    def test_returns_empty_when_identity_is_none_fields(self) -> None:
        """Returns empty dict when all identity fields are None."""

        class FakeIdentity:
            numerology = None
            astrology = None
            archetype = None
            personality = None
            strengths_map = None

        result = _extract_identity_enrichment(FakeIdentity())
        assert result == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reassess.py::TestIdentityEnrichment -v`
Expected: FAIL — `_extract_identity_enrichment` does not exist yet

- [ ] **Step 3: Implement `_extract_identity_enrichment` helper**

In `alchymine/api/routers/profile.py`, add a helper function and replace the broken enrichment:

```python
def _extract_identity_enrichment(identity) -> dict[str, Any]:
    """Extract enrichment data from an IdentityProfile ORM object.

    Maps the JSON columns (numerology, archetype, personality) to the
    flat keys that coordinator graphs expect in request_data.
    """
    enrichment: dict[str, Any] = {}

    # life_path is nested inside numerology JSON
    numerology = getattr(identity, "numerology", None)
    if isinstance(numerology, dict) and numerology.get("life_path"):
        enrichment["life_path"] = numerology["life_path"]

    # archetype JSON has {primary, secondary, ...}
    archetype = getattr(identity, "archetype", None)
    if isinstance(archetype, dict):
        if archetype.get("primary"):
            enrichment["archetype"] = archetype["primary"]
            enrichment["archetype_primary"] = archetype["primary"]
        if archetype.get("secondary"):
            enrichment["archetype_secondary"] = archetype["secondary"]

    # personality JSON has {big_five: {...}, attachment_style, ...}
    personality = getattr(identity, "personality", None)
    if isinstance(personality, dict):
        enrichment["big_five"] = personality

    # astrology pass-through
    astrology = getattr(identity, "astrology", None)
    if isinstance(astrology, dict) and astrology:
        enrichment["astrology"] = astrology
        for key in ("sun_sign", "moon_sign", "rising_sign"):
            if astrology.get(key):
                enrichment[key] = astrology[key]

    return enrichment
```

Replace lines 370-375 in `reassess_layer()`:

```python
    # Enrich with identity data if available
    if user.identity is not None:
        enrichment = _extract_identity_enrichment(user.identity)
        for key, val in enrichment.items():
            if key not in request_data:
                request_data[key] = val
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reassess.py::TestIdentityEnrichment -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/api/routers/profile.py tests/api/test_reassess.py
git commit -m "fix: reassess endpoint identity enrichment reads from JSON columns"
```

---

### Task 2: Add "intelligence" to reassess systems

Currently `_VALID_REASSESS_SYSTEMS = {"creative", "wealth", "perspective", "healing"}` — Intelligence is excluded. Users need to reassess Intelligence (personality, archetype) to update their Big Five scores, which downstream systems depend on.

**Files:**

- Modify: `alchymine/api/routers/profile.py:305`
- Modify: `alchymine/api/routers/profile.py:310-325` (add intelligence graph builder)
- Modify: `alchymine/api/routers/profile.py:397-401` (fix layer name mapping for intelligence)
- Test: `tests/api/test_reassess.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/api/test_reassess.py
class TestReassessValidSystems:
    def test_intelligence_is_valid_reassess_system(self) -> None:
        from alchymine.api.routers.profile import _VALID_REASSESS_SYSTEMS
        assert "intelligence" in _VALID_REASSESS_SYSTEMS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reassess.py::TestReassessValidSystems -v`
Expected: FAIL — "intelligence" not in set

- [ ] **Step 3: Add intelligence to valid systems and graph builders**

In `alchymine/api/routers/profile.py`:

1. Line 305: Add "intelligence" to the set:

```python
_VALID_REASSESS_SYSTEMS = {"intelligence", "creative", "wealth", "perspective", "healing"}
```

2. In `_get_graph_builders()`, add intelligence:

```python
from alchymine.agents.orchestrator.graphs import (
    build_creative_graph,
    build_healing_graph,
    build_intelligence_graph,
    build_perspective_graph,
    build_wealth_graph,
)

_GRAPH_BUILDERS.update({
    "intelligence": build_intelligence_graph,
    "creative": build_creative_graph,
    "healing": build_healing_graph,
    "wealth": build_wealth_graph,
    "perspective": build_perspective_graph,
})
```

3. In `reassess_layer()`, add layer name mapping for intelligence → identity (since `update_layer` uses "identity" not "intelligence"):

```python
    # Map system name to DB layer name
    _layer_map = {"intelligence": "identity"}
    layer_name = _layer_map.get(system, system)

    # Update the profile layer in DB
    try:
        await repository.update_layer(session, user_id, layer_name, results)
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_reassess.py::TestReassessValidSystems -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/api/routers/profile.py tests/api/test_reassess.py
git commit -m "feat: add intelligence to reassess systems"
```

---

### Task 3: HealingCoordinator pre-loads identity profile from DB

This is the core architectural change. Instead of relying on runtime enrichment from the orchestrator, HealingCoordinator fetches the user's IdentityProfile from the DB before invoking the healing graph.

**Files:**

- Modify: `alchymine/agents/orchestrator/coordinator.py:249-266`
- Test: `tests/agents/test_coordinator_profile_load.py`

- [ ] **Step 1: Write failing test**

```python
# tests/agents/test_coordinator_profile_load.py
"""Tests that HealingCoordinator pre-loads identity profile from DB."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from alchymine.agents.orchestrator.coordinator import HealingCoordinator


class TestHealingProfilePreload:
    """HealingCoordinator merges identity data into request_data before graph."""

    @pytest.mark.asyncio
    async def test_merges_identity_into_request_data(self) -> None:
        """Identity profile personality/archetype merged into request_data."""
        fake_identity = MagicMock()
        fake_identity.numerology = {"life_path": 7}
        fake_identity.archetype = {"primary": "Alchemist", "secondary": "Sage"}
        fake_identity.personality = {
            "big_five": {
                "openness": 72, "conscientiousness": 65,
                "extraversion": 45, "agreeableness": 78,
                "neuroticism": 38,
            },
            "attachment_style": "secure",
        }
        fake_identity.astrology = {"sun_sign": "Aries"}
        fake_identity.strengths_map = None

        fake_user = MagicMock()
        fake_user.identity = fake_identity

        coordinator = HealingCoordinator()
        request_data = {"intentions": ["health"]}

        with patch.object(
            coordinator, "_load_identity_profile", new_callable=AsyncMock,
            return_value=fake_user.identity,
        ):
            result = await coordinator.process("test-user", request_data)

        # After process, request_data should have been enriched
        assert request_data.get("archetype") == "Alchemist"
        assert request_data.get("big_five") is not None

    @pytest.mark.asyncio
    async def test_does_not_overwrite_existing_request_data(self) -> None:
        """If request_data already has archetype/big_five, don't overwrite."""
        coordinator = HealingCoordinator()
        request_data = {
            "intentions": ["health"],
            "archetype": "Sage",
            "big_five": {"big_five": {"openness": 90}},
        }

        with patch.object(
            coordinator, "_load_identity_profile", new_callable=AsyncMock,
            return_value=None,
        ):
            result = await coordinator.process("test-user", request_data)

        assert request_data["archetype"] == "Sage"

    @pytest.mark.asyncio
    async def test_graceful_when_no_identity_profile(self) -> None:
        """No crash when user has no identity profile in DB."""
        coordinator = HealingCoordinator()
        request_data = {"intentions": ["health"]}

        with patch.object(
            coordinator, "_load_identity_profile", new_callable=AsyncMock,
            return_value=None,
        ):
            result = await coordinator.process("test-user", request_data)

        assert result.status in ("success", "degraded")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Python/Python311/python.exe -m pytest tests/agents/test_coordinator_profile_load.py -v`
Expected: FAIL — `_load_identity_profile` does not exist

- [ ] **Step 3: Implement profile pre-loading in HealingCoordinator**

In `alchymine/agents/orchestrator/coordinator.py`, modify HealingCoordinator:

```python
class HealingCoordinator(_GraphCoordinatorMixin, BaseCoordinator):
    """Coordinator for the Ethical Healing system."""

    system_name = "healing"

    def __init__(self) -> None:
        self._graph = build_healing_graph(include_quality_gate=False)

    async def _load_identity_profile(self, user_id: str):
        """Load the user's IdentityProfile from the database.

        Returns the identity ORM object or None if not found.
        """
        try:
            from alchymine.db.base import get_async_engine, get_async_session_factory
            from alchymine.db import repository

            engine = get_async_engine()
            factory = get_async_session_factory(engine)
            async with factory() as session:
                user = await repository.get_profile(session, user_id)
                return user.identity if user else None
        except Exception as exc:
            logger.warning(
                "Healing: failed to load identity profile for %s: %s",
                user_id, exc,
            )
            return None

    async def _execute(
        self,
        user_id: str,
        request_data: dict,
    ) -> CoordinatorResult:
        # Pre-load identity profile from DB so healing doesn't depend
        # on runtime enrichment order from the orchestrator.
        identity = await self._load_identity_profile(user_id)
        if identity is not None:
            from alchymine.api.routers.profile import _extract_identity_enrichment

            enrichment = _extract_identity_enrichment(identity)
            for key, val in enrichment.items():
                if key not in request_data:
                    request_data[key] = val

        return self._invoke_graph(user_id, request_data)
```

Also add `import logging` and `logger = logging.getLogger(__name__)` at the top of the file if not already present.

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Python/Python311/python.exe -m pytest tests/agents/test_coordinator_profile_load.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/agents/orchestrator/coordinator.py tests/agents/test_coordinator_profile_load.py
git commit -m "feat: HealingCoordinator pre-loads identity profile from DB"
```

---

### Task 4: Remove fallback defaults, add missing_prerequisites reporting

Replace the silent fallback defaults in `_healing_personality_context` with structured `missing_prerequisites` data that the frontend can act on. Keep `crisis_flag` default (it's a safety feature).

**Files:**

- Modify: `alchymine/agents/orchestrator/graphs.py:567-628`
- Modify: `tests/agents/test_graphs.py` (update existing healing tests)

- [ ] **Step 1: Write failing test for missing_prerequisites**

```python
# Add to tests/agents/test_graphs.py, in TestHealingGraphTransitions

def test_missing_prerequisites_reported_when_no_intelligence_data(self) -> None:
    """Healing graph reports missing_prerequisites when identity data absent."""
    state = _make_initial_state(request_data={"intentions": ["health"]})

    graph = build_healing_graph(include_quality_gate=False)
    result = graph.invoke(state)

    prereqs = result["results"].get("missing_prerequisites", [])
    assert "big_five" in prereqs or "archetype" in prereqs
    assert result["status"] == "degraded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Python/Python311/python.exe -m pytest tests/agents/test_graphs.py -k "test_missing_prerequisites" -v`
Expected: FAIL — no `missing_prerequisites` key in results

- [ ] **Step 3: Implement missing_prerequisites in \_healing_personality_context**

Replace the fallback logic in `_healing_personality_context` (graphs.py):

```python
def _healing_personality_context(state: CoordinatorState) -> CoordinatorState:
    """Extract Big Five and attachment style from request_data for narrative template.

    Reports missing_prerequisites when Intelligence data is unavailable
    so the frontend can guide the user to complete their assessment.
    """
    results = dict(state.get("results", {}))
    request_data = state.get("request_data", {})
    missing: list[str] = []

    big_five_raw = request_data.get("big_five", {})
    has_personality = False

    if big_five_raw and isinstance(big_five_raw, dict):
        scores = big_five_raw.get("big_five", big_five_raw)
        if isinstance(scores, dict) and "openness" in scores:
            has_personality = True
            for trait in ("openness", "neuroticism"):
                results[trait] = scores[trait]

            attachment = big_five_raw.get("attachment_style") or request_data.get(
                "attachment_style"
            )
            if attachment:
                results["attachment_style"] = attachment

    if not has_personality:
        missing.append("big_five")

    if not request_data.get("archetype"):
        missing.append("archetype")

    # Ensure crisis_flag always has a value (safety default — not a fallback)
    results.setdefault("crisis_flag", False)

    if missing:
        results["missing_prerequisites"] = missing

    return {**state, "results": results}
```

- [ ] **Step 4: Update quality gate test**

The test `test_healing_quality_gate_passes_with_disclaimers` (line 801) runs with empty request_data and currently expects `quality_passed=True`. With fallbacks removed, modalities won't have difficulty_level unless real data is present. Update the test to provide real intelligence data:

```python
def test_healing_quality_gate_passes_with_disclaimers(self) -> None:
    """Healing graph with quality gate passes when intelligence data present."""
    state = _make_initial_state(request_data={
        "archetype": "Alchemist",
        "big_five": {
            "big_five": {
                "openness": 72, "conscientiousness": 65,
                "extraversion": 45, "agreeableness": 78,
                "neuroticism": 38,
            },
            "attachment_style": "secure",
        },
        "intentions": ["health"],
    })

    graph = build_healing_graph(include_quality_gate=True)
    result = graph.invoke(state)

    assert result["quality_passed"] is True
```

Add a complementary test for the degraded path:

```python
def test_healing_quality_gate_degraded_without_intelligence(self) -> None:
    """Healing graph degrades gracefully without intelligence data."""
    state = _make_initial_state(request_data={})

    graph = build_healing_graph(include_quality_gate=True)
    result = graph.invoke(state)

    assert result["status"] == "degraded"
    prereqs = result["results"].get("missing_prerequisites", [])
    assert len(prereqs) > 0
```

- [ ] **Step 5: Run all healing tests**

Run: `D:/Python/Python311/python.exe -m pytest tests/agents/test_graphs.py -k "healing" -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add alchymine/agents/orchestrator/graphs.py tests/agents/test_graphs.py
git commit -m "feat: replace healing fallbacks with missing_prerequisites reporting"
```

---

## Chunk 2: Backend — Profile Completeness & Section Assessment

### Task 5: Profile completeness endpoint

New endpoint that returns which assessment sections are complete and which need data. The frontend will use this to show status and guide users.

**Files:**

- Create: `alchymine/api/schemas/completeness.py`
- Modify: `alchymine/api/routers/profile.py`
- Test: `tests/api/test_profile_completeness.py`

- [ ] **Step 1: Write failing test**

```python
# tests/api/test_profile_completeness.py
"""Tests for the profile completeness endpoint logic."""

import pytest
from alchymine.api.schemas.completeness import compute_completeness


class TestComputeCompleteness:
    def test_empty_profile_all_incomplete(self) -> None:
        result = compute_completeness(None, None)
        assert result["big_five"]["complete"] is False
        assert result["attachment"]["complete"] is False
        assert result["overall_pct"] == 0

    def test_big_five_complete_with_20_items(self) -> None:
        responses = {f"bf_e{i}": 3 for i in range(1, 5)}
        responses.update({f"bf_a{i}": 3 for i in range(1, 5)})
        responses.update({f"bf_c{i}": 3 for i in range(1, 5)})
        responses.update({f"bf_n{i}": 3 for i in range(1, 5)})
        responses.update({f"bf_o{i}": 3 for i in range(1, 5)})
        result = compute_completeness(responses, None)
        assert result["big_five"]["complete"] is True
        assert result["big_five"]["answered"] == 20
        assert result["big_five"]["total"] == 20

    def test_partial_completion(self) -> None:
        responses = {"bf_e1": 3, "bf_e2": 4}
        result = compute_completeness(responses, None)
        assert result["big_five"]["complete"] is False
        assert result["big_five"]["answered"] == 2

    def test_identity_layer_detected(self) -> None:
        """Shows identity as computed when identity profile has personality."""
        identity = {"personality": {"big_five": {"openness": 72}}}
        result = compute_completeness(None, identity)
        assert result["identity_computed"] is True

    def test_identity_not_computed_when_none(self) -> None:
        result = compute_completeness(None, None)
        assert result["identity_computed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_profile_completeness.py -v`
Expected: FAIL — module does not exist

- [ ] **Step 3: Create schemas package and completeness module**

```bash
mkdir -p alchymine/api/schemas && touch alchymine/api/schemas/__init__.py
```

```python
# alchymine/api/schemas/completeness.py
"""Profile completeness computation."""

from __future__ import annotations

from typing import Any

# Question ID prefixes per section and their expected counts
_SECTION_SPECS: dict[str, tuple[str, int]] = {
    "big_five": ("bf_", 20),
    "attachment": ("att_", 4),
    "risk_tolerance": ("risk_", 3),
    "enneagram": ("enn_", 9),
    "perspective": ("kegan_", 5),
    "creativity": ("guil_", 26),
}


def compute_completeness(
    assessment_responses: dict[str, int] | None,
    identity_layer: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute which assessment sections are complete.

    Parameters
    ----------
    assessment_responses:
        The user's assessment responses dict (question_id → likert value).
    identity_layer:
        The user's identity profile layer dict (from DB or None).

    Returns
    -------
    dict with keys for each section plus overall stats.
    """
    responses = assessment_responses or {}
    sections: dict[str, Any] = {}
    total_answered = 0
    total_questions = 0

    for section, (prefix, expected) in _SECTION_SPECS.items():
        answered = sum(1 for k in responses if k.startswith(prefix))
        sections[section] = {
            "complete": answered >= expected,
            "answered": answered,
            "total": expected,
        }
        total_answered += answered
        total_questions += expected

    # Check if identity profile has been computed
    identity_computed = bool(
        identity_layer
        and isinstance(identity_layer, dict)
        and identity_layer.get("personality")
    )

    overall_pct = round(total_answered / total_questions * 100) if total_questions else 0

    return {
        **sections,
        "identity_computed": identity_computed,
        "overall_pct": overall_pct,
        "total_answered": total_answered,
        "total_questions": total_questions,
    }
```

- [ ] **Step 4: Add completeness API endpoint**

In `alchymine/api/routers/profile.py`, add:

```python
@router.get("/profile/{user_id}/completeness")
async def get_profile_completeness(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return assessment section completeness for a user."""
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    user = await repository.get_profile(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    from alchymine.api.schemas.completeness import compute_completeness

    responses = user.intake.assessment_responses if user.intake else None
    identity = None
    if user.identity:
        identity = {
            "personality": user.identity.personality,
            "archetype": user.identity.archetype,
            "numerology": user.identity.numerology,
        }

    return compute_completeness(responses, identity)
```

- [ ] **Step 5: Run tests**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_profile_completeness.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add alchymine/api/schemas/completeness.py alchymine/api/routers/profile.py tests/api/test_profile_completeness.py
git commit -m "feat: add profile completeness endpoint"
```

---

### Task 6: Return missing_sections in report response

When a report is fetched, include a `missing_sections` field listing systems that couldn't produce narratives due to missing prerequisites. The frontend uses this to show targeted guidance.

**Files:**

- Modify: `alchymine/workers/tasks.py` (persist missing_prerequisites in report result)
- Modify: `alchymine/api/routers/reports.py` (include in GET response)
- Test: `tests/api/test_reports.py` or inline in existing report tests

- [ ] **Step 1: Write failing test**

```python
# Add to existing report tests or create new file
def test_report_result_includes_missing_sections() -> None:
    """Report result dict includes missing_sections from coordinator results."""
    from alchymine.workers.tasks import _extract_missing_sections

    coordinator_results = [
        {"system": "healing", "data": {"missing_prerequisites": ["big_five", "archetype"]}, "status": "degraded"},
        {"system": "intelligence", "data": {"personality": {}}, "status": "success"},
    ]
    result = _extract_missing_sections(coordinator_results)
    assert result == {"healing": ["big_five", "archetype"]}
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL — `_extract_missing_sections` does not exist

- [ ] **Step 3: Implement `_extract_missing_sections` in tasks.py**

```python
def _extract_missing_sections(
    coordinator_results: list[dict],
) -> dict[str, list[str]]:
    """Extract missing_prerequisites from coordinator results.

    Returns a map of system → list of missing prerequisite names.
    """
    missing: dict[str, list[str]] = {}
    for cr in coordinator_results:
        data = cr.get("data", {})
        prereqs = data.get("missing_prerequisites", [])
        if prereqs:
            missing[cr.get("system", "unknown")] = prereqs
    return missing
```

In `generate_report()`, after the orchestrator finishes and before saving to DB, add `missing_sections` to the serialised result:

```python
serialised["missing_sections"] = _extract_missing_sections(
    serialised.get("coordinator_results", [])
)
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/workers/tasks.py
git commit -m "feat: include missing_sections in report result"
```

---

## Chunk 3: Frontend — Targeted Assessment Flow

### Task 7: Assessment page accepts section filter

Allow the assessment page to accept a `?sections=big_five,attachment` query parameter that filters which questions are shown. This enables retaking specific sections without redoing all 67 questions.

**Files:**

- Modify: `alchymine/web/src/app/discover/assessment/page.tsx`
- Modify: `alchymine/web/src/lib/questions.ts` (export section filter helper)

- [ ] **Step 1: Add section filter helper to questions.ts**

```typescript
// Add to alchymine/web/src/lib/questions.ts

export type QuestionCategory = Question["category"];

export const QUESTION_CATEGORIES: QuestionCategory[] = [
  "big_five",
  "attachment",
  "risk_tolerance",
  "enneagram",
  "perspective",
  "creativity",
];

/**
 * Filter ALL_QUESTIONS to only include the specified categories.
 * Returns all questions if sections is empty or undefined.
 */
export function filterQuestionsBySection(
  sections?: QuestionCategory[],
): Question[] {
  if (!sections || sections.length === 0) return ALL_QUESTIONS;
  return ALL_QUESTIONS.filter((q) => sections.includes(q.category));
}
```

- [ ] **Step 2: Update assessment page to read `sections` param**

In `assessment/page.tsx`, add `useSearchParams` and filter questions:

```typescript
import { useSearchParams } from "next/navigation";
import {
  filterQuestionsBySection,
  type QuestionCategory,
} from "@/lib/questions";

// Inside AssessmentPage component:
const searchParams = useSearchParams();
const sectionsParam = searchParams.get("sections");
const selectedSections = sectionsParam
  ? (sectionsParam.split(",") as QuestionCategory[])
  : undefined;

const questions = filterQuestionsBySection(selectedSections);
const totalQuestions = questions.length;
```

Replace references to `ALL_QUESTIONS` with `questions`, `TOTAL_QUESTIONS` with `totalQuestions`.

- [ ] **Step 3: Merge partial responses with existing profile data**

When in section mode, load existing responses from the profile and merge:

```typescript
// In the useEffect that verifies intake data:
useEffect(() => {
  if (!selectedSections || !user?.id) return;

  // In section mode, load existing responses from profile
  getProfile(user.id)
    .then((profile) => {
      const existing = profile.intake?.assessment_responses;
      if (existing) {
        sessionStorage.setItem(
          "alchymine_existing_responses",
          JSON.stringify(existing),
        );
      }
    })
    .catch(() => {});
}, [selectedSections, user?.id]);
```

In `handleSubmit`, merge with existing responses:

```typescript
// Before building intake payload:
const existingRaw = sessionStorage.getItem("alchymine_existing_responses");
const existingResponses = existingRaw ? JSON.parse(existingRaw) : {};
const mergedResponses = { ...existingResponses, ...finalResponses };
```

- [ ] **Step 4: Add section-mode completion behavior**

When in section mode, after completing the filtered questions, call the reassess endpoint instead of creating a new report. Map sections to the correct coordinator system:

```typescript
// Section-to-system mapping: which coordinator processes which question categories
const SECTION_TO_SYSTEM: Record<string, string> = {
  big_five: "intelligence",
  attachment: "intelligence",
  risk_tolerance: "intelligence",
  enneagram: "intelligence",
  perspective: "perspective",
  creativity: "creative",
};

// In handleSubmit, if in section mode:
if (selectedSections && user?.id) {
  // Determine which systems need reassessment based on selected sections
  const systems = [...new Set(selectedSections.map((s) => SECTION_TO_SYSTEM[s]))];
  for (const system of systems) {
    await reassessProfile(user.id, system, mergedResponses);
  }
  router.push("/profile");
  return;
}
```

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/lib/questions.ts alchymine/web/src/app/discover/assessment/page.tsx
git commit -m "feat: assessment page supports section-specific question filtering"
```

---

### Task 8: Add getCompleteness API function

The `reassessProfile()` function already exists in `api.ts` (lines 888-904) with the correct signature. We only need to add `getCompleteness()` and the `CompletenessResponse` type.

**Files:**

- Modify: `alchymine/web/src/lib/api.ts`

- [ ] **Step 1: Add getCompleteness and CompletenessResponse to api.ts**

```typescript
// Add to alchymine/web/src/lib/api.ts

export interface SectionCompleteness {
  complete: boolean;
  answered: number;
  total: number;
}

export interface CompletenessResponse {
  big_five: SectionCompleteness;
  attachment: SectionCompleteness;
  risk_tolerance: SectionCompleteness;
  enneagram: SectionCompleteness;
  perspective: SectionCompleteness;
  creativity: SectionCompleteness;
  identity_computed: boolean;
  overall_pct: number;
  total_answered: number;
  total_questions: number;
}

export async function getCompleteness(
  userId: string,
): Promise<CompletenessResponse> {
  return request<CompletenessResponse>(
    `${BASE}/profile/${encodeURIComponent(userId)}/completeness`,
  );
}
```

Note: Task 7 uses the existing `reassessProfile()` (line 888) — no new function needed.

- [ ] **Step 2: Commit**

```bash
git add alchymine/web/src/lib/api.ts
git commit -m "feat: add getCompleteness API function and CompletenessResponse type"
```

---

## Chunk 4: Frontend — Profile & Report UX Guidance

### Task 9: Profile page shows section completeness

Add completeness indicators to the profile page so users can see which sections are complete and retake specific ones.

**Files:**

- Modify: `alchymine/web/src/app/profile/page.tsx`

- [ ] **Step 1: Fetch completeness data on profile page**

```typescript
// In the profile page component:
import { getCompleteness, type CompletenessResponse } from "@/lib/api";

const [completeness, setCompleteness] = useState<CompletenessResponse | null>(
  null,
);

useEffect(() => {
  if (!userId) return;
  getCompleteness(userId)
    .then(setCompleteness)
    .catch(() => {});
}, [userId]);
```

- [ ] **Step 2: Add AssessmentCompleteness section to profile page**

Add a new section below the identity data that shows each assessment category with its completion status and a retake link:

```typescript
{completeness && (
  <div className="card-surface p-6">
    <h3 className="font-display text-lg font-medium mb-4">Assessment Status</h3>
    <div className="space-y-3">
      {([
        { key: "big_five", label: "Personality (Big Five)", sections: "big_five" },
        { key: "attachment", label: "Attachment Style", sections: "attachment" },
        { key: "risk_tolerance", label: "Risk Tolerance", sections: "risk_tolerance" },
        { key: "enneagram", label: "Enneagram", sections: "enneagram" },
        { key: "perspective", label: "Perspective (Kegan)", sections: "perspective" },
        { key: "creativity", label: "Creativity", sections: "creativity" },
      ] as const).map(({ key, label, sections }) => {
        const section = completeness[key];
        return (
          <div key={key} className="flex items-center justify-between py-2 border-b border-white/[0.06] last:border-0">
            <div>
              <span className="text-sm font-body text-text">{label}</span>
              <span className="text-xs text-text/40 ml-2">
                {section.answered}/{section.total}
              </span>
            </div>
            {section.complete ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-primary/70">Complete</span>
                <a
                  href={`/discover/assessment?sections=${sections}`}
                  className="text-xs text-text/30 hover:text-text/60 transition-colors"
                >
                  Retake
                </a>
              </div>
            ) : (
              <a
                href={`/discover/assessment?sections=${sections}`}
                className="text-xs font-medium text-primary hover:text-primary-light transition-colors"
              >
                Complete
              </a>
            )}
          </div>
        );
      })}
    </div>
    <div className="mt-4 pt-3 border-t border-white/[0.06]">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text/40">Overall</span>
        <span className="text-xs text-text/50">{completeness.overall_pct}%</span>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 3: Commit**

```bash
git add alchymine/web/src/app/profile/page.tsx
git commit -m "feat: profile page shows assessment section completeness with retake links"
```

---

### Task 10: Report page shows guidance for missing sections

Instead of silently hiding empty narrative sections, show the user what's missing and link them directly to the section-specific assessment.

**Files:**

- Modify: `alchymine/web/src/app/discover/report/[id]/page.tsx`

- [ ] **Step 1: Extract missing_sections from report data**

```typescript
// In the report page component, after fetching report:
const missingSections: Record<string, string[]> =
  report?.result?.missing_sections ?? {};
```

- [ ] **Step 2: Show guidance cards for missing sections**

In the Personalized Insights section, after rendering `activeNarratives`, add guidance for systems that have missing prerequisites:

```typescript
{/* Missing section guidance */}
{Object.entries(missingSections).map(([system, prerequisites]) => {
  const systemLabels: Record<string, string> = {
    healing: "Ethical Healing",
    wealth: "Generational Wealth",
    creative: "Creative Development",
    perspective: "Perspective Enhancement",
  };
  const prerequisiteLabels: Record<string, { label: string; sections: string }> = {
    big_five: { label: "Personality Assessment", sections: "big_five" },
    archetype: { label: "Complete Identity Assessment", sections: "big_five,attachment" },
    risk_tolerance: { label: "Risk Tolerance Assessment", sections: "risk_tolerance" },
  };

  return (
    <div key={system} className="card-surface p-6 border-l-4 border-primary/30">
      <h3 className="font-display text-lg font-medium mb-2">
        {systemLabels[system] ?? system}
      </h3>
      <p className="text-sm text-text/40 mb-4">
        Complete the following to unlock this section:
      </p>
      <div className="space-y-2">
        {prerequisites.map((prereq) => {
          const info = prerequisiteLabels[prereq];
          return (
            <a
              key={prereq}
              href={`/discover/assessment?sections=${info?.sections ?? prereq}`}
              className="flex items-center gap-2 text-sm text-primary hover:text-primary-light transition-colors"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
              </svg>
              {info?.label ?? prereq}
            </a>
          );
        })}
      </div>
    </div>
  );
})}
```

- [ ] **Step 3: Commit**

```bash
git add alchymine/web/src/app/discover/report/[id]/page.tsx
git commit -m "feat: report page shows guidance for missing sections with direct assessment links"
```

---

## Chunk 5: Integration Verification

### Task 11: End-to-end integration test

Verify the full pipeline works: Intelligence computes personality → persists to DB → Healing reads from DB → produces real modality matches → narrative renders.

**Files:**

- Test: `tests/integration/test_healing_pipeline_e2e.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_healing_pipeline_e2e.py
"""End-to-end test: Intelligence → DB → Healing pipeline."""

import pytest

from alchymine.agents.orchestrator.graphs import (
    build_healing_graph,
    build_intelligence_graph,
)


class TestHealingPipelineE2E:
    """Verify healing works with real intelligence data, not fallbacks."""

    def _make_assessment_responses(self) -> dict[str, int]:
        """Build a complete 67-question assessment response dict."""
        responses: dict[str, int] = {}
        # 20 Big Five items
        for trait in ("e", "a", "c", "n", "o"):
            for i in range(1, 5):
                responses[f"bf_{trait}{i}"] = 4
        # 4 Attachment
        for key in ("att_closeness", "att_abandonment", "att_trust", "att_self_reliance"):
            responses[key] = 3
        # 3 Risk tolerance
        for i in range(1, 4):
            responses[f"risk_{i}"] = 3
        # 9 Enneagram
        for i in range(1, 10):
            responses[f"enn_{i}"] = 3
        # 5 Kegan
        for i in range(1, 6):
            responses[f"kegan_{i}"] = 4
        # 26 Guilford (actual IDs from questions.ts)
        for prefix in ("flu", "flex", "orig", "elab", "sens", "redef"):
            for i in range(1, 4):
                responses[f"guil_{prefix}{i}"] = 3
        for i in range(1, 9):
            responses[f"guil_conv{i}"] = 3
        return responses

    def test_intelligence_output_feeds_healing(self) -> None:
        """Intelligence output, when passed to Healing, produces real modalities."""
        request_data = {
            "full_name": "Test User",
            "birth_date": "1990-01-15",
            "assessment_responses": self._make_assessment_responses(),
            "intentions": ["health"],
        }

        # Run Intelligence graph
        intel_graph = build_intelligence_graph(include_quality_gate=False)
        intel_state = {
            "user_id": "test",
            "request_data": request_data,
            "results": {},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        intel_result = intel_graph.invoke(intel_state)

        # Verify Intelligence produced personality data
        personality = intel_result["results"].get("personality", {})
        assert "big_five" in personality, "Intelligence must produce big_five scores"
        assert personality["big_five"]["openness"] > 0

        archetype = intel_result["results"].get("archetype", {})

        # Simulate orchestrator enrichment
        healing_request = dict(request_data)
        if personality:
            healing_request["big_five"] = personality
        if archetype.get("primary"):
            healing_request["archetype"] = archetype["primary"]
            healing_request["archetype_secondary"] = archetype.get("secondary")

        # Run Healing graph with enriched data
        healing_graph = build_healing_graph(include_quality_gate=False)
        healing_state = {
            "user_id": "test",
            "request_data": healing_request,
            "results": {},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        healing_result = healing_graph.invoke(healing_state)

        # Verify Healing produced REAL modalities, not fallbacks
        results = healing_result["results"]
        assert "recommended_modalities" in results
        modalities = results["recommended_modalities"]
        assert len(modalities) > 0
        # Real modalities have preference_score (fallbacks don't)
        assert "preference_score" in modalities[0], (
            "Modalities should come from real matching, not fallbacks"
        )

        # Verify personality data was extracted
        assert "openness" in results
        assert results["openness"] > 0
        assert "neuroticism" in results

        # No missing prerequisites
        assert "missing_prerequisites" not in results
        assert healing_result["status"] == "success"
```

- [ ] **Step 2: Run integration test**

Run: `D:/Python/Python311/python.exe -m pytest tests/integration/test_healing_pipeline_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_healing_pipeline_e2e.py
git commit -m "test: end-to-end integration test for Intelligence → Healing pipeline"
```

---

### Task 12: Run full test suite and lint

- [ ] **Step 1: Run ruff lint + format check**

```bash
ruff check alchymine/
ruff format --check alchymine/
```

- [ ] **Step 2: Run full test suite (excluding LLM tests)**

```bash
D:/Python/Python311/python.exe -m pytest tests/ -v --ignore=tests/agents/test_llm.py
```

- [ ] **Step 3: Fix any failures, commit**

- [ ] **Step 4: Push and verify CI**

```bash
git push origin <branch>
gh run list -R realsammyt/Alchymine --limit 1
```

# Fix Healing Narrative Placeholders & PDF Export

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two report bugs: (1) Ethical Healing narrative has unfilled template placeholders (`{modalities_section}`, `{openness}`, `{neuroticism}`, `{attachment_style}`), and (2) "Export PDF" button returns 404 because Playwright isn't installed in production containers.

**Architecture:** Bug 1 is a missing graph node — the healing coordinator graph doesn't extract Big Five personality traits from `request_data` into `results` for the narrative template. The creative graph already has this pattern (`_creative_personality_context`). Bug 2 is a missing dependency — Playwright is in `[project.optional-dependencies]` but the worker Dockerfile only installs `pip install .` (no extras), so `import playwright` fails silently and `pdf_data` stays NULL.

**Tech Stack:** Python 3.11, LangGraph StateGraphs, YAML templates, Docker, Playwright

---

## Phase 1: Healing Narrative Placeholders

### Task 1: Add `_healing_personality_context` graph node

**Files:**

- Modify: `alchymine/agents/orchestrator/graphs.py:520-530` (new node after modality_matching)
- Modify: `alchymine/agents/orchestrator/graphs.py:927-945` (wire into build_healing_graph)
- Test: `tests/agents/test_graphs.py`

**Step 1: Write the failing test**

In `tests/agents/test_graphs.py`, add to the `TestHealingGraphTransitions` class:

```python
def test_personality_context_surfaces_big_five(self) -> None:
    """Healing graph extracts openness, neuroticism, attachment_style from big_five."""
    state = _make_initial_state(
        request_data={
            "big_five": {
                "openness": 72,
                "neuroticism": 45,
                "conscientiousness": 60,
                "extraversion": 55,
                "agreeableness": 68,
            },
            "attachment_style": "secure",
        },
    )

    graph = build_healing_graph(include_quality_gate=False)
    result = graph.invoke(state)

    assert result["results"]["openness"] == 72
    assert result["results"]["neuroticism"] == 45
    assert result["results"]["attachment_style"] == "secure"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/agents/test_graphs.py::TestHealingGraphTransitions::test_personality_context_surfaces_big_five -v`
Expected: FAIL with KeyError — `openness` not in results

**Step 3: Write the `_healing_personality_context` node**

Add after `_healing_modality_matching` (around line 530) in `graphs.py`:

```python
def _healing_personality_context(state: CoordinatorState) -> CoordinatorState:
    """Extract Big Five and attachment style from request_data for narrative template."""
    results = dict(state.get("results", {}))
    request_data = state.get("request_data", {})

    big_five = request_data.get("big_five", {})
    if big_five:
        for trait in ("openness", "neuroticism"):
            if trait in big_five:
                results[trait] = big_five[trait]

    attachment = request_data.get("attachment_style")
    if attachment:
        results["attachment_style"] = attachment

    return {**state, "results": results}
```

**Step 4: Wire into `build_healing_graph`**

In `build_healing_graph()`, update the nodes list and edges:

```python
nodes: list[tuple[str, Any]] = [
    ("init", _healing_init),
    ("crisis_detection", _healing_crisis_detection),
    ("modality_matching", _healing_modality_matching),
    ("personality_context", _healing_personality_context),  # NEW
    ("status", _healing_status),
]
```

And update the edge chain:

```python
graph.add_edge("modality_matching", "personality_context")
graph.add_edge("personality_context", "status")
```

(Remove the old `graph.add_edge("modality_matching", "status")` line.)

**Step 5: Run test to verify it passes**

Run: `pytest tests/agents/test_graphs.py::TestHealingGraphTransitions::test_personality_context_surfaces_big_five -v`
Expected: PASS

**Step 6: Update node order test**

The existing `test_healing_node_order` test expects: `init -> crisis_detection -> modality_matching -> status`. Update it to include `personality_context`:

- Add a patch for `_healing_personality_context` with `log_node("personality_context")`
- Update the expected order: `["init", "crisis_detection", "modality_matching", "personality_context", "status"]`
- Update the docstring

**Step 7: Run all healing graph tests**

Run: `pytest tests/agents/test_graphs.py -k "healing" -v`
Expected: All PASS

**Step 8: Commit**

```bash
git add alchymine/agents/orchestrator/graphs.py tests/agents/test_graphs.py
git commit -m "fix: add healing personality context node for narrative placeholders"
```

### Task 2: Add `recommended_modalities` flattening alias for healing narrative

**Files:**

- Modify: `alchymine/llm/narrative.py:146-180` (add healing alias)
- Test: `tests/agents/test_llm.py` (or create inline test)

The healing template uses `{modalities_section}`. The `flatten_engine_data` function already converts lists to `{key}_section` (line 132-142), so `recommended_modalities` → `recommended_modalities_section`. But the template expects `{modalities_section}`, not `{recommended_modalities_section}`.

**Step 1: Write the failing test**

Add to `tests/agents/test_llm.py` (or `tests/agents/test_synthesis.py`):

```python
def test_flatten_healing_modalities_alias():
    """flatten_engine_data creates modalities_section alias from recommended_modalities."""
    from alchymine.llm.narrative import flatten_engine_data

    data = {
        "recommended_modalities": [
            {"modality": "Breathwork", "skill_trigger": "anxiety relief", "preference_score": 0.85},
            {"modality": "Yoga", "skill_trigger": "stress reduction", "preference_score": 0.78},
        ],
    }
    flat = flatten_engine_data(data)
    assert "modalities_section" in flat
    assert "Breathwork" in flat["modalities_section"]
```

**Step 2: Run test to verify it fails**

Expected: FAIL — `modalities_section` not in flat (only `recommended_modalities_section` is)

**Step 3: Add healing alias in `flatten_engine_data`**

After the existing Perspective aliases (around line 178), add:

```python
# Healing: recommended_modalities_section → {modalities_section}
if "recommended_modalities_section" in flat:
    flat["modalities_section"] = flat["recommended_modalities_section"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/agents/test_llm.py::test_flatten_healing_modalities_alias -v`
Expected: PASS

**Step 5: Also add crisis_section alias**

The template uses `{crisis_section}`. The crisis data is stored as `crisis_response` (a dict). The `flatten_engine_data` function flattens dicts but doesn't create a `{crisis_section}` key.

Add to `_healing_personality_context` or a new snippet in `flatten_engine_data`:

```python
# Healing: crisis_response dict → {crisis_section}
cr = data.get("crisis_response")
if isinstance(cr, dict):
    severity = cr.get("severity", "unknown")
    resources = cr.get("resources", [])
    lines = [f"- Severity: {severity}"]
    for r in resources:
        if isinstance(r, dict):
            lines.append(f"- {r.get('name', '')}: {r.get('contact', '')}")
    flat["crisis_section"] = "\n  ".join(lines)
elif data.get("crisis_flag") is False:
    flat["crisis_section"] = "No crisis indicators detected."
```

**Step 6: Run full test suite for narrative flattening**

Run: `pytest tests/agents/ -k "flatten or narrative" -v`
Expected: PASS

**Step 7: Commit**

```bash
git add alchymine/llm/narrative.py tests/
git commit -m "fix: add healing narrative template aliases (modalities_section, crisis_section)"
```

---

## Phase 2: PDF Export Fix

### Task 3: Install Playwright in worker Docker image

**Files:**

- Modify: `infrastructure/docker/Dockerfile.worker` (add playwright + chromium)
- Modify: `pyproject.toml` (move playwright to main deps OR install [pdf] extra)

**Step 1: Move playwright to main dependencies**

In `pyproject.toml`, move `playwright>=1.40.0` from `[project.optional-dependencies]` to `[project.dependencies]`. This ensures `pip install .` includes it.

Alternatively (preferred for image size), keep it optional but install the extra in the worker Dockerfile:

```dockerfile
# In Dockerfile.worker, Stage 1 (builder), change:
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir watchdog

# To:
RUN pip install --no-cache-dir ".[pdf]" && \
    pip install --no-cache-dir watchdog
```

**Step 2: Install Chromium browser in worker runtime stage**

After the `apt-get` install block in Stage 2, add Playwright browser installation:

```dockerfile
# Install Playwright and Chromium browser for PDF rendering
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Chromium system dependencies and browser
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install chromium --with-deps
```

Note: The `playwright install chromium --with-deps` command must run AFTER the venv is copied, since it uses the `playwright` CLI from the venv.

**Step 3: Verify locally (smoke test)**

Run: `docker compose -f infrastructure/docker-compose.yml build worker`
Expected: Build succeeds, includes Playwright + Chromium

**Step 4: Commit**

```bash
git add infrastructure/docker/Dockerfile.worker
git commit -m "fix: install Playwright + Chromium in worker for PDF generation"
```

### Task 4: Add auth token to PDF fetch request

**Files:**

- Modify: `alchymine/web/src/app/discover/report/[id]/page.tsx:1002-1008`

**Step 1: Check auth flow**

The current PDF fetch uses `{ credentials: "include" }` which sends cookies. Verify the API endpoint requires auth — it does (via `current_user` dependency). Since Alchymine uses JWT tokens (not cookies), the `credentials: "include"` approach won't work. The fetch needs the Authorization header.

**Step 2: Update fetch to include auth token**

```typescript
const token = localStorage.getItem("access_token");
const response = await fetch(`${apiUrl}/api/v1/reports/${reportId}/pdf`, {
  headers: token ? { Authorization: `Bearer ${token}` } : {},
});
```

**Step 3: Commit**

```bash
git add alchymine/web/src/app/discover/report/\[id\]/page.tsx
git commit -m "fix: include auth token in PDF download request"
```

### Task 5: Verify end-to-end and run full test suite

**Step 1: Run Python tests**

Run: `CELERY_ALWAYS_EAGER=true pytest tests/ -v`
Expected: All tests pass (including new healing personality context tests)

**Step 2: Run lint + format**

Run: `ruff check alchymine/ && ruff format --check alchymine/`
Expected: Clean

**Step 3: Commit any remaining fixes and push**

---

## Summary

| Task | Bug                  | What                                                           |
| ---- | -------------------- | -------------------------------------------------------------- |
| 1    | Healing placeholders | Add `_healing_personality_context` graph node                  |
| 2    | Healing placeholders | Add `modalities_section` + `crisis_section` flattening aliases |
| 3    | PDF export           | Install Playwright + Chromium in worker Dockerfile             |
| 4    | PDF export           | Add auth token to PDF fetch request                            |
| 5    | Both                 | Full verification pass                                         |

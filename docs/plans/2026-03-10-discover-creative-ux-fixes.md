# Fix Discover Page Routing, Creative Fingerprint Display, and Project Journal Flow

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three UX bugs: (1) Discover page intention buttons all produce identical system rankings, (2) Creative page Guilford scores show "10000%" with all-zero bars, (3) "Start Project" creates journal entry but doesn't navigate to it.

**Architecture:** Bug 1 is a key mismatch — frontend sends narrative keys ("self-understanding") but backend expects canonical keys ("purpose"). Fix by adding a mapping in the backend router. Bug 2 is a data shape mismatch — `guilford_summary` contains `{score, label, tier}` dicts but frontend reads them as plain numbers. Bug 3 is missing navigation — need `useRouter` + `router.push` after journal creation.

**Tech Stack:** TypeScript, Next.js 15, React 18, Python 3.11, FastAPI

---

## Task 1: Fix intention key mapping in spiral router

**Files:**

- Modify: `alchymine/engine/spiral/router.py:162-164`

The frontend SpiralHub buttons send narrative keys:

- "self-understanding", "financial-decision", "creative-block", "emotional-healing",
  "career-direction", "build-wealth", "perspective-shift", "relationship-growth",
  "find-purpose", "legacy-planning"

The backend `INTENTION_WEIGHTS` expects canonical keys:

- "career", "love", "purpose", "money", "health", "family", "business", "legacy"

All unknown keys default to "purpose" (line 164), so every button produces the same ranking.

**Step 1: Add narrative-to-canonical mapping**

In `alchymine/engine/spiral/router.py`, before the `route_user()` function (around line 131), add:

```python
# Map frontend narrative intention keys to canonical intention keys.
# The SpiralHub UI uses descriptive button keys; the routing engine
# uses short canonical keys from INTENTION_WEIGHTS.
_NARRATIVE_TO_CANONICAL: dict[str, str] = {
    "self-understanding": "purpose",
    "financial-decision": "money",
    "creative-block": "creative",  # not in INTENTION_WEIGHTS — will need entry
    "emotional-healing": "health",
    "career-direction": "career",
    "build-wealth": "money",
    "perspective-shift": "purpose",
    "relationship-growth": "love",
    "find-purpose": "purpose",
    "legacy-planning": "legacy",
}
```

**Step 2: Add "creative" intention to INTENTION_WEIGHTS**

In `alchymine/engine/intention_map.py`, add after the "legacy" entry:

```python
"creative": {
    "creative": 40,
    "intelligence": 20,
    "perspective": 20,
    "healing": 10,
    "wealth": 10,
},
```

Also add "creative" entry to `INTENTION_PRIMARY_SYSTEMS`:

```python
"creative": ["creative", "intelligence"],
```

Also add "creative" entry actions to `_ENTRY_ACTIONS` in `router.py`:

```python
# In each system's dict, add "creative" key:
```

Actually, the simplest fix: since "creative" as an intention key isn't in the \_ENTRY_ACTIONS sub-dicts, we need a fallback. The existing code uses `_ENTRY_ACTIONS[system].get(intention, "")`. Let's add "creative" to each system's entry actions dict.

**Step 3: Use the mapping in route_user()**

Change lines 162-164 in `router.py` from:

```python
intention = intention.lower()
if intention not in INTENTION_WEIGHTS:
    intention = "purpose"  # Default to purpose if unknown
```

To:

```python
intention = intention.lower()
# Map narrative UI keys to canonical intention keys
intention = _NARRATIVE_TO_CANONICAL.get(intention, intention)
if intention not in INTENTION_WEIGHTS:
    intention = "purpose"  # Default to purpose if unknown
```

**Step 4: Add "creative" entry actions to \_ENTRY_ACTIONS**

Add a "creative" key to each system's dict in `_ENTRY_ACTIONS`:

```python
"intelligence": {
    ...existing...
    "creative": "Explore how your numerology shapes your creative expression",
},
"healing": {
    ...existing...
    "creative": "Release creative blocks through somatic breathwork",
},
"wealth": {
    ...existing...
    "creative": "Discover income streams aligned with your creative gifts",
},
"creative": {
    ...existing...
    "creative": "Dive into your Guilford scores and discover your creative DNA",
},
"perspective": {
    ...existing...
    "creative": "Explore how expanding perspectives fuels creative breakthroughs",
},
```

**Step 5: Commit**

```bash
git add alchymine/engine/spiral/router.py alchymine/engine/intention_map.py
git commit -m "fix: map narrative intention keys to canonical keys in spiral router"
```

---

## Task 2: Fix creative Guilford scores display

**Files:**

- Modify: `alchymine/web/src/app/creative/page.tsx:93-110, 262-263, 275-281`

Two problems:

**Problem A: "Overall Score: 10000%"**
Line 263: `Math.round(style.data.overall_score * 100)` — but `overall_score` is already on a 0-100 scale (it's the average of Guilford component scores which are 0-100). So `100 * 100 = 10000`.

Fix: Change line 263 from:

```typescript
{Math.round(style.data.overall_score * 100)}%
```

To:

```typescript
{Math.round(style.data.overall_score)}%
```

**Problem B: All Guilford scores show 0**
The `guilford_summary` from the API contains `{score: number, label: string, tier: string}` dicts, NOT plain numbers. The `ScoreBar` component receives the whole dict as `value`, then `Number(val)` on a dict gives `NaN`, and `NaN || 0 = 0`.

Fix the mapping at lines 275-281. Change from:

```typescript
{Object.entries(style.data.guilford_summary).map(
  ([key, val]) => (
    <ScoreBar
      key={key}
      label={key}
      value={Number(val) || 0}
    />
  ),
)}
```

To:

```typescript
{Object.entries(style.data.guilford_summary).map(
  ([key, val]) => {
    const entry = val as { score?: number; label?: string } | number;
    const score = typeof entry === "number"
      ? entry
      : (entry?.score ?? 0);
    return (
      <ScoreBar
        key={key}
        label={typeof entry === "object" && entry?.label ? entry.label : key}
        value={score / 100}
      />
    );
  },
)}
```

This extracts `score` from the `{score, label, tier}` dict and divides by 100 (since ScoreBar expects 0-1 range and multiplies by 100 internally). It also uses the human-readable `label` field instead of the raw key.

**Problem C: Text hard to read**
The `ScoreBar` label uses `text-text/60` (60% opacity) which is low contrast. Change line 96 from:

```typescript
<span className="font-body text-sm text-text/60 w-28 text-right">
```

To:

```typescript
<span className="font-body text-sm text-text/80 w-28 text-right capitalize">
```

**Step 5: Commit**

```bash
git add alchymine/web/src/app/creative/page.tsx
git commit -m "fix: display Guilford scores correctly from {score,label,tier} response"
```

---

## Task 3: Navigate to journal entry after "Start Project"

**Files:**

- Modify: `alchymine/web/src/components/creative/CreativeProjects.tsx:1-4, 128-137`

**Step 1: Add useRouter import**

Change line 3 from:

```typescript
import { useState, useCallback } from "react";
```

To:

```typescript
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
```

**Step 2: Add router hook inside the component**

Inside `CreativeProjects` function (after line 127), add:

```typescript
const router = useRouter();
```

**Step 3: Capture journal entry ID and navigate**

Change `handleStartProject` (lines 128-137) from:

```typescript
const handleStartProject = useCallback(async (project: ProjectResponse) => {
  await createJournalEntry({
    system: "creative",
    entry_type: "project_start",
    title: `Started: ${project.title}`,
    content: `Beginning the creative project "${project.title}".\n\nDescription: ${project.description}\n\nMedium: ${project.medium}\nSkill level: ${project.skill_level}\nType: ${project.type}`,
    tags: ["creative", "project", project.medium, project.type],
    mood_score: null,
  });
}, []);
```

To:

```typescript
const handleStartProject = useCallback(
  async (project: ProjectResponse) => {
    const entry = await createJournalEntry({
      system: "creative",
      entry_type: "project_start",
      title: `Started: ${project.title}`,
      content: `Beginning the creative project "${project.title}".\n\nDescription: ${project.description}\n\nMedium: ${project.medium}\nSkill level: ${project.skill_level}\nType: ${project.type}`,
      tags: ["creative", "project", project.medium, project.type],
      mood_score: null,
    });
    router.push(`/journal?highlight=${entry.id}`);
  },
  [router],
);
```

This navigates to the journal page with the new entry ID as a query param so the UI can scroll to / highlight it.

**Step 4: Commit**

```bash
git add alchymine/web/src/components/creative/CreativeProjects.tsx
git commit -m "fix: navigate to journal after starting creative project"
```

---

## Task 4: Run verification

**Step 1: Run frontend lint**

Run: `cd alchymine/web && npm run lint`
Expected: Clean

**Step 2: Run frontend tests**

Run: `cd alchymine/web && npm test -- --watchAll=false`
Expected: All pass

**Step 3: Run Python tests for spiral router**

Run: `D:/Python/Python311/python.exe -m pytest tests/engine/test_spiral_router.py -v`
Expected: All pass (existing tests use canonical keys, should still work)

**Step 4: Run Python lint**

Run: `D:/Python/Python311/python.exe -m ruff check alchymine/engine/spiral/ alchymine/engine/intention_map.py`
Expected: Clean

---

## Summary

| Task | Bug                       | What                                                            |
| ---- | ------------------------- | --------------------------------------------------------------- |
| 1    | Same rankings for all     | Map narrative button keys to canonical intention keys           |
| 2    | Guilford "10000%" + zeros | Fix overall_score scale + extract score from {score,label,tier} |
| 3    | Start Project no navigate | Add router.push to journal after entry creation                 |
| 4    | Verification              | Full lint + test pass                                           |

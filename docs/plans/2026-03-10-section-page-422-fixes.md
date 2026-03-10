# Fix Section Page 422 Errors & Data Wiring

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 422 validation errors on system section pages (wealth, creative, perspective) by correcting frontend payload shapes, wire biorhythm data to the intelligence page, and fix "Update Profile" button routing.

**Architecture:** All 422 errors share the same root cause: frontend pages spread raw profile layer data into API payloads, but backend Pydantic request models expect specific top-level fields that are nested inside layer sub-objects. The fix is to extract/reshape data in the frontend `useMemo` payload constructors. Biorhythm needs a new API client function + frontend call to the existing backend endpoint. "Update Profile" buttons need system-specific routing.

**Tech Stack:** TypeScript, Next.js 15, React 18, FastAPI, Pydantic

---

## Task 1: Fix wealth page 422 errors (3 endpoints)

**Files:**

- Modify: `alchymine/web/src/app/wealth/page.tsx:698-705`

The wealth page spreads `identityLayerData` (shape: `{ numerology: {life_path: 7, ...}, archetype: {primary: "Creator", ...}, ... }`) flat into the payload. The three wealth endpoints expect `life_path` (int) and `archetype_primary` (string) at the TOP level.

**Step 1: Read the current payload construction**

Read `alchymine/web/src/app/wealth/page.tsx` lines 688-720 to confirm the current state.

**Step 2: Fix the payload construction**

Replace the `wealthPayload` useMemo (lines 698-705) with:

```typescript
const wealthPayload = useMemo((): Record<string, unknown> | null => {
  if (!identityLayerData && !wealthLayerData) return null;

  // Extract top-level fields the wealth endpoints require from nested
  // identity layer sub-objects (numerology.life_path, archetype.primary).
  const numerology = identityLayerData?.numerology as
    | Record<string, unknown>
    | undefined;
  const archetype = identityLayerData?.archetype as
    | Record<string, unknown>
    | undefined;

  return {
    life_path: numerology?.life_path,
    archetype_primary: archetype?.primary,
    risk_tolerance: wealthLayerData?.risk_tolerance ?? "moderate",
    wealth_context: wealthLayerData?.wealth_context ?? null,
    intentions: intakeIntentions,
  };
}, [identityLayerData, wealthLayerData, intakeIntentions]);
```

**Step 3: Verify no TypeScript errors**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors in `wealth/page.tsx`

**Step 4: Commit**

```bash
git add alchymine/web/src/app/wealth/page.tsx
git commit -m "fix: extract life_path and archetype_primary for wealth endpoints"
```

---

## Task 2: Fix creative page 422 error (projects endpoint)

**Files:**

- Modify: `alchymine/web/src/app/creative/page.tsx:142-161`

The creative page sends the raw creative layer data to `getCreativeProjects`. The `ProjectSuggestRequest` backend model requires:

- `orientation` (str) — stored in creative layer as `creative_orientation` (string)
- `strengths` (list[str]) — must be derived from `guilford_scores` (dict of component name → score); use the top-scoring components

**Step 1: Read the current payload and projects call**

Read `alchymine/web/src/app/creative/page.tsx` lines 137-161.

**Step 2: Fix the projects payload**

Replace the `projects` useApi call (lines 152-161) with:

```typescript
const projects = useApi<ProjectListResponse>(
  creativePayload && style.data
    ? () => {
        // ProjectSuggestRequest requires: orientation (str), strengths (list[str])
        const guilford = creativePayload.guilford_scores as
          | Record<string, number>
          | undefined;
        const strengths = guilford
          ? Object.entries(guilford)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 3)
              .map(([name]) => name)
          : [];
        return getCreativeProjects({
          orientation:
            (creativePayload.creative_orientation as string) ?? "Explorer",
          strengths,
          medium_affinities: Array.isArray(creativePayload.medium_affinities)
            ? (creativePayload.medium_affinities as string[])
            : [],
          creative_style: style.data?.creative_style,
        });
      }
    : null,
  [JSON.stringify(creativePayload), style.data?.creative_style],
);
```

**Step 3: Verify no TypeScript errors**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors in `creative/page.tsx`

**Step 4: Commit**

```bash
git add alchymine/web/src/app/creative/page.tsx
git commit -m "fix: construct correct ProjectSuggestRequest payload for creative projects"
```

---

## Task 3: Fix perspective page 422 error (kegan/assess endpoint)

**Files:**

- Modify: `alchymine/web/src/app/perspective/page.tsx:163-171`
- Modify: `alchymine/web/src/lib/api.ts:567-573`

Two issues:

1. The perspective page sends the entire perspective layer (with `kegan_stage`, `kegan_dimension_scores`, `kegan_description`, etc.) but the `KeganAssessRequest` expects only `{ responses: dict }`.
2. The `getKeganAssessment` function in `api.ts` does `JSON.stringify(responses)` — it sends the raw arg as the body. It needs to wrap in `{ responses: ... }`.

**Step 1: Fix the API client function**

In `alchymine/web/src/lib/api.ts`, change `getKeganAssessment` (lines 567-573) from:

```typescript
export async function getKeganAssessment(
  responses: Record<string, unknown>,
): Promise<KeganAssessResponse> {
  return request<KeganAssessResponse>(`${BASE}/perspective/kegan/assess`, {
    method: "POST",
    body: JSON.stringify(responses),
  });
}
```

To:

```typescript
export async function getKeganAssessment(
  responses: Record<string, unknown>,
): Promise<KeganAssessResponse> {
  return request<KeganAssessResponse>(`${BASE}/perspective/kegan/assess`, {
    method: "POST",
    body: JSON.stringify({ responses }),
  });
}
```

**Step 2: Fix the perspective page payload**

In `alchymine/web/src/app/perspective/page.tsx`, change the `keganPayload` useMemo (lines 163-166) from:

```typescript
const keganPayload = useMemo((): Record<string, unknown> | null => {
  if (!perspectiveLayerData) return null;
  return { ...perspectiveLayerData };
}, [perspectiveLayerData]);
```

To:

```typescript
const keganPayload = useMemo((): Record<string, unknown> | null => {
  if (!perspectiveLayerData) return null;
  // KeganAssessRequest expects dimension scores (1-5).
  // These are stored in the kegan_dimension_scores column.
  const scores = perspectiveLayerData.kegan_dimension_scores as
    | Record<string, number>
    | null
    | undefined;
  if (!scores) return null;
  return scores;
}, [perspectiveLayerData]);
```

The `getKeganAssessment` function now wraps `scores` in `{ responses: scores }`.

**Step 3: Verify no TypeScript errors**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors

**Step 4: Commit**

```bash
git add alchymine/web/src/lib/api.ts alchymine/web/src/app/perspective/page.tsx
git commit -m "fix: wrap Kegan dimension scores in {responses} for assess endpoint"
```

---

## Task 4: Wire biorhythm data to intelligence page

**Files:**

- Modify: `alchymine/web/src/lib/api.ts` (add biorhythm API functions + response types)
- Modify: `alchymine/web/src/app/intelligence/page.tsx:74-94, 430-456`

The backend already has `POST /biorhythm/range` which returns an array of daily biorhythm values. The frontend has no API function for it and shows static placeholder text.

**Step 1: Add biorhythm types and API function to api.ts**

In `alchymine/web/src/lib/api.ts`, after the Healing section (around line 498), add:

```typescript
// ─── Biorhythm ──────────────────────────────────────────────────────

export interface BiorhythmResult {
  date: string;
  physical: number;
  emotional: number;
  intellectual: number;
  days_alive: number;
}

export interface BiorhythmRangeResponse {
  results: BiorhythmResult[];
  days_requested: number;
  evidence_rating: string;
  methodology_note: string;
}

export async function getBiorhythmRange(
  birthDate: string,
  startDate: string,
  days: number = 30,
): Promise<BiorhythmRangeResponse> {
  return request<BiorhythmRangeResponse>(`${BASE}/biorhythm/range`, {
    method: "POST",
    body: JSON.stringify({
      birth_date: birthDate,
      start_date: startDate,
      days,
    }),
  });
}
```

**Step 2: Update intelligence page to fetch and render biorhythm data**

In `alchymine/web/src/app/intelligence/page.tsx`:

a) Add import for `getBiorhythmRange` and `BiorhythmRangeResponse`:

```typescript
import { ..., getBiorhythmRange, BiorhythmRangeResponse } from "@/lib/api";
```

b) After the existing `useApi` calls for numerology/astrology (around line 141), add:

```typescript
// Fetch 30-day biorhythm range starting from today
const biorhythm = useApi<BiorhythmRangeResponse>(
  intake?.birthDate
    ? () => {
        const today = new Date().toISOString().split("T")[0];
        return getBiorhythmRange(intake.birthDate!, today, 30);
      }
    : null,
  [intake?.birthDate],
);
```

c) Replace the static biorhythm cycle cards (lines 431-456) with dynamic data:

```typescript
<MotionStagger className="grid sm:grid-cols-3 gap-4 mb-4">
  {BIORHYTHM_CYCLES.map((cycle) => {
    const key = cycle.name.toLowerCase() as
      | "physical"
      | "emotional"
      | "intellectual";
    const todayValue = biorhythm.data?.results?.[0]?.[key];
    const pct =
      todayValue != null ? Math.round(todayValue * 100) : null;
    return (
      <MotionStaggerItem key={cycle.name}>
        <div className="card-surface p-5 h-full transition-all duration-300 hover:glow-gold hover:-translate-y-1">
          <div className="flex items-center justify-between mb-3">
            <h3
              className={`font-display text-sm font-medium ${cycle.color}`}
            >
              {cycle.name}
            </h3>
            <span className="font-body text-xs text-text/30">
              {cycle.period}
            </span>
          </div>
          <p className="font-body text-sm text-text/50 leading-relaxed">
            {cycle.description}
          </p>
          <div className="mt-4 h-8 bg-bg/50 rounded-lg flex items-center justify-center">
            {biorhythm.loading ? (
              <span className="font-body text-xs text-text/20">
                Loading...
              </span>
            ) : pct != null ? (
              <div className="w-full px-3 flex items-center gap-2">
                <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      pct >= 0
                        ? "bg-accent/60"
                        : "bg-secondary/60"
                    }`}
                    style={{
                      width: `${Math.abs(pct)}%`,
                      marginLeft:
                        pct < 0
                          ? `${100 - Math.abs(pct)}%`
                          : undefined,
                    }}
                  />
                </div>
                <span className="font-mono text-xs text-text/50 w-10 text-right">
                  {pct}%
                </span>
              </div>
            ) : (
              <span className="font-body text-xs text-text/20">
                Complete intake to view
              </span>
            )}
          </div>
        </div>
      </MotionStaggerItem>
    );
  })}
</MotionStagger>
```

**Step 3: Verify no TypeScript errors**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors

**Step 4: Commit**

```bash
git add alchymine/web/src/lib/api.ts alchymine/web/src/app/intelligence/page.tsx
git commit -m "feat: wire biorhythm range data to intelligence page charts"
```

---

## Task 5: Fix "Update Profile" button routing on all section pages

**Files:**

- Modify: `alchymine/web/src/app/wealth/page.tsx:1159`
- Modify: `alchymine/web/src/app/creative/page.tsx:524`
- Modify: `alchymine/web/src/app/perspective/page.tsx:537`

All three pages have an "Update Your [System] Profile" link that points to `/discover/intake`. This sends the user back to the very beginning. Instead, it should link to `/discover/assessment` (the assessment page where they can adjust their answers).

**Step 1: Fix wealth page**

In `alchymine/web/src/app/wealth/page.tsx`, find the `<Link href="/discover/intake">` near line 1159 and change it to:

```typescript
<Link href="/discover/assessment">
```

**Step 2: Fix creative page**

In `alchymine/web/src/app/creative/page.tsx`, find the `<Link href="/discover/intake">` near line 524 and change it to:

```typescript
<Link href="/discover/assessment">
```

**Step 3: Fix perspective page**

In `alchymine/web/src/app/perspective/page.tsx`, find the `<Link href="/discover/intake">` near line 537 and change it to:

```typescript
<Link href="/discover/assessment">
```

**Step 4: Verify no TypeScript errors**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors

**Step 5: Commit**

```bash
git add alchymine/web/src/app/wealth/page.tsx alchymine/web/src/app/creative/page.tsx alchymine/web/src/app/perspective/page.tsx
git commit -m "fix: route 'Update Profile' buttons to assessment page instead of intake"
```

---

## Task 6: Run full frontend verification

**Step 1: Run TypeScript check**

Run: `cd alchymine/web && npx tsc --noEmit --pretty`
Expected: Clean

**Step 2: Run ESLint**

Run: `cd alchymine/web && npm run lint`
Expected: Clean

**Step 3: Run frontend tests**

Run: `cd alchymine/web && npm test -- --watchAll=false`
Expected: All pass

**Step 4: Fix any failures and commit**

---

## Summary

| Task | Bug                   | What                                                             |
| ---- | --------------------- | ---------------------------------------------------------------- |
| 1    | Wealth 422 errors     | Extract `life_path`, `archetype_primary` from nested identity    |
| 2    | Creative 422 error    | Build `ProjectSuggestRequest` with `orientation` + `strengths`   |
| 3    | Perspective 422 error | Send `kegan_dimension_scores` wrapped in `{ responses }` wrapper |
| 4    | Biorhythm placeholder | Add `getBiorhythmRange` API call + render actual chart bars      |
| 5    | Wrong button routing  | Point "Update Profile" to `/discover/assessment` not `/intake`   |
| 6    | Verification          | Full TypeScript + lint + test pass                               |

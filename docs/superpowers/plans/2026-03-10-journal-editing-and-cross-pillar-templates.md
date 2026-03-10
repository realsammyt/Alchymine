# Journal Editing & Cross-Pillar Templates Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add edit/delete UI to the journal, create a template library with guided prompts for all five pillars, and add post-analysis CTAs on system pages.

**Architecture:** Frontend-first approach — the backend already has full CRUD. We extend `JournalEntryUpdate` with two optional fields, add `updateJournalEntry`/`deleteJournalEntry` to the API client, build inline edit/delete in the detail modal, create a `journalTemplates.ts` config with ~24 templates, add a Templates tab, and place a reusable `JournalCTA` component on each system page.

**Tech Stack:** Next.js 15 (App Router), React 18, TypeScript, Tailwind CSS, FastAPI, Pydantic

**Spec:** `docs/superpowers/specs/2026-03-10-journal-editing-and-cross-pillar-templates-design.md`

---

## File Structure

### New Files

| File                                                 | Responsibility                                         |
| ---------------------------------------------------- | ------------------------------------------------------ |
| `alchymine/web/src/lib/journalTemplates.ts`          | Template definitions for all 5 pillars (~24 templates) |
| `alchymine/web/src/components/shared/JournalCTA.tsx` | Reusable post-analysis CTA component                   |

### Modified Files

| File                                               | Changes                                                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------ |
| `alchymine/api/routers/journal.py:43-49`           | Add `system`, `entry_type` to `JournalEntryUpdate`                       |
| `alchymine/api/routers/journal.py:195-205`         | Add `system`, `entry_type` to `update_journal_entry` changes dict        |
| `alchymine/db/repository.py:553`                   | No change needed — `allowed` set already includes `system`, `entry_type` |
| `alchymine/web/src/lib/api.ts:576-637`             | Add `updateJournalEntry`, `deleteJournalEntry` functions                 |
| `alchymine/web/src/app/journal/page.tsx`           | Edit/delete UI, new entry types, Templates tab, `?template=` param       |
| `alchymine/web/src/app/perspective/page.tsx:~497`  | Add JournalCTA after Scenario Planning                                   |
| `alchymine/web/src/app/wealth/page.tsx:~1102`      | Add JournalCTA after 90-Day Plan                                         |
| `alchymine/web/src/app/healing/page.tsx:~725`      | Add JournalCTA after Matched Modalities                                  |
| `alchymine/web/src/app/intelligence/page.tsx:~306` | Add JournalCTA after Astrology results                                   |
| `alchymine/web/src/app/creative/page.tsx:~484`     | Add JournalCTA after Projects & Collaboration                            |

---

## Chunk 1: Backend Tweak + API Client

### Task 1: Extend JournalEntryUpdate with system and entry_type

**Files:**

- Modify: `alchymine/api/routers/journal.py:43-49` (JournalEntryUpdate model)
- Modify: `alchymine/api/routers/journal.py:195-203` (update endpoint changes dict)
- Test: `tests/api/test_journal.py`

- [ ] **Step 1: Add fields to JournalEntryUpdate**

In `alchymine/api/routers/journal.py`, change the `JournalEntryUpdate` class (lines 43-49) to:

```python
class JournalEntryUpdate(BaseModel):
    """Request to update an existing journal entry."""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1, max_length=5000)
    tags: list[str] | None = None
    mood_score: int | None = Field(None, ge=1, le=10)
    system: str | None = Field(None, max_length=50)
    entry_type: str | None = Field(None, max_length=50)
```

- [ ] **Step 2: Add system/entry_type to update endpoint changes dict**

In the `update_journal_entry` endpoint (lines 195-203), add after line 203:

```python
    if update.system is not None:
        changes["system"] = update.system
    if update.entry_type is not None:
        changes["entry_type"] = update.entry_type
```

- [ ] **Step 3: Verify repository already accepts system/entry_type**

Check `alchymine/db/repository.py:553` — the `allowed` set already includes `"system"` and `"entry_type"`. No change needed.

- [ ] **Step 4: Run existing tests to confirm nothing breaks**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_journal.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/api/routers/journal.py
git commit -m "feat(journal): allow system and entry_type updates in PUT endpoint"
```

---

### Task 2: Add updateJournalEntry and deleteJournalEntry to frontend API client

**Files:**

- Modify: `alchymine/web/src/lib/api.ts:576-637`

- [ ] **Step 1: Add updateJournalEntry function**

After the `getJournalStats` function (line 637) and before the `// ─── Outcomes` comment (line 639), add:

```typescript
export async function updateJournalEntry(
  entryId: string,
  data: Partial<
    Pick<
      JournalEntry,
      "title" | "content" | "tags" | "mood_score" | "system" | "entry_type"
    >
  >,
): Promise<JournalEntry> {
  return request<JournalEntry>(`${BASE}/journal/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
```

- [ ] **Step 2: Add deleteJournalEntry function**

Add immediately after `updateJournalEntry`:

```typescript
export async function deleteJournalEntry(entryId: string): Promise<void> {
  const res = await fetch(`${BASE}/journal/${entryId}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...getLegacyAuthHeaders(),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }
  // 204 No Content — no body to parse
}
```

Note: We can't use the shared `request<T>` helper because it calls `res.json()` on success, which throws on HTTP 204 (empty body). This function uses a direct `fetch` with the same auth pattern.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors in `api.ts`

- [ ] **Step 4: Commit**

```bash
git add alchymine/web/src/lib/api.ts
git commit -m "feat(journal): add updateJournalEntry and deleteJournalEntry API client functions"
```

---

## Chunk 2: Journal Page — Edit/Delete UI + New Entry Types

### Task 3: Add new entry types to ENTRY_TYPES array

**Files:**

- Modify: `alchymine/web/src/app/journal/page.tsx:27-33`

- [ ] **Step 1: Extend the ENTRY_TYPES constant**

Change lines 27-33 from:

```typescript
const ENTRY_TYPES = [
  "reflection",
  "insight",
  "gratitude",
  "intention",
  "freeform",
];
```

To:

```typescript
const ENTRY_TYPES = [
  "reflection",
  "insight",
  "gratitude",
  "intention",
  "freeform",
  "practice-log",
  "decision",
  "assessment",
  "progress",
];
```

- [ ] **Step 2: Update the label formatter for hyphenated types**

The existing label uses `t.charAt(0).toUpperCase() + t.slice(1)` which renders `"practice-log"` as `"Practice-log"`. Add a formatter function near the top of the file (after the `moodLabel` function, ~line 113):

```typescript
function formatLabel(value: string): string {
  return value
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
```

Then replace all instances of `t.charAt(0).toUpperCase() + t.slice(1)` and `s.charAt(0).toUpperCase() + s.slice(1)` in filter dropdowns and form selectors with `formatLabel(t)` or `formatLabel(s)`.

These appear at lines: 338, 370, 448, 480.

- [ ] **Step 3: Verify the page renders**

Run: `cd alchymine/web && npm run dev` (manually check `/journal` page shows new types in filter and create form dropdowns)

- [ ] **Step 4: Commit**

```bash
git add alchymine/web/src/app/journal/page.tsx
git commit -m "feat(journal): add practice-log, decision, assessment, progress entry types"
```

---

### Task 4: Add inline edit functionality to entry detail modal

**Files:**

- Modify: `alchymine/web/src/app/journal/page.tsx`

- [ ] **Step 1: Add imports for updateJournalEntry and deleteJournalEntry**

Update the import on lines 4-10:

```typescript
import {
  createJournalEntry,
  getJournalEntries,
  getJournalStats,
  updateJournalEntry,
  deleteJournalEntry,
  JournalEntry,
  JournalStatsResponse,
} from "@/lib/api";
```

- [ ] **Step 2: Add edit state variables**

After the `selectedEntry` state (line 136), add:

```typescript
// Edit mode
const [editing, setEditing] = useState(false);
const [editTitle, setEditTitle] = useState("");
const [editContent, setEditContent] = useState("");
const [editSystem, setEditSystem] = useState("");
const [editType, setEditType] = useState("");
const [editMood, setEditMood] = useState<number>(5);
const [editTags, setEditTags] = useState("");
const [saving, setSaving] = useState(false);

// Delete confirmation
const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
const [deleting, setDeleting] = useState(false);
```

- [ ] **Step 3: Add startEdit helper**

After the edit state variables, add:

```typescript
const startEdit = (entry: JournalEntry) => {
  setEditTitle(entry.title);
  setEditContent(entry.content);
  setEditSystem(entry.system);
  setEditType(entry.entry_type);
  setEditMood(entry.mood_score ?? 5);
  setEditTags(entry.tags.join(", "));
  setEditing(true);
};
```

- [ ] **Step 4: Add handleSaveEdit handler**

```typescript
const handleSaveEdit = async () => {
  if (!selectedEntry || !editTitle.trim() || !editContent.trim()) return;
  setSaving(true);
  try {
    const updated = await updateJournalEntry(selectedEntry.id, {
      title: editTitle.trim(),
      content: editContent.trim(),
      system: editSystem,
      entry_type: editType,
      mood_score: editMood,
      tags: editTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });
    setSelectedEntry(updated);
    setEditing(false);
    await fetchEntries();
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to update entry");
  } finally {
    setSaving(false);
  }
};
```

- [ ] **Step 5: Add handleDelete handler**

```typescript
const handleDelete = async () => {
  if (!selectedEntry) return;
  setDeleting(true);
  try {
    await deleteJournalEntry(selectedEntry.id);
    setSelectedEntry(null);
    setShowDeleteConfirm(false);
    setEditing(false);
    await fetchEntries();
  } catch (err) {
    setError(err instanceof Error ? err.message : "Failed to delete entry");
  } finally {
    setDeleting(false);
  }
};
```

- [ ] **Step 6: Update Escape key handler for edit mode**

Change the Escape key handler (lines 173-181) to:

```typescript
useEffect(() => {
  if (!selectedEntry) return;
  const handleKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      if (showDeleteConfirm) {
        setShowDeleteConfirm(false);
      } else if (editing) {
        setEditing(false);
      } else {
        setSelectedEntry(null);
      }
    }
  };
  document.addEventListener("keydown", handleKey);
  return () => document.removeEventListener("keydown", handleKey);
}, [selectedEntry, editing, showDeleteConfirm]);
```

- [ ] **Step 7: Reset edit state when modal closes**

Add a `useEffect` after the Escape handler:

```typescript
useEffect(() => {
  if (!selectedEntry) {
    setEditing(false);
    setShowDeleteConfirm(false);
  }
}, [selectedEntry]);
```

- [ ] **Step 8: Replace the modal header with edit/delete buttons**

Replace the modal header section (lines 763-788). The header should show Edit and Delete buttons in read-only mode, and Save/Cancel in edit mode:

```tsx
{
  /* Modal header */
}
<div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4 border-b border-white/[0.06]">
  {editing ? (
    <input
      type="text"
      value={editTitle}
      onChange={(e) => setEditTitle(e.target.value)}
      className={inputClass}
      required
    />
  ) : (
    <h2 className="font-display text-xl font-medium text-text leading-snug">
      {selectedEntry.title}
    </h2>
  )}
  <div className="flex items-center gap-1 flex-shrink-0">
    {!editing && (
      <>
        <button
          onClick={() => startEdit(selectedEntry)}
          aria-label="Edit entry"
          className="touch-target flex items-center justify-center w-8 h-8 rounded-lg text-text/40 hover:text-accent/70 hover:bg-accent/[0.08] transition-all duration-200"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </button>
        <button
          onClick={() => setShowDeleteConfirm(true)}
          aria-label="Delete entry"
          className="touch-target flex items-center justify-center w-8 h-8 rounded-lg text-text/40 hover:text-red-400/70 hover:bg-red-400/[0.08] transition-all duration-200"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </>
    )}
    <button
      ref={modalCloseRef}
      onClick={() => setSelectedEntry(null)}
      aria-label="Close entry"
      className="touch-target flex items-center justify-center w-8 h-8 rounded-lg text-text/40 hover:text-text/70 hover:bg-white/[0.05] transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      <svg
        className="w-5 h-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </svg>
    </button>
  </div>
</div>;
```

- [ ] **Step 9: Replace the modal body with conditional edit/read view**

Replace the modal body section (lines 790-864). When `editing` is true, show editable fields; otherwise show the existing read-only view.

```tsx
{
  /* Modal body */
}
<div className="px-6 py-5 space-y-5">
  {editing ? (
    <>
      {/* Editable fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="edit-system" className={labelClass}>
            System
          </label>
          <div className="relative">
            <select
              id="edit-system"
              value={editSystem}
              onChange={(e) => setEditSystem(e.target.value)}
              className={selectClass}
            >
              {SYSTEMS.map((s) => (
                <option key={s} value={s}>
                  {formatLabel(s)}
                </option>
              ))}
            </select>
            <svg
              className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text/30 pointer-events-none"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </div>
        </div>
        <div>
          <label htmlFor="edit-type" className={labelClass}>
            Entry type
          </label>
          <div className="relative">
            <select
              id="edit-type"
              value={editType}
              onChange={(e) => setEditType(e.target.value)}
              className={selectClass}
            >
              {ENTRY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {formatLabel(t)}
                </option>
              ))}
            </select>
            <svg
              className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text/30 pointer-events-none"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </div>
        </div>
      </div>

      <div>
        <label htmlFor="edit-content" className={labelClass}>
          Your thoughts
        </label>
        <textarea
          id="edit-content"
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          rows={8}
          className={`${inputClass} resize-y`}
          required
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="edit-mood" className={labelClass}>
            Mood score — {editMood}/10{" "}
            <span aria-label={moodLabel(editMood)}>{moodEmoji(editMood)}</span>
          </label>
          <input
            id="edit-mood"
            type="range"
            min={1}
            max={10}
            value={editMood}
            onChange={(e) => setEditMood(Number(e.target.value))}
            className="w-full accent-primary mt-2 h-1.5"
          />
        </div>
        <div>
          <label htmlFor="edit-tags" className={labelClass}>
            Tags{" "}
            <span className="text-text/25 font-normal">(comma-separated)</span>
          </label>
          <input
            id="edit-tags"
            type="text"
            value={editTags}
            onChange={(e) => setEditTags(e.target.value)}
            className={inputClass}
          />
        </div>
      </div>

      {/* Save / Cancel buttons */}
      <div className="flex items-center gap-3 pt-1">
        <button
          type="button"
          onClick={handleSaveEdit}
          disabled={saving}
          className="touch-target inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium text-sm rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
        >
          {saving ? (
            <>
              <span
                className="w-4 h-4 border-2 border-bg/30 border-t-bg rounded-full animate-spin"
                aria-hidden="true"
              />
              Saving…
            </>
          ) : (
            "Save Changes"
          )}
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          className="touch-target px-5 py-2.5 border border-white/[0.08] text-text/40 font-body text-sm rounded-xl hover:bg-white/[0.03] hover:text-text/60 hover:border-white/[0.12] transition-all duration-300"
        >
          Cancel
        </button>
      </div>
    </>
  ) : (
    <>
      {/* Read-only view (existing content) */}
      {/* Metadata badges */}
      <div className="flex flex-wrap gap-2">
        {(() => {
          const colors = getSystemColors(selectedEntry.system);
          return (
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-body font-medium ${colors.badge}`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${colors.dot}`}
                aria-hidden="true"
              />
              {formatLabel(selectedEntry.system)}
            </span>
          );
        })()}
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-body font-medium bg-white/[0.05] text-text/40">
          {formatLabel(selectedEntry.entry_type)}
        </span>
        {selectedEntry.mood_score !== null && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-body font-medium bg-accent/[0.08] text-accent/70">
            <span aria-label={`Mood: ${moodLabel(selectedEntry.mood_score)}`}>
              {moodEmoji(selectedEntry.mood_score)}
            </span>
            <span>
              {selectedEntry.mood_score}/10 —{" "}
              {moodLabel(selectedEntry.mood_score)}
            </span>
          </span>
        )}
      </div>

      {/* Entry content */}
      <p className="text-sm font-body text-text/60 leading-[1.8] whitespace-pre-wrap">
        {selectedEntry.content}
      </p>

      {/* Tags */}
      {selectedEntry.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedEntry.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.65rem] font-body font-medium bg-white/[0.03] border border-white/[0.06] text-text/30"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Timestamp */}
      <time
        dateTime={selectedEntry.created_at}
        className="block text-xs font-body text-text/20"
      >
        {new Date(selectedEntry.created_at).toLocaleString(undefined, {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </time>
    </>
  )}

  {/* Delete confirmation dialog */}
  {showDeleteConfirm && (
    <div className="card-surface border border-red-400/20 p-4 space-y-3">
      <p className="text-sm font-body text-text/60">
        Delete this journal entry? This cannot be undone.
      </p>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="touch-target inline-flex items-center gap-2 px-5 py-2 bg-red-500/20 border border-red-400/30 text-red-400 font-body text-sm rounded-xl hover:bg-red-500/30 transition-all duration-200 disabled:opacity-50"
        >
          {deleting ? "Deleting…" : "Delete"}
        </button>
        <button
          type="button"
          onClick={() => setShowDeleteConfirm(false)}
          className="touch-target px-5 py-2 border border-white/[0.08] text-text/40 font-body text-sm rounded-xl hover:bg-white/[0.03] transition-all duration-200"
        >
          Cancel
        </button>
      </div>
    </div>
  )}
</div>;
```

- [ ] **Step 10: Verify the page renders with edit/delete working**

Run: `cd alchymine/web && npm run dev` (manually test on `/journal`: open an entry, click Edit, modify fields, save; open another, delete it)

- [ ] **Step 11: Commit**

```bash
git add alchymine/web/src/app/journal/page.tsx
git commit -m "feat(journal): add inline edit and delete with confirmation dialog"
```

---

## Chunk 3: Template Library

### Task 5: Create journalTemplates.ts with all pillar templates

**Files:**

- Create: `alchymine/web/src/lib/journalTemplates.ts`

- [ ] **Step 1: Create the template definitions file**

Create `alchymine/web/src/lib/journalTemplates.ts`:

```typescript
export type AlchymineSystem =
  | "intelligence"
  | "healing"
  | "wealth"
  | "creative"
  | "perspective";

export interface JournalTemplate {
  id: string;
  system: AlchymineSystem;
  entryType: string;
  title: string;
  promptQuestions: string[];
  tags: string[];
  label: string;
  description: string;
}

export const JOURNAL_TEMPLATES: JournalTemplate[] = [
  // ── Perspective ────────────────────────────────────────────────────
  {
    id: "perspective-decision-matrix",
    system: "perspective",
    entryType: "decision",
    title: "Decision Matrix Reflection",
    promptQuestions: [
      "What decision did you evaluate using the weighted matrix?",
      "Which option ranked highest, and does that feel right?",
      "What criteria shifted the outcome the most?",
      "How confident are you in this decision now?",
    ],
    tags: ["decision", "framework", "perspective"],
    label: "Decision Matrix Reflection",
    description: "Reflect on a decision you analyzed with the weighted matrix.",
  },
  {
    id: "perspective-six-hats",
    system: "perspective",
    entryType: "reflection",
    title: "Six Thinking Hats Synthesis",
    promptQuestions: [
      "Which thinking hat was easiest for you to wear? Why?",
      "Which hat challenged you the most?",
      "What emerged when you synthesized all six perspectives?",
      "What action will you take based on this analysis?",
    ],
    tags: ["six-hats", "thinking", "perspective"],
    label: "Six Thinking Hats Synthesis",
    description:
      "Synthesize insights from exploring a problem through six perspectives.",
  },
  {
    id: "perspective-bias-discovery",
    system: "perspective",
    entryType: "insight",
    title: "Cognitive Bias Discovery",
    promptQuestions: [
      "What cognitive bias did the analysis detect in your reasoning?",
      "Can you recall a past decision where this bias may have influenced you?",
      "How does the suggested reframe change your perspective?",
      "What will you watch for going forward?",
    ],
    tags: ["bias", "awareness", "perspective"],
    label: "Cognitive Bias Discovery",
    description:
      "Explore a cognitive bias pattern discovered in your thinking.",
  },
  {
    id: "perspective-scenario-planning",
    system: "perspective",
    entryType: "decision",
    title: "Scenario Planning Narrative",
    promptQuestions: [
      "What decision or situation did you model scenarios for?",
      "What does the most likely scenario look like for you?",
      "Which risk variables matter most, and can you influence them?",
      "What early warning signs should you watch for?",
    ],
    tags: ["scenarios", "planning", "perspective"],
    label: "Scenario Planning Narrative",
    description: "Capture your scenario planning analysis and key takeaways.",
  },
  {
    id: "perspective-kegan-growth",
    system: "perspective",
    entryType: "assessment",
    title: "Kegan Growth Edge",
    promptQuestions: [
      "What developmental stage were you assessed at? Does it feel accurate?",
      "What growth edge resonates most with where you are right now?",
      "Can you recall a recent moment where you operated from this stage?",
      "Which growth practice will you commit to trying this week?",
    ],
    tags: ["kegan", "development", "growth"],
    label: "Kegan Growth Edge",
    description: "Reflect on your developmental stage and growth edges.",
  },

  // ── Wealth ─────────────────────────────────────────────────────────
  {
    id: "wealth-archetype-discovery",
    system: "wealth",
    entryType: "assessment",
    title: "Wealth Archetype Discovery",
    promptQuestions: [
      "What wealth archetype were you matched with? Does it resonate?",
      "What blind spot surprised you most about your archetype?",
      "How does your natural archetype align or conflict with your financial goals?",
      "Which recommended action will you take first, and why?",
    ],
    tags: ["archetype", "wealth", "identity"],
    label: "Archetype Discovery",
    description: "Reflect on your wealth archetype and its insights.",
  },
  {
    id: "wealth-lever-commitment",
    system: "wealth",
    entryType: "intention",
    title: "Wealth Lever Commitment",
    promptQuestions: [
      "Which wealth lever (Earn, Keep, Grow, Protect, Transfer) is your top priority right now?",
      "Why does this lever matter most at this point in your life?",
      "What tension exists between your current priority and where you want to be?",
      "What one action will you take this week to strengthen this lever?",
    ],
    tags: ["levers", "commitment", "wealth"],
    label: "Wealth Lever Commitment",
    description: "Set intentions around your prioritized wealth levers.",
  },
  {
    id: "wealth-90day-reflection",
    system: "wealth",
    entryType: "progress",
    title: "90-Day Phase Reflection",
    promptQuestions: [
      "Which phase of your 90-day plan did you just complete?",
      "What daily habits worked well? Which ones didn't stick?",
      "What unexpected obstacles did you encounter?",
      "What financial wins, however small, can you celebrate?",
    ],
    tags: ["90-day", "progress", "wealth"],
    label: "90-Day Phase Reflection",
    description: "Reflect on a completed phase of your wealth activation plan.",
  },
  {
    id: "wealth-debt-journey",
    system: "wealth",
    entryType: "progress",
    title: "Debt Payoff Journey",
    promptQuestions: [
      "How did you feel when you first saw your debt landscape visualized?",
      "Which payoff strategy did you choose, and what drove that decision?",
      "What spending patterns have you noticed since starting this journey?",
      "What milestone will you celebrate next?",
    ],
    tags: ["debt", "journey", "wealth"],
    label: "Debt Payoff Journey",
    description:
      "Track your emotional and practical journey through debt payoff.",
  },
  {
    id: "wealth-financial-patterns",
    system: "wealth",
    entryType: "insight",
    title: "Financial Pattern Awareness",
    promptQuestions: [
      "What financial pattern or money script have you become aware of?",
      "Where did this pattern originate — family, culture, past experience?",
      "How has this pattern served you? How has it held you back?",
      "What would a healthier relationship with this pattern look like?",
    ],
    tags: ["patterns", "awareness", "wealth"],
    label: "Financial Pattern Awareness",
    description: "Explore inherited financial patterns and money scripts.",
  },

  // ── Healing ────────────────────────────────────────────────────────
  {
    id: "healing-breathwork-log",
    system: "healing",
    entryType: "practice-log",
    title: "Breathwork Session Log",
    promptQuestions: [
      "Which breathwork pattern did you practice today (Box, 4-7-8, Coherence)?",
      "How long was your session? How did your state shift before vs. after?",
      "What physical sensations did you notice during the practice?",
      "What level of difficulty felt right? Are you ready to progress?",
    ],
    tags: ["breathwork", "practice", "healing"],
    label: "Breathwork Session Log",
    description: "Log and reflect on a breathwork practice session.",
  },
  {
    id: "healing-modality-experience",
    system: "healing",
    entryType: "practice-log",
    title: "Modality Experience",
    promptQuestions: [
      "Which healing modality did you try (somatic, contemplative, expressive, etc.)?",
      "What was your experience like — physically, emotionally, spiritually?",
      "What surprised you about this practice?",
      "Would you return to this modality? Why or why not?",
    ],
    tags: ["modality", "experience", "healing"],
    label: "Modality Experience",
    description: "Capture your experience with a healing modality.",
  },
  {
    id: "healing-assessment-reflection",
    system: "healing",
    entryType: "assessment",
    title: "Healing Assessment Reflection",
    promptQuestions: [
      "What did your healing assessment reveal about your current state?",
      "How does this compare to how you felt a month ago?",
      "What emerging edges do you notice in your healing work?",
      "What goals will you set for your next healing cycle?",
    ],
    tags: ["assessment", "reflection", "healing"],
    label: "Healing Assessment Reflection",
    description: "Reflect on your healing assessment results and progress.",
  },
  {
    id: "healing-practice-progress",
    system: "healing",
    entryType: "progress",
    title: "Practice Progress",
    promptQuestions: [
      "How many sessions have you completed this week/month?",
      "What cumulative changes have you noticed in your body, mood, or outlook?",
      "How has this healing practice integrated into your daily life?",
      "Has your affinity for any particular modality shifted over time?",
    ],
    tags: ["progress", "practice", "healing"],
    label: "Practice Progress",
    description: "Track your cumulative healing practice progress.",
  },
  {
    id: "healing-state-shift",
    system: "healing",
    entryType: "reflection",
    title: "State Shift Journal",
    promptQuestions: [
      "Describe your emotional or physical state before today's practice.",
      "What shifted during or immediately after the practice?",
      "What word or image captures the quality of this shift?",
      "What would you like to carry forward from this experience?",
    ],
    tags: ["state-shift", "awareness", "healing"],
    label: "State Shift Journal",
    description: "Document before/after state shifts from healing practices.",
  },

  // ── Intelligence ───────────────────────────────────────────────────
  {
    id: "intelligence-natal-chart",
    system: "intelligence",
    entryType: "assessment",
    title: "Natal Chart Resonance",
    promptQuestions: [
      "Look at your Sun, Moon, and Rising signs — which one feels most like you?",
      "Does your Moon sign description match your emotional inner life?",
      "How does your Rising sign compare to how others perceive you?",
      "Which planetary aspect stood out as particularly meaningful?",
    ],
    tags: ["astrology", "natal-chart", "identity"],
    label: "Natal Chart Resonance",
    description:
      "Reflect on how your astrological chart resonates with your experience.",
  },
  {
    id: "intelligence-life-path",
    system: "intelligence",
    entryType: "reflection",
    title: "Life Path Narrative",
    promptQuestions: [
      "What is your Life Path number? Does it describe your life trajectory?",
      "How does your Expression number compare to the talents you actually use?",
      "What deep yearnings does your Soul Urge number point to — are you honoring them?",
      "How does your Personal Year number relate to what's happening in your life right now?",
    ],
    tags: ["numerology", "life-path", "reflection"],
    label: "Life Path Narrative",
    description:
      "Explore your numerology profile and how it maps to your life.",
  },
  {
    id: "intelligence-personal-year",
    system: "intelligence",
    entryType: "reflection",
    title: "Personal Year Transition",
    promptQuestions: [
      "What Personal Year are you entering or currently in?",
      "What themes does this year's number suggest for your growth?",
      "How does this compare to what you experienced in your previous Personal Year?",
      "What intention will you set to align with this year's energy?",
    ],
    tags: ["numerology", "personal-year", "transition"],
    label: "Personal Year Transition",
    description: "Reflect on your current Personal Year and its lessons.",
  },
  {
    id: "intelligence-biorhythm",
    system: "intelligence",
    entryType: "practice-log",
    title: "Biorhythm Cycle Reflection",
    promptQuestions: [
      "Where are your physical, emotional, and intellectual cycles positioned right now?",
      "Does your current energy level match what the cycles predict?",
      "Have you noticed any patterns that correlate with high or low cycle periods?",
      "How will you plan your week based on these cycle positions?",
    ],
    tags: ["biorhythm", "cycles", "tracking"],
    label: "Biorhythm Cycle Reflection",
    description:
      "Track how your biorhythm cycles correlate with lived experience.",
  },

  // ── Creative ───────────────────────────────────────────────────────
  {
    id: "creative-style-fingerprint",
    system: "creative",
    entryType: "assessment",
    title: "Style Fingerprint Identity",
    promptQuestions: [
      "What did your Creative Style Fingerprint reveal as your dominant components?",
      "Does this description match how you experience your own creative process?",
      "What blind spots in your creative practice did the assessment uncover?",
      "Do you feel confident calling yourself 'creative'? What shifts when you do?",
    ],
    tags: ["fingerprint", "identity", "creative"],
    label: "Style Fingerprint Identity",
    description:
      "Explore your creative identity through your style fingerprint.",
  },
  {
    id: "creative-project-progress",
    system: "creative",
    entryType: "practice-log",
    title: "Project Progress Log",
    promptQuestions: [
      "Which creative project are you working on? What progress did you make today?",
      "What creative blocks did you encounter, and how did you work through them?",
      "What surprised you during the creative process?",
      "What will you focus on in your next session?",
    ],
    tags: ["project", "progress", "creative"],
    label: "Project Progress Log",
    description: "Track progress on a creative project.",
  },
  {
    id: "creative-block-breakthrough",
    system: "creative",
    entryType: "insight",
    title: "Creative Block Breakthrough",
    promptQuestions: [
      "What creative block were you facing? How long had it persisted?",
      "What finally broke through it — a technique, a change of environment, time?",
      "What did you learn about your creative process from this breakthrough?",
      "How will you approach similar blocks in the future?",
    ],
    tags: ["breakthrough", "blocks", "creative"],
    label: "Creative Block Breakthrough",
    description: "Document a creative block breakthrough and what you learned.",
  },
  {
    id: "creative-guilford-growth",
    system: "creative",
    entryType: "reflection",
    title: "Guilford Growth Area",
    promptQuestions: [
      "Which Guilford dimension (fluency, flexibility, originality, elaboration, sensitivity, redefinition) is your strongest?",
      "Which dimension feels most challenging? Why do you think that is?",
      "How do these thinking dimensions show up in your daily life beyond creative work?",
      "What one exercise could you try this week to strengthen your weakest dimension?",
    ],
    tags: ["guilford", "growth", "creative"],
    label: "Guilford Growth Area",
    description:
      "Reflect on your divergent thinking strengths and growth areas.",
  },
  {
    id: "creative-collaboration",
    system: "creative",
    entryType: "reflection",
    title: "Collaboration Reflection",
    promptQuestions: [
      "Who did you collaborate with, and what was the creative outcome?",
      "Where did your creative styles clash? Where did they complement each other?",
      "What synergies emerged that wouldn't have happened working alone?",
      "What did this collaboration teach you about your own creative process?",
    ],
    tags: ["collaboration", "teamwork", "creative"],
    label: "Collaboration Reflection",
    description: "Reflect on creative collaboration dynamics and discoveries.",
  },
];

/** Look up a template by its ID. Returns undefined if not found. */
export function getTemplateById(id: string): JournalTemplate | undefined {
  return JOURNAL_TEMPLATES.find((t) => t.id === id);
}

/** Get all templates for a given system. */
export function getTemplatesBySystem(
  system: AlchymineSystem,
): JournalTemplate[] {
  return JOURNAL_TEMPLATES.filter((t) => t.system === system);
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -5`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add alchymine/web/src/lib/journalTemplates.ts
git commit -m "feat(journal): add 24 cross-pillar journal templates"
```

---

### Task 6: Add Templates tab and ?template= query param to journal page

**Files:**

- Modify: `alchymine/web/src/app/journal/page.tsx`

- [ ] **Step 1: Add imports**

Add to the top of the file:

```typescript
import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  JOURNAL_TEMPLATES,
  getTemplateById,
  getTemplatesBySystem,
  type AlchymineSystem,
  type JournalTemplate,
} from "@/lib/journalTemplates";
```

**IMPORTANT — Next.js 15 Suspense requirement**: `useSearchParams()` requires a `<Suspense>` boundary in Next.js 15 App Router or the production build will fail. Wrap the default export:

Change the existing `export default function JournalPage()` to be a non-exported inner component, then add a wrapper as the default export:

```typescript
// Rename the existing component:
function JournalPageInner() {
  // ... all existing component code ...
}

// New default export with Suspense wrapper:
export default function JournalPage() {
  return (
    <Suspense fallback={null}>
      <JournalPageInner />
    </Suspense>
  );
}
```

- [ ] **Step 2: Add tab state and template param handling**

Inside `JournalPageInner`, after the existing state declarations (near line 136), add:

```typescript
// Tabs: "entries" | "templates"
const [activeTab, setActiveTab] = useState<"entries" | "templates">("entries");

const searchParams = useSearchParams();
const router = useRouter();
```

- [ ] **Step 3: Add useEffect to process ?template= param**

After the existing `useEffect` blocks, add:

```typescript
// Handle ?template= query param
useEffect(() => {
  const templateId = searchParams.get("template");
  if (!templateId) return;

  const template = getTemplateById(templateId);
  // Clear the query param
  router.replace("/journal", { scroll: false });

  if (template) {
    applyTemplate(template);
  } else {
    // Unknown template ID — just open blank create form
    setActiveTab("entries");
    setShowForm(true);
  }
}, [searchParams, router]);
```

- [ ] **Step 4: Add applyTemplate helper**

```typescript
const applyTemplate = (template: JournalTemplate) => {
  setFormTitle(template.title);
  setFormContent(template.promptQuestions.map((q) => `## ${q}\n\n`).join("\n"));
  setFormSystem(template.system);
  setFormType(template.entryType);
  setFormTags(template.tags.join(", "));
  setFormMood(5);
  setActiveTab("entries");
  setShowForm(true);
};
```

- [ ] **Step 5: Add tab switcher UI**

After the horizontal rule (`<hr className="rule-gold mb-8" />` at line 287), before the stats bar, add:

```tsx
{
  /* ── Tab switcher ──────────────────────────────────────── */
}
<MotionReveal delay={0.08}>
  <div className="flex gap-1 mb-8 p-1 bg-white/[0.02] border border-white/[0.06] rounded-xl w-fit">
    <button
      onClick={() => setActiveTab("entries")}
      className={`px-4 py-2 text-sm font-body rounded-lg transition-all duration-200 ${
        activeTab === "entries"
          ? "bg-white/[0.08] text-text font-medium"
          : "text-text/40 hover:text-text/60 hover:bg-white/[0.03]"
      }`}
    >
      Entries
    </button>
    <button
      onClick={() => setActiveTab("templates")}
      className={`px-4 py-2 text-sm font-body rounded-lg transition-all duration-200 ${
        activeTab === "templates"
          ? "bg-white/[0.08] text-text font-medium"
          : "text-text/40 hover:text-text/60 hover:bg-white/[0.03]"
      }`}
    >
      Templates
    </button>
  </div>
</MotionReveal>;
```

- [ ] **Step 6: Wrap existing entries content in activeTab === "entries" conditional**

Wrap the stats bar, filters, form, error banner, loading, empty state, and entries list sections in:

```tsx
{
  activeTab === "entries" && (
    <>{/* ... existing stats, filters, form, entries ... */}</>
  );
}
```

- [ ] **Step 7: Add Templates tab content**

After the entries conditional, add:

```tsx
{
  activeTab === "templates" && (
    <MotionReveal delay={0.1}>
      <div className="space-y-8">
        {(
          [
            "perspective",
            "wealth",
            "healing",
            "intelligence",
            "creative",
          ] as AlchymineSystem[]
        ).map((system) => {
          const templates = getTemplatesBySystem(system);
          if (templates.length === 0) return null;
          const colors = getSystemColors(system);
          return (
            <section key={system}>
              <h3
                className={`font-display text-lg font-medium ${colors.text} mb-4 flex items-center gap-2`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${colors.dot}`}
                  aria-hidden="true"
                />
                {formatLabel(system)}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {templates.map((tmpl) => (
                  <button
                    key={tmpl.id}
                    onClick={() => applyTemplate(tmpl)}
                    className="group text-left card-surface px-5 py-4 hover:-translate-y-0.5 transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  >
                    <h4 className="font-display text-sm font-medium text-text group-hover:text-text/90 mb-1">
                      {tmpl.label}
                    </h4>
                    <p className="text-xs font-body text-text/35 leading-relaxed">
                      {tmpl.description}
                    </p>
                    <div className="flex items-center gap-2 mt-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.6rem] font-body font-medium bg-white/[0.04] text-text/30">
                        {formatLabel(tmpl.entryType)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </MotionReveal>
  );
}
```

- [ ] **Step 8: Verify templates tab renders and template selection works**

Run: `cd alchymine/web && npm run dev` (check `/journal` — Templates tab should show 24 templates grouped by pillar; clicking one should switch to Entries tab with pre-populated form)

- [ ] **Step 9: Verify ?template= param works**

Navigate to `/journal?template=healing-breathwork-log` — should open create form with breathwork template pre-populated.
Navigate to `/journal?template=nonexistent` — should open blank create form.

- [ ] **Step 10: Commit**

```bash
git add alchymine/web/src/app/journal/page.tsx
git commit -m "feat(journal): add Templates tab and ?template= query param support"
```

---

## Chunk 4: JournalCTA Component + System Page Integration

### Task 7: Create JournalCTA component

**Files:**

- Create: `alchymine/web/src/components/shared/JournalCTA.tsx`

- [ ] **Step 1: Create the component**

Create `alchymine/web/src/components/shared/JournalCTA.tsx`:

```tsx
"use client";

import Link from "next/link";

interface JournalCTAProps {
  templateId: string;
  /** Optional custom heading text */
  heading?: string;
  /** Optional custom description text */
  description?: string;
}

export default function JournalCTA({
  templateId,
  heading = "Reflect on this in your journal",
  description = "Capture your thoughts while they're fresh.",
}: JournalCTAProps) {
  return (
    <div className="card-surface border border-primary/[0.12] px-6 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h3 className="font-display text-base font-medium text-text mb-1">
          {heading}
        </h3>
        <p className="text-sm font-body text-text/35">{description}</p>
      </div>
      <Link
        href={`/journal?template=${templateId}`}
        className="touch-target inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium text-sm rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98] self-start sm:self-auto whitespace-nowrap"
      >
        <svg
          className="w-4 h-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
        Start Journal Entry
      </Link>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd alchymine/web && npx tsc --noEmit --pretty 2>&1 | head -5`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add alchymine/web/src/components/shared/JournalCTA.tsx
git commit -m "feat(journal): add reusable JournalCTA component"
```

---

### Task 8: Add JournalCTA to all five system pages

**Files:**

- Modify: `alchymine/web/src/app/perspective/page.tsx`
- Modify: `alchymine/web/src/app/wealth/page.tsx`
- Modify: `alchymine/web/src/app/healing/page.tsx`
- Modify: `alchymine/web/src/app/intelligence/page.tsx`
- Modify: `alchymine/web/src/app/creative/page.tsx`

For each page, the pattern is the same:

1. Add import at top: `import JournalCTA from "@/components/shared/JournalCTA";`
2. Add `<MotionReveal>` wrapped `<JournalCTA>` at the identified insertion point

- [ ] **Step 1: Add JournalCTA to Perspective page**

In `alchymine/web/src/app/perspective/page.tsx`:

- Add import: `import JournalCTA from "@/components/shared/JournalCTA";`
- After the Scenario Planning section (around line 497), before the Connections section, insert:

```tsx
<MotionReveal delay={0.05}>
  <div className="mb-12">
    <JournalCTA
      templateId="perspective-scenario-planning"
      heading="Reflect on your scenario analysis"
      description="Journal about the scenarios you modeled and what early warning signs to watch for."
    />
  </div>
</MotionReveal>
```

- [ ] **Step 2: Add JournalCTA to Wealth page**

In `alchymine/web/src/app/wealth/page.tsx`:

- Add import: `import JournalCTA from "@/components/shared/JournalCTA";`
- After the 90-Day Activation Plan section (around line 1102), before the Methodology Panel, insert:

```tsx
<MotionReveal delay={0.05}>
  <div className="mb-12">
    <JournalCTA
      templateId="wealth-archetype-discovery"
      heading="Reflect on your wealth profile"
      description="Journal about your archetype, wealth levers, and what actions you'll take."
    />
  </div>
</MotionReveal>
```

- [ ] **Step 3: Add JournalCTA to Healing page**

In `alchymine/web/src/app/healing/page.tsx`:

- Add import: `import JournalCTA from "@/components/shared/JournalCTA";`
- After the Matched Modalities section (around line 725), before the Breathwork Timer, insert:

```tsx
<MotionReveal>
  <div className="mb-12">
    <JournalCTA
      templateId="healing-modality-experience"
      heading="Reflect on your healing journey"
      description="Journal about which modality draws you in and what your first session goal is."
    />
  </div>
</MotionReveal>
```

- [ ] **Step 4: Add JournalCTA to Intelligence page**

In `alchymine/web/src/app/intelligence/page.tsx`:

- Add import: `import JournalCTA from "@/components/shared/JournalCTA";`
- After the Astrology results section (around line 306), before the Numerology Education section, insert:

```tsx
<MotionReveal delay={0.1}>
  <div className="mb-12">
    <JournalCTA
      templateId="intelligence-natal-chart"
      heading="Reflect on your personal blueprint"
      description="Journal about which numbers and signs resonate with your lived experience."
    />
  </div>
</MotionReveal>
```

- [ ] **Step 5: Add JournalCTA to Creative page**

In `alchymine/web/src/app/creative/page.tsx`:

- Add import: `import JournalCTA from "@/components/shared/JournalCTA";`
- After the Projects & Collaboration section (around line 484), before the Connections section, insert:

```tsx
<MotionReveal delay={0.05}>
  <div className="mb-12">
    <JournalCTA
      templateId="creative-style-fingerprint"
      heading="Reflect on your creative identity"
      description="Journal about your style fingerprint and what creative project you'll start."
    />
  </div>
</MotionReveal>
```

- [ ] **Step 6: Verify all pages render without errors**

Run: `cd alchymine/web && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 7: Commit**

```bash
git add alchymine/web/src/app/perspective/page.tsx alchymine/web/src/app/wealth/page.tsx alchymine/web/src/app/healing/page.tsx alchymine/web/src/app/intelligence/page.tsx alchymine/web/src/app/creative/page.tsx
git commit -m "feat(journal): add post-analysis JournalCTA to all five system pages"
```

---

## Chunk 5: Final Verification

### Task 9: Full build and integration check

**Files:** None (verification only)

- [ ] **Step 1: Run TypeScript type check**

Run: `cd alchymine/web && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 2: Run Next.js build**

Run: `cd alchymine/web && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run linter**

Run: `cd alchymine/web && npm run lint`
Expected: No errors

- [ ] **Step 4: Run backend tests**

Run: `D:/Python/Python311/python.exe -m pytest tests/api/test_journal.py -v`
Expected: All tests pass

- [ ] **Step 5: Run ruff checks**

Run: `ruff check alchymine/api/routers/journal.py && ruff format --check alchymine/api/routers/journal.py`
Expected: No errors

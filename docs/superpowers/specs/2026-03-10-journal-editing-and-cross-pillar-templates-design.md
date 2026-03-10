# Journal Editing & Cross-Pillar Templates Design

**Date**: 2026-03-10
**Status**: Approved

## Problem

The journal system has full backend CRUD but the frontend only supports creation and viewing. Users cannot edit or delete entries. Additionally, journaling is siloed — no connection between system analyses and journal reflection, missing opportunities across all five pillars.

## Solution

1. Add edit/delete UI to the journal page
2. Create a template library with guided prompts for all five pillars
3. Add post-analysis CTAs on system pages to drive journal engagement
4. Expand entry types to support new use cases

## Design Decisions

- **Edit approach**: Inline edit — entry detail modal transforms into editable form in-place
- **Delete approach**: Confirmation dialog before permanent deletion
- **Templates**: Frontend-only configuration (no new API endpoints)
- **CTAs**: Reusable component with URL-param-based template loading
- **Scope**: Full build across all pillars in one pass
- **Backend tweak**: Extend `JournalEntryUpdate` with optional `system` and `entry_type` fields (trivial addition)

---

## Section 1: Journal Edit/Delete UI

### Edit Flow

- Entry detail modal gets an "Edit" button in the header
- Clicking transforms modal content into editable fields: title input, content textarea, system/type selectors, mood slider, tags input — all pre-populated
- "Save" and "Cancel" buttons replace the Edit button
- Save calls `updateJournalEntry()` → PUT `/api/v1/journal/{id}`, refreshes entry in list
- Cancel reverts to read-only view

### Delete Flow

- "Delete" button (trash icon) in entry detail header, next to Edit
- Confirmation dialog: "Delete this journal entry? This cannot be undone."
- Confirm calls `deleteJournalEntry()` → DELETE `/api/v1/journal/{id}`, closes modal, removes from list

### API Client Additions (`api.ts`)

```typescript
updateJournalEntry(entryId: string, data: Partial<JournalEntry>): Promise<JournalEntry>
deleteJournalEntry(entryId: string): Promise<void>
```

**Note**: `deleteJournalEntry` must handle HTTP 204 (no body) — skip `res.json()` when `res.status === 204`.

### Backend Tweak

Extend `JournalEntryUpdate` in `alchymine/api/routers/journal.py` with optional `system` and `entry_type` fields so the edit form can update them. Add both to the `allowed_fields` set in `update_journal_entry` in `alchymine/db/repository.py`.

### Escape Key Handling

When the edit form is active inside the modal, Escape should trigger "Cancel" (revert to read-only) rather than closing the modal. Only Escape from read-only view closes the modal.

---

## Section 2: New Entry Types

**Current**: reflection, insight, gratitude, intention, freeform

**New**:

- `practice-log` — Recurring tracking (Healing sessions, Creative project work)
- `decision` — Perspective framework outcomes (decision matrices, pros/cons, scenario planning)
- `assessment` — Post-analysis reflections after system assessments
- `progress` — Goal tracking and milestone entries (Wealth plan phases, healing progression)

**Backend**: No migration needed — `entry_type` is a free-form `String(50)`, not an enum. Stats automatically pick up new types.

**Frontend**: The `ENTRY_TYPES` array in `journal/page.tsx` must be extended with all four new values so they appear in the filter dropdown and create form type selector.

---

## Section 3: Template Library

### Template Interface

```typescript
interface JournalTemplate {
  id: string;
  system: string; // intelligence | healing | wealth | creative | perspective
  entryType: string; // any valid entry type
  title: string; // Pre-filled title
  promptQuestions: string[]; // Guided questions placed in content area
  tags: string[]; // Pre-filled tags
  label: string; // Display name in template library
  description: string; // Short description of when to use
}
```

### Templates Per Pillar

**Perspective** (~5):

- Decision Matrix Reflection (decision)
- Six Thinking Hats Synthesis (reflection)
- Cognitive Bias Discovery (insight)
- Scenario Planning Narrative (decision)
- Kegan Growth Edge (assessment)

**Wealth** (~5):

- Archetype Discovery (assessment)
- Wealth Lever Commitment (intention)
- 90-Day Phase Reflection (progress)
- Debt Payoff Journey (progress)
- Financial Pattern Awareness (insight)

**Healing** (~5):

- Breathwork Session Log (practice-log)
- Modality Experience (practice-log)
- Healing Assessment Reflection (assessment)
- Practice Progress (progress)
- State Shift Journal (reflection)

**Intelligence** (~4):

- Natal Chart Resonance (assessment)
- Life Path Narrative (reflection)
- Personal Year Transition (reflection)
- Biorhythm Cycle Reflection (practice-log)

**Creative** (~5):

- Style Fingerprint Identity (assessment)
- Project Progress Log (practice-log)
- Creative Block Breakthrough (insight)
- Guilford Growth Area (reflection)
- Collaboration Reflection (reflection)

### UI — Tab State Machine

The journal page has two tabs: **"Entries"** (default) and **"Templates"**.

**Entries tab** (active by default):

- Shows: stats bar, filter row, entry list (or empty state), "New Entry" button
- "New Entry" opens the create form inline (existing behavior)

**Templates tab**:

- Shows: templates grouped by pillar with system icons and descriptions
- Hides: stats bar, filter row, entry list
- Selecting a template switches to Entries tab and opens the create form pre-populated with the template's title, system, entry type, tags, and prompt questions as content scaffolding

**URL param `?template={id}`**:

- Auto-switches to Entries tab
- Opens create form pre-populated from the matching template
- If template ID is not found, opens a blank create form with no pre-population and no error shown
- Query param is consumed and cleared from the URL after processing

---

## Section 4: Post-Analysis CTAs

### Component

Reusable `<JournalCTA templateId={id} />` component rendering:

```
Reflect on this in your journal
"Capture your thoughts while they're fresh"
[Start Journal Entry →]
```

### Navigation

Links to `/journal?template={templateId}` — journal page reads query param, finds matching template, opens pre-populated create form.

### Placement

| System Page  | CTA appears after                       | Template triggered             |
| ------------ | --------------------------------------- | ------------------------------ |
| Perspective  | Framework analysis results              | Matching framework template    |
| Wealth       | Archetype / Lever / Plan results        | Matching wealth template       |
| Healing      | Modality recommendations / Assessment   | Matching healing template      |
| Intelligence | Natal chart / Numerology profile        | Matching intelligence template |
| Creative     | Style fingerprint / Project suggestions | Matching creative template     |

---

## Files to Modify

### New Files

- `alchymine/web/src/lib/journalTemplates.ts` — Template definitions
- `alchymine/web/src/components/shared/JournalCTA.tsx` — Reusable CTA component

### Modified Files

- `alchymine/web/src/lib/api.ts` — Add updateJournalEntry, deleteJournalEntry
- `alchymine/web/src/app/journal/page.tsx` — Edit/delete UI, template tab, query param handling
- `alchymine/web/src/app/perspective/page.tsx` — Add JournalCTA
- `alchymine/web/src/app/wealth/page.tsx` — Add JournalCTA
- `alchymine/web/src/app/healing/page.tsx` — Add JournalCTA
- `alchymine/web/src/app/intelligence/page.tsx` — Add JournalCTA
- `alchymine/web/src/app/creative/page.tsx` — Add JournalCTA

### Minimal Backend Changes

- PUT and DELETE endpoints already exist and are tested
- entry_type is free-form string, accepts new types automatically
- Stats endpoint auto-aggregates new types
- **Only change**: Add optional `system` and `entry_type` fields to `JournalEntryUpdate` Pydantic model and `allowed_fields` in repository

### Modified Files (Backend)

- `alchymine/api/routers/journal.py` — Add `system`, `entry_type` to `JournalEntryUpdate`
- `alchymine/db/repository.py` — Add `system`, `entry_type` to `allowed_fields` in `update_journal_entry`

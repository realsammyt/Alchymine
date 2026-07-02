# HANDOFF — Alchymine

> **Living document.** Single source of truth for where this work stands and
> what's next. Any agent starting fresh reads this first, then updates it before
> ending. If anything here disagrees with reality, reality wins — fix the doc.

**Last updated:** 2026-07-02 by Claude (with Tyler)
**Active branch:** `main` (fixes branch to be created: see Next action)
**Driving plan / refs:** project `CLAUDE.md` (commands, CI protocol), `Alchymine PRD v7 FiveSystem.docx`

---

## 1. Read-this-first orientation (for a fresh agent)

1. Read this whole file.
2. Read the project `CLAUDE.md` — the pre-merge checklist and CI monitoring protocol are mandatory.
3. Verify ground truth live (`git status`, run the gates below) before trusting any number here.
4. Check the **Status** table for what's done and what's next.
5. Check **Open questions** — don't guess on these; they're the user's to call.
6. When you finish a unit of work, update Sections 3, 5, and 7.

**Ground truth (re-verify; never trust a stale number):**

| Thing | Value | How to check |
| ----- | ----- | ------------ |
| Backend tests | 2281 passed, 1 skipped | `$env:CELERY_ALWAYS_EAGER='true'; .venv\Scripts\python.exe -m pytest tests/ -q` |
| Frontend tests | 333 passed (40 suites) | `cd alchymine/web; npm test` |
| mypy / ruff | clean | `.venv\Scripts\python.exe -m mypy alchymine/` / `-m ruff check alchymine/` |
| CI | green on main | `gh run list -R realsammyt/Alchymine --limit 3` |

---

## 2. What this effort is

Alchymine is an AI-powered personal transformation OS (5 deterministic engine
systems + FastAPI + Celery + Next.js). Current effort: post-review hardening —
a 2026-07-01 full-project review fixed 7 bugs (merged as PR #206); three
design-level findings remain and are the active work.

---

## 3. Status

Statuses: `Not started` · `In progress` · `Blocked` · `Done`.

| # | Item | Status | Updated | Note |
| - | ---- | ------ | ------- | ---- |
| 1 | Full-project review + 7 bug fixes (PR #206) | Done | 2026-07-02 | Squash-merged to main, all 10 CI checks green |
| 2 | Finding 1: birth time local→UTC conversion | In progress | 2026-07-02 | Implemented on `fix/review-findings` (engine zoneinfo conversion, intake form field, DB column, migration 0014); gates running |
| 3 | Finding 2: wealth MCP vs "no financial data to LLM" rule | In progress | 2026-07-02 | Promise rescoped everywhere + tool disclosures; gates running |
| 4 | Finding 3: orphaned reports readable by any authed user | In progress | 2026-07-02 | `created_by_sub` column (migration 0015) + ownership helper on all report reads; gates running |

**Next action:** full gates → commit → PR → CI green → merge → mark rows Done.

---

## 4. Decisions locked (don't relitigate without the user)

1. Squash-merge is the PR merge convention — 2026-07-02 / observed repo history.
2. Local dev uses `.venv` (Python 3.11 via uv); system Python 3.10 and global ruff give false results vs CI — 2026-07-01.
3. Orphan-report fallback (`user_id=None` on FK miss) stays; access control fix must track the creator instead of denying creation — 2026-07-01 review.

---

## 5. Open questions owned by the user (get answers before acting)

_None currently._

---

## 6. Key facts a fresh agent will want (so you don't re-discover them)

- Repo lives at `I:\GithubI\Alchymine` (not under `I:\GithubI\claude`).
- Run all Python tooling via `.venv\Scripts\python.exe -m ...`.
- A PR whose `mergeStateStatus` is `DIRTY` (merge conflict) silently gets **no CI run at all** — merge main in first, or CI appears "stuck".
- Route registration order matters in FastAPI: literal paths (e.g. `/reports/diagnose`) must be registered before parameterized siblings.
- Middleware: `add_middleware` is LIFO — last added is outermost. CORS must stay outside RateLimit.
- Alembic migration head as of 2026-07-02: check `.venv\Scripts\python.exe -m alembic heads` before adding migrations; coordinate revision ids when parallel agents both add one.
- `ruff format` runs in CI — always `ruff format alchymine/` before committing.

---

## 7. Activity log (newest first — append, don't overwrite)

- **2026-07-02** — Merged PR #206 (7 review fixes + CI fixes). Created this handoff. Next: 3 remaining findings via agent team.
- **2026-07-01** — Full-project review (4 parallel review agents). Fixed: gemini mypy, tsc test error, session poisoning in workers, /reports/diagnose shadowing, CORS/rate-limit order, feedback email HTML injection, debt waterfall math, chat history clobbering. All gates + CI green.

---

## 8. Update protocol (keep this doc honest)

Update this file at the end of any session that touched the work, and before
handing off or clearing context. Minimum: Status table (status + date + note),
one Activity-log line, move answered items from Open questions to Decisions, and
the `Last updated` line. Keep it tight — state, not narrative.

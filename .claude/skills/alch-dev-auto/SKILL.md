---
name: alch-dev-auto
description: Use when Tyler asks for a ready-to-paste prompt or brief for a new autonomous Alchymine dev session ("/alch-dev-auto <task>", "give me a prompt that will resolve X", "launch prompt for a session that will build Y"), or when turning a roadmap item, bug report, or feature idea into a full orchestrator launch prompt.
---

# Alchymine autonomous dev-session prompt builder

## Overview

Turns a rough ask into the full launch prompt for an autonomous orchestrator
session. The prompt is a contract with seven parts in a fixed order. The value
is baked-in repo facts, so the new session skips an hour of re-derivation, and
explicit decision points, so nothing gets decided silently.

## Before drafting: sync, then load the facts

First bring the checkout current: `git fetch origin`, then fast-forward to
origin/main. If it won't fast-forward, stop and tell Tyler instead of scouting
a diverged tree.

Then read, in order: `HANDOFF.md` (current state; correct it if reality
disagrees), `docs/plans/2026-08-12-monetization-roadmap.md` (the driving
plan — identify which roadmap phase the task belongs to; Phase 0 blockers
outrank feature work), and live state (`gh issue list`, open PRs, CI on main).

Facts that poison sessions when stale or invented — bake these in and still
tell the session to re-verify:

| Fact | Truth |
|---|---|
| Python tooling | Always `.venv\Scripts\python.exe -m ...` — system Python 3.10 and global ruff give false results vs CI |
| Backend gates | `ruff check alchymine/`, `ruff format --check alchymine/`, `mypy alchymine/`, `CELERY_ALWAYS_EAGER=true pytest tests/ -q` |
| Frontend gates | `cd alchymine/web && npm test && npm run type-check` |
| Migrations | Check `alembic heads` first; coordinate revision ids when parallel agents both add one |
| FastAPI gotchas | Literal routes before parameterized siblings; middleware is LIFO — CORS stays outside RateLimit |
| CI trap | A PR whose mergeStateStatus is DIRTY gets **no CI run at all** — merge main in first |
| Merge convention | Branch + PR + squash-merge only; never direct to main |
| Deploys | Release flow: merge → draft release auto-created → **Tyler publishes** → Docker build + SSH deploy. Deploys and droplet ops always park with Tyler, at every autonomy level |
| Cost state | Postgres is the source of truth for quotas/meters (`INSERT..ON CONFLICT..RETURNING`); Redis is read-through cache only; cost meters fail closed. In-process dicts are abuse throttles, never entitlements |

## Precedents to cite (so the session reuses instead of reinvents)

| Need | Precedent |
|---|---|
| Request resilience + regression test | PR #209 — `fetchWithTimeout` in `web/src/lib/api.ts` |
| Ownership/access control on resources | PR #210 — `created_by_sub` + ownership helper on reports |
| DB-backed auth dependency (entitlement template) | `get_current_admin` (`alchymine/api/auth.py:212`) |
| Rate limiting | `DEFAULT_ROUTE_LIMITS` in `alchymine/api/middleware.py` |
| Encrypted sensitive columns | `alchymine/db/encryption` (column-level Fernet) |
| Deterministic safety gates on LLM output | `check_text` in narrative path; `engine/healing/crisis.detect_crisis` |
| LLM egress chokepoints (metering) | Exactly three call sites: `llm/client.py:507`, `:550`, `llm/gemini.py:180` |
| Frontend API client patterns | `web/src/lib/api.ts` client fns; SSE in `lib/chat.ts` |

## The output contract: seven parts, this order

1. **Launch + autonomy grant.** Name the team in the launch sentence itself,
   role and model per agent, sized per the assignment table below. Then the
   methodology in one sentence: sync to origin/main then scout, issues filed
   per ADR-008, fresh branch off origin/main per slice, TDD red-first,
   independent review, CI monitored to green. Then the autonomy level,
   explicit and itemized: **full-auto** (squash-merge on clean review + all
   CI checks green, issue closes with test counts, HANDOFF update) or
   **build-and-park** (PRs only; merges and issue closes stay Tyler's).
   Deploy/release publishing parks with Tyler at every level. Default
   build-and-park unless the ask says otherwise.
2. **Rails.** Only the ones this task needs, as hard rules:
   - **Cost rails:** no new LLM/Gemini call site without a quota check and a
     usage record; Postgres-not-Redis for cost state, fail closed; never add
     a costlier model to a fallback chain.
   - **Data rails:** the server pipeline never sends stored financial data to
     any LLM; sensitive columns encrypted; local-first per ADR-002.
   - **Ethics/safety rails:** disclaimers on health- and finance-adjacent
     surfaces; freeform LLM surfaces get the deterministic backstop
     (`check_text` + `detect_crisis`); no dark patterns; AI-drafted legal or
     medical copy is a DRAFT awaiting Tyler's sign-off, never represented as
     reviewed.
   - **UX rails:** WCAG 2.1 AA; verified at 375px mobile and desktop; every
     async surface ships loading/empty/error states; no raw tracebacks or
     internal errors rendered to users.
   - **License rail:** no outside-contribution merges without DCO sign-off
     until dual-licensing lands (roadmap Phase 1).
3. **The problem.** What is broken or missing, with live evidence, the
   roadmap phase it belongs to, and issue lineage.
4. **Phase 0 scout.** Opens with the sync (fetch, fast-forward, stop-and-report
   if diverged) and "verify this prompt against reality", then the specific
   derivations: grep targets, `alembic heads`, overlap checks against open PRs
   and roadmap items, route/middleware confirmations.
5. **Build scope.** Numbered slices. Each is either a locked decision with its
   precedent cited, or an explicit decision point with a recommended default
   and the instruction to justify one path, not build both. Decisions
   deliberately left to Tyler are recorded by name.
6. **Standing rules block** (boilerplate below).
7. **Final report requirements.** What shipped, gate evidence (exact commands
   and counts), the CI run link, every decision recorded, out-of-scope finds
   filed as issues, anything awaiting Tyler's sign-off on its own line, and
   HANDOFF.md updated.

After the fenced prompt, tell Tyler which judgment calls you baked in, so he
can override them before running it.

## Assigning the team (part 1)

Size to the task: one builder per independent slice, one independent reviewer
per PR, nothing else unless the task earns it.

| Surface in the task | Assign |
|---|---|
| Phase 0 scout fan-out | Explore agents (sonnet) |
| Backend/engine build slices | implementer or general-purpose (opus), one per slice |
| Every PR before merge | alch-reviewer or feature-dev:code-reviewer (sonnet), never the slice's builder |
| UI pages/components | ux:frontend-engineer, with a ux:ux-a11y pass before review |
| Visual/mobile verification | screenshot-feedback or test-ui at 375px + desktop |
| Auth, billing, PII, quota surfaces | security-review in the review brief — blocking |
| Error-handling-heavy work | pr-review-toolkit:silent-failure-hunter |
| Test-coverage judgment | tester or pr-review-toolkit:pr-test-analyzer |

## Standing rules boilerplate (part 6)

> Standing rules that hold: all Python gates via `.venv` (`ruff check`,
> `ruff format --check`, `mypy`, `CELERY_ALWAYS_EAGER pytest`); web gates
> (`npm test`, `npm run type-check`); CI monitored after every push and
> nothing closes until every check is green (CLAUDE.md protocol); branch +
> PR + squash-merge only; issues per ADR-008 with ✅/⚠️ comments;
> `alembic heads` before any migration; literal routes before parameterized;
> CORS outside RateLimit; house style in user-facing copy (no em-dashes, no
> banned AI-tell words); HANDOFF.md updated before session end; deploys and
> release publishing stay Tyler's.

## Common mistakes

- Producing task instructions instead of a session contract. The seven parts,
  in order, every time — the baseline failure mode is a competent to-do list
  with no autonomy grant, no team, no report contract.
- Granting autonomy implicitly. The grant must name merge, issue-close, and
  HANDOFF individually or the session parks them. Deploy is never granted.
- Inventing infra facts instead of citing them. A baseline session designed
  cost tracking on Redis as durable truth; the roadmap says Postgres, fail
  closed. Bake the fact table in.
- Building against the wrong roadmap phase. Phase 0 blockers outrank
  features; name the phase in the problem statement.
- Stating the mechanism Tyler imagined instead of the outcome he wants.
  Deliver the outcome; make the mechanism a decision point with a
  recommended default.
- Baking in facts without the re-verify instruction. Always include "verify
  this prompt against reality."
- Desktop-only verification. Users are phone-first; 375px is part of done.

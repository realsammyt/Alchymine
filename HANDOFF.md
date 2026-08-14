# HANDOFF — Alchymine

> **Living document.** Single source of truth for where this work stands and
> what's next. Any agent starting fresh reads this first, then updates it before
> ending. If anything here disagrees with reality, reality wins — fix the doc.

**Last updated:** 2026-08-14 by Claude (autonomous practice-layer session complete; epic #251 shipped)
**Active branch:** `main` (all epic #251 slice branches merged and deleted; verify CI at bdb0ccc)
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
| Backend tests | 3161 passed, 1 skipped | `$env:CELERY_ALWAYS_EAGER='true'; .venv\Scripts\python.exe -m pytest tests/ -q` |
| Frontend tests | 526 passed (55 suites) | `cd alchymine/web; npm test` |
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
| 2 | Finding 1: birth time local→UTC conversion | Done | 2026-07-02 | PR #210, all 10 CI checks green — awaiting merge |
| 3 | Finding 2: wealth MCP vs "no financial data to LLM" rule | Done | 2026-07-02 | PR #210, promise rescoped + tool disclosures — awaiting merge |
| 4 | Finding 3: orphaned reports readable by any authed user | Done | 2026-07-02 | PR #210, `created_by_sub` + ownership helper — awaiting merge |
| 5 | Monetization roadmap (7-lens agent review + synthesis) | Done | 2026-08-12 | PR #211 merged — `docs/plans/2026-08-12-monetization-roadmap.md`, numerology pricing ($33/$11/$222) |
| 6 | alch-dev-auto session tooling (skill + 2 agents) | Done | 2026-08-12 | `.claude/skills/alch-dev-auto/` + `alch-implementer`/`alch-reviewer`; ported from Bekin, RED/GREEN tested |
| 7 | Cost-exposure hardening (issue #213: usage counter + global breaker + art cap + drop Opus + delete /stream/narrative) | Done | 2026-08-13 | Merged to main as b9404d2 (PR #214, squash), main CI + CodeQL green, #213/#215 closed. Ceilings set: 2000 global LLM calls/day, 3 art/user/day (env-tunable, rationale in config.py). Follow-ups open: #216-#220 |
| 8 | Unit economics (epic #221: entitlement schema 0017 + get_current_account, dollar cost ledger, per-plan monthly allowances + upsell UI, revenue-linked global budget + /admin/usage, Haiku chat routing + prompt caching) | Done | 2026-08-13 | All 6 slices merged (PRs #228 design, #229, #232, #238, #244, #247 + docs #237), issues #222-#227 + #243 closed with evidence. Tests 2366→2724 backend, 356→411 web, zero regressions. ALL dollar numbers are provisional env defaults pending 2-4wk beta ledger data (design doc section 10 register). Awaiting Tyler: 14 DRAFT upsell strings (PR #238 body), real allowance/budget numbers, provider-console caps, /pricing page (#239). Follow-ups #230-#249 |
| 9 | Practice layer (epic #251: pack schema v2 + loader + external mounts, migration 0018 + practice log, deterministic ecology recommender, daily protocol + integration loop surfaces, practice coach scope) | Done | 2026-08-14 | All 6 slices merged (PRs #258 design, #259, #260, #261, #262, #277), issues #252-#257 closed with evidence. Tests 2724→3161 backend, 411→526 web, zero regressions. Every merge behind independent review; blocking security pass on slices 1/2/4/5 (all PASS); mutation-tested recommender coverage (slice 3); WCAG 2.1 AA audit on slice 4 (2 blockers found and fixed). Licensing rail held: generic engine only, original 10-practice example pack, zero third-party frameworks or vocabulary in-repo; branded packs mount later via PRACTICE_PACK_DIRS with required license+attribution metadata. Design doc: docs/plans/2026-08-14-practice-layer.md (28-entry decision register). Awaiting Tyler: licensing conversation with Carl, SWIM permission via Jose, Nexus partnership positioning, ~110 DRAFT strings across slices 3-5 (inventories in PR bodies; crisis-frame wrapper lines in PR #277 flagged for priority read), example-pack content review. Follow-ups #263-#280 |

**Next action:** (1) Tyler: the epic #251 AWAITING list — the Carl licensing conversation (seven-framework taxonomy + prompts as a licensed external pack), SWIM permission via Jose (Warner/Roy IP), Cyberdelic Nexus partnership positioning (business conversation, not a build), DRAFT copy review (inventories in PR #262/#277 bodies; the practice coach crisis-frame wrapper lines first), and the alchymine-foundations example pack content read (10 practices, speaks in Alchymine's voice); (2) Tyler: epic #221 parked items still open — 14 DRAFT upsell strings (PR #238 body), provisional allowance/budget numbers, provider-console caps, /pricing (#239); (3) Tyler: publish the auto-drafted release when ready to deploy (migrations 0016+0017+0018 run on deploy; 0018 is additive, forward-only in production); (4) NEXT session candidates: SSE newline-drop bug #278 (live on all six chat scopes), safety-gate rollout to the other five scopes #263, Stripe/ToS//pricing (#239), practice ecology settings surface #269.

_Correction 2026-08-12: PR #210 was already merged 2026-07-02 11:54 UTC; the "awaiting merge" status above was stale._

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

- **2026-08-14** — Practice-layer session complete: all 6 slices of epic #251 merged to main (design 683b769, schema+loader+example-pack 7649084, migration 0018+log API 25f8fbd, ecology recommender f848294, daily protocol+integration surfaces 275ac2b, coach practice scope bdb0ccc), every merge behind an independent alch-reviewer, blocking security reviews on slices 1/2/4/5 (all PASS; every LOW advisory fixed on-branch before merge: source_url scheme validation, owner-filtered by-id accessor, day_key double-validation pin), mutation-tested coverage review on the recommender (7 mutations run, 6 survived the original 123 tests, all gaps closed and each new test verified to kill its mutation), WCAG 2.1 AA audit on the frontend (2 blockers fixed: focus destruction, unannounced success; browser screenshots caught 2 bugs jsdom passes). Tests 2724→3161 backend / 411→526 web, zero regressions. Licensing rail held end to end: generic engine + original example pack only; the design doc's section 8 external-pack contract is the mount point for future licensed content. Coach cost-measurement method shipped (usage_records.request_id = chat_messages.id exact join); observed dollars need live traffic. Key decisions in the design doc's 28-entry register plus per-slice PR bodies; kill-switch nuance documented in review (crisis gate deliberately survives scope disablement). Live pre-existing bug found and filed: SSE frames drop post-newline text on all six scopes (#278). Follow-ups #263-#280.
- **2026-08-13** — Unit-economics session complete: all 6 slices merged to main (design b2a8a32, entitlements bfbb2ea, ledger 3d05c4d + docs 6dfa6e8, allowances 610837b, budget 885faeb, Haiku/caching e3b784a), every merge behind independent alch-reviewer + blocking security pass (zero findings x5) + slice-specific gates (silent-failure-hunter on the ledger: 2 blockers found+fixed over 3 converging rounds incl. CancelledError bypassing except-Exception nets and a single-probe circuit breaker; pr-test-analyzer on allowances: 2 critical gaps closed incl. the blueprint calendar-month decision). Tests 2366→2724 backend / 356→411 web, zero regressions. Decisions recorded: beta plan for invite cohort; single admission gate at charge_paid_call (check_ceiling stays pure); blueprint metered by calendar month (bounded 99-cent straddle, flagged for Tyler); budget env-set until Stripe; Haiku+caching flags on by default with honest zero-cache-hits framing (prefix 880 tok < Haiku 4096 min, growth = #248). Sixth paid surface (profile reassess, #243) found by security review and gated. Expected chat delta -67%/turn from price table; observed costs need live beta traffic. Follow-ups #230-#249.
- **2026-08-13** — Launched autonomous unit-economics session (epic #221, slices #222-#227 filed per ADR-008). Phase 0 scout verified prompt against b9404d2: alembic head 0016 (0017 claimed, no competing PRs), 3 egress chokepoints confirmed only SDK sites (client.py:504/:551, gemini.py:137), get_current_user JWT-only vs get_current_admin template (auth.py:212), 4 product chokepoints + frontend upsell precedents located, baselines green (2366 backend / 356 web). claude-api skill loaded before pinning prices: Sonnet 4.6 = 3/15 micros/token, Haiku 4.5 = 1/5, cache read 0.1x / write 1.25x, stream.get_final_message() for SSE capture, Haiku min cacheable prefix 4096 tok. Architect (opus) dispatched for slice-0 design doc.
- **2026-08-13** — Tyler authorized merge + ceiling numbers. Set global ceiling 2000 LLM calls/day (bounds runaway at ~$100-200/day, above a legitimate beta day) and kept art at 3/user/day (upsell scarcity signal), commit 7e4af19; full gates re-run (2366 backend green). Squash-merged PR #214 as b9404d2; main CI + CodeQL green; closed #213 and #215 with evidence; local main synced, feature branch deleted. Release draft auto-created — publishing and deploy stay Tyler's.
- **2026-08-13** — Cost-exposure hardening parked. PR #214 CI-green at e0965c8, 9 commits: migration 0016 usage_counters (fail-closed, atomic, UTC reset, live-verified on real Postgres), global daily breaker on all 3 paid chokepoints (structured 503/SSE frame), per-user art cap on BOTH art routes with refund-on-delivered-nothing (period-key threaded across midnight) + wait-states on 3 pages, Opus dropped from fallback chain, /stream/narrative deleted. Gates: 2366 backend + 356 web tests green, ruff/mypy clean. Review: security pass zero findings; alch-reviewer + test-analyzer findings all landed over 2 fix rounds; delta review APPROVE. Follow-ups #215-#220 filed. Awaiting Tyler: merge, real ceiling numbers, issue closure.
- **2026-08-12** — Launched autonomous cost-exposure hardening session (build-and-park). Phase 0 scout confirmed all 4 findings live at 9f97ecb: uncapped `/art/generate` (real caller artApi.ts:41), `/stream/narrative` proxy with zero web callers (delete-safe), CLAUDE_MODELS Sonnet→Haiku→Opus 529-walk, no spend counter anywhere; alembic head 0015 (0016 free, no competing PRs). Filed issue #213; dispatched alch-implementer (opus) on `fix/cost-exposure-hardening` for 6 slices TDD red-first. Pre-merge gate queued: alch-reviewer (sonnet) + blocking security-review + pr-test-analyzer.
- **2026-08-12** — Built `alch-dev-auto` (session-prompt-builder skill ported from Bekin's `bekin-dev-auto`) plus `alch-implementer`/`alch-reviewer` agents. TDD'd per writing-skills: baseline agent produced a task list with no autonomy grant and invented Redis-as-cost-truth; with-skill agent produced the full 7-part contract with correct facts. PR #211 (roadmap + pricing) merged by Tyler as `5af6b6c`.
- **2026-08-12** — Ran 7-lens product/monetization review (8 agents: 4 opus + 3 sonnet lenses + opus synthesis, all findings file-verified). Wrote `docs/plans/2026-08-12-monetization-roadmap.md`: $33 Blueprint one-time → $11/mo Pro (gated on retention spine), $222×111 founding lifetime — numerology-aligned undeniable pricing (11/22/33/111/222) per Tyler, revised same day from the synthesis's $79/$19; 16 blockers incl. likely-broken prod PDF (worker image lacks Chromium), uncapped Gemini endpoint (~$5k/day exposure), no ToS/Privacy, no entitlement model. Discovered PR #210 was already merged 2026-07-02 (handoff was stale); PR #209 (web API request timeout) marked ready and squash-merged same day, all main CI workflows green.
- **2026-07-02** — Fixed all 3 findings via 3-agent team on `fix/review-findings`; PR #210 opened, 2317 backend + 333 web tests green, all 10 CI checks green. Backend test count grew to 2317 (was 2281).
- **2026-07-02** — Merged PR #206 (7 review fixes + CI fixes). Created this handoff. Next: 3 remaining findings via agent team.
- **2026-07-01** — Full-project review (4 parallel review agents). Fixed: gemini mypy, tsc test error, session poisoning in workers, /reports/diagnose shadowing, CORS/rate-limit order, feedback email HTML injection, debt waterfall math, chat history clobbering. All gates + CI green.

---

## 8. Update protocol (keep this doc honest)

Update this file at the end of any session that touched the work, and before
handing off or clearing context. Minimum: Status table (status + date + note),
one Activity-log line, move answered items from Open questions to Decisions, and
the `Last updated` line. Keep it tight — state, not narrative.

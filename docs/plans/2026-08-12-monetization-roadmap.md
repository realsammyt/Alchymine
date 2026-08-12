# Alchymine — Monetization Roadmap

**Date:** 2026-08-12
**Method:** Seven-lens multi-agent review (product-completeness, user-value, monetization-architecture, market-positioning on Opus; trust-safety-compliance, ops-unit-economics, quality-reliability on Sonnet) synthesized by an eighth agent. ~2.5M tokens, 686 tool calls. Every finding below was verified against the repo at the stated file:line, not inferred.
**Status:** Proposed. Each phase should get its own `/plan` before implementation.

---

## 1. Executive summary

Alchymine is a genuinely strong engine with no commercial surface and no second session. The deterministic layer (103 engine files, five LangGraph coordinators, Celery pipeline, five populated profile tables, PDF, Gemini art, five MCP servers) is real and defensible in a category dominated by LLM wrappers. Everything that would make it a business is either absent or disconnected: no billing of any kind (zero Stripe references repo-wide), no entitlement model (User has no plan field), no cost attribution (token counts are discarded), no legal surface (no /terms, /privacy, footer, or contact email), and no day-2 return trigger (no scheduler, no lifecycle email; "For You Today" is five hardcoded strings).

Money can currently leave but not come in: two live cost holes exist today in the invite beta (uncapped Gemini art at ~$5k/day exposure per IP; an authenticated arbitrary-prompt Claude proxy with zero frontend callers).

Unit economics are not the problem: ~$0.07-0.18 per full five-system report, ~$0.01-0.03 per chat message, >90% gross margin at every scale modelled. The path to revenue is roughly 12-14 weeks of solo work: ~4 weeks closing blockers (Phase 0), ~5 weeks building billing (Phase 1), then retention (Phase 2). Sell the artifact first ($33 one-time Blueprint + $222 founding lifetime), open the $11/mo subscription only after the retention spine exists. The product currently has a world-class first session and almost nothing for the second.

## 2. Verdict: the value spine

The value spine is one artifact and one loop, and only the artifact exists.

**The artifact** (exists): discover → intake → assessment → five-system report → PDF. End-to-end real, no mocks in the worker or orchestrator. Would justify $79 today with about two weeks of trust work in front of it.

**The loop** (built but disconnected): a coach that knows you, a practice you repeat, evidence that something changed. All three parts exist as code with zero production callers:
- `build_user_context()` (agents/growth/context_builder.py) — unit-tested, never called
- 15 evidence-rated healing skills with API, client function, and a finished `SkillDetailDrawer` — mounted nowhere
- `engine/astrology/transits.py` daily transit engine — no route

This pattern repeats (compatibility.py 334 lines with no UI, perspective frameworks with no callers, sw.js never registered). The distance to monetizable is not "build a product," it is 8-10 solo weeks of wiring, gating, and legal surface.

The three surfaces a paying user touches most currently argue *against* paying: a coach with amnesia every turn, a dashboard Overall Score pinned near zero for a maximally engaged user, and a Journey page that reads 100% complete on day one. Those three plus the legal pages are the real gate.

## 3. Packaging & pricing

Hybrid artifact-then-loop. Not subscription-only, not per-system.

| Tier | Price | Contents | Notes |
|------|-------|----------|-------|
| **Snapshot** (free) | $0 | Birth-date-only numerology + archetype + today's transit line, <60s, no assessment | Fully deterministic, ~$0 COGS. Replaces the invite wall as top of funnel. No LLM, no PDF, no chat. |
| **Blueprint** | $33 one-time (Master 33) | Full intake + assessment + five-system report + narratives + art + PDF + read-only system pages | COGS ~$0.20. The conversion event. Shippable the moment Phase 0 + Stripe land. A/B against $22 (Master Builder — thematically exact for a "Blueprint"). |
| **Alchymine Pro** | $11/mo (Master 11) or $111/yr | Coach with profile+memory, ~222 msg/mo soft cap (degrade to Haiku, don't hard-block), practice library + streaks, server-side 90-day plan, weekly digest email, journey time series, quarterly report re-run with diff, 22 art images/mo, MCP API key | **Do not open for sale until Phase 2 exit criteria are met.** Selling monthly before the loop exists is the churn pattern that kills astrology apps. |
| **Founding Member** | $222 lifetime, 111 seats | Everything, forever | Sold through the existing InviteCode table (max_uses/expires_at/is_active + admin UI already work). Converts beta + waitlist into cash during Phase 1; caps perpetual-COGS liability at 111 accounts; produces launch testimonials. |

Blueprint credits toward the first year of Pro ($33 off the $111 annual within 33 days), making the one-time SKU a subscription funnel rather than a cannibal.

**Pricing rationale (revised 2026-08-12, owner decision — numerology-aligned, undeniable):** Prices are drawn from the product's own number system, so the pricing IS a marketing story: Blueprint $33 (Master Teacher — the report that teaches you yourself; A/B $22, Master Builder), Pro $11/mo (Master 11, intuition — the coach surface) or $111/yr, Founding $222 (partnership) × 111 seats, with on-theme meters (222 messages, 22 images). The undeniability logic: $33 sits at the bottom of the one-time deep-report band ($25-90) for an artifact the review independently valued at $79 — the buyer is offered a thing at less than half its assessed worth. $11 lands inside the astrology band (CHANI $11.99, The Pattern) while shipping five systems plus a coach, so the comparison becomes "CHANI's price, five engines." Trade-offs accepted: per-unit revenue roughly halves versus the $79/$19 scheme, betting on conversion volume; the premium-above-the-band story is deferred — the wealth engine becomes price-rise headroom rather than launch positioning. Raising prices later is harder than lowering them, so frame $11/$33 explicitly as launch pricing and grandfather early buyers. $111/yr is a ~16% annual discount (deliberately far from Calm's ~60%; the annual price must fund a year of real inference). Margin floor at $11 depends on the meters: a heavy Pro user at the 222-message cap costs ~$3/mo (~72% margin worst case); blended ~$0.28 keeps >90%. **Still true and now more binding: do not finalize until 2-4 weeks of real usage_records data sets p95 cost-per-active-user.**

**What gates cleanly** (single chokepoint, countable, real cost): report generation (reports.py:137), chat messages (chat.py:332), art (generative_art.py:192), PDF export.
**What does not:** gating by systems unlocked — intent.py:241-246 forces all five coordinators in one pass, so withholding systems saves zero COGS. Gate narrative depth and regeneration instead. MCP cannot be an entitlement until transport.py gets per-user API keys (it has no auth at all today).

**Free-tier safety rule:** give away artifact-shaped things (deterministic snapshot, read access), never recurring-cost things. Zero LLM calls for free accounts until the Postgres meter is live.

**Rejected alternatives:** subscription-only (nothing to renew for until Phase 2); per-system pricing (dismantles the integration story, the only claim no competitor can copy); white-label creator tier per PRD §10.7 (zero code, no multi-tenancy, NC license deters B2B — defer past year one).

## 4. The 16 blockers

Grouped; full detail with file:line citations lives in the phase items below.

**Legal / trust (Stripe will not onboard without these):**
1. No ToS, Privacy Policy, or refund policy anywhere; no consent checkbox at signup. Astrology + wellness sit in Stripe's elevated-underwriting category.
2. No user-facing account deletion (endpoint exists, zero frontend callers) or full data export — GDPR Art.17/CCPA cannot be exercised.
3. Breathwork timer ships breath-retention exercises with zero medical disclaimer, while the backend models real contraindications (epilepsy, pregnancy, cardiovascular) that never reach the user.

**Billing / cost control:**
4. No entitlement model — users table has no plan/status/stripe fields; no Subscription/UsageRecord/BillingEvent tables.
5. `get_current_user` never touches the DB — nowhere to hang an entitlement; cancelled subscribers keep access via refresh for 7 days.
6. Uncapped Gemini art endpoint: ~$5,040/day exposure from a single IP, defeated further by rotation.
7. `GET /stream/narrative`: authenticated arbitrary-prompt Claude proxy, no quota, zero frontend callers. Delete it.
8. All quota state is in-process memory, multiplied by worker count (2-4x documented limits), reset on every deploy.
9. Zero cost attribution — token counts discarded; SSE path never calls `stream.get_final_message()` at all.
10. No Stripe integration of any kind.

**Product credibility (refund/chargeback fuel):**
11. Chat coach has no profile and no memory (`build_system_prompt(system_key, None)`, single-turn prompts) on the most-touched surface in the app.
12. Outcome layer structurally can't move: one `logActivity` call site, zero `createMilestone` calls, hardcoded `checksPassed={5}` fake trust signal on the dashboard.
13. Rising sign/houses silently None for most users (~120-city hardcoded geocoder); report claims Swiss Ephemeris precision it doesn't deliver.
14. Wealth calculations are a literal empty dict (`graphs.py:738-746`); the one real calculator (debt.py, 469 lines) has no API route while the frontend reimplements the math divergently in TypeScript.

**Infrastructure:**
15. Backups live on the same disk as the database they protect; no offsite copy exists.
16. PDF export is likely broken in production: compose builds the worker from Dockerfile.api, which has no Playwright/Chromium; the deploy script omits the overlay that would fix it. No test catches it (PDFRenderer is mocked). **First action Monday: hit `GET /reports/{real-id}/pdf` on production.**

## 5. Phase 0 — Pre-revenue blockers (~3-4 weeks solo)

**Goal:** Stop money leaving, make it legally possible to take money, remove the three surfaces that argue against paying. Nothing here is billing code; all of it is prerequisite to billing code.

**Exit:** ToS/Privacy/refund live + consent checkbox; every LLM/Gemini call site metered and quota-capped from Postgres; users table has plan columns and `get_current_account()` guards all cost-bearing routes; chat knows the user's Life Path and last 5 turns; dashboard score moves when a user acts; a fresh droplet build renders a real PDF; last night's pg_dump exists offsite.

| Item | Effort | Key detail |
|------|--------|-----------|
| Publish ToS, Privacy, refund policy as real routes | days | /terms + /privacy under web/src/app, consent checkbox at signup, footer links. Privacy notice must name birth, financial, chat, journal data. |
| **Cost-exposure hardening PR — standalone, ship first** | days | Per-user daily cap + guardrail on /art/generate; delete /stream/narrative; drop Opus from the CLAUDE_MODELS fallback chain (Sonnet→Haiku→Opus means 529s escalate every concurrent report ~5x at once); global daily spend circuit breaker. The beta is exposed to all of this today. |
| Move billing quotas to atomic Postgres counters | 1-2 wks | usage_counters keyed (user_id, meter, period_key) via INSERT..ON CONFLICT..RETURNING. Redis = read-through cache only. Cost-bearing meters fail closed; keep in-process dicts as abuse throttles only. |
| Migration 0016: entitlement schema | days | users: plan, plan_status, stripe_customer_id, stripe_subscription_id, plan_period_end, cancel_at_period_end, trial_ends_at. New: usage_records (with cost_micros), usage_counters, billing_events (stripe_event_id UNIQUE). |
| `get_current_account()` DB-backed dependency | days | Near-copy of get_current_admin. Frozen dataclass, 30-60s Redis cache invalidated by Stripe webhook. **Must land before Stripe or entitlements get retrofitted into 25 routers.** Never put plan claims in the JWT. |
| Instrument LLM cost at the client layer | 1-2 wks | All egress funnels through 3 call sites (client.py:507, :550, gemini.py:180). Add stream.get_final_message() to the SSE path. Propagate user via contextvars (survives the asyncio.gather fan-out). Run 2-4 weeks against beta before fixing Pro price. |
| **Give the chat coach profile + memory** | days | Highest value-per-hour item in the codebase (~1 day). Pass profile to build_system_prompt (already accepts it); feed last 10 turns from get_chat_history. Bounds message cost under ~$0.04. |
| Make the outcome layer accumulate | 1-2 wks | logActivity from every practice/tool completion; auto-milestones from plan phases + report completion; pass journalCount; write active_plan_day; delete the hardcoded checksPassed={5} and bind to real quality_passed; move tracker globals to DB reads. |
| Resolve the astrology honesty gap | days | Ship a real offline geocoder (GeoNames cities500) + house cusps, or stop collecting birth time/city and remove Rising from the report. Fix the "Swiss Ephemeris" subtitle overstating the method. |
| Make the wealth pillar honest | month+ (deferrable) | Build Income Blueprint + Financial Defense, or rename the pillar and fix marketing. Either way: expose debt.py via API and delete the divergent TS reimplementation. Safe to defer past first revenue if copy is corrected. |
| Self-service deletion + full export | days | Wire existing DELETE /profile/{id} into profile page; extend export to chat, journal, reports, art. |
| Breathwork safety surface | days | Non-dismissible contraindications + "not medical advice" on healing page and BreathworkTimer, surfacing what the YAMLs already model. |
| Offsite DB backups | days | rclone/aws-cli step to DO Spaces in backup-db.sh. Cheapest fix on the list relative to severity. |
| Fix PDF Dockerfile drift + real-image smoke test | days | Verify live first. Point compose worker at Dockerfile.worker (or add Playwright to Dockerfile.api); one CI job that builds the real image and renders a real PDF. Decide fate of the orphaned pdf-service container (nothing calls it; burns up to 1GB RAM). |

## 6. Phase 1 — Monetization MVP (~4-6 weeks solo)

**Goal:** Take the first dollar for the Blueprint, with a trust surface a stranger will transact against and enough observability that failures reach Tyler before customers.

**Exit:** A stranger buys with a card, gets a report-ready email and a working PDF, can see and cancel billing; admin sees MRR and per-user COGS in one view; a 500 pages Tyler within 5 minutes; every quota rejection renders an upsell, not an error.

| Item | Effort | Key detail |
|------|--------|-----------|
| Stripe billing package + router | 1-2 wks | alchymine/billing/ + routers/billing.py (checkout-session, portal-session, subscription, webhook). construct_event on raw body; idempotency via billing_events UNIQUE; handle checkout.completed, subscription.*, invoice.paid/failed. Stripe secrets as production-required Settings validators — missing webhook secret fails startup. |
| Webhook rate-limit entry | days | Explicit high-ceiling DEFAULT_ROUTE_LIMITS entry — Stripe retries from wide IP ranges would hit the 100/60s bucket and silently desync paid state ("customer paid but has no access"). |
| Gate the four clean chokepoints | 1-2 wks | require_entitlement + consume_quota + usage record on reports, chat, art, PDF. Do not gate by system count. |
| Reject orphan reports | days | reports.py:184-205 currently creates reports with user_id=None when the JWT user is missing — the most expensive operation in the product running unbilled, then the profile never populates. 401 it. |
| Pricing page, billing page, upgrade touchpoints | 1-2 wks | /pricing + /account/billing + lib/billing.ts. Upgrade prompts at highest intent: report-complete screen above all, chat quota exhaustion, art button, PDF button. |
| Structured quota-exceeded responses | days | {error:'quota_exceeded', meter, limit, used, resets_at, upgrade_url} rendered as inline upsell — the highest-intent conversion moment currently reads as a bug. |
| **Replace the report exit ramp with a commitment step** | days | The report page ends the highest-emotion moment with "Back to Home" → marketing landing. Replace with: pick one practice, set a daily time, one-line reflection, Pro offer. Largest single effect on day-1 return and conversion. |
| Celery beat + report-ready email | days | No scheduler exists anywhere. Add beat_schedule; ship report-ready (generation takes minutes; tab-closers are never told) and payment receipt/dunning. Resend is already wired. |
| Fix PDF race + art in the PDF | days | Poll HEAD before enabling the export button (currently 404s in the redirect window); pass hero_image_data_uri so the downloaded PDF contains the Gemini art. |
| Error tracking + uptime alerting + log levels | days | Sentry (free tier) on API + web; external uptime monitor on /health to phone. Worker LOG_LEVEL is hardcoded WARNING — the pipeline you most need visibility into drops every logger.info. |
| Right-size the droplet | days | Container limits sum ~5.6GB; the "2GB droplet" path in the guide can't hold reservations. Document 4GB/$24 as hard minimum. |
| Stuck-job sweeper + visibility_timeout | days | acks_late without visibility_timeout = 3600s redelivery vs a 10-min frontend timeout: stuck "generating" reports and silent duplicate paid LLM runs. Set 900s + beat sweeper. |
| Stop leaking tracebacks to customers | days | tasks.py stores format_exc() as report.error and the frontend renders it. Store a user-safe message; log the traceback. |
| Stop paying for tokens after disconnect | days | One-line `await request.is_disconnected()` check in the chat stream loop. |
| Age gate + email verification + legible disclaimers | days | 18+ at signup/intake; email_verified before receipts; raise report disclaimers from 0.6rem/20% opacity (the product's own ethics_check bans buried terms). |
| Admin revenue + cost/margin views | days | /analytics/revenue (MRR, ARPU, churn, failed payments) + /analytics/costs (spend per user, margin per plan, top-20 costliest accounts). The margin view is what tells you whether $11 works. |
| Contributor IP + dual-license | days | No CLA/DCO exists while LICENSE already names "Alchymine Contributors" as joint holders — every outside merge adds a consent needed to relicense. Add DCO now; CC-BY-NC-SA stays on the public repo as trust asset; separate proprietary grant covers the hosted service. CC 4.0's anti-TPM clause conflicts with app-store terms. Days now, potentially unresolvable later. |

## 7. Phase 2 — Retention & value spine (~5-7 weeks; Pro opens only at exit)

**Goal:** The three things that make month two happen: a daily reflection loop, a coach that knows you, a practice you repeat with evidence it accumulated.

**Exit:** An engaged user's score climbs week over week and the journey page's shape changes; the weekly email genuinely differs from last week's; day-30 Blueprint retention >35%; Pro trial-to-paid >25% before public opening.

| Item | Effort | Key detail |
|------|--------|-----------|
| Mount the healing practice library | 1-2 wks | 15 evidence-rated practices, API, client fn, finished drawer with Start Practice button — all with zero call sites. Largest built-but-invisible asset in the repo. Add completion logging for all 15. |
| Real Today card from the transit engine | 1-2 wks | transits.py implements exactly the daily mechanism Co-Star/The Pattern charge for — no route, no UI. Combine with biorhythm + next plan item; delete the 5 hardcoded "For You Today" strings. ~$0/user/day COGS. |
| Full lifecycle email suite | 1-2 wks | Day-1 welcome, weekly digest (transit + practice + wealth check-in), day-30/60/90 transitions with regenerate offer. PRD §10.4, entirely unbuilt. Converts $33-one-time into defensible $11/mo. |
| 90-day plan server-side + cross-system | 1-2 wks | Currently localStorage-only (cache clear wipes a paying user's progress), generic constants, buried at line 1104. plan_progress table, personalized actions, above the fold, beyond wealth-only. |
| Rebuild /journey as a time series | 1-2 wks | All milestones flip simultaneously at report creation → reads 100% forever. Replace with dated events: mood over weeks, completions, plan days, regenerations. Answers "am I different than in March?" |
| Personal cross-system bridges | days | Panels show identical frozen XS-01..07 cards to every user; the personalized functions already exist and feed the dashboard. Swap them in — integration is the stated moat. |
| Cut assessment to 27 required questions | days | 67 required vs PRD's 20; landing promises 10 minutes. Big Five 20 + attachment 4 + risk 3; rest optional post-report deepening. Also fix silent wealth_context drop on cross-device resume. |
| Close the demo-versus-real gap | month+ | Streaks, modality progress, entire wealth Financial Dashboard are isDemoUser-only with no real input/persistence path. Build it or delete it — showing prospects a richer product than buyers receive is refund fuel. |
| Decision-support tools as weekly surface | 1-2 wks | pros-cons, weighted-matrix, bias-detect endpoints have no UI. Occasion-driven jobs users return for, unlike "what's my life path" (answered once forever). |
| Quarterly report re-run with diff | 1-2 wks | No regeneration/comparison exists. "What changed since your first Blueprint" is the Pro renewal moment; pairs with the day-90 email. |
| Chat deterministic safety backstop | days | Chat never calls filter_content/detect_crisis/check_text — the one freeform surface has the weakest backstop. Run final replies through both; add region-aware crisis resources (current ones are US-only). |
| Persist safety audit + encrypt birth data | days | Audit trail is a process-local deque, unreachable from the worker container. Persist like AdminAuditLog. Encrypt birth_date/birth_time (name and city already are). |
| Real data visualization | 1-2 wks | No charting dependency exists. PRD §11.2: Big Five radar, natal chart SVG, archetype wheel, lever distribution, progress timeline. The journey time series needs a chart to exist at all. |

## 8. Phase 3 — Growth (parallel with late Phase 2)

**Goal:** Get the Blueprint in front of the one audience that pays; turn buyers into distribution. Solo-operator motions only; no paid acquisition until CAC is measurable against known LTV.

**Exit:** One repeatable channel producing Blueprint sales without manual recruiting; at least one motion with CAC below one-third of $33.

- **Pick one ICP and rewrite the hero** (days): the self-employed seeker-builder, 30-45, solo creator/consultant, $60-150k, already paying for an astrology app + Calm + a course. Test: "The operating system for people building a life and a business at the same time." Lead with the collision of inner work and money math — the wealth engine is the pricing permission and the current hero buries it.
- **Founding Member launch** (days): 111 seats × $222 through the existing InviteCode table.
- **Free Snapshot as top of funnel** (1-2 wks): value in <60s before the 67-question wall; competitors deliver a first personalized hit in under a minute.
- **Blueprint drops into one narrow community** (1-2 wks): 20 free reads in public, anonymized PDFs published. The report is the marketing asset. Highest-signal test of whether $33 converts at volume.
- **MCP directory distribution** (1-2 wks): five MCP servers shipped, no competitor has this surface, lands directly on the AI-native ICP. Prerequisite: per-user MCP API keys (transport has no auth today).
- **Compatibility as the referral surface** (days): 334-line router complete and tested, zero UI. "Run this with your partner" is the natural viral loop. Highest value-per-hour on the growth list.
- **Build in public on transparency, not "open source"** (1-2 wks): weekly engine teardowns convert the skeptics; don't lead with open source (invites "then why pay?") — frame as auditable methodology.
- **Outcome data as retention marketing** (1-2 wks): once Phase 2 instrumentation accumulates, "here's what changed in 90 days" is the strongest testimonial engine in the category. Impossible before Phase 2 (numbers pinned at zero).
- **Promises audit before any paid copy** (days): claimed without code today: Creator Dashboard/Stripe Connect, family dashboard, PWA offline/push, guided audio, the 28-agent CrewAI architecture (CrewAI isn't even a dependency; CLAUDE.md's structure section is wrong), Spiral Dynamics/AQAL, portfolio management. Build, defer publicly, or cut from the pitch. Explicitly defer white-label past year one.

## 9. Risks & resolved conflicts

**Conflicts the synthesis resolved by verifying the repo:**
- **PDF**: wired at the code layer, broken at the image layer (worker built from Dockerfile.api without Chromium). Treat as broken until a live GET returns bytes. Check before any roadmap work.
- **Chat statelessness**: cost-favorable (O(1)) but unsellable. Cap history at 10 turns: bounded ~$0.04/message, ~$6/mo COGS for a heavy Pro user.
- **Opus fallback**: the chain Sonnet→Haiku→Opus makes the final hop a ~5x escalation triggered by 529s that correlate across tenants — every concurrent report escalates at once. Drop or plan-gate Opus.
- **Gemini severity**: confirmed blocker (zero guardrails in the file, ~hour of work to fix).
- **"Nothing brings users back day 2" vs "one-time SKU shippable now"**: both true — it blocks the subscription, not the artifact. Hence artifact-first packaging.
- **Pricing spread** ($59 vs $79-129): the synthesis settled $79 with a $59/$99 A/B. Superseded 2026-08-12 by owner decision: numerology-aligned undeniable pricing ($33/$11/$111/$222) — see §3. The review's $79 value assessment stands as evidence of underpricing, which is the point.

**Standing risks:**
1. **Solo-operator bandwidth is the dominant risk**, not any technical item. Phases 0+1 are 8-10 weeks with no slack. Cut scope (wealth build, demo-gap build are safely deferrable with corrected copy), never compress schedule.
2. **First-week refund/chargeback concentration**: broken PDF + amnesiac coach + zero dashboard + overstated astrology = four independent dispute grounds. >1% chargebacks endangers the Stripe account in an already-elevated category. Phase 0 exists to close all four before the first charge.
3. **Regulatory surface rises with payment**: not-financial-advice and not-medical-advice must live in ToS and marketing, not just prompt-level disclaimers. Breathwork is the sharpest edge.
4. **License decay is silent and compounding**: every outside merge without DCO adds a relicensing veto. Days now, unresolvable later.
5. **Single droplet, no offsite backup, no alerting**: the most likely incident destroys data and backups together, unpaged.
6. **Metering before pricing is a hard dependency**: $11 without 2-4 weeks of usage_records is a guess wrong in either direction — and the lower price leaves less room for the guess to be wrong on the high-cost side.
7. **`get_current_account()` before Stripe** is the single most expensive ordering constraint (else retrofit 25 routers).
8. **Positioning after the pricing revision**: at $11 the product sits inside the astrology band rather than above it, so launch positioning no longer depends on the wealth build (it becomes upsell and price-rise headroom instead — the coupling risk is deferred, not gone). The flip side: margin now leans harder on the chat meter, the Haiku degrade path, and the 222-message cap actually being enforced.

## 10. Success metrics (gates, not vanity)

- **Phase 0 — cost**: 0 unguarded LLM/Gemini call sites (today: 4 of 7); verified per-account daily spend cap; 100% of completions writing usage_records with tokens + cost_micros (today: 0%).
- **Phase 0 — trust**: legal pages live + consent; deletion <60s end-to-end; full export; contraindications visible before first timer start.
- **Phase 0 — credibility**: 9/10 chat spot-checks reference the user's own profile; scripted engaged-user sim scores >45 and rising (today ~0); rising sign for 95%+ of test cities or birth-time collection removed; fresh droplet build renders a PDF first try.
- **Phase 1 — revenue**: 33 paying Blueprints in 30 days (raised from 25 — the $33 price is a volume bet and should convert harder); checkout completion >45% from pricing page; disputes <0.5%; refunds <8% in 60 days.
- **Phase 1 — funnel**: signup→report >40%; report→day-1 return >25% (near zero today); report-ready email open >55%.
- **Phase 1 — ops**: p95 report <180s, completion >97%; error time-to-detection <5 min; zero reports stuck >15 min; offsite pg_dump verified every morning.
- **Phase 1 — economics**: cost per Blueprint ≤$0.30 all-in; margin >95%; p95 cost per active user <$2.75/mo, i.e. 25% of $11 (the number that validates the Pro price).
- **Phase 2 — retention**: day-30 Blueprint >35%; Pro m1→m2 >70%, m3 >55%; digest open >40% CTR >12%; 30%+ of Pro logging ≥8 practices/mo.
- **Phase 2 — conversion**: Blueprint→Pro >20% within 60 days; trial→paid >25% (the gate on opening Pro at all).
- **Phase 3 — growth**: one channel at 20+ Blueprints/mo unassisted; blended CAC <$11 (one-third of the $33 price); compatibility referral →second signup on 15%+ of runs; 12-month LTV >$77 (Blueprint plus roughly four Pro months).
- **North star**: MRR + one-time revenue tracked against p95 cost per active user in the same admin view.

## 11. First moves (this week)

1. Merge PR #210 (already green, awaiting squash) and pull main.
2. **Live-check the PDF**: `GET /api/v1/reports/{real-completed-id}/pdf` on production. (Blocker 16 — everything about the paid deliverable depends on the answer.)
3. **Ship the cost-exposure hardening PR** (blockers 6, 7, Opus fallback, spend circuit breaker) — standalone, independent of all other work, and the beta is exposed today.
4. Start Phase 0 legal pages + entitlement migration in parallel.
5. Run `/plan` on Phase 0 to turn it into an implementation plan with tests.

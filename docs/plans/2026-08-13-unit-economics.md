# Design: Unit Economics (cost ledger, entitlements, allowances)

**Date:** 2026-08-13
**Status:** Proposed. Slices 1-5 build directly from this document; no further design decisions should be needed.
**Base:** main at `b9404d2` (PR #214, cost-exposure hardening).
**Parent:** [2026-08-12-monetization-roadmap.md](2026-08-12-monetization-roadmap.md) sections 3, 5 and 10.

---

## 0. What this is and what it is not

PR #214 gave the product a brake. It counts paid model calls in Postgres, trips a global breaker at 2000/day, and caps art at 3/user/day. It does not know what anything costs. `usage_counters` counts *calls*; `config.py:92-94` says so in a comment, and no code anywhere records a token count or a dollar.

This design adds the missing half: an entitlement model on `users`, a per-call cost ledger written at the three egress sites, per-plan monthly spend allowances, a revenue-linked global budget, and the two cost reductions (Haiku routing, prompt caching) that make the $11 Pro price defensible.

Every dollar figure here is a **provisional env default**. The roadmap is explicit that pricing and allowances are not final until 2 to 4 weeks of measured beta data exist (risk 6, section 9), and that data cannot exist until slice 2 ships. Section 10 lists every provisional number in one place so they can be revisited as a set.

Out of scope: Stripe (the `billing_events` table is built here and stays empty), the free Snapshot tier, MCP API keys, Redis caching of entitlements.

---

## 1. Entitlement schema (migration 0017)

Alembic head is `0016` (`alchymine/db/migrations/versions/2026_08_12_0016_add_usage_counters.py`, revises `0015`). This design adds `0017`, revising `0016`.

### 1.1 New columns on `users`

`alchymine/db/models.py:69` currently has no plan, billing, or entitlement field of any kind.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `plan` | `String(20)` | NOT NULL | server_default `'free'` | `free \| beta \| blueprint \| pro \| founding` |
| `plan_status` | `String(20)` | NOT NULL | server_default `'active'` | `active \| trialing \| past_due \| canceled \| expired` |
| `stripe_customer_id` | `EncryptedString()` | NULL | — | Text at rest, Fernet |
| `stripe_subscription_id` | `EncryptedString()` | NULL | — | Text at rest, Fernet |
| `plan_period_end` | `DateTime(timezone=True)` | NULL | — | when the current paid window lapses |
| `cancel_at_period_end` | `Boolean` | NOT NULL | server_default `false` | |
| `trial_ends_at` | `DateTime(timezone=True)` | NULL | — | |

**Encryption decision, and the constraint it creates.** `stripe_customer_id` and `stripe_subscription_id` use `EncryptedString()` from `alchymine/db/encryption.py:77`, the same type `WealthProfile.income_range` uses. Fernet is non-deterministic, so these columns cannot be indexed and cannot be matched by equality in SQL. That is not a defect to work around later, it is a constraint the Stripe slice must be built to respect:

> When the billing router lands, the webhook handler MUST resolve the user from `metadata.user_id` (or `client_reference_id`), which we set ourselves at checkout-session creation. It must never issue a `WHERE stripe_customer_id = ...`. Reads of these columns are always keyed by `users.id`.

Write that as a comment on both columns in the model so the constraint travels with the schema.

**Migration safety.** Every column is either nullable or has a server_default, so Postgres 11+ adds them as a metadata-only operation with no table rewrite. Existing rows fill in without a lock that matters.

**The data migration is load-bearing.** Every account that exists today came through an invite code and is a beta tester. If they wake up on `plan='free'` (allowance 0, section 2) the beta loses chat, art and reports on deploy. `0017.upgrade()` runs, after the column add:

```sql
UPDATE users SET plan = 'beta', plan_status = 'active';
```

New signups then get `'free'` from the column default. `downgrade()` drops the seven columns; the plan assignment is not recoverable, which is acceptable for a forward-only production migration and should be stated in the docstring.

### 1.2 New table `usage_records` (the ledger)

One row per delivered paid call. This is the source of truth for analytics; the counters in `usage_counters` are gates, not history.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BigInteger` PK autoincrement | | |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, server_default `now()` | |
| `user_id` | `String(36)` FK `users.id` ON DELETE SET NULL | NULL | NULL means unattributed (section 5) |
| `scope` | `String(64)` | NOT NULL | user id, or `'unattributed'`; mirrors `usage_counters.scope` |
| `surface` | `String(32)` | NOT NULL | `chat \| report_narrative \| art \| brand_logo \| unknown` |
| `meter` | `String(64)` | NOT NULL | `llm_calls \| art_generations` |
| `provider` | `String(16)` | NOT NULL | `anthropic \| google` |
| `model` | `String(100)` | NOT NULL | exact model id as sent |
| `input_tokens` | `Integer` | NOT NULL, default 0 | |
| `output_tokens` | `Integer` | NOT NULL, default 0 | |
| `cache_read_input_tokens` | `Integer` | NOT NULL, default 0 | |
| `cache_creation_input_tokens` | `Integer` | NOT NULL, default 0 | |
| `images` | `Integer` | NOT NULL, default 0 | Gemini rows only |
| `cost_micros` | `Integer` | NOT NULL, default 0 | micro-dollars, section 4 |
| `estimated` | `Boolean` | NOT NULL, default `false` | true when tokens were inferred, not reported (section 6) |
| `period_key` | `String(16)` | NOT NULL | `YYYY-MM-DD` of `created_at`, denormalized |
| `month_key` | `String(7)` | NOT NULL | `YYYY-MM` of `created_at`, denormalized |
| `request_id` | `String(64)` | NULL | from `RequestIdMiddleware` when present |

Indexes: `(created_at)`, `(user_id)`, `(period_key, surface)`, `(user_id, month_key)`. The last two are what `/admin/usage` reads; without them the daily rollup table-scans within a month of launch.

`ON DELETE SET NULL` on `user_id` matches the reasoning already written into `UsageCounter`'s docstring (`models.py:775-777`): a deleted user should not take the spend history with them, and nulling the id satisfies erasure while keeping the aggregate honest.

### 1.3 New table `billing_events`

Built now, zero writers until Stripe lands. Building it here means the Stripe slice is a router plus a handler, not a router plus a handler plus a migration on a live billing path.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | `BigInteger` PK autoincrement | | |
| `stripe_event_id` | `String(255)` | NOT NULL **UNIQUE** | the idempotency key; a duplicate webhook delivery hits the constraint and is discarded |
| `event_type` | `String(100)` | NOT NULL, indexed | `checkout.session.completed`, etc. |
| `user_id` | `String(36)` FK `users.id` ON DELETE SET NULL | NULL | |
| `payload` | `EncryptedJSON()` | NULL | Stripe payloads carry email and payment identifiers |
| `status` | `String(20)` | NOT NULL, default `'received'` | `received \| processed \| failed \| ignored` |
| `error` | `Text` | NULL | |
| `processed_at` | `DateTime(timezone=True)` | NULL | |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, server_default `now()`, indexed | |

### 1.4 `get_current_account()`

A near-copy of `get_current_admin` (`alchymine/api/auth.py:212`), which is already the DB-backed pattern: decode the JWT, `SELECT User`, check `is_active`. `get_current_user` (`auth.py:158`) stays exactly as it is; it is JWT-only and never touches the database, which is why there is nowhere to hang an entitlement today.

```python
@dataclass(frozen=True, slots=True)
class Account:
    user_id: str
    email: str | None
    plan: str
    plan_status: str
    is_admin: bool
    plan_period_end: datetime | None
    trial_ends_at: datetime | None

    @property
    def effective_plan(self) -> str:
        """The plan actually in force right now.

        A lapsed window degrades to 'free' rather than keeping paid
        access, so a cancelled subscriber stops costing money at the
        period end instead of at their next token refresh.
        """
```

Rules, non-negotiable:
- Plan claims never go in the JWT. Access tokens live 30 minutes and refresh tokens 7 days (`config.py:56-57`); a plan claim in a token is a cancelled subscriber with a week of free inference.
- No Redis cache in this session. A 30 to 60 second read-through cache invalidated by the Stripe webhook is a roadmap item; correctness first, one `SELECT` per gated request is affordable.
- `get_current_account` sets the attribution ContextVar as a side effect (section 5).

---

## 2. Plans and monthly spend allowances

### 2.1 Sizing formula

```
monthly COGS budget = price x (1 - margin target)
```

That is the whole method. Everything below is that formula plus a stated margin target, so when the measured p95 arrives the numbers can be re-derived rather than re-argued.

### 2.2 The table

| Plan | Price | Margin target | **Allowance (cents/month)** | Why this number |
|---|---|---|---|---|
| `free` | $0 | n/a | **0** | Deterministic surfaces only. The roadmap's free-tier safety rule (section 3): give away artifact-shaped things, never recurring-cost things. An allowance of zero makes that structural rather than a policy someone has to remember. |
| `beta` | $0 (invite) | n/a | **555** | The measurement cohort. Deliberately set above the expected p95 so the cap does not truncate the distribution it exists to measure. This is an abuse stop, not a budget. |
| `blueprint` | $33 one-time | 97% | **99** per 33-day window | 33 x 0.03 = 0.99. `plan_period_end` is set to purchase + 33 days; after that the account falls back to the free allowance while keeping read access to what it bought. That bounds a one-time purchase to a one-time COGS, instead of a perpetual monthly liability against a single $33. |
| `pro` | $11/mo | 75% | **275** | 11 x 0.25 = 2.75, which is exactly the roadmap's stated economics gate: "p95 cost per active user <$2.75/mo, i.e. 25% of $11 (the number that validates the Pro price)" (section 10). |
| `founding` | $222 lifetime, 111 seats | n/a | **333** | Above Pro as the perk. Worst case is 111 x $3.33 = $370/month in perpetuity against $24,642 collected once, roughly 5.5 years of runway at total saturation, which will not happen. The seat cap is what makes an unbounded-duration grant safe. |

**Does 275 cents actually buy a Pro month?** With slice 5 shipped (Haiku, 10-turn history at roughly 3,100 input and 400 output tokens per turn), a chat turn costs 5,100 micro-dollars. 275 cents buys 539 turns. The roadmap's on-theme 222-message cap costs $1.13, leaving $1.62 for art (24 images) or a quarterly report re-run. On Sonnet the same turn costs 15,300 micros, so 275 cents buys 179 turns, which is *under* the 222-message cap the product advertises. That gap is the entire argument for slice 5: without Haiku routing, the advertised meter and the funded meter disagree.

All five numbers are provisional env defaults. Config field:

```python
plan_allowance_cents: str = "free:0,beta:555,blueprint:99,pro:275,founding:333"
```

A `str`, not a `dict`. `pydantic-settings` v2 JSON-parses structured field types at source level before validators run, which is why `allowed_origins` is a `str` with a `get_allowed_origins()` accessor (`config.py:47-51`). Same shape here: `get_plan_allowance_cents() -> dict[str, int]`. An unknown plan name resolves to the `free` allowance and logs an error.

---

## 3. Meter semantics, and issue #220

### 3.1 The two vocabularies

Issue #220 observes that `consume()` (`usage_counters.py:217-241`) increments first and checks the ceiling second, so a blocked attempt still moves the counter. The resolution is that the codebase has two different kinds of meter and they want opposite semantics:

**Counts are attempts.** `llm_calls` and `art_generations` measure pressure on a resource. A client in a retry loop against an exhausted cap *should* show up as 40 attempts, not 3. Suppressing blocked attempts would erase the abuse signal that is the meter's reason for existing, and it changes no gate behaviour: once `count > ceiling`, every subsequent call is blocked regardless of how far past the ceiling the number has drifted. The counter resets at UTC midnight either way (`next_period_start`, `usage_counters.py:82`).

**Spend is delivered cost only.** A ledger that counts money we did not spend is simply wrong, and it would produce false upsells. Spend meters are therefore never consumed speculatively. The flow is check, call, record:

1. `check_ceiling(...)` reads the counter and raises if it is already at or past the ceiling. No increment.
2. The paid call goes out.
3. `increment_and_get(amount=cost_micros)` records what it actually cost.

The cost of this ordering is a bounded overshoot: a call authorized at 99% of budget still runs to completion, so the day or month can exceed its ceiling by roughly one call's cost per concurrent caller. The bound is concurrency, not one: `check_ceiling` is a plain read, so several calls near the ceiling can all pass it before any of them records, and `narrative.py:347-348` already fires five concurrent paid calls per report, meaning one report at the ceiling can overshoot by up to five calls' cost. That is still the correct trade, because we cannot price a call before making it, and the alternative (charge an estimate up front, refund the difference) doubles the write volume to correct a rounding error. The atomic count breaker, not `check_ceiling`, is the hard backstop for the pathological case; slice 4 must not assume `check_ceiling` gives a strict one-call bound.

### 3.2 New primitives in `alchymine/db/usage_counters.py`

```python
async def check_ceiling(*, scope, meter, ceiling, period_key=None) -> int:
    """Return the current count, raising CostCeilingExceeded if it is at
    or past *ceiling*. Does not increment.

    Fails closed exactly like consume(): an unreadable counter blocks the
    call rather than permitting it unmetered.
    """

def current_month_key(now: datetime | None = None) -> str:
    """Return the UTC calendar month, as ``YYYY-MM``."""

def next_month_start(now: datetime | None = None) -> datetime:
    """Return the next UTC month boundary, for retry_at on monthly meters."""
```

`period_key` is `String(16)` (`models.py:788`), so a 7-character month key fits with room to spare. `scope` is `String(64)` and user ids are 36-character UUIDs, also fine.

### 3.3 The full meter list after this session

| Meter name | Scope | period_key | Unit | Ceiling from | Slice |
|---|---|---|---|---|---|
| `llm_calls` | `global` | `YYYY-MM-DD` | calls (attempts) | `global_daily_llm_call_ceiling` = 2000 | shipped, #214 |
| `art_generations` | `<user_id>` | `YYYY-MM-DD` | generations (attempts, refundable) | `daily_art_generations_per_user` = 3 | shipped, #214 |
| `spend_micros_daily` | `global` | `YYYY-MM-DD` | micro-dollars delivered | derived, section 7 | 4 |
| `spend_micros_monthly` | `<user_id>` | `YYYY-MM` | micro-dollars delivered | per-plan allowance x 10,000 | 3 |

The period shape is baked into the meter *name* on purpose. `get_count(scope=user, meter="spend")` with no `period_key` would silently default to today's date key (`usage_counters.py:185`) and return 0 for a monthly meter, reading as "no spend" when the truth is "wrong row." Encoding `daily` and `monthly` in the name makes that mistake impossible to write.

**#220 is closed by this design**, with a comment pointing at this section: counters are attempt meters by design and now say so in their docstring; the number that drives money is delivery-priced and lives in a separate meter and a separate table.

---

## 4. The cost formula

### 4.1 Per-call cost

```
cost_micros = input_tokens                  * price_in_micros
            + output_tokens                 * price_out_micros
            + (cache_read_tokens     * price_in_micros)     // 10
            + (cache_creation_tokens * price_in_micros * 5) // 4
```

Cache reads are 0.1x the base input price; 5-minute cache writes are 1.25x. All four Anthropic usage fields are priced, because pricing only `input_tokens` and `output_tokens` after slice 5 turns caching on would under-count every cached call.

Integer arithmetic throughout, no floats. Multiply before dividing so the two floor divisions truncate less than one micro-dollar per record combined, which is $0.000001. Prices are micro-dollars per token, which for the two models in `CLAUDE_MODELS` (`client.py:499-502`) are:

| Model | $/MTok in | $/MTok out | micros in | micros out |
|---|---|---|---|---|
| `claude-sonnet-4-6` | $3.00 | $15.00 | 3 | 15 |
| `claude-haiku-4-5-20251001` | $1.00 | $5.00 | 1 | 5 |

### 4.2 Price table config

```python
llm_price_table: str = "claude-sonnet-4-6:3:15,claude-haiku-4-5-20251001:1:5"
```

`str` with a `get_llm_prices() -> dict[str, tuple[int, int]]` accessor, for the same pydantic-settings reason as section 2.2. Env var `LLM_PRICE_TABLE`. Per-model prices live here and are never written at a call site.

**Unknown model id:** price it at the most expensive rate in the table and log at ERROR. Never at zero. A model we forgot to add to the table must show up as expensive spend, not as free.

### 4.3 Gemini

Gemini image generation has no per-token accounting in this codebase; `generate_image` (`gemini.py:137`) returns bytes. Pin a flat per-image figure:

```python
gemini_image_cost_micros: int = 67000   # $0.067
```

That is the published price for `gemini-3.1-flash-image-preview` (the configured model, `config.py:74`) at 1K resolution as of August 2026. The same model is $0.045 at 512px and $0.101 at 2K, and the call site does not set a resolution, so 1K is the assumption. **Provisional**, and the one number here that cannot be corrected by measurement from inside the app: it has to be reconciled against a real Google Cloud invoice.

### 4.4 Micro-dollars everywhere, cents only for display

The meters count **micro-dollars**, not cents. Per-call cents with a ceiling round would inflate a Haiku chat turn from 0.51 cents to 1 cent, a 96% over-count, which at the allowance level means users get told they are out of budget at roughly half their real usage.

So: the ledger stores exact `cost_micros`, the meters accumulate `cost_micros`, and `spend_cents` is derived **once, at aggregate time**, with a ceiling:

```python
spend_cents = -(-total_cost_micros // 10_000)
```

Ceiling at the aggregate satisfies the never-under-count rail without distorting the per-call number. Allowances are configured in cents because that is legible to a human, and converted to micros (`cents * 10_000`) at compare time.

`cost_micros` is `Integer`, so a single row tops out around $2,147, and a monthly per-user counter tops out at the same. Both are orders of magnitude above any allowance. Overflow on the global daily counter would require a day above $2,147, which the count breaker (2000 calls) makes unreachable at any plausible per-call price, and would in any case raise inside `increment_and_get`, which `consume` converts to a blocked call. Overflow fails closed.

---

## 5. User-id propagation via contextvars

The three egress sites are inside `alchymine/llm/`. They have no request, no session, and no user. Something has to carry the user id down to them.

### 5.1 Where it lives

New leaf module `alchymine/llm/attribution.py`:

```python
_user_id: ContextVar[str | None] = ContextVar("alchymine_user_id", default=None)
_surface: ContextVar[str | None] = ContextVar("alchymine_surface", default=None)
_request_id: ContextVar[str | None] = ContextVar("alchymine_request_id", default=None)

def set_attribution(*, user_id: str | None, surface: str | None,
                    request_id: str | None = None) -> None
def current_attribution() -> tuple[str | None, str | None, str | None]

@contextmanager
def attributed(*, user_id: str | None, surface: str | None,
               request_id: str | None = None) -> Iterator[None]
```

A leaf module under `alchymine/llm/` rather than `alchymine/api/deps.py`, because `alchymine.api.deps` imports `alchymine.db`, and `usage_counters.py:100-103` already documents the import cycle that creates. Both the API and the Celery worker must import this, so it must depend on nothing.

### 5.2 Where routes set it

`get_current_account()` calls `set_attribution()` and returns the `Account`. It reads `request.state.request_id` (set by `RequestIdMiddleware`, `middleware.py:63`) and passes it as the third field, which is how `usage_records.request_id` gets populated; the leaf module itself never touches `request.state`. Celery-side calls through `attributed(...)` leave `request_id` as `None`, which is honest (there is no HTTP request). No reset needed: each request runs in its own asyncio task with its own copied context, so the value dies with the task and cannot leak between requests.

Surface is set per route: `chat`, `report`, `art`, `brand_logo`.

**This works for SSE.** Starlette awaits `response(scope, receive, send)` from inside the route handler's task, and `StreamingResponse` iterates the async generator there. Async generators run in their caller's context (per-generator contexts were proposed in PEP 568 and never implemented). So the ContextVar set by the dependency is visible inside `_chat_event_stream` (`chat.py:250`) when it reaches the LLM client. This is load-bearing for chat attribution and should have a test that asserts it, not just a comment.

**Do not use `BaseHTTPMiddleware` for this.** It runs the downstream app in a separate task, so a ContextVar set in `dispatch` is not visible to the endpoint. That is a well-known Starlette behaviour and it would produce silently unattributed rows.

### 5.3 Fan-out: two corrections to the assumed shape

The orchestrator does **not** use `asyncio.gather`. `orchestrator.py:155-164` is a sequential `for` loop over `systems_to_invoke` with `asyncio.wait_for` per coordinator, and it deliberately feeds Intelligence results forward into `request_data` for the later coordinators (`orchestrator.py:184-207`). Sequential await, same task, context propagates trivially.

The real LLM fan-out is one layer down, at `alchymine/llm/narrative.py:347-348`:

```python
pairs = await asyncio.wait_for(
    asyncio.gather(*[_gen(s) for s in systems]),
    timeout=300,
)
```

Five concurrent narrative generations, one paid Claude call each. `asyncio.gather` wraps each coroutine in a Task, and Task creation copies the current context, so attribution set before the gather is visible in all five branches. Confirmed by design of `asyncio`, and worth a test that asserts five ledger rows carry the same `user_id`.

### 5.4 The Celery hazard, and the fix

`_run_async` (`workers/tasks.py:57-75`) has two paths:

```python
try:
    asyncio.get_running_loop()
except RuntimeError:
    return asyncio.run(coro)          # path A

with ThreadPoolExecutor(max_workers=1) as pool:
    future = pool.submit(asyncio.run, coro)   # path B
    return future.result(timeout=560)
```

Path A propagates: `asyncio.run` creates the task inside the calling thread's context. Path B **does not**: a new thread starts with a fresh, empty context, so every ContextVar reads its default. Path B is the `CELERY_ALWAYS_EAGER` path, which is how the entire test suite runs, so without a fix the attribution tests would pass in production and fail in CI, or worse, pass in CI while silently attributing nothing in eager mode.

Two-line fix in slice 2:

```python
ctx = contextvars.copy_context()
future = pool.submit(ctx.run, asyncio.run, coro)
```

Then in `generate_report`, resolve the user before narratives run. The task already fetches the report row at `tasks.py:414`; today it re-fetches `user_id` late, at lines 511 and 529, which is after the narrative block at line 476. Resolve it once near line 419 and wrap the narrative section:

```python
with attributed(user_id=report_row.user_id, surface="report_narrative"):
    narratives = _run_async(generator.generate_all(systems, engine_data))
```

Note that `report.user_id` can legitimately be `NULL`: `reports.py:190-194` creates orphan reports when the JWT subject has no matching row. Those calls are genuinely unattributable and land in the unattributed bucket below, which is one more reason the roadmap wants that path 401'd.

### 5.5 When the var is unset

**Record globally, warn loudly, do not block.**

- Write the ledger row with `user_id = NULL` and `scope = 'unattributed'`.
- Log at WARNING with the surface and request id.
- Still charge the global daily spend meter, so an unattributed call cannot escape the budget.
- `/admin/usage` surfaces `unattributed` as its own row in `by_surface`, so the number is visible rather than buried.

This is deliberately *not* fail-closed, and the distinction matters. The fail-closed rail is about the meter being unreachable: if we cannot read the counter, we cannot know whether we have budget, so we block. A missing ContextVar is a different thing entirely, an internal wiring defect, and blocking on it would take down report generation because of a logging bug. The per-user allowance simply cannot be enforced for an unattributed call, which is exactly why the global ceiling still applies to it and why a test asserts all four product chokepoints set attribution.

---

## 6. Capturing tokens on the SSE path

`_stream_claude` (`client.py:504-549`) already uses the stream as an async context manager and iterates `stream.text_stream`. Adding usage capture is a small change to an existing shape.

### 6.1 The pinned mechanism

**There is exactly one recording call site per streamed call: the `finally` block.** The loop body never records. That single site runs on every exit path (normal completion, disconnect, exception), so it cannot double-record the common path and cannot miss the rare one.

```python
async with client.messages.stream(...) as stream:
    try:
        async for text in stream.text_stream:
            delivered_chars += len(text)
            yield text
    finally:
        # The ONLY recording site for this call. Runs once on every path.
        try:
            final = await asyncio.wait_for(stream.get_final_message(), timeout=5.0)
            record exact usage from final.usage
        except Exception:
            record estimated usage (estimated=True), section 6.2
```

`get_final_message()` returns the accumulated `Message` after `message_stop`, and its `.usage` carries `input_tokens`, `output_tokens`, `cache_creation_input_tokens` and `cache_read_input_tokens`. On normal completion the stream is already drained, so the awaited call returns immediately with exact numbers. This is the only place in the codebase that can learn what a streamed reply cost; today the SSE path discards it entirely.

`_generate_claude` (`client.py:551`) already reads `response.usage.input_tokens` and `.output_tokens` for a log line at 586-591 and puts them on `LLMResponse`. It needs the two cache fields added and a ledger write, nothing more.

### 6.2 Client disconnect, and capture-on-close

If the browser goes away mid-stream, the consumer stops iterating and the async generator is finalized: `GeneratorExit` is raised at the `yield`, and the `async with` exits. A capture placed after the loop would never run, so a naive implementation loses the cost of a call that was fully paid for. The single-site `finally` in 6.1 is the answer: on disconnect it still runs, `get_final_message()` usually cannot complete against a torn-down stream, and the `except` arm records the estimate instead:

```python
record estimated usage:
    input_tokens  = len(system_prompt + prompt) // 4
    output_tokens = delivered_chars // 4
    estimated = True
```

Awaiting during async-generator finalization is permitted (that is why `aclose()` is a coroutine); yielding a value after `GeneratorExit` is not, and this code does not. The bounded `wait_for` matters because after a disconnect the upstream HTTP response may still be undrained, and `get_final_message()` could otherwise block until the 90-second client timeout.

`estimated=True` rows are the honest signal that a number is a floor, not a measurement. `/admin/usage` reports the estimated share; if it is more than a few percent, the disconnect path needs another look rather than quiet acceptance.

### 6.3 The fail-closed rule for ledger writes

The rail is that a cost-bearing call whose usage record cannot be written must not proceed silently. Applied literally to a streaming call, that would mean raising after the user has already read the reply, which does not unspend the money and only converts a logging failure into a user-visible fault.

The precise rule:

> **A ledger-write failure must be loud and must fail the *next* call, not the current one.**

Mechanically — **amended 2026-08-13 (PR #232) to what slice 2 actually shipped.** The original draft put this block in `check_ceiling`; review moved it, for the reasons below.

1. On ledger `INSERT` failure — or on a failed spend-meter increment, which loses the same accounting — log at ERROR with the full row as structured JSON, so the spend is reconstructible from logs.
2. Open a process-local degraded episode. The row and both meters have to land before it ends, so recovery is never declared while the meters are still failing.
3. `charge_paid_call` calls `claim_ledger_admission()` before `consume()` and raises `CostCeilingExceeded(reason="meter_unavailable")` when it is refused, which the existing handler at `main.py:125-144` renders as a structured 503. **This is the only admission gate.**
4. The episode ends on the next successful write.

**`check_ceiling` never consults ledger health.** It is a pure counter read. Slice 3 calls it at the route layer to price a per-user allowance, where a degraded ledger is not that user's fault and would render a 402/429 upsell for an internal fault; a degraded ledger is a global 503 at the chokepoint or it is nothing. A second gate would also claim the probe below twice for a single call. `check_ceiling` keeps its own fail-closed rule for an unreadable counter, which is a different failure.

**The episode is a circuit breaker, not a latch.** A pure latch deadlocks: every paid call is blocked, so no write is attempted, so nothing can clear it, so one failed `INSERT` takes the process down until somebody restarts it. After `LEDGER_DEGRADED_RETRY_SECONDS` (env, default 60) the breaker goes half-open — and half-open means **one probe, not an open door**. A purely time-based lapse would admit every caller until somebody's write failed and re-armed it, which under a sustained database failure with steady traffic is a cooldown's worth of unrecorded spend per cycle; the report path alone fires five paid calls at once. So the first caller after the lapse claims the probe under a `threading.Lock` — the Celery path runs its coroutines in a worker thread, so the race is real — and everyone else stays refused until that probe resolves: a successful write ends the episode, a failed one re-arms the cooldown. Two known interleavings widen that to at most two admitted calls — a pre-episode write failing while a probe is live frees the slot, and a stream outliving the probe timeout lets its claim go stale — both bounded, both loud (every failed write still logs its full row), neither a silent drop, and both tracked in issue #235.

A claim older than `LEDGER_PROBE_TIMEOUT_SECONDS` is treated as abandoned and can be replaced, because a probe whose call died before writing would otherwise wedge the gate shut forever, which is the same deadlock in a new place. That one stays a module constant rather than an env var: it is derived from the 90-second LLM client timeout so a slow-but-alive call is never mistaken for a dead one, and it should move when that timeout moves, not when traffic does.

With the ledger switched off (`USAGE_LEDGER_ENABLED=false`) the gate is skipped and the episode is cleared. Turning the ledger off is how an operator stops a write storm; it must not be the thing that takes every paid surface down.

In the common case (Postgres unreachable) this is belt and braces, because `consume()` hits the same database and fails closed on its own. The episode covers the case the natural path misses: an `INSERT` that fails for a non-connectivity reason, such as a constraint violation or an oversized field, while reads still succeed.

---

## 7. The global budget

### 7.1 Formula

```python
monthly_llm_spend_budget_usd: float = 300.0    # MONTHLY_LLM_SPEND_BUDGET_USD
daily_spend_headroom_factor: float = 1.5       # DAILY_SPEND_HEADROOM_FACTOR

daily_global_spend_ceiling_micros = int(
    monthly_llm_spend_budget_usd * 1_000_000 / 30 * daily_spend_headroom_factor
)
```

$300/month gives $10/day flat, x1.5 headroom = **$15/day**.

**Why headroom at all.** Usage is bursty: a launch day, a batch of reports, one enthusiastic beta tester. A flat `monthly/30` ceiling trips on any above-average day and takes every paid surface down until UTC midnight. 1.5x absorbs a 50% spike. The cost of that choice is that a sustained month at the daily ceiling would land at 1.5x budget, which is the explicit trade: the daily ceiling is a runaway stop, not a budget enforcer.

**Why $300 and not $200.** A busy beta day at roadmap cost estimates is 20 reports ($2.20) plus 500 chat turns ($5.00 at Sonnet) plus 30 images ($2.01), around $9.20. A $200 budget yields a $10/day ceiling, which that day would nearly trip. The existing config comment about the call breaker says it well and applies here: raise it before it pinches real users.

**No automated monthly kill switch.** Month-to-date spend is surfaced in `/admin/usage` with budget remaining, and crossing 80% logs at ERROR with the same `COST_BREAKER`-style marker used at `cost_guard.py:56`. It does not automatically stop anything. An automatic monthly cutoff converts an overspend into an outage of unknown length, potentially weeks, and the person who should make that call is a human looking at the number.

### 7.2 Enforcement, using the machinery that already exists

All three egress sites already call `charge_paid_call()` (`client.py:520`, `client.py:565`, `gemini.py:191`). Extend that one function rather than adding call sites:

```python
async def charge_paid_call() -> None:
    await consume(scope=GLOBAL_SCOPE, meter=METER_LLM_CALLS,
                  ceiling=settings.global_daily_llm_call_ceiling)          # existing
    await check_ceiling(scope=GLOBAL_SCOPE, meter=METER_SPEND_MICROS_DAILY,
                        ceiling=settings.daily_global_spend_ceiling_micros())  # new
```

Slice 4 then needs zero new call sites and inherits the existing 503 rendering, the existing frontend handling (`ArtUnavailableError` in `web/src/lib/artApi.ts:37`), and the existing `event: error` frame in chat (`chat.py:307-316`).

**Division of labour, stated once:**
- **Chokepoint (`charge_paid_call`)**: global breakers only. Renders as a 503 wait state. Nobody's fault, clears on a schedule we can name.
- **Route layer (`require_allowance(account)`)**: per-user entitlement and allowance. Renders as a 402 or 429 upsell. Specific to this account, resolved by upgrading.

The count breaker stays as the outer backstop. At $15/day and roughly $0.01 per average call, spend binds first for typical traffic; the 2000-call ceiling binds first only for unusually cheap calls, which is exactly the case a dollar ceiling would miss.

### 7.3 `GET /admin/usage`

Lives on the existing admin router (`APIRouter(prefix="/admin")`, `admin.py:46`), behind `get_current_admin`, alongside `/analytics/overview` (`admin.py:824`). Query param `top` (default 20, 1 to 100).

Counters answer "are we blocked"; the ledger answers "what did it cost". The endpoint reads gates from `usage_counters` and every aggregate from `usage_records`.

```json
{
  "as_of": "2026-08-13T14:22:05Z",
  "today": {
    "period_key": "2026-08-13",
    "spend_micros": 412000,
    "spend_cents": 42,
    "ceiling_micros": 15000000,
    "remaining_micros": 14588000,
    "llm_calls": 138,
    "llm_call_ceiling": 2000,
    "estimated_record_count": 2
  },
  "month": {
    "month_key": "2026-08",
    "spend_micros": 5120000,
    "spend_cents": 512,
    "budget_micros": 300000000,
    "remaining_micros": 294880000,
    "pct_of_budget": 1.7
  },
  "by_surface": [
    { "surface": "chat", "calls": 96, "cost_micros": 489600, "cost_cents": 49 },
    { "surface": "report_narrative", "calls": 35, "cost_micros": 770000, "cost_cents": 77 },
    { "surface": "unattributed", "calls": 0, "cost_micros": 0, "cost_cents": 0 }
  ],
  "by_model": [
    { "model": "claude-haiku-4-5-20251001", "calls": 96,
      "input_tokens": 297600, "output_tokens": 38400,
      "cache_read_input_tokens": 0, "cost_micros": 489600 }
  ],
  "top_users": [
    { "user_id": "…", "email": "…", "plan": "beta", "calls": 42,
      "cost_micros": 210000, "cost_cents": 21,
      "allowance_cents": 555, "pct_of_allowance": 3.8 }
  ]
}
```

`by_surface` and `by_model` cover both today and the month (two blocks, or a `?window=today|month` param; either is fine, pick one and be consistent). `top_users` is the view that answers the question the roadmap says validates the Pro price: what does the p95 active user actually cost.

---

## 8. Slice 5: Haiku routing and prompt caching

### 8.1 Chat on Haiku

```python
llm_chat_model: str = "claude-haiku-4-5-20251001"   # LLM_CHAT_MODEL; "" = default chain
```

`_stream_claude` walks `CLAUDE_MODELS` (`client.py:499`) on 529. Add an optional `model` parameter to `stream_generate` and `_stream_claude`: when set, that model becomes the head of the chain and the remaining entries stay as fallbacks with duplicates removed. Chat passes `settings.llm_chat_model`; report narratives pass nothing and keep the Sonnet-first chain untouched.

The fallback direction stays downhill in price, which is the property PR #214 restored when it dropped Opus (`client.py:492-498`). Haiku-first means the chain is Haiku then Sonnet, so a 529 on Haiku escalates cost. That is acceptable and correct: 529s are rare, and the alternative is telling the user the coach is unavailable.

Per-turn cost, same 1,100-in / 400-out turn:

| | Sonnet | Haiku | Delta |
|---|---|---|---|
| No history (1,100 in / 400 out) | 9,300 micros | 3,100 micros | **-67%** |
| 10-turn history (3,100 in / 400 out) | 15,300 micros | 5,100 micros | **-67%** |
| 222 turns/month with history | $3.40 | $1.13 | **-$2.27** |

$3.40 does not fit inside a 275-cent Pro allowance. $1.13 does, with room for art. That is the number this slice exists to produce.

### 8.2 Prompt caching, and the honest expectation

```python
llm_prompt_cache_enabled: bool = True   # LLM_PROMPT_CACHE_ENABLED
```

Shape: the system prompt becomes a list with a cache breakpoint on the stable prefix, stable content first, volatile content after the last breakpoint.

```python
system=[{"type": "text", "text": stable_prefix,
         "cache_control": {"type": "ephemeral"}}]
```

**The constraint that decides whether this pays.** The minimum cacheable prefix is model-dependent: 4,096 tokens on `claude-haiku-4-5`, 1,024 on `claude-sonnet-4-6`. A shorter prefix is silently not cached. No error, no warning, no cache-hit tokens.

Measured against the actual prompts: the five assembled specialist prompts in `agents/growth/system_prompts.py` run 3,453 to 3,528 characters each, roughly 860 to 880 tokens. That is right at Sonnet's minimum and **far below Haiku's 4,096**. So:

> On chat as it stands today, with Haiku routing on, prompt caching will produce **zero cache hits**. Ship the breakpoint anyway (it is a no-op below the minimum and costs nothing), but do not book a saving the token math does not support.

The mechanism starts paying once the roadmap's Phase 0 chat item lands, which appends profile context and the last 10 turns and pushes the stable prefix past 4,096 tokens. Note also that `chat.py:285` currently calls `build_system_prompt(system_key, None)` with no profile and no history at all, so the "per-system context" this design would cache does not exist on main yet.

**Acceptance criterion, not an assumption:** within 24 hours of enabling, `SELECT sum(cache_read_input_tokens) FROM usage_records WHERE surface='chat'` is greater than zero. Slice 2 makes that query possible, which is why caching is last. If it stays at zero, the prefix is under the minimum and the answer is to grow the stable prefix or turn the flag off, not to assume it is working.

Report narratives are out of scope for caching. Their system prompts are per-system templates filled with per-user data (`narrative.py:278`), so the stable and volatile parts are interleaved and would need the templates split before a breakpoint means anything.

### 8.3 Flag mechanics

`get_settings()` is `lru_cache`d, so both flags are read once per process. Flipping either one takes a container restart, not just an env change. Say so in the runbook line of the PR description so nobody flips a var and concludes the flag is broken.

---

## 9. Rollout order and blast radius

| Slice | Ships | What it can break | What to test |
|---|---|---|---|
| **1** | Migration 0017, `Account`, `get_current_account()` | The migration itself. Every column is nullable or defaulted, so no rewrite and no lock that matters. The `UPDATE users SET plan='beta'` is the risky line: if it does not run, every beta account lands on the free allowance and slice 3 locks them all out. | Alembic up and down against a copy of production. Assert every pre-existing row is `plan='beta'`, a fresh insert is `plan='free'`, and `get_current_account` matches `get_current_admin`'s 401/403 behaviour on a disabled account. |
| **2** | `usage_records`, `ledger.record_usage()`, contextvars, `_run_async` context fix, SSE `get_final_message()` | One extra DB write per paid call on the same pool (single-digit ms). A bug in the `finally` could break narrative generation or truncate a chat stream. | Ledger row written for stream, non-stream and Gemini paths; five rows with one `user_id` after the `narrative.py:348` gather; a row with `estimated=True` on simulated disconnect; attribution survives eager-mode Celery. |
| **3** | Per-plan allowances, `require_allowance()`, 402/429 upsell responses, frontend states | **First slice that can tell a user no.** Beta at 555 cents should never bind. Free at 0 binds immediately, by design. A wrong plan value from slice 1 locks out the beta. | Each plan against each of the four chokepoints; assert `beta` passes at realistic volume; assert the 429 body carries `code`, `message`, `retry_at`, `upgrade_url`; assert the SSE path returns a real 429 before the stream opens rather than an error frame. |
| **4** | Spend meters, `check_ceiling` in `charge_paid_call`, `GET /admin/usage` | A mis-set budget takes every paid surface down until UTC midnight. Default is generous ($15/day against measured beta usage nearer $1-2/day). **Wire the spend ceiling into `charge_paid_call`, next to the admission gate slice 2 put there. Do NOT re-add a ledger-health check inside `check_ceiling`** — see 6.3: one gate, or the half-open probe gets claimed twice for one call. | Ceiling arithmetic; a tripped spend breaker renders the existing 503 shape; `/admin/usage` totals reconcile against a hand-summed `usage_records` fixture. |
| **5** | Haiku chat routing, prompt cache breakpoint | Reply quality on the most-touched surface. Reversible by env plus restart. | Model id recorded in `usage_records` equals `llm_chat_model`; report narratives still record Sonnet; cache tokens appear or the criterion in 8.2 fails and the flag goes off. |

### The four product chokepoints and how each is gated

| Chokepoint | Entitlement (402 `plan_upgrade_required`) | Allowance (429 `plan_allowance_reached`) | Notes |
|---|---|---|---|
| `POST /reports` (`reports.py:136`) | free is refused | monthly spend | Do **not** gate by system count: `intent.py:241-246` forces all five coordinators in one pass, so withholding systems saves zero COGS. |
| `GET /reports/{id}/pdf` (`reports.py:482`) | free is refused | none | Serves `report.pdf_data` bytes that were already paid for. Entitlement gate, not a spend meter. |
| `POST /chat` (`chat.py:345`) | free is refused | monthly spend | Checked in the endpoint **before** `StreamingResponse` is returned, so a real status code is still available. |
| `POST /art/generate` (`generative_art.py:248`) and `POST /art/brand/logo` (`generative_art.py:531`) | free is refused | monthly spend, on top of the existing 3/day count cap | Both already share `_charge_daily_allowance` (`generative_art.py:185`) deliberately, since they hit the same paid generator. |

Response envelope extends the one the frontend already parses (`readUnavailable`, `web/src/lib/artApi.ts:64`):

```json
{ "detail": {
    "code": "plan_allowance_reached",
    "message": "You've used this month's included coaching. Upgrade to keep going.",
    "retry_at": "2026-09-01T00:00:00Z",
    "meter": "spend_micros_monthly",
    "plan": "free",
    "upgrade_url": "/pricing"
} }
```

The frontend switches on `detail.code`, not the status code. Both new codes join the union in `ArtUnavailableError` and render as the yellow `role="status"` wait/upsell state used on the creative-studio, journey and brand pages, never the red `role="alert"` error state. A quota rejection is a sales moment, not a fault.

### Slice 2 changes no blocking behaviour

Stated explicitly because it is the slice most likely to be blamed for an unrelated incident: **slice 2 introduces no new ceiling, no new 402, no new 429, and no new 503 path.** The only behaviour change it can produce is the fail-closed rule in section 6.3, where a failed ledger write causes the *next* cost-bearing call to be blocked as `meter_unavailable`. Everything else it adds is a write and a log line. Slice 3 is where the product starts saying no.

---

## 10. Provisional numbers register

Every figure below is an env default chosen from the roadmap's model, not from measurement. The roadmap's standing risk 6 applies to all of them: "$11 without 2-4 weeks of usage_records is a guess wrong in either direction." Revisit as a set once slice 2 has produced 2 to 4 weeks of beta data.

| Env var | Default | Basis |
|---|---|---|
| `PLAN_ALLOWANCE_CENTS` | `free:0,beta:555,blueprint:99,pro:275,founding:333` | price x (1 - margin target), section 2.2 |
| `LLM_PRICE_TABLE` | `claude-sonnet-4-6:3:15,claude-haiku-4-5-20251001:1:5` | published API prices; changes when the price list changes |
| `GEMINI_IMAGE_COST_MICROS` | `67000` | published price, 1K resolution, August 2026. Reconcile against a real invoice |
| `MONTHLY_LLM_SPEND_BUDGET_USD` | `300.0` | busy-beta-day arithmetic, section 7.1 |
| `DAILY_SPEND_HEADROOM_FACTOR` | `1.5` | burst absorption vs 1.5x monthly worst case |
| `GLOBAL_DAILY_LLM_CALL_CEILING` | `2000` | unchanged from #214 |
| `DAILY_ART_GENERATIONS_PER_USER` | `3` | unchanged from #214 |
| `LLM_CHAT_MODEL` | `claude-haiku-4-5-20251001` | section 8.1 |
| `LLM_PROMPT_CACHE_ENABLED` | `true` | no-op until the prefix clears 4,096 tokens, section 8.2 |
| `USAGE_LEDGER_ENABLED` | `true` | kill switch for slice 2 |
| `LEDGER_DEGRADED_RETRY_SECONDS` | `60.0` | circuit-breaker cooldown before a single probe is admitted, section 6.3 as amended (added in slice 2 review) |

The two figures the ledger will settle first: cost per full report (roadmap models $0.07-0.18, gate is $0.30 all-in) and p95 cost per active user per month (gate is $2.75). Neither is knowable today, because nothing in the codebase has ever recorded a token.

---

## 11. Open questions

- [ ] Does `plan='blueprint'` keep chat access inside its 33-day window, or is chat Pro-only? This design assumes chat is included and metered against the 99-cent window; the alternative is a cleaner upsell but a thinner artifact.
- [ ] Confirm 1K is the default resolution `generate_image` receives from `gemini-3.1-flash-image-preview` when `GenerateContentConfig` sets no size (`gemini.py:194-200`). If it defaults to 2K, the per-image figure is $0.101, not $0.067, and every art number here moves by 50%.
- [ ] Orphan reports (`reports.py:190-194`, `user_id=None`) are unattributable spend. The roadmap wants them 401'd. Does that land in slice 3 with the entitlement gate, or separately?
- [ ] Do `estimated=True` rows count against a user's monthly allowance? This design says yes (a floor estimate is closer to the truth than zero), but it means a flaky connection can cost a user allowance for a reply they never fully received.

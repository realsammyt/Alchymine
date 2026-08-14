# Design: Practice Layer (epic #251, slice 0)

**Date:** 2026-08-14
**Status:** Proposed. Slices 1-5 (#253-#257) implement it.
**Baseline:** main `d5eaabd`, backend 2724 passed / 1 skipped, web 411 passed / 47 suites, CI green, Alembic head 0017.
**Depends on:** epic #221 (entitlements, ledger, allowances, Haiku chat routing) shipped.
**Serves:** `docs/plans/2026-08-12-monetization-roadmap.md` §7 (Phase 2 retention spine), the gate on opening the $11 Pro tier.

---

## 1. What this builds and why

Alchymine has an integration layer: journal, journey, outcomes, spiral routing (ADR-007), a healing-skills loader, a metered chat coach, cross-system bridges. It has no practice layer. There is nothing a user repeats, nothing that tracks whether repeating it changed anything, and nothing that decides what to repeat next.

This epic adds five pieces, all generic:

1. A practice-pack schema (v2) and a loader that mounts packs from inside and outside the repo.
2. A practice log, so completion is a fact in Postgres rather than a client-side checkbox.
3. A deterministic ecology recommender that balances practice across five capacity dimensions. Zero LLM calls.
4. A daily protocol surface: three time slots, 3 to 7 practices, self-check questions, rhythm display with no loss aversion.
5. An integration loop: intention, experience, reflection, tracked capacity change, landing on the journal and outcomes surfaces that already exist.

Plus one metered addition: a `practice` coach scope that rides the existing chat path.

Third-party branded practice content is out of scope for the repo, permanently. It arrives later as licensed external packs mounted from a configured directory. Section 8 is the architectural boundary that makes that possible.

### Architecture

```
  ┌──────────────── in-repo ────────────────┐   ┌─── mounted, outside repo ───┐
  │  engine/practice/packs/                 │   │  PRACTICE_PACK_DIRS         │
  │    alchymine-foundations/  (10, CC-BY-NC)│   │    <licensed-pack>/          │
  └────────────────────┬────────────────────┘   └──────────────┬──────────────┘
                       │                                       │
                       └──────────────┬────────────────────────┘
                                      ▼
                      ┌───────────────────────────────┐
                      │  PracticeRegistry (startup)   │  validate schema, DAG,
                      │  frozen, process-global       │  category, license, prose
                      └───────┬───────────────┬───────┘
                              │               │
              ┌───────────────▼──────┐   ┌────▼──────────────────┐
              │  EcologyRecommender  │   │  GET /practices       │
              │  deterministic, 0 LLM│   │  GET /practices/packs │
              └───────┬──────────────┘   └───────────────────────┘
                      │  reads
        ┌─────────────▼──────────────┬──────────────────┐
        │  practice_log              │  ecology_state   │   (0018)
        │  integration_entries       │                  │
        └─────────────┬──────────────┴──────────────────┘
                      │  derived write (one row)
                      ▼
              outcome_metrics ─────────────▶ dashboard / journey
                      ▲
                      │ links (SET NULL)
              journal_entries

  metered path (unchanged shape):
    POST /chat (system_key='practice') ─▶ require_chat ─▶ get_current_account
      ─▶ detect_crisis / check_text ─▶ LLMClient ─▶ charge_paid_call ─▶ record_usage
```

---

## 2. Practice-pack schema v2

One directory per pack: a `pack.yaml` manifest plus one `*.yaml` per practice, non-recursive glob, matching the healing-skills loader's shape (`engine/healing/skills/loader.py:64`).

### 2.1 The five purpose dimensions

Purposes are capacities a practice develops. They map one-to-one onto the five pillars, so `practice_log.primary_purpose` joins against `outcome_metrics.system` and the bridges registry's `VALID_SYSTEMS` with a lookup table and no translation logic.

| Purpose key | Pillar | One-line definition |
|---|---|---|
| `self-knowledge` | intelligence | Noticing your own patterns while they are running, not afterwards. |
| `steadiness` | healing | Coming back to a workable baseline after something knocks you off it. |
| `stewardship` | wealth | Acting well with limited resources across a longer horizon than the moment. |
| `expression` | creative | Moving an inner impulse into an outward form somebody else could meet. |
| `reframing` | perspective | Holding more than one account of the same situation without collapsing to one. |

The mapping lives in `engine/practice/purposes.py` as a frozen dict, with a `VALID_PURPOSES: frozenset[str]` checked by the schema validator (not only by tests, which is where the bridges registry left it, `engine/bridges/registry.py:25`).

The upstream corpus whose structure informed this schema carried a fifth slot for daily-protocol composition. That is not a capacity, so it is not a purpose here. It is the protocol surface (§6).

### 2.2 Category enum and the state-induction exclusion

`category` describes what kind of activity the practice is. It is the safety-class dimension.

Accepted: `reflection`, `attention`, `somatic`, `relational`, `enactment`.

Rejected, enumerated by name so the failure message is specific:

```python
REJECTED_CATEGORIES: dict[str, str] = {
    "state-induction": (
        "State-induction practices need screening questions, contraindication "
        "review and a supervision model that this schema does not carry. "
        "Alchymine does not ship them."
    ),
    "breath-retention": ...,   # same reason
    "fasting": ...,
    "cold-immersion": ...,
    "sensory-deprivation": ...,
    "substance": ...,
}
```

Validation order matters. The validator checks `REJECTED_CATEGORIES` **before** the accepted-set check, so a pack declaring `category: state-induction` fails with the reason rather than with "not a valid enumeration member". The exclusion is enforced by the engine, not by editorial vigilance.

Honest limit: the engine enforces *declared* category. A pack could declare `somatic` and ship breath retention in its body text. That is what the external-pack contract (§8.4) and human review cover. The engine closes the easy hole and says so.

### 2.3 Pack manifest (`pack.yaml`)

```yaml
schema_version: "2.0"          # Literal["2.0"], required
pack_id: alchymine-foundations # slug [a-z0-9-], unique across all mounted dirs
title: "Foundations"
summary: "One line."
version: "1.0.0"               # the pack's own content version, free string
license: "CC-BY-NC-SA-4.0"     # required, min_length 1
attribution: "Alchymine Contributors"   # required, min_length 1
source_url: null               # optional
bundled: true                  # true only for the in-repo pack
```

`PackManifest` is a separate Pydantic model from `PracticeDefinition`. This is deliberate: the healing schema put everything on one frozen `extra="forbid"` model, which is why license fields cannot be added to a healing skill YAML today (`engine/healing/skills/schema.py:27`). Splitting manifest from practice means license metadata has somewhere to live that does not compete with practice fields.

### 2.4 Practice definition (one YAML per practice)

```yaml
slug: name-the-pattern         # unique within the pack; qualified id is pack_id/slug
title: "Name the Pattern"
order: 1                       # int >= 0, display order within the pack
summary: "One line, shown on the card."
purposes: [self-knowledge]     # 1..3 entries, no duplicates, all in VALID_PURPOSES
category: reflection
builds_on: []                  # slugs in THIS pack
related: []                    # slugs in THIS pack, advisory
use_when:                      # >= 1 situational trigger, drives the "why this" line
  - "You keep having the same argument with yourself."
description: |                 # the body, multi-paragraph
  ...
expected_shift: "What is different afterwards, in one or two sentences."
applications:                  # >= 1
  - "Before a conversation you have been putting off."
daily_prompts:                 # EXACTLY 3, positionally morning / day / evening
  - "..."
  - "..."
  - "..."
self_check:
  failure_mode: "This becomes a way to describe the problem instead of touching it."
  question: "Did naming it change what you did next, or only what you called it?"
scaffold_note: "What this is holding up, and what it looks like when you no longer need it."
duration_minutes: 10           # int, 0 < n <= 120
evidence_rating: C             # Literal["A","B","C","D"], same scale as healing skills
contraindications: []          # list[str], default empty
tags: []                       # list[str], default empty
featured: false
```

Constraints and validators:

- `model_config = ConfigDict(frozen=True, extra="forbid")`, matching `SkillDefinition`.
- `slug` validator mirrors `SkillDefinition._validate_name_slug`: lowercase, `[a-z0-9-]`, no spaces or underscores.
- `daily_prompts` must be exactly 3. The three positions are the protocol's three slots (§6), so every practice is renderable in any slot without a per-practice decision.
- `self_check.question` must end with `?`. A self-check is a reflective question, never a verdict.
- `duration_minutes <= 120`: anything longer is not a daily practice, and the cap is a soft safety bound.
- `evidence_rating` reuses the healing A-D scale verbatim, including its docstring, so one rating vocabulary covers both loaders.

### 2.5 Prose gate at load time

Every text field (`summary`, `description`, `expected_shift`, `applications`, `daily_prompts`, `self_check.*`, `scaffold_note`, `use_when`) is concatenated and passed through `check_text(text, context="general")` (`agents/quality/ethics_check.py:355`) at pack load. Any violation at ERROR severity fails the load, naming the file and the violation.

Zero cost (the checker is regex-based) and it means an external pack passes the same fatalistic-language, diagnostic-language and dark-pattern gates that generated narratives already pass. This is the reuse that makes the ethics rail apply to content Alchymine did not write.

### 2.6 builds_on graph rules

- Edges reference slugs **within the same pack only**. Cross-pack edges are a load error. Justification: an external pack cannot depend on a pack it may not be mounted alongside, and per-pack graphs make load order irrelevant to validation.
- The graph must be acyclic. A cycle is a load error naming the cycle members.
- No single-root requirement. A pack spanning five purposes naturally has several roots. A pack where every practice has a `builds_on` is necessarily cyclic, so "at least one root" falls out of the DAG check rather than needing its own rule.
- An unresolved edge is a hard error: `PracticePackValidationError: pack 'x' practice 'y' (y.yaml): builds_on references unknown slug 'z'`.
- `related` resolves under the same rules, same error class.
- `progression_depth` (longest path from any root) is computed once at load and cached on the registry. The recommender reads it; it is not a YAML field.

Error classes, mirroring the healing loader's naming:

```python
class PracticePackValidationError(ValueError): ...
class PracticeNotFoundError(KeyError): ...
class PackNotFoundError(KeyError): ...
```

This is new machinery. The bridges registry validates its system enum only in tests (`tests/engine/test_bridges_registry.py`) and returns an empty tuple for an unknown system at runtime. External packs cannot rely on repo tests, so every rule above is enforced in the loader itself.

### 2.7 Schema evolution

`schema_version` is `Literal["2.0"]` today. The evolution rule: a 2.1 adds only optional fields with defaults, so 2.0 packs keep loading, and the Literal widens to `Literal["2.0", "2.1"]`. A breaking change becomes 3.0 and the loader dispatches by version to a separate model. `extra="forbid"` stays: silent typo acceptance in a licensed external pack is worse than a loud failure.

---

## 3. External-pack mount

### 3.1 Configuration

```python
# config.py, alongside healing_skills_external_dir
practice_pack_dirs: str = ""   # comma-delimited absolute paths

def get_practice_pack_dirs(self) -> list[Path]:
    """Return PRACTICE_PACK_DIRS as a list of paths, empty when unset."""
```

Declared as `str` with an accessor, not `list[str]`. pydantic-settings v2 JSON-parses structured field types at source level before validators run, which is the same reason `plan_allowance_cents` is a `str` with `get_plan_allowance_cents()`. Comma is the delimiter (not `os.pathsep`) for consistency with that precedent, and it is safe on Windows where paths contain `:` but not `,`.

### 3.2 Load order, duplicates, caching

1. Bundled pack directory (`engine/practice/packs/`), always first.
2. Each configured external dir, in declared order.

Duplicate `pack_id` across directories is a hard error. Practice slugs are namespaced by pack, so slug collisions across packs are normal and not an error (this is the improvement over `SkillRegistry`, where the flat name space forces cross-directory duplicate errors on skill names).

One process-global registry, built during FastAPI lifespan startup, frozen models, read-only afterwards. Reload requires a process restart, stated plainly: there is no reload endpoint, because an endpoint that re-reads a configurable filesystem path is a surface nobody has asked for and the deploy already restarts containers.

The registry builder is a plain function in `engine/practice/` that the API, the Celery worker and any future MCP server all call. The healing loader's failure mode (the MCP server ignores the external dir entirely) comes from the loading logic living in the API router; putting it in the engine is the fix.

### 3.3 Failure policy

The healing wrapper's silent swallow is the anti-pattern to avoid:

```python
except (FileNotFoundError, SkillValidationError) as exc:
    logger.warning("Skipping external healing skills: %s", exc)   # routers/healing_skills.py:50-51
```

An operator who mistypes a mount path gets a quietly smaller product and no signal. The practice loader hard-fails at startup on every one of:

| Condition | Behavior |
|---|---|
| Bundled pack fails any validation | Startup fails. A broken bundled pack is a shipping bug. |
| Configured dir missing or unreadable | Startup fails. Configuring a dir asserts its content is required. |
| Configured dir exists but contains zero `pack.yaml` | Startup fails. This is the wrong-volume-mount case, the most likely production mistake. |
| Non-bundled pack with empty `license` or `attribution` | Startup fails. |
| Unresolved edge, cycle, rejected category, prose gate | Startup fails, naming file and reason. |
| `PRACTICE_PACK_DIRS` unset | Normal. Bundled pack only. |

Startup rather than first request, so a bad configuration shows up in container health and the deploy's own machinery, rather than as a 500 for whichever user hits `/practices` first.

---

## 4. Migration 0018

`alchymine/db/migrations/versions/2026_08_14_0018_add_practice_layer.py`, `down_revision = "0017"`. Forward-only and idempotent throughout (inspect table names, guard each `create_table`), matching 0015 and 0017.

All three tables use `String(36)` uuid primary keys, matching `journal_entries` and `outcome_metrics`. No `BigInteger`, so the `_pk_type()` SQLite variant from 0017 (issue #230 precedent, SQLite only aliases a PK to rowid when the declared type is exactly INTEGER) is **not** needed here. Noted so nobody adds it by pattern-match.

### 4.1 `practice_log`

One row per logged practice event.

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) PK | uuid |
| `user_id` | String(36) FK users.id ON DELETE CASCADE | indexed |
| `pack_id` | String(64) NOT NULL | |
| `practice_slug` | String(64) NOT NULL | |
| `primary_purpose` | String(32) NOT NULL | first declared purpose, denormalized at write |
| `purposes` | JSON NOT NULL | full declared list, for display |
| `category` | String(32) NOT NULL | |
| `status` | String(16) NOT NULL default `'completed'` | `completed \| skipped \| started` |
| `protocol_slot` | String(16) NULL | `morning \| day \| evening \| unscheduled` |
| `duration_minutes` | Integer NULL | actual, if the user reports it |
| `occurred_at` | DateTime(tz) NOT NULL | indexed |
| `day_key` | String(10) NOT NULL | `YYYY-MM-DD` in the user's local day, client-supplied |
| `created_at` | DateTime(tz) server_default now() | |
| `reflection` | Text, `EncryptedString()` | comment `SENSITIVE — encrypted` |
| `self_check_response` | Text, `EncryptedString()` | comment `SENSITIVE — encrypted` |

Indexes: `(user_id, day_key)`, `(user_id, primary_purpose, occurred_at)`, `(user_id, pack_id, practice_slug, occurred_at)`.

**Encryption tradeoff, stated because it is load-bearing.** The recommender aggregates by `primary_purpose`, `day_key`, `pack_id`, `practice_slug`, `status` and `occurred_at`. Fernet is non-deterministic, so an encrypted column cannot be grouped or compared in SQL. Encrypting those columns would move the entire recommender into Python over a full table scan. They stay plaintext: they are pack identifiers and timestamps, not content. The two columns holding what the user actually wrote are encrypted, and nothing in the recommender reads them.

`purposes` is denormalized rather than joined against the registry, so a log row stays interpretable after a pack is unmounted or revised.

There is deliberately **no** boolean or scored field on the self-check. The self-check is a reflective question and its answer never feeds the recommender. Scoring it would make it a diagnosis by another name.

### 4.2 `ecology_state`

One row per user. Recommender state only.

| Column | Type | Notes |
|---|---|---|
| `user_id` | String(36) PK, FK users.id ON DELETE CASCADE | PK is the FK; one row per user |
| `protocol_size` | Integer NOT NULL default 5 | clamped 3-7 at the API layer |
| `active_pack_ids` | JSON NULL | user opt-in subset; NULL means all mounted packs |
| `last_recommended_at` | DateTime(tz) NULL | |
| `last_recommendation` | JSON NULL | the emitted set, for the stable-day rule (§5.6) |
| `rotation_cursor` | Integer NOT NULL default 0 | round-robin start offset |
| `created_at` / `updated_at` | DateTime(tz) | |

Nothing encrypted: every column is recommender input and none of it is user-authored text.

**Scope:** practice-scoped only. `ecology_state` models nothing spiral. `route_user` (`engine/spiral/router.py:154`) stays pure and unpersisted, and ADR-007's three depth layers stay in the ADR. If spiral state is ever persisted it gets its own table and its own decision.

### 4.3 `integration_entries`

The link between an intention, an experience and a reflection.

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) PK | uuid |
| `user_id` | String(36) FK users.id ON DELETE CASCADE | indexed |
| `practice_log_id` | String(36) FK practice_log.id ON DELETE CASCADE, NULL | the experience |
| `intention_entry_id` | String(36) FK journal_entries.id ON DELETE SET NULL, NULL | |
| `reflection_entry_id` | String(36) FK journal_entries.id ON DELETE SET NULL, NULL | |
| `purpose` | String(32) NOT NULL | |
| `capacity_delta` | Integer NULL | user self-report, -2..+2, optional |
| `note` | Text, `EncryptedString()`, NULL | comment `SENSITIVE — encrypted` |
| `created_at` | DateTime(tz) server_default now() | |

Indexes: `(user_id, created_at)`, `(user_id, purpose, created_at)`.

Cascade asymmetry is deliberate. Deleting the practice_log row destroys the link (it has no meaning without the experience). Deleting a journal entry is a user-facing action and must not destroy the integration record, so those two are SET NULL.

**Why a table rather than `journal_entries.parent_id`.** A self-referential column on `journal_entries` would change the shape of every journal read and the export contract, and it still could not express "this reflection closes this practice_log row", which is a link between two different tables. A join table expresses the whole triple without touching the journal schema or its API. The journal keeps its free `entry_type` String(50) and its existing client-sent values (`intention`, `practice-log`, `progress`); slice 4 adds no server-side validation there, which stays a separate concern.

---

## 5. The deterministic ecology recommender

`engine/practice/ecology.py`. Pure function of (registry, user's practice_log rows, ecology_state, `now`). No LLM, no network, no RNG. `now` is injected so tests are deterministic.

The design owes its balance-across-purposes framing to Vervaeke's ecology of practices and its "practice changes what you can perceive" framing to von Uexküll's umwelt (§8.6, References). Neither name appears anywhere in the product.

### 5.1 Eligibility

A practice is eligible when all hold:

1. Its pack is mounted and in `active_pack_ids` (or `active_pack_ids` is NULL).
2. Every `builds_on` slug has at least one `status='completed'` log row for this user, ever. **Invariant: never recommend a practice with an unmet prerequisite.**
3. It has no `completed` row for today's `day_key`.
4. It is not *declined*: fewer than `practice_decline_threshold` (default 3) `skipped` rows in the last `practice_balance_window_days` (default 28) with zero `completed` rows in the same window.

Rule 4 is the answer to "a skipped practice keeps coming back". A skip is logged (the recommender must distinguish "never offered" from "offered and declined") but three declines with no completions retires it for the window.

### 5.2 Scoring

Four terms, each in [0, 1], summed with named weights.

```
score = w_balance     * balance_term
      + w_staleness   * staleness_term
      + w_progression * progression_term
      + w_featured    * featured_term
```

- `balance_term = 1 - share_p`, where `share_p = completions_in_purpose_p / max(1, total_completions)` over the last `practice_balance_window_days`. An under-practiced purpose scores high. With no history every share is 0 and every term is 1.
- `staleness_term = min(1.0, days_since_last_completion / practice_staleness_full_days)`, and `1.0` when never completed. Default `practice_staleness_full_days = 14`.
- `progression_term = 1.0` when the practice has at least one prerequisite and all are met (it is the unlocked next step in a thread the user started), `0.5` when it is a root. Progression beats restarting.
- `featured_term = 1.0` when `featured` else `0.0`. A small nudge a pack author controls, mostly for cold start.

Settings defaults (`config.py`), summing to 1.0:

```python
practice_weight_balance: float = 0.40
practice_weight_staleness: float = 0.30
practice_weight_progression: float = 0.20
practice_weight_featured: float = 0.10
practice_staleness_full_days: int = 14
practice_balance_window_days: int = 28
practice_decline_threshold: int = 3
practice_protocol_default_size: int = 5
```

If the four weights do not sum to 1.0 (+/- 0.01) the recommender normalizes by their sum and logs an ERROR once. A typo in an env var should not take the app down, which is the same posture `get_plan_allowance_cents()` takes.

### 5.3 Selection: balance quota, not top-N

A plain top-N can return five practices of one purpose. Instead:

1. Order the five purposes by ascending user share over the window (most neglected first), tie-broken by the fixed purpose order.
2. Rotate that list left by `rotation_cursor mod 5`.
3. Round-robin: take the highest-scoring eligible practice of the current purpose, move to the next purpose, wrap, until N are chosen or the eligible pool is empty.
4. Increment `rotation_cursor` on each recomputation.

**Balance invariant:** for `N >= number of purposes with an eligible practice`, the result contains at least one practice from every such purpose. For smaller N, the chosen purposes are the N most neglected.

### 5.4 Tie-breaking

Fully deterministic, applied in order:

`score desc` → `purpose share asc` → `days since last completion desc` → `order asc` → `(pack_id, slug)` lexicographic.

The last key is total, so the output is a pure function of the inputs. There is no RNG anywhere, not even seeded. Considered and rejected: a seeded shuffle for variety. "Why am I seeing this?" has to be answerable from data the user can see, and a seed that resets on process restart makes it unanswerable. Variety comes from the log changing, which is the honest source.

### 5.5 Cold start

Empty log: every balance term is 1, every staleness term is 1, nothing is unlocked, so ranking reduces to `featured` then `order` then slug. Result: N root practices, one per purpose in the rotated order, featured first. **Invariant test:** a user with an empty log gets exactly `min(N, eligible_purposes)` distinct purposes and every returned practice has an empty `builds_on`.

### 5.6 The stable-day rule

If `last_recommended_at` falls in the same `day_key` and the mounted pack set is unchanged, `GET /practice/today` returns `last_recommendation` rather than recomputing. Completing one practice at 9am must not reshuffle the other four under the user's fingers at 9:05. Recompute on a new `day_key`, on an explicit `?refresh=true`, or when the pack set changes.

### 5.7 API shape

All routes require auth (`get_current_user`). None are plan-gated: nothing here costs money and gating the retention loop would defeat its purpose.

| Method | Path | Returns |
|---|---|---|
| GET | `/api/v1/practices` | all practices in mounted packs, filterable by `purpose`, `category`, `pack_id` |
| GET | `/api/v1/practices/{pack_id}/{slug}` | one practice, 404 as `PracticeNotFoundError` |
| GET | `/api/v1/practices/packs` | manifests including license and attribution |
| GET | `/api/v1/practice/today` | `{ protocol_size, generated_at, slots: {morning[], day[], evening[]}, items: [{pack_id, slug, title, purpose, duration_minutes, reason}] }` |
| POST | `/api/v1/practice/log` | 201, the created row (encrypted fields echoed back to the owner only) |
| GET | `/api/v1/practice/log?from=&to=` | the user's own rows, paginated |
| GET | `/api/v1/practice/summary` | `{ days_practiced_last_7, last_7: [bool×7], by_purpose: {...}, total_completed }` |
| POST | `/api/v1/practice/integration` | 201, creates the link and the derived outcome row (§6.3) |

`reason` is assembled from named deterministic templates keyed on which term dominated ("You have not practiced steadiness this week", "This follows on from *Name the Pattern*", "It has been 16 days"). No LLM, and the template id ships alongside the string so the frontend can style it.

### 5.8 Invariants the tests pin (property-style)

1. **Balance:** for N >= eligible purposes, every eligible purpose appears at least once.
2. **Staleness rotation:** given two practices identical except `days_since_last_completion`, the staler one ranks higher.
3. **Prerequisites:** no returned practice has an unmet `builds_on`, across randomized log fixtures.
4. **Cold start:** empty log returns only roots, N of them, spread across purposes.
5. **Determinism:** the same (registry, log, now) returns a byte-identical payload across 100 calls and across a fresh process.
6. **Stable day:** two calls in the same `day_key` without `refresh` return the identical set.
7. **Declined:** a practice with 3 skips and 0 completions in the window is absent.

---

## 6. The integration loop

Four steps, generic names, landing on surfaces that already exist.

```
  intention          experience             reflection            capacity
  ─────────          ──────────             ──────────            ────────
  journal entry  ──▶ practice_log      ──▶  journal entry    ──▶  outcome_metrics
  entry_type=        status=completed       entry_type=            metric_name=
  'intention'        + protocol_slot        'integration'          'practice_integration'
       │                    │                     │                      ▲
       └────────────────────┴─────────────────────┴──────────────────────┘
                        integration_entries (the link row)
```

### 6.1 Surfaces touched

- **Journal** (`/journal`, `routers/journal.py`): no schema change. The intention and reflection are ordinary journal entries with `entry_type` values `intention` and `integration`. Two new templates join the existing 24 in `web/src/lib/journalTemplates.ts`, reachable from the practice surface through the existing `JournalCTA` → `/journal?template=<id>` path.
- **Practice** (`/practice`): the completion interaction writes `practice_log`.
- **Outcomes**: one derived row per integration entry (§6.3).
- **Journey** (`/journey`): out of scope this epic. It is a fixed 7-node client-side checklist reading only profile shape and reports. Rebuilding it as a time series is a roadmap item (§7 of the roadmap), and this epic gives it the data to read when it happens.

### 6.2 The linking mechanism

`integration_entries` (§4.3). `POST /practice/integration` accepts `{practice_log_id, intention_entry_id?, reflection_entry_id?, capacity_delta?, note?}` and creates one row. Every reference is optional except `practice_log_id`, so a user who logs a practice and writes nothing still has a valid loop, and a user who journals without logging a practice is simply not in this table.

### 6.3 How capacity change becomes visible

**Decision: practice data is written to `practice_log`, not through `POST /outcomes/activity`.** That path drops its metadata server-side (`ActivityRequest` has no metadata field, `routers/outcomes.py:92-100`), writes into process-global dicts that make summaries worker-dependent, and takes a client-supplied `user_id` it then 403-checks. Routing practice completions through it would inherit all three, and the recommender's input would be as unreliable as the dashboard.

But capacity change has to show up where users already look. So on `integration_entries` insert, the service makes **one** direct repository call writing a single `outcome_metrics` row:

```
system      = PURPOSE_TO_SYSTEM[purpose]      # e.g. steadiness -> healing
metric_name = "practice_integration"
value       = float(capacity_delta) if capacity_delta is not None else 1.0
period      = "daily"
```

A direct repository call, not a trip through the router, so it bypasses the in-memory dicts and the metadata drop. `outcome_metrics` is a real table the existing trend code already reads, so the dashboard and any future journey time series pick it up with no further wiring.

The in-memory `_milestones` / `_activity_log` cleanup and the `logActivity` metadata drop are **follow-up issues**, filed but not this epic.

---

## 7. The daily protocol surface

### 7.1 Sequencing model

Three slots: **morning**, **during the day**, **evening**. Every practice carries exactly three `daily_prompts` mapped positionally to those slots, so slot assignment is not a per-practice decision. The protocol is N practices (default 5, configurable 3-7) rendered three times, once per slot, each with that slot's prompt. `practice_log.protocol_slot` records which slot the user was in.

The default of 5 is attributed to nobody and justified only by the range: fewer than 3 is not a protocol, more than 7 is a to-do list.

### 7.2 Routes and components

- `/practice` — today's protocol (new top-level route)
- `/practice/library` — browse all mounted packs, with per-pack attribution

`web/src/components/practice/`:

| Component | Responsibility |
|---|---|
| `DailyProtocol.tsx` | three slot sections, each a list of practice cards |
| `PracticeCard.tsx` | title, summary, duration chip, purpose chip, `reason` line, complete / not-today |
| `SelfCheckPrompt.tsx` | the reflective question plus an optional free-text box |
| `PracticeRhythm.tsx` | the 7-day display (§7.4) |
| `IntegrationPrompt.tsx` | appears after a completion, offers the reflection |
| `PracticeLibrary.tsx` / `PackAttribution.tsx` | browse plus license and attribution surfacing |

Every async surface ships loading, empty and error states. Layouts verified at 375px and desktop. WCAG 2.1 AA throughout. `UpsellNotice` / `PlanGateError` appear only on the coach path, since nothing else here is metered.

### 7.3 Completion interaction

One tap marks completed, optimistic with rollback on error. A "not today" control writes `status='skipped'` with no penalty copy at all. The self-check appears after a completion, clearly optional, labelled as being for the user and not scored.

### 7.4 Rhythm display, no loss aversion

The exact pattern:

- A row of 7 markers, one per day of the last 7, filled where there is at least one completed row.
- Caption: **"Practiced 4 of the last 7 days."**
- Empty state: **"No practice logged in the last 7 days. Start wherever you are."**

Banned from this surface, asserted by a test that greps the rendered output against a fixed list: "streak", "don't break", "you're about to lose", flame or fire iconography, any countdown to a reset, any number that resets to zero, any comparison to other users.

Accessibility: the marker row is a `<ul>` where each `<li>` carries `aria-label="Tuesday 12 August: practiced"` / `"...: no practice logged"`, the visual markers are `aria-hidden`, and the caption is the accessible summary. Keyboard path covers complete, not-today, self-check and integration without a mouse.

All copy above is **DRAFT for Tyler**.

---

## 8. Licensing boundary

### 8.1 What ships in-repo

- `engine/practice/`: schema, loader, registry, purposes, ecology recommender.
- Migration 0018, models, repository functions.
- `api/routers/practice.py` and the frontend surfaces.
- Exactly one bundled pack: `engine/practice/packs/alchymine-foundations/`.

### 8.2 The bundled example pack

**10 practices**, two per purpose dimension: one root and one that builds on it. Written fresh for Alchymine, in Alchymine's voice, against Alchymine's five pillars.

Ten is the recommendation because it is the smallest number that exercises every schema feature (five purposes populated, real `builds_on` edges at depth 2, at least three categories, both featured and unfeatured) and gives the recommender a genuine cold start, without turning slice 1 into a content project. Categories limited to `reflection`, `attention`, `enactment` and `relational`, plus at most two gentle `somatic` entries carrying explicit `contraindications`. `license: CC-BY-NC-SA-4.0`, `attribution: Alchymine Contributors`, `bundled: true`.

### 8.3 Never in-repo

No named third-party framework, model, protocol, brand or product name. No verbatim or paraphrased third-party prompt or practice text. No third-party controlled vocabulary. No pack whose license Alchymine does not hold. Not in the code, not in the bundled pack, not in the system prompt, not in test fixtures, not in this document's product prose.

### 8.4 The external-pack contract

A future licensed pack must satisfy all of:

1. A directory containing `pack.yaml` plus one `*.yaml` per practice.
2. `schema_version: "2.0"`.
3. Non-empty `license` and `attribution`; `bundled: false`.
4. Every practice declares an accepted `category` (§2.2).
5. `builds_on` and `related` resolve within the pack; the graph is acyclic.
6. All prose passes `check_text` at ERROR severity.
7. `pack_id` unique across every mounted directory.
8. Mounted through `PRACTICE_PACK_DIRS` from a read-only volume outside the repo tree.
9. Never committed, vendored, or baked into a Docker image.

Every one of these is enforced at load, so a pack that violates any of them fails container start rather than reaching a user.

### 8.5 Relationship to healing skills

The two loaders stay separate this epic. Healing skills (`engine/healing/skills/`, 15 entries, `HEALING_SKILLS_EXTERNAL_DIR`) are unchanged: no schema edits, no migration, no behavior change. Practice packs are the generic future shape, with the license metadata, per-pack namespacing, graph validation and loud failure policy that the healing schema cannot express today (`extra="forbid"` on a single flat model blocks adding license fields via YAML).

A later migration of healing skills onto pack schema v2 is plausible and explicitly **out of scope**. Filed as a follow-up. Two loaders is the correct cost of not destabilizing a shipped surface mid-epic.

### 8.6 References (this document only)

- John Vervaeke, *Awakening from the Meaning Crisis* (lecture series, 2019), and Vervaeke, Mastropietro & Miscevic, *Zombies in Western Culture: A Twenty-First Century Crisis* (Open Book Publishers, 2017), on the ecology of practices: the argument that a single practice cannot correct its own distortions and that a set of complementary practices is the unit that works. This is what the balance-across-purposes selection rule (§5.3) is for.
- Jakob von Uexküll, *A Stroll Through the Worlds of Animals and Men* (1934), on umwelt: the observation that a creature's perceptual world is shaped by what it can act upon. This is what the `expected_shift` field is for.

Both are published academic work cited here by reference with attribution. Neither name, nor its vocabulary, appears in product prose, the bundled pack, the system prompt, or any user-facing surface.

---

## 9. Coach scope extension

New system key: `practice`. This is the only metered addition in the epic.

### 9.1 The five sync points

| # | File | Change |
|---|---|---|
| 1 | `agents/growth/system_prompts.py` (~line 153) | `_PRACTICE_FOCUS` block, `SYSTEM_PROMPTS["practice"]` |
| 2 | `api/routers/chat.py:161` | add `"practice"` to `_VALID_SYSTEM_KEYS` |
| 3 | `web/src/hooks/usePageContext.ts:24` | `SystemKey` union, `SYSTEM_LABELS`, `ROUTE_TO_SYSTEM["practice"]` |
| 4 | `web/src/lib/starterPrompts.ts` | practice starters in `getStarterPrompts` |
| 5 | `web/src/components/chat/SystemCoachBanner.tsx:25,33` | label and description |

Points 3, 4 and 5 fail at build time if omitted, because the `Record<SystemKey, ...>` types make TypeScript reject an incomplete map. Points 1 and 2 drift silently today, guarded only by a comment. Slice 5 adds a test pinning `_VALID_SYSTEM_KEYS == set(SYSTEM_PROMPTS)`, which closes that gap for all six scopes at once.

### 9.2 In-conversation-only data access

`agents/growth/practice_context.py`:

```python
async def build_practice_context(session, user_id: str) -> str | None
```

Deterministic, no LLM. Reads a fixed column list from `practice_log` and `ecology_state`: completed practice titles from the last 7 days, per-purpose counts, today's protocol. Renders a compact labelled block.

**Hard data rail:** the SQL selects an explicit column list that excludes `reflection`, `self_check_response` and `integration_entries.note`. The encrypted columns are never read by the context builder, so no practice reflection reaches any LLM unless the user types it into the chat box themselves. A test asserts the emitted prompt contains no reflection text from a fixture that has some.

**Placement, and why it matters for caching.** The block is appended to the **user message**, after the cache breakpoint, never to the system prompt. `_system_payload` (`llm/client.py:56`) marks the assembled system prompt as the stable cacheable prefix, and per-user practice context changes daily, so putting it there would invalidate the prefix on every change. Assembly happens at call time:

```python
assembled = f"{practice_block}\n\n{message}" if practice_block else message
# stream_generate(prompt=assembled, ...)
# save_chat_message(content=message)   # the raw text, unchanged
```

Only `request.message` is persisted to `chat_messages`, matching current behavior.

`_PRACTICE_FOCUS` does grow the stable prefix by roughly 200 tokens. That is helpful for issue #248 (the prefix pays nothing below Haiku's 4096-token minimum and sits near 880 today) but nowhere near sufficient on its own. Cross-referenced, not solved here.

### 9.3 The system prompt block (DRAFT for Tyler)

```
Specialist focus — Practice Integration:
- The user is working with a practice library they already have. Help
  them choose, sequence and reflect on those practices. Don't invent new
  ones or design new protocols.
- Every practice is scaffolding. Say so when it matters: the point is
  the capacity it builds, not the practice itself. If someone is leaning
  on a practice to avoid something, name it gently and ask, don't assert.
- Reflection questions, not verdicts. You don't tell the user what their
  pattern means. You ask what they noticed, and you let them answer.
- Never suggest practices aimed at producing altered states, breath
  retention, fasting, or anything that needs screening. If the user asks
  for those, say plainly that Alchymine doesn't carry them, and why.
- A missed day is information, not failure. No pressure, no guilt, no
  streak language.
```

### 9.4 Safety gate wiring

The chat path does not use `check_text` or `detect_crisis` today. It has a local regex `_check_content_safety` (`chat.py:138`). This epic wires the real gates for the `practice` scope.

**Inbound.** In the `/chat` handler, when `system_key == "practice"`, run `detect_crisis(request.message)` (`engine/healing/crisis.py:158`) before anything else. On a `CrisisResponse` at high or emergency severity, short-circuit: open the SSE stream, emit the crisis resources and disclaimers as `data:` frames, emit `event: done`, and make **no LLM call**. Not an HTTP 400, which would read as "you did something wrong" at exactly the wrong moment. Side benefit: the crisis path costs nothing and writes no ledger row.

**Outbound.** `check_text(accumulated, context="healing")` (`ethics_check.py:355`) runs inside the existing streaming loop at the same point `_check_content_safety` runs, tripping the same truncate-and-error path. Running it on the accumulation every chunk is O(n²) over a reply, so it runs every 8 chunks plus once at the end. Checking after the stream finished would be honest-but-useless: it cannot unsend what already streamed.

**Scope of the change.** A helper `run_safety_gates(system_key, text)` in the chat router, applied to `practice` only. Adopting it across the other five scopes changes behavior on five live surfaces and deserves its own PR and regression pass. **Follow-up issue**, recommended next, called out in the epic close-out.

### 9.5 Metering

`POST /chat` already carries `Depends(require_chat)` (`chat.py:356`), so the practice scope is metered with **zero new code**: `get_current_account` re-reads Postgres, the plan gate and monthly allowance apply, `charge_paid_call` fails closed, `record_usage` writes the ledger row. Surface stays `"chat"`. No new surface string, following the `entitlements.py:263` precedent of reusing an existing value rather than growing the ledger a synonym.

### 9.6 Measuring the added cost (pinned method)

`save_chat_message` already returns the refreshed row with a populated `id` (`db/repository.py:900-929`), and the user message is persisted before the LLM call (`chat.py:274`). So slice 5 passes that id as the attribution `request_id`:

```python
user_row = await repository.save_chat_message(..., role="user", ...)
# then, around the stream:
attributed(user_id=user_id, surface="chat", request_id=user_row.id)
```

`usage_records.request_id` is already `String(64)` and a uuid is 36 characters, so no schema change. Measurement is then an exact join, not a time-window correlation:

```sql
SELECT count(*), sum(u.cost_micros)
FROM usage_records u
JOIN chat_messages c ON u.request_id = c.id
WHERE c.system_key = 'practice' AND u.created_at >= :since;
```

Ephemeral turns persist no user message, so they pass `request_id=None` (unchanged behavior) and are excluded from the per-scope measurement. Note the side benefit: this makes every chat scope exactly attributable, not just this one.

---

## 10. Per-slice plan

| Slice | Issue | Builds | Blast radius | Rollback |
|---|---|---|---|---|
| 1 | #253 | schema v2, loader, registry, `PRACTICE_PACK_DIRS`, bundled 10-practice pack, `GET /practices*` | New engine package, one config field, one router. Nothing existing changes. | Revert the package. No data written. |
| 2 | #254 | migration 0018, models, repository, practice-log API | Additive DB schema, `models.py`, new router | `downgrade()` drops three tables. Practice history is lost, so treat a merged 0018 as forward-only in production. |
| 3 | #255 | ecology recommender, `/practice/today`, `/practice/summary` | Engine plus two read endpoints; only `ecology_state` is written | Revert. `ecology_state` rows are inert. |
| 4 | #256 | protocol surface, integration loop, derived outcome write | New frontend routes and components, one repository call into `outcome_metrics`, journal schema untouched | Revert the frontend. Derived outcome rows are additive and harmless. |
| 5 | #257 | `practice` coach scope, context builder, safety gates, `request_id` attribution | **The live chat endpoint.** Highest of the five. | Remove `"practice"` from `_VALID_SYSTEM_KEYS`: the scope 422s, every other chat scope is untouched. Cheap kill switch, keep it in mind during review. |

### Red-first behaviors, named per slice

**Slice 1.** A pack with a cycle fails naming the members. An unresolved `builds_on` fails naming file, practice and missing slug. `category: state-induction` fails with the screening reason, not a generic enum error. A non-bundled pack with an empty `license` fails. Duplicate `pack_id` across two dirs fails. A configured dir that exists but holds zero `pack.yaml` fails. Prose containing a diagnostic phrase fails via `check_text`. The bundled pack loads with exactly 10 practices covering all 5 purposes.

**Slice 2.** `alembic upgrade head` then `downgrade` then `upgrade` is idempotent on SQLite and Postgres. `reflection` and `self_check_response` round-trip while the raw column bytes are not the plaintext. A log write naming a slug that is not in any mounted pack is rejected. User A cannot read user B's log. `day_key` is stored as sent and not recomputed server-side in a different timezone.

**Slice 3.** The seven invariants in §5.8, each as its own test.

**Slice 4.** The protocol renders three slot groups. Completion is optimistic and rolls back on a 500. The rhythm surface renders "practiced N of the last 7 days" and contains none of the banned loss-aversion strings. axe passes; the keyboard path covers complete, skip, self-check and integration; layout holds at 375px. One integration entry writes exactly one `outcome_metrics` row.

**Slice 5.** `_VALID_SYSTEM_KEYS == set(SYSTEM_PROMPTS)`. The practice context excludes reflection and self-check text (asserted against the emitted prompt). The cached system prefix is byte-identical with and without practice context. A crisis-keyword message returns resources, makes zero LLM calls and writes zero ledger rows. `check_text` trips the truncate path mid-stream. `require_chat` still returns 402 and 429 correctly. The ledger row's `request_id` equals the persisted user message id.

Every slice runs the full local gate before push: `ruff check`, `ruff format --check`, `mypy`, `CELERY_ALWAYS_EAGER=true pytest tests/ -v`, plus `npm test`, `npm run lint`, `npm run type-check` for slices 4 and 5. Issues close only after CI is green on the merged branch.

---

## 11. Decision register

| # | Decision point | Taken path | Rationale |
|---|---|---|---|
| 1 | Purpose vocabulary | Five new capacity names, 1:1 onto the five pillars | Generic and original, no upstream vocabulary; the 1:1 mapping lets `practice_log.primary_purpose` join `outcome_metrics.system` with a lookup, no translation logic. |
| 2 | Relationship to healing skills | Practice packs are a separate v2 loader; healing skills unchanged this epic | The healing schema cannot express license metadata (`extra="forbid"` on one flat model). Migrating it mid-epic destabilizes a shipped surface. Filed as follow-up. |
| 3 | State-induction exclusion | Rejected-category dict checked before the accepted enum, with per-category reasons | The exclusion is enforced by the engine, not editorial vigilance, and the error tells the author why. |
| 4 | Pack prose quality | `check_text` at ERROR severity at load time | Zero cost, and it applies the ethics rail to content Alchymine did not write. |
| 5 | `builds_on` edge scope | Within-pack only | An external pack cannot depend on a pack it may not be mounted with; per-pack graphs make load order irrelevant to validation. |
| 6 | Single-root DAG | Not required; forest of DAGs | Five purposes naturally means several roots. "At least one root" falls out of the acyclicity check. |
| 7 | External dir failure policy | Hard-fail at startup on missing, unreadable, empty, unlicensed or invalid | The healing loader's warn-and-skip means a typo'd mount silently ships a smaller product. Startup rather than first request, so container health catches it. |
| 8 | Registry reload | Process restart only, no endpoint | No operational need, and a reload endpoint is a configurable-path filesystem read nobody asked for. |
| 9 | Where the loader lives | `engine/practice/`, one builder function every entry point calls | The healing loader lives in the API router, which is why the MCP server ignores its external dir. |
| 10 | Primary key type | `String(36)` uuid on all three tables | Matches `journal_entries` and `outcome_metrics`; no `BigInteger`, so the #230 SQLite variant is not needed. |
| 11 | What gets encrypted | `reflection`, `self_check_response`, `integration_entries.note` only | Fernet is non-deterministic, so encrypted columns cannot be grouped in SQL. Encrypting the recommender's inputs would move it to a full scan in Python. Identifiers and timestamps stay plaintext; what the user wrote is encrypted. |
| 12 | Self-check scoring | Free text only, no boolean, no score, never read by the recommender | Scoring a reflective question turns it into a diagnosis. |
| 13 | Integration link mechanism | Separate `integration_entries` table | A `parent_id` on `journal_entries` changes every journal read and the export contract, and still cannot link across two tables. |
| 14 | Outcomes write path | Write `practice_log`; one derived `outcome_metrics` row per integration entry, through the repository | The `/outcomes/activity` path drops metadata, writes process-global dicts and trusts a client-supplied `user_id`. Its cleanup is a follow-up, not this epic. |
| 15 | `ecology_state` scope | Practice-scoped only, models nothing spiral | `route_user` stays pure and unpersisted; persisted spiral state would be its own decision and its own table. |
| 16 | Recommender randomness | None, not even seeded | "Why am I seeing this?" must be answerable from visible data. A seed that resets on restart makes it unanswerable. Variety comes from the log. |
| 17 | Selection algorithm | Purpose round-robin, not top-N | Top-N can return five practices of one purpose, which is the exact failure the balance invariant exists to prevent. |
| 18 | Same-day stability | Stable-day rule via `last_recommendation` | Completing one practice must not reshuffle the other four mid-day. |
| 19 | Skipped practices | Logged, and retired after 3 skips with 0 completions in 28 days | The recommender needs to tell "never offered" from "declined", without a practice nagging forever. |
| 20 | Slot assignment | Positional: the three `daily_prompts` are morning, day, evening | Turns a would-be editorial judgment into a schema constraint, and justifies the exactly-3 rule. |
| 21 | Streak display | "Practiced N of the last 7 days", 7 markers, no resetting counter | No loss aversion, no shame copy. Asserted by a banned-string test. |
| 22 | Coach scope surface string | Reuse `"chat"` via `require_chat` | Precedent at `entitlements.py:263`: reuse rather than grow the ledger a synonym. |
| 23 | Practice context placement | Appended to the user message, never to the system prompt | The system prompt is the cacheable stable prefix; daily-changing context there would invalidate it every day. |
| 24 | Safety gate scope | `detect_crisis` + `check_text` on the `practice` scope only | Smallest correct change. Adopting them across five live scopes deserves its own PR and regression pass. Follow-up issue. |
| 25 | Crisis response shape | SSE resources with zero LLM calls, not HTTP 400 | A 400 reads as "you did something wrong" at the worst possible moment, and this path costs nothing. |
| 26 | Cost measurement | `request_id = chat_messages.id`, joined against `system_key` | Exact rather than a time-window correlation, one line at the call site, no schema change, and it fixes attribution for every chat scope. |
| 27 | Practice API gating | Auth required, no plan gate | Nothing here costs money, and gating the retention loop defeats the loop. |
| 28 | Bundled pack size | 10 practices, two per purpose | The smallest set that exercises every schema feature and gives the recommender a real cold start, without slice 1 becoming a content project. |

---

## 12. Follow-up issues to file (not this epic)

1. Adopt `detect_crisis` + `check_text` across the other five coach scopes.
2. Replace the outcomes tracker's process-global `_milestones` / `_activity_log` dicts with DB reads; add the dropped `metadata` field to `ActivityRequest`; stop taking `journal_count` as a client query param.
3. Migrate healing skills onto pack schema v2, or add license and attribution fields to `SkillDefinition`; fix the API wrapper's silent external-dir swallow (`routers/healing_skills.py:50-51`) and teach the MCP server about the external dir.
4. Rebuild `/journey` as a time series reading `practice_log` and `outcome_metrics`.
5. Grow the chat stable prefix past Haiku's 4096-token cache minimum (issue #248).
6. Server-side validation of `journal_entries.entry_type` against a known set.

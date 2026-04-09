# Alchymine — Archon Integration Guide

How Alchymine uses [Archon](https://github.com/coleam00/Archon) as its remote
agentic coding platform. This is the single authoritative reference for the
integration — if something here conflicts with another doc, this file wins.

**Target audience:** developers working on Alchymine who want to run AI
workflows against the repo (fix an issue, review a PR, refactor a module,
sweep the architecture) without manually pasting prompts into a chat window.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [The `.secrets/.env` Convention](#the-secretsenv-convention)
4. [Using Archon from Claude Code](#using-archon-from-claude-code)
5. [Using Archon from the CLI](#using-archon-from-the-cli)
6. [Using Archon from the Web UI](#using-archon-from-the-web-ui)
7. [Recommended Workflows for Alchymine](#recommended-workflows-for-alchymine)
8. [Where Secrets Live](#where-secrets-live)
9. [Gotchas and Rollback](#gotchas-and-rollback)
10. [Further Reading](#further-reading)

---

## Overview

**Archon** is a remote agentic coding platform built on Bun + TypeScript +
SQLite. It runs AI workflows (Claude Code SDK, Codex SDK) inside isolated git
worktrees and can be driven from:

- A CLI (`archon ...` — global command, works from any directory)
- A Web UI (React, SSE streaming, dashboards)
- Telegram (`@ArchonOkieBot` with a user whitelist)
- GitHub webhooks (`@archon` mentions in issue/PR comments)

Archon lives at `I:\GithubI\Archon`. Alchymine is registered with it as the
codebase `realsammyt/Alchymine` pointing at `I:\GithubI\Alchymine`. Every
workflow run creates its own git worktree so concurrent runs never stomp on
each other or on your working copy.

**Why we wired it up:** Alchymine has enough moving parts (FastAPI backend,
Next.js frontend, Celery workers, Postgres, Redis, infra scripts) that
long-running AI tasks — "fix issue #123", "review PR #42", "refactor the
encryption module" — benefit from running in an isolated worktree rather than
blocking the working copy. Archon gives us that isolation for free, plus
multi-transport access (Claude Code, CLI, web, Telegram, GitHub webhooks).

**What changed when we integrated it** (2026-04-09):

| Change                                                 | Reason                                                                 |
| ------------------------------------------------------ | ---------------------------------------------------------------------- |
| Secrets moved from `.env` → `.secrets/.env`            | Archon's env-leak gate refuses registration if repo-root `.env` exists |
| `alchymine/config.py:30` now reads `.secrets/.env`     | Pydantic Settings needs to follow the new path                         |
| `.gitignore` ignores `.secrets/`                       | Keep secrets out of git (they already were, but make it explicit)      |
| New `run.ps1` at repo root                             | Pins `docker compose` to `--env-file .secrets/.env` so muscle-memory `docker compose up` still works |
| `.claude/skills/archon/` copied into the repo          | Claude Code sessions in Alchymine auto-load the archon skill           |
| `.env.example` updated with a header comment           | New devs learn the convention immediately                              |

Alchymine is registered with `allow_env_keys = 0` — we do **not** bypass the
env-leak gate, we satisfy it.

---

## Quick Start

The shortest path from a fresh clone to running your first workflow.

```powershell
# 1. Clone and install
git clone https://github.com/realsammyt/Alchymine.git
cd Alchymine
# ... your normal setup (uv sync, bun install, etc.) ...

# 2. Create your secrets file
mkdir .secrets
copy .env.example .secrets\.env
# Fill in ANTHROPIC_API_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, etc.

# 3. Verify Archon can see Alchymine
archon workflow list
# Should print ~20 workflows with no errors

# 4. Run your first workflow in the background (isolated worktree)
archon workflow run archon-assist --branch assist/first-try "What does alchymine/config.py do?"

# 5. Watch it run
archon workflow status
```

From Claude Code running inside Alchymine, the same thing is even simpler — the
archon skill is preloaded, so you just say:

> use archon to explain what `alchymine/config.py` does

Claude Code will translate that into an `archon workflow run archon-assist ...`
invocation and launch it as a background task.

---

## Usage Patterns

Use direct Claude Code for interactive, exploratory work in your live checkout.
Delegate long-running, isolated, or multi-pass work to Archon via the preloaded
skill — runs land in a dedicated worktree and you keep coding.

| Task                                          | Use                          |
| --------------------------------------------- | ---------------------------- |
| Debug a Celery worker hang, poke at a file    | Claude Code (direct)         |
| Fix a filed GitHub issue end-to-end           | `archon-fix-github-issue`    |
| Refactor `alchymine/services/encryption.py`   | `archon-refactor-safely`     |
| Architectural sweep of `alchymine/services/`  | `archon-architect`           |
| Deep review of a PR                           | `archon-comprehensive-pr-review` |

For the full cross-project decision tree, see the canonical usage-patterns doc:
`.claude\skills\archon\references\usage-patterns.md`

For anti-patterns, the "typical day" example, and project-onboarding steps,
see the canonical doc.

---

## The `.secrets/.env` Convention

**This is the most important section of this doc.** If you only read one
thing, read this.

### The Rule

Alchymine's secrets live at `I:\GithubI\Alchymine\.secrets\.env`. **Never** put
them in the repo-root `.env`. Don't even create an empty repo-root `.env`.

```
I:\GithubI\Alchymine\
  .env.example          <- committed, template with header comment
  .secrets\
    .env                <- gitignored, real secrets go here
  .gitignore            <- ignores .secrets/
```

### Why (The Long Version)

When Archon spawns a Claude or Codex subprocess inside a repo, that subprocess
runs on the Bun runtime. **Bun auto-loads `.env` from its cwd at startup.**
This means any `.env` file at the Alchymine repo root gets read by every AI
subprocess Archon runs — completely bypassing Archon's internal env allowlist.

Alchymine's secrets include (at minimum):

- `ANTHROPIC_API_KEY` — billing-linked
- `JWT_SECRET_KEY` — auth tokens
- `POSTGRES_PASSWORD` — database
- `ALCHYMINE_ENCRYPTION_KEY` — at-rest encryption
- `REDIS_PASSWORD` — cache / queue
- `RESEND_API_KEY` — transactional email
- ...plus provider keys, webhook secrets, feature flags

Any of these leaking into an AI subprocess is a security incident. So Archon's
**env-leak gate** refuses to register a codebase if the repo root contains any
of:

```
.env
.env.local
.env.development
.env.production
.env.development.local
.env.production.local
```

The scan is **root-only** — subdirectories are not checked. That's why
`.secrets/.env` works: it's outside both the scan path *and* Bun's auto-load
path.

When Alchymine was first registered, Archon returned a 422 at
`POST /api/codebases` listing the forbidden files. The fix was:

```powershell
# From I:\GithubI\Alchymine
mkdir .secrets
move .env .secrets\.env
```

Then updating the Pydantic Settings loader at
`I:\GithubI\Alchymine\alchymine\config.py:30` from `env_file=".env"` to
`env_file=".secrets/.env"`.

### What Reads From Where

| Component            | File it reads                     | Resolution                                            |
| -------------------- | --------------------------------- | ----------------------------------------------------- |
| Pydantic Settings    | `.secrets/.env`                   | Relative to **cwd** — you must run from repo root     |
| Docker Compose       | `.secrets/.env` (via `--env-file`)| Must pass `--env-file` explicitly or use `run.ps1`    |
| Next.js (dev)        | `.env.local` in `frontend/`       | Frontend has its own env — unaffected by this change  |
| pytest               | `.secrets/.env`                   | Same as Pydantic Settings — run from repo root        |
| CI (GitHub Actions)  | Repository secrets                | Injected via `env:` in workflow YAML — unaffected     |
| Archon subprocesses  | Nothing from this repo            | Archon injects its own allowlisted env                |

### Docker Compose Wrapper

Because `docker compose up` out of the box looks for a cwd-relative `.env`,
we ship `I:\GithubI\Alchymine\run.ps1`:

```powershell
# run.ps1 — pins env-file and compose-file so muscle memory still works
docker compose --env-file .secrets/.env -f infrastructure/docker-compose.yml @args
```

Use it exactly like `docker compose`:

```powershell
.\run.ps1 up -d
.\run.ps1 logs -f api
.\run.ps1 down
.\run.ps1 exec api bash
```

If you run `docker compose` directly without `--env-file`, it will fail with
missing-variable errors. That's the intended guardrail.

---

## Using Archon from Claude Code

This is the common case — you're already in a Claude Code session inside
`I:\GithubI\Alchymine`, and you want Archon to go do a thing.

### The Skill Is Preloaded

`.claude/skills/archon/SKILL.md` is copied into the Alchymine repo, so Claude
Code auto-discovers it. You don't need to invoke it manually.

### How to Ask

Use natural phrasing with an "archon" trigger:

- *"use archon to fix issue #123"*
- *"have archon review PR #42"*
- *"let archon refactor the encryption module"*
- *"ask archon why the Celery worker is hanging"*
- *"run archon architect on the alchymine/services folder"*

Claude Code maps those to the right `archon workflow run ...` command. You
don't need to remember workflow names.

### Always in the Background

Archon workflows take **minutes to hours**. Claude Code will launch them with
`run_in_background: true` on the Bash tool so your interactive session stays
responsive. You can keep working while the workflow runs.

Under the hood it looks like:

```powershell
archon workflow run archon-fix-github-issue --branch fix/issue-123 "Fix issue #123"
```

...launched as a background bash task. The foreground Claude Code session gets
the run ID immediately and can poll for status.

### Checking on a Running Workflow

Ask Claude Code things like:

- *"what's the status of the archon run?"*
- *"show me the latest archon workflows"*
- *"is the fix-issue-123 workflow done?"*

Or directly:

```powershell
archon workflow status
archon workflow status <run-id>
```

### Interactive Workflows

A few workflows need foreground execution with approval gates:

- `archon-piv-loop` — interactive guided development
- `archon-interactive-prd` — interactive PRD creation

These use a "transparent relay" protocol where the workflow pauses and asks
the user for approval via the web UI or chat adapter. **Don't background
these.** If Claude Code suggests one of these, switch to the Web UI for the
interactive part.

---

## Using Archon from the CLI

Every command below runs from `I:\GithubI\Alchymine` unless noted. The
`archon` binary is linked globally, so it works from any directory — but
workflow / isolation commands need to be run from inside a git repo (or
subdirectory — they resolve to the repo root).

### Listing

```powershell
# All workflows (bundled + repo-specific)
archon workflow list

# Machine-readable
archon workflow list --json

# All active worktrees across all projects
archon isolation list
```

### Running a Workflow

Every run creates an isolated worktree by default. Pass `--branch` to name it:

```powershell
# General Q&A, exploration, debugging
archon workflow run archon-assist --branch assist/celery-hang `
  "Why is the Celery worker hanging on the encrypt_payload task?"

# Fix a GitHub issue end-to-end (clone → implement → tests → PR)
archon workflow run archon-fix-github-issue --branch fix/issue-123 "Fix issue #123"

# Review a PR in depth (multiple agent passes)
archon workflow run archon-comprehensive-pr-review --branch review/pr-42 "Review PR #42"

# Lighter, faster PR review
archon workflow run archon-smart-pr-review --branch review/pr-42 "Review PR #42"

# Run tests + linters on a PR branch
archon workflow run archon-validate-pr --branch validate/pr-42 "Validate PR #42"

# Implement from an existing plan document
archon workflow run archon-plan-to-pr --branch feat/billing `
  "Execute docs/plans/2026-04-15-billing.md"

# Architectural sweep / complexity reduction
archon workflow run archon-architect --branch arch/services-sweep `
  "Sweep alchymine/services for complexity hotspots"
```

You can start **multiple runs in parallel** — each gets its own worktree and
branch, so they don't collide.

### Status and Resume

```powershell
# All runs
archon workflow status

# Specific run
archon workflow status <run-id>

# Resume a failed run (re-runs, skipping completed nodes)
archon workflow resume <run-id>

# Abandon a non-terminal run (marks as cancelled)
archon workflow abandon <run-id>
```

### Worktree Cleanup

Archon worktrees for Alchymine live at:

```
C:\Users\info\.archon\workspaces\realsammyt\Alchymine\worktrees\<branch-name>\
```

You can `cd` into any of them to inspect state mid-run or post-run. To clean
up:

```powershell
# Clean up worktrees older than 7 days
archon isolation cleanup

# Clean up worktrees whose branches are merged into main
# (also deletes the remote branches)
archon isolation cleanup --merged

# Also remove worktrees with closed (abandoned) PRs
archon isolation cleanup --merged --include-closed

# Complete lifecycle for one branch (remove worktree + local + remote branch)
archon complete fix/issue-123
```

---

## Using Archon from the Web UI

The Web UI is the best interface for monitoring multiple runs at once and for
interactive workflows that need approval gates.

### Starting the Archon Server

The CLI works standalone, but the Web UI, GitHub webhooks, and Telegram all
need the server running.

```powershell
cd I:\GithubI\Archon
bun run dev
```

This starts:

- Backend on `http://localhost:3000` (we set `PORT=3000` in
  `I:\GithubI\Archon\.env` — Archon's default is 3090, but we collide with
  Alchymine's backend on that port)
- Frontend dev server on `http://localhost:5173` (proxies API calls to :3000)

> **Log tip:** `bun run dev` from the Archon repo root truncates sub-process
> logs (a known Bun filter quirk — see `I:\GithubI\Archon\.claude\rules\dx-quirks.md`).
> If the server errors and you need full logs, run it directly:
>
> ```powershell
> cd I:\GithubI\Archon\packages\server
> bun --watch src/index.ts
> ```

The production build serves both API and UI from `http://localhost:3000`.

### Opening the UI

- Dev: [http://localhost:5173](http://localhost:5173)
- Prod: [http://localhost:3000](http://localhost:3000)

### Running a Workflow

1. In the sidebar, click the project selector and pick `realsammyt/Alchymine`
2. At the top of the sidebar, the workflow invoker lets you:
   - Pick a workflow from the dropdown
   - Write a message / prompt
   - Click **Run**
3. A new conversation is created and the workflow starts in the background
4. The conversation view shows streaming output (SSE) from the workflow

### Dashboard

Navigate to [http://localhost:5173/dashboard](http://localhost:5173/dashboard)
(or `:3000/dashboard` in prod). You'll see:

- All running workflows across all projects
- Recent completed / failed runs
- Per-run timeline with node-level progress
- Artifact files produced by each run
- Resume / abandon / delete actions

---

## Recommended Workflows for Alchymine

A curated subset of Archon's bundled workflows, with Alchymine-specific
guidance. Run `archon workflow list` to see the full catalog.

| Workflow                          | When to use it                                          | Example                                                                                     |
| --------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `archon-assist`                   | General Q&A, exploration, debugging — the fallback      | `archon workflow run archon-assist --branch assist/debug "Why does celery hang?"`           |
| `archon-fix-github-issue`         | End-to-end fix for a filed issue                        | `archon workflow run archon-fix-github-issue --branch fix/issue-123 "Fix issue #123"`       |
| `archon-comprehensive-pr-review`  | Deep multi-pass review of a PR                          | `archon workflow run archon-comprehensive-pr-review --branch review/pr-42 "Review PR #42"`  |
| `archon-smart-pr-review`          | Lighter / faster review — good for small PRs            | `archon workflow run archon-smart-pr-review --branch review/pr-42 "Review PR #42"`          |
| `archon-validate-pr`              | Run tests + linters against a PR branch                 | `archon workflow run archon-validate-pr --branch validate/pr-42 "Validate PR #42"`          |
| `archon-feature-development`      | Implement a feature from a plan document                | `archon workflow run archon-feature-development --branch feat/billing "Implement billing per docs/plans/..."` |
| `archon-plan-to-pr`               | Execute an existing plan.md end-to-end to a PR          | `archon workflow run archon-plan-to-pr --branch feat/billing "docs/plans/2026-04-15-billing.md"` |
| `archon-idea-to-pr`               | Plan AND implement a rough idea end-to-end              | `archon workflow run archon-idea-to-pr --branch feat/idea "Add webhook retry backoff"`     |
| `archon-refactor-safely`          | Refactoring with safety checks (tests, diffs, review)   | `archon workflow run archon-refactor-safely --branch refactor/services "Refactor alchymine/services/encryption.py"` |
| `archon-architect`                | Architectural sweep, complexity reduction               | `archon workflow run archon-architect --branch arch/services "Sweep alchymine/services"`   |
| `archon-resolve-conflicts`        | Resolve merge conflicts on a PR                         | `archon workflow run archon-resolve-conflicts --branch conflicts/pr-42 "Resolve conflicts on PR #42"` |
| `archon-create-issue`             | Draft and file a new GitHub issue                       | `archon workflow run archon-create-issue --branch issue/new "File issue for the Celery bug"` |

### Interactive workflows (run in Web UI, not background)

| Workflow                  | When to use it                                              |
| ------------------------- | ----------------------------------------------------------- |
| `archon-piv-loop`         | Interactive guided development with approval gates         |
| `archon-interactive-prd`  | Interactive PRD creation with live feedback                 |

These need foreground execution and use Archon's transparent relay protocol.
Run them from the Web UI so the approval gates have somewhere to land.

---

## Where Secrets Live

Three separate `.env` files exist on this machine. They serve different
purposes — do not merge them.

| Path                                       | Contains                                                          | Who reads it                                                                                 |
| ------------------------------------------ | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `C:\Users\info\.archon\.env`               | Archon CLI credentials (API keys, webhook secrets, bot tokens)    | `archon` CLI when run from any directory — global infra config                              |
| `I:\GithubI\Archon\.env`                   | Same content as `~/.archon/.env`                                  | Archon **server** when started via `bun run dev` — server reads from its repo root           |
| `I:\GithubI\Alchymine\.secrets\.env`       | Alchymine application secrets (DB, JWT, encryption, provider keys)| Alchymine's Pydantic Settings, `run.ps1` docker compose, pytest — **all cwd-relative**       |

Key Archon environment flags set on this machine:

- `PORT=3000` — in `I:\GithubI\Archon\.env`. Archon defaults to 3090, but we
  moved it to avoid a collision with Alchymine's backend.
- `CLAUDE_USE_GLOBAL_AUTH=true` — in both Archon `.env` files. Uses Claude
  Code's existing login instead of a separate API key.
- `TELEGRAM_ALLOWED_USER_IDS=<your id>` — whitelist for `@ArchonOkieBot`.

Archon's SQLite database is at `C:\Users\info\.archon\archon.db`. No setup
needed — Archon auto-initializes it on first run.

---

## Gotchas and Rollback

### 1. Don't restore `.env` to the repo root

Doing this will:

- Re-trigger Archon's env-leak gate — next registration or scan refresh fails
  with a 422
- Expose every Alchymine secret to any AI subprocess Archon spawns with
  `cwd=I:\GithubI\Alchymine`

If you find yourself wanting to do this, fix the consumer instead (make it
read from `.secrets/.env`).

### 2. `docker compose` without `--env-file`

If you run `docker compose up` from the Alchymine repo root out of muscle
memory, it will fail because there's no cwd-relative `.env`. Use:

```powershell
.\run.ps1 up -d
# or, if you must call docker compose directly:
docker compose --env-file .secrets/.env -f infrastructure/docker-compose.yml up -d
```

### 3. uvicorn / pytest / CLI from subdirectories

Pydantic Settings resolves `.secrets/.env` **relative to the current working
directory**. If you run `pytest` or `uvicorn` from, say, `alchymine/services/`,
the path won't resolve and you'll get a stack of "missing required env
variable" errors. Always run from the repo root.

```powershell
cd I:\GithubI\Alchymine
uv run uvicorn alchymine.main:app --reload
uv run pytest
```

### 4. Archon server must be running for Web UI / webhooks / Telegram

The CLI works standalone. But the Web UI, GitHub webhooks, and Telegram
adapters all need `bun run dev` running inside `I:\GithubI\Archon`. If the
dashboard won't load, that's the first thing to check.

### 5. Archon worktrees live outside the repo

Don't go looking for workflow output in `I:\GithubI\Alchymine` — it's not
there. It's at:

```
C:\Users\info\.archon\workspaces\realsammyt\Alchymine\worktrees\<branch>\
```

You can `cd` into any of these to inspect state. They're real git worktrees,
so you can run `git log`, `git diff`, etc.

### 6. Docker port collisions inside worktrees

If a workflow runs `./run.ps1 up` inside a worktree, it'll try to bind the
same ports as any other running Alchymine stack. **Stop the main stack first**,
or be aware that the worktree run will fail on port binding. (In general,
workflows shouldn't be starting the full Docker stack — prefer unit tests and
isolated services.)

### 7. Rotate secrets if `.secrets/.env` is ever compromised

The file is gitignored, but screen shares, logs, and crash dumps are still
risks. If you suspect exposure, rotate:

- `ANTHROPIC_API_KEY` at [console.anthropic.com](https://console.anthropic.com/)
- `JWT_SECRET_KEY` — generate a new random value, restart the API
- `POSTGRES_PASSWORD` — `ALTER USER alchymine WITH PASSWORD '...';` then
  update the env file
- `ALCHYMINE_ENCRYPTION_KEY` — **careful**, this invalidates at-rest encrypted
  data; only rotate with a re-encryption migration
- `REDIS_PASSWORD` — update both Redis config and env file
- `RESEND_API_KEY` at [resend.com](https://resend.com/api-keys)
- Any provider keys (Stripe, webhooks, etc.)

### How to Un-Integrate (You Shouldn't, But)

If for some reason you need to fully back out the Archon integration:

```powershell
cd I:\GithubI\Alchymine

# 1. Restore .env to the repo root (this re-exposes secrets to AI subprocesses!)
move .secrets\.env .env
rmdir .secrets

# 2. Revert the Pydantic Settings change
# Edit alchymine/config.py:30 — change env_file=".secrets/.env" back to env_file=".env"

# 3. Remove the docker wrapper
del run.ps1

# 4. Remove the archon skill from the repo
rmdir /s /q .claude\skills\archon

# 5. Revert .env.example header comment and .gitignore changes

# 6. Deregister Alchymine from Archon
archon codebase remove realsammyt/Alchymine   # or via Web UI
```

**Do not do this lightly.** The `.secrets/.env` convention exists for
security reasons that long outlive the Archon integration.

---

## Further Reading

- **Archon usage patterns** (when to use Archon vs direct Claude Code, decision tree, cross-project best practices):
  `.claude\skills\archon\references\usage-patterns.md`
- **Archon skill reference** (deep dive on workflow authoring):
  `I:\GithubI\Archon\.claude\skills\archon\references\`
- **Archon skill guides** (how-to articles):
  `I:\GithubI\Archon\.claude\skills\archon\guides\`
- **Archon docs site source** (user-facing documentation):
  `I:\GithubI\Archon\packages\docs-web\src\content\docs\`
- **Archon source code** (for tweaking Archon itself):
  `I:\GithubI\Archon\`
- **ADR-009: Archon Integration** (the why/how decision record):
  `I:\GithubI\Alchymine\docs\adr\009-archon-integration.md`
- **Alchymine deployment guide** (production deployment):
  `I:\GithubI\Alchymine\docs\guides\deployment-guide.md`
- **Alchymine config loader** (the line that reads `.secrets/.env`):
  `I:\GithubI\Alchymine\alchymine\config.py:30`

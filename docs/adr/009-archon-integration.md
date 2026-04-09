# ADR-009: Archon Integration — Secrets Relocation and Docker Wrapper

**Status:** Accepted

**Date:** 2026-04-09

**Authors:** Sammy + Claude Code session

## Context

On 2026-04-09 Alchymine was integrated with [Archon](https://github.com/coleam00/Archon), a remote agentic coding platform living at `I:\GithubI\Archon`. Archon spawns AI subprocesses (Claude Agent SDK, Codex SDK) against target repositories and drives them from chat platforms (Slack, Telegram, GitHub, Discord, Web). To use Archon against Alchymine, the Alchymine repository must be registered as an Archon "codebase".

Registration failed on the first attempt. Two distinct — but related — problems surfaced.

### Problem 1: Bun auto-loads `.env` into AI subprocesses

Archon is built on Bun. When it spawns an AI subprocess with `cwd=<target repo>`, Bun auto-loads any `.env` (and similarly-named) file from that cwd directly into the subprocess environment. For Alchymine, that meant every secret in the repo-root `.env` would become visible to the AI subprocess:

- `ANTHROPIC_API_KEY` (production key the Alchymine app itself uses for its own Claude calls — not a throwaway)
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `ALCHYMINE_ENCRYPTION_KEY`
- `REDIS_PASSWORD`
- `RESEND_API_KEY`
- `PDF_SERVICE_TOKEN`
- …and anything else ever added to `.env`

Any of these could be exfiltrated via a `bash cat .env`, an `echo $ANTHROPIC_API_KEY`, a tool-call output, a prompt injection, or a well-meaning workflow that logs environment for debugging. The blast radius was the entire Alchymine production secret surface.

### Problem 2: Archon's env-leak gate blocks registration

Archon ships an env-leak scanner (`I:\GithubI\Archon\packages\core\src\utils\env-leak-scanner.ts`) that refuses to register a codebase when it finds AI-specific API keys in the repo root. The scanner:

- Scans only the repo **root** (not subdirectories).
- Scans only these filenames: `.env`, `.env.local`, `.env.development`, `.env.production`, `.env.development.local`, `.env.production.local`.
- Flags these key names: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `OPENAI_API_KEY`, `CODEX_API_KEY`, `GEMINI_API_KEY`.

`POST /api/codebases` returned 422 because Alchymine's `.env` contained `ANTHROPIC_API_KEY`. This gate is not the full safety story — it only flags the AI-specific subset — but it is a forcing function that surfaced Problem 1 before any AI subprocess actually ran.

We needed to resolve both problems without compromising secrets and without breaking Alchymine's existing developer workflow (Docker Compose, Pydantic Settings, pytest, the Next.js frontend, and production deploys).

## Decision

Move Alchymine's runtime secrets from `.env` at the repo root to `.secrets/.env` inside the repo. Update `alchymine/config.py` to read from the new location. Add a `run.ps1` wrapper that invokes `docker compose --env-file .secrets/.env` so contributors do not have to remember the flag. Register Alchymine in Archon without granting any env-leak consent — the gate should be **satisfied**, not bypassed.

The file stays inside the repo tree (so it travels with the project and stays close to the code that uses it), stays gitignored, and lives in a directory whose name makes its purpose unambiguous.

## Alternatives Considered

### 1. Grant Archon consent (`allowEnvKeys: true`)

Archon allows a codebase owner to acknowledge the risk and bypass the gate via `PATCH /api/codebases/:id` with `{"allowEnvKeys": true}`. **Rejected** because:

- The scanner only flags the AI-specific keys, but **all** keys in `.env` leak to the AI subprocess (JWT, DB password, encryption key, etc.). Granting consent is honest about one risk and silently exposes a much bigger surface.
- `ANTHROPIC_API_KEY` in Alchymine's `.env` is the production key Alchymine itself uses. Leaking it has real blast radius.
- Consent is a long-term liability: any future secret added to `.env` also leaks, silently, forever.

### 2. Rename `.env` → `.env.local` in place

**Rejected.** Bun still auto-loads `.env.local`, and Archon's gate also scans `.env.local`. This would change nothing.

### 3. Rename `.env` → `.env.private` (or another non-auto-loaded name) in the repo root

Would solve both the Bun auto-load problem and the Archon gate (since the gate only scans the specific filenames listed above). **Rejected** because Docker Compose specifically looks for `.env` in the project directory for variable substitution, and Alchymine's `docker-compose.yml` uses variable substitution extensively (`${ANTHROPIC_API_KEY:-}`, `${POSTGRES_PASSWORD:?...}`, etc.). We would have to pass `--env-file` on every `docker compose` invocation anyway — and if we are doing that, we may as well move the file to a more meaningful location.

### 4. Move keys to a dedicated secrets manager (Doppler, 1Password CLI, Infisical)

Structurally the best long-term answer: secrets never live on disk in the repo at all. **Rejected for this pass** because it is invasive (requires changing how every Alchymine component reads its config), the Archon integration was needed immediately, and the investment is significant. Captured as follow-up work.

### 5. Move `.env` to a subdirectory inside the repo

Chose between three candidate locations:

- **`config/.env`** — `config/` already exists and holds runtime YAML. Rejected because mixing secrets into a non-secret directory reads ambiguously and fights the existing purpose of the folder.
- **`~/.alchymine/.env`** (outside the repo entirely) — strongest isolation. Rejected because it requires setting the file up on every machine and CI runner, breaks repo-portability, and is awkward on Windows (`$HOME` ergonomics).
- **`.secrets/.env`** — a clearly-labeled secrets subdirectory inside the repo, gitignored, obvious purpose, trivially reversible. **Chosen.**

## Changes Made

- **Created directory** `I:\GithubI\Alchymine\.secrets\`.
- **Moved file** `I:\GithubI\Alchymine\.env` → `I:\GithubI\Alchymine\.secrets\.env`.
- **Modified** `I:\GithubI\Alchymine\alchymine\config.py` line 30: `env_file=".env"` → `env_file=".secrets/.env"`.
- **Modified** `I:\GithubI\Alchymine\.gitignore`: appended `.secrets/` under the `# ─── Environment & Secrets ───` section.
- **Created** `I:\GithubI\Alchymine\run.ps1`: PowerShell wrapper that runs `docker compose --env-file .secrets/.env -f infrastructure/docker-compose.yml @args`. Usage: `./run.ps1 up -d`, `./run.ps1 logs -f api`, `./run.ps1 down`, `./run.ps1 config`.
- **Modified** `I:\GithubI\Alchymine\.env.example`: added a 10-line header comment explaining the `.secrets/.env` convention and pointing to `docs/guides/archon-integration.md`.
- **Copied** `I:\GithubI\Archon\.claude\skills\archon\` → `I:\GithubI\Alchymine\.claude\skills\archon\` so Claude Code sessions inside Alchymine can invoke the `archon` skill.
- **Updated** `I:\GithubI\Alchymine\CLAUDE.md`: added a new "Archon Integration" section.
- **Created** `I:\GithubI\Alchymine\docs\guides\archon-integration.md`: long-form reference guide.
- **Registered** Alchymine in Archon via `POST /api/codebases` — codebase id `493dc1f45b4234ce0e3558c3351bad7d`, `allow_env_keys = 0` (the gate was **not** tripped after the move, so no consent was needed).

## Consequences

**Positive:**

- Archon integration works with **zero** consent grants. No `allowEnvKeys: true` anywhere. The gate was satisfied, not bypassed.
- AI subprocesses running with `cwd=I:\GithubI\Alchymine` do not see Alchymine's secrets via Bun auto-load.
- Secrets are physically separated from application code. Harder to accidentally `git add .`, `tar cf`, or log-dump them.
- A single explicit location for all runtime secrets — easier to audit, rotate, back up.
- `.env.example` stays at the repo root where contributors expect it.
- Tests were unaffected — `tests/test_config.py:22` passes `_env_file=None` and so never loads `.env` at all.
- Production deploys (`docker-compose.prod.yml`) were unaffected — they already use `env_file: ../.env.production` via explicit paths.
- The Next.js frontend was unaffected — it reads its own `.env*` files under `alchymine/web/`, not the repo root.
- Reversible in under a minute (see Rollback Plan).

**Negative:**

- `docker compose up` directly (without `--env-file` or the wrapper) will fail because there is no `.env` in the cwd. Must use `./run.ps1` or pass the flag explicitly. Muscle memory risk.
- `uvicorn alchymine.api.main:app`, `pytest`, and other Python invocations must be run from the Alchymine repo root (not from `alchymine/` or `tests/`) because Pydantic Settings resolves `.secrets/.env` relative to the cwd. A more robust fix would be to resolve the path relative to `__file__`, but that is a future improvement — and the cwd-relative path is what the code had before this change.
- New contributors must be told about the convention; they will not discover `./run.ps1` by running `docker compose` from habit. Mitigated by the updated `.env.example` header, the `CLAUDE.md` section, and `docs/guides/archon-integration.md`.
- If a future workflow or script assumes `I:\GithubI\Alchymine\.env` exists, it will break. The `scripts/` directory should be audited (see Follow-up Work).
- `run.ps1` is Windows-only. Contributors on Linux/macOS would need a `run.sh` equivalent. Out of scope for this change; the primary developer is on Windows.

**Risks:**

- A secret added in future to `.secrets/.env` is still only as safe as the `.secrets/` directory's gitignore line. A careless `git add -f` can still commit it. The convention does not remove the need for pre-commit hygiene.

## Rollback Plan

If this decision needs to be reverted, the exact steps are:

1. `mv I:\GithubI\Alchymine\.secrets\.env I:\GithubI\Alchymine\.env` — move the file back.
2. Edit `alchymine\config.py` line 30: change `.secrets/.env` back to `.env`.
3. Delete `I:\GithubI\Alchymine\run.ps1`.
4. Remove `.secrets/` from `I:\GithubI\Alchymine\.gitignore`.
5. Delete `I:\GithubI\Alchymine\.claude\skills\archon\` (optional — the skill does not hurt).
6. Revert the `CLAUDE.md` and `.env.example` edits.
7. Delete `I:\GithubI\Alchymine\docs\guides\archon-integration.md` and this planning doc.
8. In Archon, either delete the Alchymine codebase (`DELETE /api/codebases/493dc1f45b4234ce0e3558c3351bad7d`) or grant consent (`PATCH /api/codebases/493dc1f45b4234ce0e3558c3351bad7d` with body `{"allowEnvKeys": true}`).

## Follow-up Work

- Audit `scripts/` for any shell scripts that read `.env` directly from the repo root.
- Consider making `alchymine/config.py` resolve `env_file` relative to `Path(__file__).parent.parent` so it works regardless of cwd.
- If Alchymine ever adds Linux/macOS dev support, add a `run.sh` equivalent to `run.ps1`.
- Long-term: evaluate Doppler / Infisical / 1Password CLI as a cleaner secrets story that removes `.env` from disk entirely.
- Periodically re-audit `.secrets/.env` contents against a documented inventory of required keys, to catch drift and stale secrets.

## References

- Archon integration guide: `I:\GithubI\Alchymine\docs\guides\archon-integration.md`
- Archon env-leak scanner: `I:\GithubI\Archon\packages\core\src\utils\env-leak-scanner.ts`
- Alchymine config loader: `I:\GithubI\Alchymine\alchymine\config.py` (see `env_file=".secrets/.env"` on line 30)
- Docker Compose wrapper: `I:\GithubI\Alchymine\run.ps1`
- Archon codebase registration API: `POST /api/codebases`, `PATCH /api/codebases/:id` (see `I:\GithubI\Archon\packages\server\src\routes\api.ts`)
- Registered Archon codebase id: `493dc1f45b4234ce0e3558c3351bad7d` (`allow_env_keys = 0`)

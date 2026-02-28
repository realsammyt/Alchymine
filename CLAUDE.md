# Alchymine — Claude Code Configuration

## Project Overview
Alchymine is an open-source, AI-powered Personal Transformation Operating System
with five integrated pillars: Personalized Intelligence, Ethical Healing,
Generational Wealth, Creative Development, and Perspective Enhancement.

- **License**: CC-BY-NC-SA 4.0
- **PRD**: `Alchymine PRD v7 FiveSystem.docx`
- **Upstream**: github.com/realsammyt/healing-swarm-skills

## Tech Stack
- **Engine**: Python 3.11+ (numerology, astrology, wealth, creative, perspective — all deterministic)
- **API**: FastAPI + Celery + Redis
- **Frontend**: Next.js 14+ (App Router), React, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 15+
- **Queue**: Celery with Redis broker
- **PDF**: Puppeteer/Playwright
- **LLM**: Claude API (recommended) + Ollama fallback
- **Agents**: CrewAI + LangGraph + MCP
- **Deployment**: Docker Compose (local-first per ADR-002)

## Commands

### Python (engine + api)
```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/engine/ tests/api/ -v

# Lint
ruff check alchymine/
ruff format --check alchymine/

# Type check
mypy alchymine/

# Run API server (dev)
uvicorn alchymine.api.main:app --reload --port 8000
```

### Frontend (web)
```bash
cd alchymine/web

# Install dependencies
npm install

# Run dev server
npm run dev

# Run tests
npm test

# Lint
npm run lint

# Type check
npm run type-check

# Build
npm run build
```

### Docker
```bash
# Start full dev stack
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.dev.yml up

# Run all tests in Docker
docker compose -f infrastructure/docker-compose.yml run --rm api pytest

# Build production images
docker compose -f infrastructure/docker-compose.yml build
```

### Ethics & Quality
```bash
# Validate all YAML prompts
python -m alchymine.prompts.validate

# Run ethics check on prompts
python -m alchymine.agents.quality.ethics_check

# Run quality gate regression tests
pytest tests/agents/ -v
```

## Architecture
- Five systems share data through a unified UserProfile v2.0 (Pydantic model)
- All financial calculations are deterministic (never LLM-generated)
- All outputs pass through Quality Swarm validation before delivery
- Financial data classified as Sensitive — encrypted, isolated, never sent to LLM
- Hub-and-spoke agent architecture: 1 Master Orchestrator → 5 Coordinators → 28 agents

## Agent Workflow — GitHub Issue Tracking (ADR-008)

When building features with parallel agent swarms:
1. **Before launching**: Identify relevant GitHub issue numbers
2. **Each agent must**: Comment on its issue when tests pass (✅) or when blocked (⚠️)
3. **Orchestrator must**: Comment + close issues after merging and full test suite passes
4. **Token**: Set `GH_TOKEN` env var for `gh` CLI access
5. **Reference**: See `docs/adr/008-agent-issue-tracking.md` for full protocol

### Issue Creation
```bash
# IMPORTANT: Use separate --label flags, NOT comma-separated
gh issue create -R realsammyt/Alchymine \
  --title "Issue title" \
  --label "system:core" --label "type:feature" --label "priority:critical" --label "phase:9" \
  --body "Issue body"
```

### Issue Comment Templates
```bash
# On success
gh issue comment <#> -R realsammyt/Alchymine --body "✅ [Feature] complete — [summary]. All tests passing."

# On blocked
gh issue comment <#> -R realsammyt/Alchymine --body "⚠️ [Feature] blocked — [blocker]. Needs: [resolution]."

# On merge + close
gh issue close <#> -R realsammyt/Alchymine --comment "🔀 Merged. Full suite: [N] tests passing."
```

## CI Monitoring Protocol (MANDATORY)

**Every PR merge or push MUST be verified against GitHub Actions before closing issues or marking work complete.**

### Pre-Merge Checklist
Before committing code, always run locally:
```bash
ruff check alchymine/             # 0 errors required
ruff format --check alchymine/    # All files formatted
mypy alchymine/                   # Success: no issues found
CELERY_ALWAYS_EAGER=true pytest tests/ -v  # All tests passing
```

### Post-Push Verification
After every `git push`, monitor the GitHub Actions run:
```bash
# Check latest CI run status (poll until complete)
gh run list -R realsammyt/Alchymine --limit 3
gh run view <run-id> -R realsammyt/Alchymine

# If a run fails, view the logs
gh run view <run-id> -R realsammyt/Alchymine --log-failed
```

### Issue/Task Closure Rules
1. **NEVER close a GitHub issue until CI is green** on the branch/PR that implements it
2. **NEVER mark a task as complete** if CI has not been verified
3. If CI fails after push, fix the failures before doing any other work
4. Include the CI run URL or test count in the issue close comment

### Common CI Failure Categories
| Check | Fix |
|-------|-----|
| `ruff check` | Run `ruff check --fix alchymine/` then fix remaining manually |
| `ruff format` | Run `ruff format alchymine/` |
| `mypy` | Check `pyproject.toml` overrides; add `type: ignore` only as last resort |
| `pytest` | Run failing tests locally with `-v --tb=long` |
| `pip-audit` | Update vulnerable deps or add `[tool.pip-audit]` ignore with justification |

## Key Principles
- Ethics-first: "First, Do No Harm" applies to all outputs
- Local-first: User data stays on user's device/infrastructure (ADR-002)
- Transparency: Open-source prompts, methodology panels, evidence ratings
- No dark patterns: Never use calming design to mask problems or manipulate decisions
- Cultural sensitivity: Proper attribution of all traditions and frameworks

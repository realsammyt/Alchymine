# Alchymine

**Open-Source AI-Powered Personal Transformation Operating System**

*"Turn knowing into gold."*

Personalized Intelligence | Ethical Healing | Generational Wealth | Creative Development | Perspective Enhancement

---

## What is Alchymine?

Alchymine is a five-system platform that transforms self-knowledge into actionable life strategy:

1. **Alchymine Core** -- Deep self-discovery through numerology, astrology, archetypes, and personality science
2. **Healing Swarm** -- Ethical holistic practices: breathwork, meditation, and 15+ evidence-grounded healing modalities
3. **Wealth Engine** -- Actionable wealth-building across 6 domains: income, investment, business, defense, family, and intelligence
4. **Creative Forge** -- 7-domain creative development grounded in the neuroscience of DMN-ECN coupling
5. **Perspective Prism** -- 3-layer perspective enhancement: cognitive reframing (CBT), strategic positioning, worldview expansion

Built on [healing-swarm-skills](https://github.com/realsammyt/healing-swarm-skills). Licensed under CC-BY-NC-SA 4.0.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/realsammyt/Alchymine.git
cd Alchymine

# Start the full development stack
docker compose -f infrastructure/docker-compose.yml \
               -f infrastructure/docker-compose.dev.yml up

# Access the application
# Web: http://localhost:3000
# API: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Manual Setup

```bash
# Python engine + API
pip install -e ".[dev]"
uvicorn alchymine.api.main:app --reload --port 8000

# Frontend
cd alchymine/web && npm install && npm run dev
```

## Architecture

```
User Intake → Master Orchestrator → 5 System Coordinators → 28 Domain Agents → Quality Gates → Report
                    │
    ┌───────────────┼───────────────┐───────────────┐───────────────┐
    ▼               ▼               ▼               ▼               ▼
 PI Core        Healing         Wealth          Creative       Perspective
 6 agents       5 agents        5 agents        7 agents        5 agents
 6 skills       10 skills       7 skills        7 skills        7 skills
```

- **34 agents** (28 domain + 5 coordinators + 1 Master Orchestrator)
- **46 skills** contributed upstream to healing-swarm-skills
- **19 quality gates** ensuring ethical, accurate, and culturally sensitive outputs
- All financial calculations are **deterministic** (never LLM-generated)
- Hub-and-spoke **Alchemical Spiral** user journey with adaptive entry

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Engine | Python 3.11+ (numerology, astrology, wealth, creative, perspective) |
| API | FastAPI + Celery + Redis |
| Frontend | Next.js 14+ (App Router), React, TypeScript, Tailwind CSS |
| Database | PostgreSQL 15+ |
| Agents | CrewAI + LangGraph + MCP |
| LLM | Claude API (recommended) + Ollama fallback |
| PDF | Puppeteer/Playwright |
| Deployment | Docker Compose (local-first) |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

```bash
# Run Python tests
pytest tests/engine/ tests/api/ -v

# Run frontend tests
cd alchymine/web && npm test

# Lint
ruff check alchymine/
cd alchymine/web && npm run lint

# Type check
mypy alchymine/
cd alchymine/web && npm run type-check
```

## Project Tracking

Development is tracked through GitHub Issues with 8 milestones across 60 weeks:

| Phase | Focus | Weeks |
|-------|-------|-------|
| 1 | Insight Foundation | 1--4 |
| 2 | Healing + Wealth Archetype | 5--8 |
| 3 | Wealth Engine Core | 9--14 |
| 4 | Family & Ecosystem | 15--20 |
| 5 | Expanded Healing Modalities | 21--28 |
| 6 | Global & Ecosystem Maturity | 29--36 |
| 7 | Creative Forge Launch | 37--48 |
| 8 | Perspective Prism + Alchemical Spiral | 49--60 |

## Ethics

Alchymine operates under a unified ethical framework:

- **Do No Harm**: No health claims, no financial guarantees, mandatory disclaimers
- **Honor Traditions**: Proper attribution of all cultural and spiritual lineages
- **Evidence + Humility**: Evidence ratings on every framework, transparent methodology
- **Empower, Not Control**: User autonomy, no dark patterns, no fake scarcity
- **Privacy as Sanctuary**: Local-first data, AES-256 encryption, zero telemetry
- **Accessible to All**: WCAG 2.1 AA, screen reader support, plain-language financial glossary
- **Continuous Improvement**: Skill versioning, community contributions, outcome measurement

## License

CC-BY-NC-SA 4.0. See [LICENSE](LICENSE).

For commercial licensing: tyler@futuretalk.ca

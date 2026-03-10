# Alchymine System Diagrams & Roadmap Design

**Date:** 2026-03-10
**Status:** Approved
**Author:** Claude + Sam

## Scope

Create 5 Excalidraw diagrams with progressive disclosure (3 zoom levels each) covering:

1. System Architecture
2. Information Flow
3. User Journey
4. Current Functions Matrix
5. 90-Day Compressed Roadmap

## Audience

All diagrams serve three audiences simultaneously:

- **Executive/Stakeholder** — top-level boxes, clean arrows, one-sentence labels
- **Architect** — components, protocols, data shapes, boundaries
- **Developer** — file paths, function names, port numbers, specific gaps

## Design Decisions

### Color System (consistent across all 5 diagrams)

| Color     | Hex     | Meaning                             |
| --------- | ------- | ----------------------------------- |
| Gold      | #DAA520 | Intelligence / User / Core identity |
| Teal      | #20B2AA | Frontend / Creative                 |
| Purple    | #7B2D8E | Backend / Agent layer               |
| Red/Coral | #E8553A | Data / Storage                      |
| Green     | #4CAF50 | Future / Planned                    |
| Gray      | #888888 | Supporting services                 |

### Visual Conventions

- Solid borders = existing/working
- Dashed borders = planned/future
- Same spatial positions at every zoom level (detail adds, layout doesn't change)
- Green dashed boxes for: AI Growth Agent (Agent SDK), Gemini Art Service, healing-swarm-skills

---

## Diagram 1: System Architecture

**Purpose:** Show the full stack — infrastructure, services, networks, and planned additions.

**Executive level:**

- Users → Next.js Frontend → FastAPI + Celery Workers → PostgreSQL + Redis → Future services (Growth Agent, Gemini Art, PDF)

**Architect level adds:**

- Docker network topology (alchymine-net connects api/web/worker/db/redis; pdf-net isolates pdf-service)
- Middleware stack (RequestId → RateLimit → Logging → CORS → ErrorHandler)
- Queue routing (celery queue + reports queue)
- Redis DB slots (0=broker, 1=cache)
- Encryption boundary around wealth data
- Auth flow (JWT + httpOnly cookies)

**Developer level adds:**

- File paths: api/main.py, workers/tasks.py, workers/celery_app.py
- Port numbers: 8000 (API), 3000 (web), 3001 (pdf), 5432 (pg), 6379 (redis)
- Dockerfile references per service
- Environment variable callouts

---

## Diagram 2: Information Flow

**Purpose:** Trace a user request from click to completed report.

**Executive level:**

- Linear pipeline: User Click → API → Orchestrator → 5 Systems → Synthesis → Report → PDF

**Architect level adds:**

- Hub-and-spoke: MasterOrchestrator dispatches to 5 coordinators
- Intelligence enrichment: life_path, archetype, big_five, risk_tolerance, astrology pipe downstream
- LangGraph node sequences per system:
  - Intelligence: numerology → astrology → personality → archetype → biorhythm → status
  - Healing: init → crisis_detection → modality_matching → status
  - Wealth: init → archetype → lever_prioritisation → calculations → status
  - Creative: orientation → strengths → personality_context → status
  - Perspective: bias_detection → kegan_assessment → decision_framework → status
- Narrative generation: YAML templates → Claude API → ethics check → content filter
- Quality gates at each coordinator output
- Synthesis: 6 cross-system bridges (XS-01 through XS-06)

**Developer level adds:**

- Function call chain with file:line references
- Data shapes: IntakeData → CoordinatorResult → SynthesisResult → ProfileSummary
- Celery task dispatch and DB status transitions (pending → generating → complete)
- PDF generation subprocess

---

## Diagram 3: User Journey

**Purpose:** Map the complete user experience from landing to ongoing engagement.

**Executive level:**

- 7 stages: Land → Auth → Intake → Assess → Generate → Report → Explore
- Future: Growth Agent touchpoints woven throughout

**Architect level adds:**

- Page-by-page flow with branching paths
- Dashboard as hub (loops back to discover, system pages)
- Session storage vs server state at each stage
- Polling mechanics (4s interval, 10min timeout, backoff on 429)
- Admin panel branch
- Future growth agent entry points: chat panel, per-system coaching, proactive nudges
- Gemini art touchpoints: report visuals, creative studio, journey illustrations

**Developer level adds:**

- Route paths (/discover/intake, /discover/assessment, etc.)
- Component names (SpiralHub, BreathworkTimer, DebtCalculator)
- API calls at each step (POST /reports, GET /reports/{id}, etc.)
- Auth guards (ProtectedRoute, AdminRoute)
- SessionStorage keys (alchymine_intake)

---

## Diagram 4: Current Functions Matrix

**Purpose:** Status grid showing what works, what's partial, what's planned across all 5 systems.

**Executive level:**

- 5 systems × 4 layers (Engine, API, Frontend, MCP) status grid
- Status indicators: COMPLETE / PARTIAL / PLANNED / EMPTY

**Architect level adds:**

- Per-system capability list:
  - Intelligence: 6 engines (numerology, astrology, personality, archetype, biorhythm, compatibility)
  - Healing: 15 modalities, crisis detection, breathwork, assessment
  - Wealth: archetype, levers, debt calc, plan, export
  - Creative: Guilford assessment, style fingerprint, projects, collaboration
  - Perspective: bias detection, Kegan stages, 3 frameworks, scenarios
- Specific gaps:
  - MCP: no transport layer (in-process only)
  - Cross-system bridges: backend only, not in UI
  - Skills directory: 6 subdirectories, all empty
  - Creative graph: personality_context node not connected
  - Streaming endpoint: declared but not wired

**Developer level adds:**

- File counts per system
- Test file references
- Specific broken edges with file:line

---

## Diagram 5: 90-Day Compressed Roadmap

**Purpose:** 12-month vision compressed into 3 months across 3 parallel tracks.

### Track 1: Healing-Swarm-Skills + Cross-System UX (Gold)

- Weeks 1-2: Declare dependency, populate skills directory, activate MCP transport
- Weeks 3-4: Wire cross-system bridges (XS-01 through XS-06) into frontend
- Weeks 5-6: Build interactive healing tools (breathwork logging, modality explorer)
- Weeks 7-8: Spiral Dynamics integration, journal system completion
- Weeks 9-10: 46 healing-swarm skills populated and tested
- Weeks 11-12: Upstream PR contributions, skill refinement

### Track 2: AI Growth Assistant Agent (Purple)

- Weeks 1-2: Agent SDK setup, MCP transport layer (stdio/HTTP), base agent scaffold
- Weeks 3-4: Chat-based interface — conversational sidebar with profile-aware context
- Weeks 5-6: Proactive coach — daily practice suggestions, progress nudges, milestone tracking
- Weeks 7-8: Embedded companion — per-system persona adaptation (healing coach, wealth mentor, etc.)
- Weeks 9-10: Cross-system intelligence — agent uses synthesis bridges for holistic guidance
- Weeks 11-12: Agent refinement, memory/persistence, multi-turn coaching sessions

### Track 3: Gemini Generative Art (Teal)

- Weeks 1-2: Gemini 3.1 Flash Image Preview API integration, image generation pipeline
- Weeks 3-4: Report enhancement — personalized archetype art, chart visualizations
- Weeks 5-6: Interactive creative studio on Creative system page
- Weeks 7-8: Growth journey visuals — coaching conversation illustrations, progress art
- Weeks 9-10: Brand/identity generation — avatar, color palette, symbolic artwork from profile
- Weeks 11-12: Polish, caching, gallery, sharing

### Dependencies

- Track 2 needs MCP transport (Track 1, week 1-2) before agent can call system tools
- Track 3 report enhancement needs working report pipeline (already exists)
- Track 2 embedded companion needs Track 1 cross-system bridges in UI

### Milestones

- **Week 4:** MVP — Chat agent working, cross-system bridges in UI, first generated art in reports
- **Week 8:** Beta — Full agent with proactive coaching, 15+ healing skills active, creative studio live
- **Week 12:** Launch — All 3 tracks complete, 46 skills, full-spectrum agent, generative art throughout

---

## Output

5 Excalidraw JSON files saved to `docs/diagrams/`:

1. `01-system-architecture.excalidraw`
2. `02-information-flow.excalidraw`
3. `03-user-journey.excalidraw`
4. `04-current-functions.excalidraw`
5. `05-roadmap-90-day.excalidraw`

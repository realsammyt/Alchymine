#!/usr/bin/env bash
# Alchymine — Create all GitHub issues for Phases 0-8
# Run after setup-github-tracking.sh
# Usage: ./scripts/create-phase-issues.sh [phase-number]
# If no phase given, creates all issues for all phases

set -euo pipefail

REPO="realsammyt/Alchymine"

create_issue() {
  local title="$1"
  local body="$2"
  local labels="$3"
  local milestone="$4"

  gh issue create -R "$REPO" \
    --title "$title" \
    --body "$body" \
    --label "$labels" \
    --milestone "$milestone" 2>/dev/null && echo "  Created: $title" || echo "  FAILED: $title"
}

# ═══ PHASE 0: Bootstrap ═══════════════════════════════════════════════════
create_phase_0() {
  echo "=== Phase 0: Bootstrap & Infrastructure ==="
  local M="Phase 1: Insight Foundation"  # Bootstrap issues go into Phase 1 milestone

  create_issue "[Infra] Repository directory structure scaffold" \
    "Create the full directory structure per the plan: alchymine/, skills/, infrastructure/, tests/, docs/, templates/, examples/. Add .gitkeep files to empty directories." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[Infra] Python project configuration (pyproject.toml)" \
    "Configure pyproject.toml with all dependencies: FastAPI, Celery, Redis, pyswisseph, Pydantic, SQLAlchemy, cryptography, anthropic SDK. Include dev dependencies: pytest, ruff, mypy." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[Infra] Next.js project scaffold (package.json, tsconfig, tailwind)" \
    "Initialize Next.js 14+ project in alchymine/web/ with App Router, TypeScript, Tailwind CSS, and base configuration." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[CI/CD] Main CI pipeline (ci.yml)" \
    "GitHub Actions workflow: lint (ruff, eslint), type check (mypy, tsc), unit tests (pytest, Jest), integration tests, ethics check, Docker build, coverage enforcement." \
    "system:infrastructure,type:ci-cd,phase:0" "$M"

  create_issue "[CI/CD] Security scanning pipeline (security.yml)" \
    "Weekly security scan: pip-audit, npm audit, bandit, trufflehog, trivy container scanning." \
    "system:infrastructure,type:ci-cd,type:security,phase:0" "$M"

  create_issue "[CI/CD] Docker build pipeline (build.yml)" \
    "Build all Docker images on merge to develop, push to ghcr.io, run smoke tests." \
    "system:infrastructure,type:ci-cd,phase:0" "$M"

  create_issue "[CI/CD] Release pipeline (release.yml)" \
    "Semantic versioning with conventional commits, CHANGELOG generation, GitHub Release, Docker semver tags." \
    "system:infrastructure,type:ci-cd,phase:0" "$M"

  create_issue "[Infra] Docker Compose dev stack" \
    "docker-compose.yml with: FastAPI, Celery worker, Next.js, PostgreSQL 15, Redis 7, PDF service. Dev overrides with hot reload." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[Infra] Docker Compose production config" \
    "Production overrides: restart policies, resource limits, health checks, no code mounts. Staging config as intermediate." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[Docs] Architecture Decision Records (ADR 001-007)" \
    "Create ADRs: 001-monorepo, 002-local-first, 003-healing-swarm, 004-wealth-engine, 005-creative-forge, 006-perspective-prism, 007-alchemical-spiral." \
    "system:infrastructure,type:docs,phase:0" "$M"

  create_issue "[Docs] CONTRIBUTING.md + CODE_OF_CONDUCT.md" \
    "Contribution guide: PR process, skill creation, domain-specific reviews. Code of conduct with financial/healing-specific additions." \
    "system:infrastructure,type:docs,phase:0" "$M"

  create_issue "[Infra] PR template + CODEOWNERS + dependabot" \
    "Pull request template with system checklist. CODEOWNERS per domain. Dependabot for Python and npm." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[Infra] GitHub issue templates (bug, feature, skill, wealth, creative)" \
    "YAML-form issue templates for all issue types with appropriate fields and dropdowns." \
    "system:infrastructure,type:feature,phase:0" "$M"

  create_issue "[Infra] CLAUDE.md project configuration" \
    "Claude Code configuration with commands, architecture context, and key principles." \
    "system:infrastructure,type:docs,phase:0" "$M"

  create_issue "[Infra] .env.example + .gitignore" \
    "Environment variable template covering all services. Comprehensive gitignore for Python, Node.js, Docker." \
    "system:infrastructure,type:feature,phase:0" "$M"

  echo ""
}

# ═══ PHASE 1: Insight Foundation ═══════════════════════════════════════════
create_phase_1() {
  echo "=== Phase 1: Insight Foundation (Weeks 1-4) ==="
  local M="Phase 1: Insight Foundation"

  # Engine
  create_issue "[Engine] Pythagorean numerology engine" \
    "Implement Pythagorean numerology calculations: Life Path, Expression, Soul Urge, Personality numbers. Handle master numbers (11, 22, 33). Include letter-to-number mapping and reduction algorithms.\n\nAcceptance:\n- All calculations match reference tables\n- Master numbers preserved correctly\n- 100% test coverage for all number types" \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Engine] Chaldean numerology engine" \
    "Implement Chaldean numerology as alternative system. Different letter-to-number mapping than Pythagorean. Number 9 not assigned to any letter." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Engine] Astrological chart engine (pyswisseph)" \
    "Integrate pyswisseph for natal chart calculations: Sun, Moon, Rising signs; house placements; current transits; personal year overlay. Bundle Swiss Ephemeris data files." \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Engine] Archetype mapping engine" \
    "Build Jungian archetype mapping: 12 archetypes with light/shadow profiles. Map from combined numerology + astrology data. Include shadow integration analysis." \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Engine] Big Five personality scoring (mini-IPIP)" \
    "Implement mini-IPIP 20-item Big Five personality assessment scoring. Scale calculation, normative comparison, trait descriptions." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Engine] Attachment style + Enneagram scoring" \
    "Implement attachment style assessment (secure/anxious/avoidant/disorganized) and Enneagram type scoring from questionnaire data." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Engine] UserProfile v2.0 unified schema" \
    "Define the 5-layer UserProfile Pydantic model: identity (numerology, astrology, archetype), healing (modality preferences, practice history), wealth (financial context, risk tolerance), creative (Blueprint, Guilford scores, Creative DNA), perspective (Kegan stage, mental models). This is the shared data contract across all 5 systems." \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Engine] Personal year/cycle calculation" \
    "Calculate numerological Personal Year, Personal Month, and Universal Year/Month. Map to life cycle phases for timing recommendations." \
    "system:core,type:feature,phase:1" "$M"

  # API
  create_issue "[API] FastAPI application scaffold" \
    "FastAPI app with: health check endpoint, CORS middleware, error handling, request validation, structured logging. Modular router registration." \
    "system:infrastructure,type:feature,phase:1,P1-critical" "$M"

  create_issue "[API] POST /api/v1/reports — async report generation" \
    "Accept intake data, create Celery task for report generation, return job ID. Run complete swarm pipeline asynchronously." \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[API] GET /api/v1/reports/{id} — retrieve report" \
    "Retrieve completed report by ID with quality gate validation status. Return 202 if still generating." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[API] GET /api/v1/numerology/{name} — raw calculations" \
    "Deterministic numerology calculations endpoint. No LLM. Returns all number types for a given name." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[API] GET /api/v1/astrology/{date} — raw chart data" \
    "Deterministic astrological chart via Swiss Ephemeris. Returns planetary positions, house placements, aspects." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[API] Authentication + rate limiting middleware" \
    "Bearer token authentication. Rate limits: 100/hr free, 1000/hr paid, unlimited self-hosted. API key generation and validation." \
    "system:infrastructure,type:feature,type:security,phase:1" "$M"

  # Frontend
  create_issue "[Web] Next.js 14+ project scaffold" \
    "Initialize Next.js with App Router, TypeScript, Tailwind CSS, sacred-visuals design tokens, Playfair Display + Inter + JetBrains Mono typography." \
    "system:infrastructure,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Web] Landing page with three-path entry" \
    "Entry page: 'Know Yourself' (insight), 'Heal & Grow' (practices), 'Build Wealth' (engine), or unified 'Full Alchymine'. Premium, intentional design." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Web] Intake form — identity step" \
    "Full name + birthdate. Optional: birth time (for Rising sign accuracy), birth city (for house calculations), family structure." \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Web] Intake form — 20-question assessment" \
    "Card-swipe UI, one question at a time. mini-IPIP Big Five + attachment style + risk tolerance + wealth goals. Skip always visible. Large touch targets." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Web] Intake form — intention setting" \
    "'What matters most right now?' with chips: Career, Love, Purpose, Money, Health, Family, Business, Legacy." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Web] Report generation progress screen" \
    "Animated progress showing five-system pipeline: Research → Build → Quality. Real progress per agent. CalmLoading pattern with breathing invitation. 45-90 second target." \
    "system:core,type:feature,phase:1" "$M"

  create_issue "[Web] Act I Report Viewer — 5 modules" \
    "Progressive disclosure layout. Deep purple/indigo zone. Modules: Life Path, Expression, Celestial Snapshot, Archetype, Strengths Map. Methodology panels, radar charts." \
    "system:core,type:feature,phase:1,P1-critical" "$M"

  create_issue "[Web] PDF export via Puppeteer/Playwright" \
    "One-click PDF export matching web design quality. Advisor-ready formatting option. < 10 second generation." \
    "system:core,type:feature,phase:1" "$M"

  # Skills
  create_issue "[Skill] /numerology skill (YAML prompt)" \
    "Create YAML prompt template for numerology analysis. Research Swarm template base (traditions-research). Include evidence rating, methodology, and tradition attribution." \
    "system:core,type:skill,phase:1" "$M"

  create_issue "[Skill] /archetype-map skill (YAML prompt)" \
    "Create YAML prompt for archetype mapping. Research Swarm template (mechanism-mapping). Map 12 archetypes with light/shadow." \
    "system:core,type:skill,phase:1" "$M"

  create_issue "[Skill] /astro-chart skill (YAML prompt)" \
    "Create YAML prompt for astrological chart interpretation. Research Swarm template (clinical-research). Include transit analysis." \
    "system:core,type:skill,phase:1" "$M"

  # Infrastructure
  create_issue "[Skill] /alchymine orchestrator skill" \
    "Master orchestrator skill coordinating Research → Build → Quality pipeline across all 5 systems. Hub-and-spoke delegation to system coordinators." \
    "system:core,type:skill,type:agent,phase:1,P1-critical" "$M"

  echo ""
}

# ═══ PHASE 2: Healing + Wealth Archetype ══════════════════════════════════
create_phase_2() {
  echo "=== Phase 2: Healing + Wealth Archetype (Weeks 5-8) ==="
  local M="Phase 2: Healing + Wealth Archetype"

  create_issue "[Healing] Breathwork module with BreathworkTimer" "Inline breathwork experience with phase-aware timer. Counts UP (not down). Safety gates for hyperventilation. Gentler rounds for anxious-secure baselines." "system:healing,type:feature,phase:2,P1-critical" "$M"
  create_issue "[Healing] Coherence meditation module" "Guided meditation with audio player. HRV-inspired coherence techniques. Personalized focus based on shadow profile." "system:healing,type:feature,phase:2" "$M"
  create_issue "[Healing] Language awareness module" "Cognitive deautomatization exercises. Language pattern recognition tied to shadow work." "system:healing,type:feature,phase:2" "$M"
  create_issue "[Healing] Resilience training (cold exposure)" "WHM-inspired protocol with safety disclaimers. Progressive difficulty. Contraindication check." "system:healing,type:feature,phase:2" "$M"
  create_issue "[Healing] Consciousness journey module" "Extended contemplative practice. Highest difficulty tier. Requires explicit opt-in." "system:healing,type:feature,phase:2" "$M"
  create_issue "[Web] Act II Report Viewer — healing modules" "Emerald/teal visual zone. Personalized module selection based on profile. Integration patterns embedded." "system:healing,type:feature,phase:2,P1-critical" "$M"
  create_issue "[Skill] /wealth-code — money archetype" "Derive wealth archetype from Alchymine profile. Map earning style, spending patterns, risk tolerance, lever priority." "system:wealth,type:skill,phase:2,P1-critical" "$M"
  create_issue "[Skill] /activation-plan — 90-day unified plan" "Generate personalized 90-day plan across all 5 systems. Three phases: Foundation (1-30), Momentum (31-60), Acceleration (61-90)." "system:wealth,system:cross-system,type:skill,phase:2,P1-critical" "$M"
  create_issue "[Skill] /wealth-review quality gate" "5 wealth quality gates: Clarity, Actionability, Accuracy, Relevance, Durability. Validates all financial outputs." "system:wealth,type:skill,type:ethics,phase:2,P1-critical" "$M"
  create_issue "[Skill] /compatibility — two-person engine" "Two-person compatibility analysis using both profiles. Numerology, archetype, and astrological compatibility." "system:core,type:skill,phase:2" "$M"
  create_issue "[Web] Act IV Report Viewer — 90-day plan" "Gradient synthesis zone. Three-phase timeline. Daily practices + wealth actions per phase." "system:cross-system,type:feature,phase:2" "$M"
  create_issue "[Web] PWA service worker + manifest" "Service worker for offline caching. Installability on iOS/Android. Alchymine branding. Offline report access." "system:infrastructure,type:feature,phase:2" "$M"
  create_issue "[Web] Push notification system" "Web Push API integration. Daily practice reminders, weekly progress, phase transitions. Anti-manipulation: one-click unsubscribe, no fake urgency." "system:infrastructure,type:feature,phase:2" "$M"
  create_issue "[Infra] Email delivery integration" "Resend or SendGrid integration. PDF attachment. Report delivery email. Configurable templates." "system:infrastructure,type:feature,phase:2" "$M"
  create_issue "[API] POST /api/v1/compatibility" "Two-person compatibility endpoint. Accepts two profiles, returns compatibility analysis." "system:core,type:feature,phase:2" "$M"
  create_issue "[API] POST /api/v1/wealth/profile + /plan/90day" "Wealth archetype generation and 90-day plan endpoints." "system:wealth,type:feature,phase:2" "$M"

  echo ""
}

# ═══ Main ═════════════════════════════════════════════════════════════════
PHASE="${1:-all}"

if [ "$PHASE" = "all" ] || [ "$PHASE" = "0" ]; then create_phase_0; fi
if [ "$PHASE" = "all" ] || [ "$PHASE" = "1" ]; then create_phase_1; fi
if [ "$PHASE" = "all" ] || [ "$PHASE" = "2" ]; then create_phase_2; fi

if [ "$PHASE" = "all" ]; then
  echo "=== Phases 3-8 ==="
  echo "Issues for Phases 3-8 will be created as each phase approaches."
  echo "Run: ./scripts/create-phase-issues.sh [3|4|5|6|7|8] when ready."
fi

echo ""
echo "=== Issue Creation Complete ==="
echo "Total issues created for requested phase(s)."
echo "View: https://github.com/$REPO/issues"

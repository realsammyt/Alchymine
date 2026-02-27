#!/usr/bin/env bash
# Alchymine — GitHub Project Tracking Setup
# Run this script with gh CLI authenticated: gh auth login
# Usage: ./scripts/setup-github-tracking.sh

set -euo pipefail

REPO="realsammyt/Alchymine"

echo "=== Alchymine GitHub Tracking Setup ==="
echo "Repository: $REPO"
echo ""

# ─── Milestones ─────────────────────────────────────────────────────────
echo "Creating milestones..."

gh api repos/$REPO/milestones -f title="Phase 1: Insight Foundation" \
  -f description="Weeks 1-4: 6 Alchymine Core skills, numerology/astro engines, web intake, Act I viewer, UserProfile v2.0, Docker Compose, PDF export" \
  -f due_on="2026-04-03T00:00:00Z" 2>/dev/null || echo "  Phase 1 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 2: Healing + Wealth Archetype" \
  -f description="Weeks 5-8: Act II integration, wealth-code/activation-plan skills, PWA, notifications, email delivery" \
  -f due_on="2026-05-01T00:00:00Z" 2>/dev/null || echo "  Phase 2 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 3: Wealth Engine Core" \
  -f description="Weeks 9-14: income/invest/biz/shield skills, interactive tools, creator dashboard, Stripe, security audit" \
  -f due_on="2026-06-12T00:00:00Z" 2>/dev/null || echo "  Phase 3 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 4: Family & Ecosystem" \
  -f description="Weeks 15-20: family-vault/wealth-intel, family dashboard, decision journal, lifecycle loop, i18n prep" \
  -f due_on="2026-07-24T00:00:00Z" 2>/dev/null || echo "  Phase 4 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 5: Expanded Healing Modalities" \
  -f description="Weeks 21-28: P0 safety infrastructure, P1 healing skills, outcome measurement, healing UI components" \
  -f due_on="2026-09-18T00:00:00Z" 2>/dev/null || echo "  Phase 5 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 6: Global & Ecosystem Maturity" \
  -f description="Weeks 29-36: P2/P3 healing skills, full i18n, practitioner pathway, agent testing" \
  -f due_on="2026-11-13T00:00:00Z" 2>/dev/null || echo "  Phase 6 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 7: Creative Forge Launch" \
  -f description="Weeks 37-48: Creative Identity, Skill Development, Production Pipeline, Block Resolution, Creative Business, Collaboration" \
  -f due_on="2027-02-05T00:00:00Z" 2>/dev/null || echo "  Phase 7 milestone exists"

gh api repos/$REPO/milestones -f title="Phase 8: Perspective Prism + Alchemical Spiral" \
  -f description="Weeks 49-60: Cognitive Reframing, Strategic Positioning, Worldview Expansion, Alchemical Spiral UX" \
  -f due_on="2027-04-30T00:00:00Z" 2>/dev/null || echo "  Phase 8 milestone exists"

echo "  Milestones created."
echo ""

# ─── Labels ─────────────────────────────────────────────────────────────
echo "Creating labels..."

# System labels
gh label create "system:core" --color "7B68EE" --description "Alchymine Core (Personalized Intelligence)" -R $REPO 2>/dev/null || true
gh label create "system:healing" --color "2E8B57" --description "Healing Swarm (Ethical Healing)" -R $REPO 2>/dev/null || true
gh label create "system:wealth" --color "DAA520" --description "Wealth Engine (Generational Wealth)" -R $REPO 2>/dev/null || true
gh label create "system:creative" --color "FF6347" --description "Creative Forge (Creative Development)" -R $REPO 2>/dev/null || true
gh label create "system:perspective" --color "4169E1" --description "Perspective Prism (Perspective Enhancement)" -R $REPO 2>/dev/null || true
gh label create "system:cross-system" --color "9370DB" --description "Cross-System Integration" -R $REPO 2>/dev/null || true
gh label create "system:infrastructure" --color "708090" --description "Infrastructure & DevOps" -R $REPO 2>/dev/null || true

# Type labels
gh label create "type:feature" --color "1D76DB" --description "New feature or capability" -R $REPO 2>/dev/null || true
gh label create "type:bug" --color "D73A4A" --description "Bug fix" -R $REPO 2>/dev/null || true
gh label create "type:security" --color "B60205" --description "Security-related" -R $REPO 2>/dev/null || true
gh label create "type:ethics" --color "E6E6FA" --description "Ethics framework and quality gates" -R $REPO 2>/dev/null || true
gh label create "type:a11y" --color "0075CA" --description "Accessibility (WCAG 2.1 AA)" -R $REPO 2>/dev/null || true
gh label create "type:docs" --color "0E8A16" --description "Documentation" -R $REPO 2>/dev/null || true
gh label create "type:ci-cd" --color "FBCA04" --description "CI/CD and deployment" -R $REPO 2>/dev/null || true
gh label create "type:skill" --color "C5DEF5" --description "New skill (YAML prompt + agent)" -R $REPO 2>/dev/null || true
gh label create "type:agent" --color "BFD4F2" --description "Agent definition or configuration" -R $REPO 2>/dev/null || true

# Priority labels
gh label create "P0-safety" --color "B60205" --description "Safety infrastructure — implement before expanding scope" -R $REPO 2>/dev/null || true
gh label create "P1-critical" --color "D93F0B" --description "High-impact with manageable effort" -R $REPO 2>/dev/null || true
gh label create "P2-important" --color "FBCA04" --description "Valuable, requires careful planning" -R $REPO 2>/dev/null || true
gh label create "P3-nice-to-have" --color "0E8A16" --description "Important but complex, longer-term" -R $REPO 2>/dev/null || true

# Phase labels
for i in $(seq 0 8); do
  gh label create "phase:$i" --color "D4C5F9" --description "Phase $i" -R $REPO 2>/dev/null || true
done

# Wealth domain labels
gh label create "domain:income" --color "FFD700" --description "Wealth: Income Generation" -R $REPO 2>/dev/null || true
gh label create "domain:investment" --color "FFA500" --description "Wealth: Investment & Growth" -R $REPO 2>/dev/null || true
gh label create "domain:business" --color "FF8C00" --description "Wealth: Business Building" -R $REPO 2>/dev/null || true
gh label create "domain:defense" --color "CD853F" --description "Wealth: Financial Defense" -R $REPO 2>/dev/null || true
gh label create "domain:family" --color "D2691E" --description "Wealth: Family Infrastructure" -R $REPO 2>/dev/null || true
gh label create "domain:intelligence" --color "B8860B" --description "Wealth: Knowledge & Intelligence" -R $REPO 2>/dev/null || true

# Wealth lever tags
gh label create "lever:earn" --color "32CD32" --description "Wealth Lever: Earn More" -R $REPO 2>/dev/null || true
gh label create "lever:keep" --color "228B22" --description "Wealth Lever: Keep More" -R $REPO 2>/dev/null || true
gh label create "lever:grow" --color "006400" --description "Wealth Lever: Grow More" -R $REPO 2>/dev/null || true
gh label create "lever:protect" --color "2F4F4F" --description "Wealth Lever: Protect More" -R $REPO 2>/dev/null || true
gh label create "lever:transfer" --color "556B2F" --description "Wealth Lever: Transfer More" -R $REPO 2>/dev/null || true

# Creative domain labels
gh label create "creative:identity" --color "FF6347" --description "Creative: Identity Discovery" -R $REPO 2>/dev/null || true
gh label create "creative:skills" --color "FF7F50" --description "Creative: Skill Development" -R $REPO 2>/dev/null || true
gh label create "creative:design" --color "FF4500" --description "Creative: Design Process" -R $REPO 2>/dev/null || true
gh label create "creative:production" --color "DC143C" --description "Creative: Production Pipeline" -R $REPO 2>/dev/null || true
gh label create "creative:business" --color "CD5C5C" --description "Creative: Business & Monetization" -R $REPO 2>/dev/null || true
gh label create "creative:blocks" --color "B22222" --description "Creative: Blocks & Psychology" -R $REPO 2>/dev/null || true
gh label create "creative:collaboration" --color "8B0000" --description "Creative: Collaboration & Community" -R $REPO 2>/dev/null || true

# Perspective domain labels
gh label create "perspective:reframing" --color "4169E1" --description "Perspective: Cognitive Reframing (Layer 1)" -R $REPO 2>/dev/null || true
gh label create "perspective:positioning" --color "1E90FF" --description "Perspective: Strategic Positioning (Layer 2)" -R $REPO 2>/dev/null || true
gh label create "perspective:worldview" --color "0000CD" --description "Perspective: Worldview Expansion (Layer 3)" -R $REPO 2>/dev/null || true

echo "  Labels created."
echo ""

# ─── Project Board ──────────────────────────────────────────────────────
echo "Creating project board..."

# Create a GitHub Projects (v2) board
gh project create --title "Alchymine Development" --owner realsammyt 2>/dev/null || echo "  Project board may already exist"

echo "  Project board created."
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Open the project board: https://github.com/orgs/realsammyt/projects"
echo "  2. Add custom fields: System, Phase, Priority, Wealth Lever, Status"
echo "  3. Configure board views: Kanban (by Status), Table (by Phase), Roadmap"
echo "  4. Run: ./scripts/create-phase-issues.sh to create all ~236 issues"

# ADR-008: Agent-Driven GitHub Issue Tracking

## Status

Accepted

## Context

Alchymine development uses parallel agent swarms (Claude Code subagents) to build
features across isolated worktrees. The project owner needs real-time visibility
into build progress without monitoring each agent individually.

## Decision

All orchestrator and build agents MUST update GitHub Issues as part of their
workflow. This creates an audit trail and gives the team visibility via the
GitHub Issues timeline.

### Workflow Protocol

```
┌─────────────────┐
│  Orchestrator    │
│  (main context)  │
└───────┬─────────┘
        │ Spawns parallel agents
        ▼
┌───────────────────────────────────────────────┐
│  Build Agent (isolated worktree)              │
│                                               │
│  1. Read existing code + issue requirements   │
│  2. Implement feature                         │
│  3. Write tests                               │
│  4. Run tests → fix failures                  │
│  5. On GREEN tests:                           │
│     └─► gh issue comment <#> --body "✅ ..."  │
│  6. On BLOCKED:                               │
│     └─► gh issue comment <#> --body "⚠️ ..."  │
│  7. Return results to orchestrator            │
└───────────────────────────────────────────────┘
        │
        ▼
┌─────────────────┐
│  Orchestrator    │
│  merges results  │
│  runs full suite │
│  updates issues  │
│  closes issues   │
└─────────────────┘
```

### Issue Comment Format

**On success (tests green):**

```
✅ [Feature Name] complete — [bullet summary of what was built].
All tests passing ([N] tests, [X]% coverage).
```

**On partial/blocked:**

```
⚠️ [Feature Name] partially complete — [what's done].
Blocked: [description of blocker].
Needs: [what's required to unblock].
```

**On orchestrator merge:**

```
🔀 Merged into main dev branch. Full test suite: [N] tests passing.
Closing issue.
```

### GitHub Infrastructure

| Resource        | Count | Purpose                                             |
| --------------- | ----- | --------------------------------------------------- |
| Milestones      | 8     | Phase 1–8 tracking                                  |
| Labels          | 27    | system, type, priority, phase, special              |
| Issue Templates | 5     | bug, feature, skill, wealth module, creative module |

### Label Taxonomy

- `system:` — intelligence, healing, wealth, creative, perspective, core, agents, frontend
- `type:` — feature, bug, refactor, test, docs, infra, ethics, security
- `priority:` — critical, high, medium, low
- `phase:` — 1 through 8
- Special — `ethics-review`, `deterministic`, `sensitive-data`

## Consequences

### Positive

- Real-time visibility for project owner via GitHub Issues timeline
- Audit trail of what each agent built and when
- Clear blocker documentation for debugging
- Agents can reference each other's issue comments for dependencies

### Negative

- Requires GH_TOKEN in agent environment
- Small overhead per agent (~2 API calls)
- Issue comments can get noisy on large batches — mitigated by structured format

### Risks

- Token expiration during long builds — agents should handle 401 gracefully
- Rate limiting on GitHub API — unlikely at our scale (~50 issues)

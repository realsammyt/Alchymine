# ADR-001: Standalone Monorepo Structure

**Status:** Accepted

**Date:** 2025-01-15

## Context

Alchymine extends the healing-swarm-skills framework to encompass five integrated systems: Expanded Healing, Wealth Engine, Creative Forge, Perspective Prism, and the Alchemical Spiral journey. The original healing-swarm-skills repository is a focused project with its own release cadence and governance.

We evaluated three approaches:

1. **Fork healing-swarm-skills** and build on top of it.
2. **Monorepo** that embeds healing-swarm-skills as a submodule.
3. **Standalone monorepo** with healing-swarm-skills as a dependency.

Forking creates merge conflicts with upstream and conflates two governance models. Submodules add operational complexity. A standalone repository with a clear dependency boundary provides the cleanest separation.

## Decision

Alchymine is a standalone monorepo. healing-swarm-skills is declared as a dependency in `pyproject.toml`. The project maintains its own CI/CD pipelines, release process, and governance.

Skills that are generally useful to the healing-swarm community are contributed upstream via pull requests to healing-swarm-skills. Alchymine-specific skills (wealth, creative, perspective, cross-system) live exclusively in this repository under `skills/`.

The monorepo contains all five system domains, shared infrastructure, tests, and documentation in a single tree to enable atomic cross-system changes.

## Consequences

**Positive:**

- Independent CI/CD and release cadence.
- Clear ownership boundaries between Alchymine and healing-swarm-skills.
- Atomic commits across all five systems when cross-cutting changes are needed.
- Upstream contributions follow healing-swarm-skills' own review standards.

**Negative:**

- Must track healing-swarm-skills releases and update the dependency manually.
- Skills contributed upstream may diverge from Alchymine's copies during the PR process.
- New contributors must understand two codebases to work on healing-related skills.

# ADR-003: Healing-Swarm-Skills Integration

**Status:** Accepted

**Date:** 2025-01-15

## Context

Alchymine's Expanded Healing system builds on healing-swarm-skills, which provides an ethics-first agent architecture with three cooperative swarms: Research, Synthesis, and Guidance. This architecture enforces quality gates that prevent harmful or culturally insensitive outputs. Alchymine must inherit these safeguards while extending the system with 46 additional skills across wellness domains.

The integration must preserve healing-swarm-skills' core invariants: cultural sensitivity review, evidence grounding, and the three-swarm consensus model. At the same time, Alchymine introduces cross-system interactions (e.g., healing insights feeding into the Wealth Engine or Creative Forge) that healing-swarm-skills was not designed for.

## Decision

Alchymine integrates healing-swarm-skills as follows:

- **Inherit the 3-swarm model:** Research, Synthesis, and Guidance swarms operate unchanged for all healing skills. Extended healing skills in `skills/expanded-healing/` follow the same swarm routing.
- **Preserve quality gates:** All healing outputs pass through the existing evidence-check, cultural-sensitivity, and safety gates before reaching the user.
- **Upstream contributions:** The 46 new healing skills are developed in Alchymine's `skills/expanded-healing/` directory. Skills that are general-purpose (not dependent on Alchymine's cross-system features) are contributed upstream to healing-swarm-skills via pull requests.
- **Cross-system bridge:** A dedicated integration layer in `skills/cross-system/` mediates between healing outputs and other Alchymine systems, ensuring healing data is never reinterpreted without passing through appropriate safety checks.

## Consequences

**Positive:**

- Full inheritance of healing-swarm-skills' ethical safeguards and cultural review.
- Clear contribution path back to the upstream project.
- Cross-system interactions are mediated rather than ad-hoc.

**Negative:**

- Upstream PR acceptance is outside Alchymine's control and may lag.
- Cross-system bridge adds a layer of indirection for healing-related features.
- Maintaining compatibility with upstream API changes requires ongoing effort.

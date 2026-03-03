# ADR-007: Alchemical Spiral User Journey

**Status:** Accepted

**Date:** 2025-02-01

## Context

The original Alchymine user journey followed a linear 4-Act narrative structure (Calcination, Dissolution, Conjunction, Projection). While thematically compelling, the linear model assumed all users start at the same point and progress through the same sequence. In practice, users arrive with different needs, skill levels, and goals. Some need financial help first; others seek creative expression or cognitive reframing. A rigid sequence creates friction and dropout.

## Decision

The user journey is restructured from a linear 4-Act model to a hub-and-spoke **Alchemical Spiral**:

- **Hub:** A central orientation space where users are assessed and routed to the most relevant system based on their immediate needs, goals, and readiness.
- **Spokes:** The five pillars (Expanded Healing, Wealth Engine, Creative Forge, Perspective Prism) serve as entry points. Users can begin with any spoke.
- **Spiral progression:** Rather than linear advancement, users spiral through the systems with increasing depth. Each return visit builds on prior engagement across all systems.
- **Adaptive entry routing:** Initial assessment determines the recommended starting spoke. Users can override the recommendation. Routing logic is transparent and explainable.
- **3 depth layers:** (1) Exploration -- low-commitment introduction to each system's core concepts. (2) Practice -- structured exercises and skill-building with feedback. (3) Integration -- cross-system synthesis where insights from multiple pillars combine.
- **Progressive disclosure:** Each depth layer reveals additional capabilities. Users are not overwhelmed with the full system on first contact.

## Consequences

**Positive:**

- Users engage with the most relevant system immediately, reducing time-to-value.
- Non-linear progression accommodates diverse starting points and learning styles.
- Progressive disclosure prevents cognitive overload for new users.
- Spiral model encourages cross-system exploration organically.

**Negative:**

- Adaptive routing requires robust assessment logic that must be validated.
- The alchemical narrative metaphor is harder to maintain in a non-linear structure.
- Three depth layers multiply the content and testing surface for each system.
- Analytics and progress tracking are more complex without a fixed sequence.

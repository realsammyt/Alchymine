# ADR-005: Creative Forge as Fourth Pillar

**Status:** Accepted

**Date:** 2025-02-01

## Context

Version 7 of Alchymine introduces the Creative Forge as the fourth pillar, recognizing that creative expression is integral to personal transformation. The system must support development across multiple creative domains while grounding its approach in neuroscience rather than vague inspiration.

Research on the Default Mode Network (DMN) and Executive Control Network (ECN) interaction provides an evidence-based framework for understanding creative states. The Creative Forge uses this neuroscience foundation to guide users through creative development without replacing human creativity with AI generation.

## Decision

The Creative Forge covers 7 creative domains: writing, visual arts, music, movement, culinary arts, craftsmanship, and digital media. It is implemented with the following architecture:

- **DMN-ECN neuroscience grounding:** Creative exercises and guidance are mapped to the interplay between the Default Mode Network (divergent thinking, imagination) and Executive Control Network (evaluation, refinement). Users learn to recognize and cultivate both modes.
- **7 agents:** Domain Analyst, Technique Coach, Inspiration Catalyst, Critique Partner, Portfolio Curator, Practice Scheduler, and Cross-Domain Synthesizer.
- **7 skills:** Located in `skills/creative-development/`, covering domain assessment, technique instruction, creative prompting, constructive critique, portfolio organization, practice planning, and cross-domain exploration.
- **4 quality gates:** (1) Originality verification -- outputs must foster original work, not generate it. (2) AI attribution -- any AI-assisted elements are clearly labeled. (3) Cultural respect -- creative traditions are credited properly. (4) Developmental appropriateness -- guidance matches the user's skill level.

## Consequences

**Positive:**
- Neuroscience grounding provides credible, evidence-based creative development.
- 7-domain coverage supports diverse creative interests within a unified framework.
- Quality gates prevent the system from replacing human creativity with AI output.

**Negative:**
- 7 domains require broad domain expertise for skill authoring and review.
- DMN-ECN framework may oversimplify the neuroscience for practical application.
- Originality verification is inherently difficult and may produce false positives.

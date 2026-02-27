# ADR-006: Perspective Prism as Fifth Pillar

**Status:** Accepted

**Date:** 2025-02-01

## Context

Version 7 introduces the Perspective Prism as the fifth pillar, addressing the need for structured cognitive and worldview development. Users benefit from tools that help them reframe challenges, evaluate opportunities from multiple angles, and grow in cognitive complexity. However, any system that engages with psychological processes must prioritize safety, particularly around crisis detection and the boundary between coaching and therapy.

## Decision

The Perspective Prism implements a 3-layer system for cognitive development:

- **Layer 1 -- CBT Reframing:** Cognitive Behavioral Therapy-informed techniques for identifying and restructuring cognitive distortions. Focused on practical, evidence-based thought pattern improvement.
- **Layer 2 -- Effectuation Positioning:** Saras Sarasvathy's effectuation framework applied to decision-making and opportunity evaluation. Helps users work with available means rather than predicted outcomes.
- **Layer 3 -- Kegan Worldview Development:** Robert Kegan's constructive-developmental framework for understanding and advancing through stages of meaning-making complexity.

Architecture:
- **5 agents:** Reframe Analyst, Decision Facilitator, Worldview Guide, Integration Coach, and Crisis Sentinel.
- **7 skills:** Located in `skills/perspective-enhancement/`, covering cognitive distortion identification, reframing exercises, effectual reasoning, worldview assessment, perspective integration, growth tracking, and crisis detection.
- **6 quality gates:** (1) Psychological safety screen, (2) crisis detection and escalation, (3) scope boundary enforcement (coaching, not therapy), (4) evidence grounding, (5) developmental stage appropriateness, and (6) cross-layer coherence.
- **Crisis detection as deterministic code:** Crisis indicators (suicidal ideation, self-harm, acute distress) are detected by rule-based pattern matching, never by LLM inference. Detection triggers immediate escalation to human resources and crisis hotlines.

## Consequences

**Positive:**
- Three complementary frameworks cover practical, strategic, and developmental perspectives.
- Deterministic crisis detection eliminates false-negative risk from LLM uncertainty.
- Six quality gates enforce clear boundaries between coaching and therapy.

**Negative:**
- Kegan's framework requires careful simplification to be accessible without distortion.
- Crisis detection rules must be maintained and validated against evolving clinical standards.
- Three theoretical frameworks increase onboarding complexity for contributors.

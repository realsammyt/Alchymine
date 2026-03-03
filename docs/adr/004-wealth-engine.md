# ADR-004: Wealth Engine as Peer System

**Status:** Accepted

**Date:** 2025-01-15

## Context

The Wealth Engine provides financial literacy, budgeting, and wealth-building guidance within Alchymine. Financial calculations carry higher correctness requirements than conversational AI outputs -- an incorrect budget projection or savings calculation can cause real financial harm. The system must also avoid any appearance of providing regulated financial advice.

Financial data (income, expenses, savings, debt) is among the most sensitive categories of personal information. It must be isolated from other systems and protected against accidental leakage through cross-system interactions.

## Decision

The Wealth Engine operates as a peer system alongside Expanded Healing, with the following architectural constraints:

- **Deterministic calculations:** All financial computations (compound interest, budget projections, debt payoff schedules) use deterministic code paths, never LLM-generated arithmetic. The LLM provides framing and explanation; the math is executed by verified functions.
- **5 quality gates:** Every Wealth Engine output passes through: (1) calculation verification, (2) assumption validation, (3) disclaimer injection, (4) financial safety review, and (5) regulatory compliance check.
- **Data isolation:** Financial data is stored in a separate encrypted namespace. Cross-system queries (e.g., "How does my financial stress affect my wellness?") receive only aggregated sentiment, never raw financial figures.
- **No product promotion:** The system never recommends specific financial products, services, or investment vehicles. Outputs are educational only.
- **Spreadsheet export:** All financial plans can be exported to spreadsheet format for independent verification.

## Consequences

**Positive:**

- Deterministic math eliminates LLM hallucination risk for financial figures.
- Data isolation prevents accidental exposure of financial details to other systems.
- Quality gates enforce disclaimers and regulatory compliance consistently.
- Export capability supports user trust through independent verification.

**Negative:**

- Dual-path architecture (deterministic math + LLM framing) adds implementation complexity.
- Data isolation limits the richness of cross-system wellness insights.
- Strict no-promotion policy may frustrate users seeking specific product guidance.

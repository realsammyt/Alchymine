# ADR-002: Local-First Data Architecture

**Status:** Accepted

**Date:** 2025-01-15

## Context

Alchymine processes three categories of sensitive data: personally identifiable information (PII) from user profiles, financial data from the Wealth Engine, and psychological/emotional data from healing and perspective systems. Cloud-hosted storage introduces risks around data breaches, regulatory compliance (GDPR, CCPA), and erosion of user trust.

Users of personal-development tools are especially privacy-conscious. Any perception that their healing journey, financial situation, or psychological state is being collected would undermine adoption and the therapeutic relationship the system aims to support.

## Decision

All user data is stored locally on the user's device or on operator-controlled infrastructure. There is no Alchymine-operated cloud backend that holds user data.

Specific measures:
- **Encryption at rest:** AES-256 encryption for all persisted user data, including SQLite databases and file exports.
- **Zero telemetry:** No analytics, usage tracking, or crash reporting that transmits user data. Operators may opt into anonymous aggregate metrics on their own infrastructure.
- **Self-hosted deployment:** The reference deployment uses Docker Compose on operator infrastructure. No managed SaaS offering.
- **Key management:** Encryption keys are derived from user credentials and never leave the local environment.
- **Export/portability:** Users can export all their data in standard formats (JSON, CSV) at any time.

## Consequences

**Positive:**
- Maximum privacy protection for sensitive personal, financial, and psychological data.
- No regulatory exposure from holding user data centrally.
- Users retain full ownership and control of their information.
- Simplified compliance posture for operators.

**Negative:**
- No cross-device sync without operator-provided infrastructure.
- Operators bear full responsibility for backups and disaster recovery.
- Aggregate analytics for product improvement require explicit operator opt-in.
- Support and debugging are harder without server-side telemetry.

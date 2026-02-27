# Contributing to Alchymine

Thank you for your interest in contributing to Alchymine. This guide covers the process for contributing code, skills, and documentation across all five systems.

## Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/Alchymine.git
   cd Alchymine
   ```
2. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```
3. **Run tests:**
   ```bash
   pytest tests/
   ```
4. **Start the local development environment:**
   ```bash
   docker compose -f infrastructure/docker/docker-compose.yml up
   ```

## Pull Request Process

1. Create a feature branch from `main` with a descriptive name (e.g., `feat/wealth-budget-export`).
2. Write tests for new functionality. All PRs must maintain or improve test coverage.
3. Ensure all quality gates pass for the relevant system (see domain-specific reviews below).
4. Submit a PR with a clear description of the change, its motivation, and any trade-offs.
5. At least one core maintainer and one domain expert must approve before merge.
6. Squash-merge to `main`. The PR title becomes the commit message.

## Skill Creation

All skills follow a standard structure regardless of domain:

1. Create the skill definition in the appropriate `skills/` subdirectory.
2. Include metadata: name, description, domain, required swarm, quality gates.
3. Write unit tests covering expected outputs and edge cases.
4. Add integration tests demonstrating interaction with relevant agents.
5. Document the skill's purpose, inputs, outputs, and safety considerations.

## Domain-Specific Review Requirements

### Healing Skills (`skills/expanded-healing/`)

- **Cultural review (required):** A domain expert verifies that the skill respects cultural traditions, avoids appropriation, and correctly attributes traditional knowledge sources.
- **Evidence grounding:** Claims must cite peer-reviewed or recognized traditional sources.
- **Safety review:** Skills must not provide medical diagnoses or replace professional healthcare.

### Wealth Skills (`skills/wealth-engine/`)

- **Financial domain review (required):** A reviewer with financial literacy expertise verifies calculation correctness and assumption validity.
- **Spreadsheet verification:** All financial calculations must be independently reproducible in a spreadsheet. The reviewer validates this.
- **Disclaimer check:** Outputs must include appropriate disclaimers and must never recommend specific financial products.

### Creative Skills (`skills/creative-development/`)

- **Plagiarism check (required):** A reviewer verifies the skill fosters original creation and does not generate derivative content without attribution.
- **AI attribution review:** Any AI-assisted elements in skill outputs must be clearly labeled. The reviewer confirms attribution mechanisms are in place.
- **Cultural respect:** Creative traditions referenced by the skill must be credited properly.

### Perspective Skills (`skills/perspective-enhancement/`)

- **Psychological safety review (required):** A domain expert verifies the skill maintains the coaching-not-therapy boundary, includes appropriate scope disclaimers, and handles sensitive topics safely.
- **Crisis pathway verification:** Skills that may surface distress indicators must correctly integrate with the deterministic crisis detection system.
- **Framework fidelity:** CBT, effectuation, and Kegan-based skills must accurately represent their underlying frameworks.

## RFC Process for Major Changes

Major changes that affect architecture, cross-system interactions, or public APIs require a Request for Comments (RFC):

1. **Draft an RFC** using the template in `docs/adr/` as a starting point. Include: context, proposal, alternatives considered, and migration plan.
2. **Open a discussion** by submitting the RFC as a PR to `docs/adr/` with the `rfc` label.
3. **Review period:** RFCs are open for comment for a minimum of 7 days.
4. **Decision:** Core maintainers accept, reject, or request revision. Accepted RFCs become numbered ADRs.

Examples of changes that require an RFC:
- Adding a new system or pillar.
- Changing the quality gate pipeline for any domain.
- Modifying the cross-system data bridge.
- Altering the encryption or data storage architecture.

## Code of Conduct

All contributors must adhere to the [Code of Conduct](CODE_OF_CONDUCT.md). In particular, note the project-specific additions around financial product promotion, healing tradition respect, and psychological safety.

## Questions

If you are unsure where a contribution fits or which review process applies, open a discussion issue and the maintainers will guide you.

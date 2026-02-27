## Description

<!-- Provide a clear and concise description of the changes in this PR. -->
<!-- Include the motivation, context, and any relevant background. -->



### Related Issues

<!-- Link related issues using "Closes #123" or "Relates to #456". -->

- Closes #

---

## System Affected

<!-- Check all systems that are modified or impacted by this PR. -->

- [ ] **Core** — Personalized Intelligence / Orchestrator / UserProfile
- [ ] **Healing** — Ethical Healing System / healing skills
- [ ] **Wealth** — Generational Wealth Engine / financial modules
- [ ] **Creative** — Creative Development System / creative modules
- [ ] **Perspective** — Perspective Enhancement System / perspective skills
- [ ] **Infrastructure** — API / Database / Queue / Docker / CI / deployment
- [ ] **Cross-System** — Changes that span multiple systems or affect shared interfaces

---

## Type of Change

<!-- Check all that apply. -->

- [ ] New feature (non-breaking change that adds functionality)
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Refactoring (no functional changes, code improvement)
- [ ] Documentation update
- [ ] New skill or module
- [ ] Dependency update
- [ ] CI/CD or infrastructure change

---

## Testing Checklist

<!-- Check all tests that have been performed. -->
<!-- Items marked with * are conditionally required — see notes. -->

### Required

- [ ] **Unit tests** — New and existing unit tests pass (`pytest tests/engine/ tests/api/ -v`)
- [ ] **Integration tests** — Cross-component tests pass (`pytest tests/ -v`)
- [ ] **Linting** — Code passes `ruff check` and `ruff format --check`
- [ ] **Type checking** — Code passes `mypy alchymine/`
- [ ] **Frontend tests** — If frontend changes: `npm test` passes
- [ ] **Frontend lint** — If frontend changes: `npm run lint` passes
- [ ] **Frontend build** — If frontend changes: `npm run build` succeeds

### Ethics and Safety

- [ ] **Ethics review** — Outputs reviewed for harm prevention ("First, Do No Harm") *
- [ ] **Cultural sensitivity review** — Content reviewed for proper attribution and cultural respect *
- [ ] **Emotional safety check** — No toxic positivity, no calming design masking real problems *

### Domain-Specific

- [ ] **Financial accuracy** — All financial calculations are deterministic and verified against test vectors *
- [ ] **Financial data isolation** — No financial data sent to LLM; encrypted at rest *
- [ ] **Disclaimer validation** — Required disclaimers present on financial/health outputs *
- [ ] **Accessibility check** — WCAG 2.1 AA compliance verified (UI changes) *
- [ ] **Evidence-level labeling** — Evidence ratings present on methodology claims *

<!-- * = Required only when the PR touches the relevant system or output type. -->

---

## Quality Gate Status

<!-- Report the status of quality gate checks. -->

| Gate | Status | Notes |
|------|--------|-------|
| Prompt validation (`python -m alchymine.prompts.validate`) | :white_circle: Not run / :green_circle: Pass / :red_circle: Fail | |
| Ethics check (`python -m alchymine.agents.quality.ethics_check`) | :white_circle: Not run / :green_circle: Pass / :red_circle: Fail | |
| Quality Swarm regression (`pytest tests/agents/ -v`) | :white_circle: Not run / :green_circle: Pass / :red_circle: Fail | |
| Docker build (`docker compose build`) | :white_circle: Not run / :green_circle: Pass / :red_circle: Fail | |

---

## Data Sensitivity

<!-- If this PR handles user data, confirm compliance. -->

- [ ] No new user data is collected or processed
- [ ] New data handling follows local-first principles (ADR-002)
- [ ] Sensitive data (financial, health) is encrypted and isolated
- [ ] No sensitive data is sent to external LLM APIs
- [ ] Privacy impact has been assessed

---

## Screenshots / Demos

<!-- If applicable, add screenshots, GIFs, or screen recordings. -->
<!-- Redact any personal, financial, or health data. -->



---

## Reviewer Notes

<!-- Any specific areas where you would like reviewer attention? -->
<!-- Any known limitations or follow-up work needed? -->



---

## Checklist

<!-- Final checklist before requesting review. -->

- [ ] My code follows the project's coding standards and conventions
- [ ] I have added/updated tests that prove my fix or feature works
- [ ] I have updated documentation where necessary
- [ ] I have verified my changes do not introduce security vulnerabilities
- [ ] I have verified my changes work in the Docker Compose dev environment
- [ ] My changes generate no new warnings or errors
- [ ] I have read and agree to the project's [Code of Conduct](CODE_OF_CONDUCT.md)

"""Shared fixtures for integration tests."""

from __future__ import annotations

from datetime import date, time

import pytest


@pytest.fixture
def full_assessment_responses() -> dict[str, int]:
    """Complete assessment responses covering all 67 questions.

    Big Five (20) + Attachment (4) + Risk (3) + Enneagram (9)
    + Kegan (5) + Guilford (26) = 67 items.
    """
    responses: dict[str, int] = {}

    # Big Five — 20 items (bf_{trait}{1..4})
    for trait in ("e", "a", "c", "n", "o"):
        for i in (1, 2, 3, 4):
            responses[f"bf_{trait}{i}"] = 4

    # Attachment — 4 items
    for i in range(1, 5):
        responses[f"attachment_{i}"] = 3

    # Risk tolerance — 3 items (high risk → aggressive)
    responses["risk_1"] = 5
    responses["risk_2"] = 4
    responses["risk_3"] = 5

    # Enneagram — 9 items
    for i in range(1, 10):
        responses[f"enn_{i}"] = 3
    # Make type 4 dominant
    responses["enn_4"] = 5

    # Kegan perspective — 5 items (high scores → higher stage)
    for i in range(1, 6):
        responses[f"kegan_{i}"] = 4

    # Guilford creativity — 18 divergent + 8 convergent = 26 items
    for prefix in ("flu", "flex", "orig", "elab", "sens", "redef"):
        for j in range(1, 4):
            responses[f"guil_{prefix}{j}"] = 4
    for j in range(1, 9):
        responses[f"guil_conv{j}"] = 3

    return responses


@pytest.fixture
def full_request_data(full_assessment_responses: dict[str, int]) -> dict:
    """Request data dict as the orchestrator receives it — mimics the
    shape built by the Celery task from an intake submission.
    """
    return {
        "id": "integration-test-user",
        "full_name": "Integration Test User",
        "birth_date": date(1990, 6, 15),
        "birth_time": time(10, 30),
        "birth_city": "New York",
        "text": "Generate my full report",
        "intention": "health",
        # "health" → HEALING, "money" → WEALTH, "purpose" → CREATIVE + PERSPECTIVE
        # INTELLIGENCE is always included as the base system.
        "intentions": ["health", "money", "purpose"],
        "assessment_responses": full_assessment_responses,
    }

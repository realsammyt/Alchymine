"""End-to-end test: Intelligence → DB → Healing pipeline."""

from __future__ import annotations

from alchymine.agents.orchestrator.graphs import (
    build_healing_graph,
    build_intelligence_graph,
)


class TestHealingPipelineE2E:
    """Verify healing works with real intelligence data, not fallbacks."""

    def _make_assessment_responses(self) -> dict[str, int]:
        """Build a complete 67-question assessment response dict."""
        responses: dict[str, int] = {}
        # 20 Big Five items
        for trait in ("e", "a", "c", "n", "o"):
            for i in range(1, 5):
                responses[f"bf_{trait}{i}"] = 4
        # 4 Attachment
        for key in ("att_closeness", "att_abandonment", "att_trust", "att_self_reliance"):
            responses[key] = 3
        # 3 Risk tolerance
        for i in range(1, 4):
            responses[f"risk_{i}"] = 3
        # 9 Enneagram
        for i in range(1, 10):
            responses[f"enn_{i}"] = 3
        # 5 Kegan
        for i in range(1, 6):
            responses[f"kegan_{i}"] = 4
        # 26 Guilford (actual IDs from questions.ts)
        for prefix in ("flu", "flex", "orig", "elab", "sens", "redef"):
            for i in range(1, 4):
                responses[f"guil_{prefix}{i}"] = 3
        for i in range(1, 9):
            responses[f"guil_conv{i}"] = 3
        return responses

    def test_intelligence_output_feeds_healing(self) -> None:
        """Intelligence output, when passed to Healing, produces real modalities."""
        request_data = {
            "full_name": "Test User",
            "birth_date": "1990-01-15",
            "assessment_responses": self._make_assessment_responses(),
            "intentions": ["health"],
        }

        # Run Intelligence graph
        intel_graph = build_intelligence_graph(include_quality_gate=False)
        intel_state = {
            "user_id": "test",
            "request_data": request_data,
            "results": {},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        intel_result = intel_graph.invoke(intel_state)

        # Verify Intelligence produced personality data
        personality = intel_result["results"].get("personality", {})
        assert "big_five" in personality, "Intelligence must produce big_five scores"
        assert personality["big_five"]["openness"] > 0

        archetype = intel_result["results"].get("archetype", {})

        # Simulate orchestrator enrichment
        healing_request = dict(request_data)
        if personality:
            healing_request["big_five"] = personality
        if archetype.get("primary"):
            healing_request["archetype"] = archetype["primary"]
            healing_request["archetype_secondary"] = archetype.get("secondary")

        # Run Healing graph with enriched data
        healing_graph = build_healing_graph(include_quality_gate=False)
        healing_state = {
            "user_id": "test",
            "request_data": healing_request,
            "results": {},
            "errors": [],
            "status": "success",
            "quality_passed": True,
        }
        healing_result = healing_graph.invoke(healing_state)

        # Verify Healing produced REAL modalities, not fallbacks
        results = healing_result["results"]
        assert "recommended_modalities" in results
        modalities = results["recommended_modalities"]
        assert len(modalities) > 0
        # Real modalities have preference_score (fallbacks don't)
        assert "preference_score" in modalities[0], (
            "Modalities should come from real matching, not fallbacks"
        )

        # Verify personality data was extracted
        assert "openness" in results
        assert results["openness"] > 0
        assert "neuroticism" in results

        # No missing prerequisites
        assert "missing_prerequisites" not in results
        assert healing_result["status"] == "success"

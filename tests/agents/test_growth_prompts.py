"""Unit tests for Growth Assistant system prompts.

Tests get_system_prompt() routing and prompt content validation.
"""

from __future__ import annotations

from alchymine.agents.growth.system_prompts import (
    MAIN_SYSTEM_PROMPT,
    STARTER_PROMPTS,
    SYSTEM_PROMPTS,
    get_system_prompt,
)


class TestGetSystemPrompt:
    def test_returns_main_prompt_for_none(self) -> None:
        assert get_system_prompt(None) == MAIN_SYSTEM_PROMPT

    def test_returns_main_prompt_for_unknown_context(self) -> None:
        assert get_system_prompt("unknown_system") == MAIN_SYSTEM_PROMPT

    def test_returns_specialist_prompt_for_intelligence(self) -> None:
        result = get_system_prompt("intelligence")
        assert result == SYSTEM_PROMPTS["intelligence"]
        assert "numerology" in result.lower()

    def test_returns_specialist_prompt_for_healing(self) -> None:
        result = get_system_prompt("healing")
        assert result == SYSTEM_PROMPTS["healing"]
        assert "healing" in result.lower()

    def test_returns_specialist_prompt_for_wealth(self) -> None:
        result = get_system_prompt("wealth")
        assert "wealth" in result.lower()
        assert "investment advice" in result.lower()

    def test_returns_specialist_prompt_for_creative(self) -> None:
        result = get_system_prompt("creative")
        assert "guilford" in result.lower()

    def test_returns_specialist_prompt_for_perspective(self) -> None:
        result = get_system_prompt("perspective")
        assert "kegan" in result.lower()

    def test_all_specialist_prompts_extend_main(self) -> None:
        for key, prompt in SYSTEM_PROMPTS.items():
            assert MAIN_SYSTEM_PROMPT in prompt, f"System prompt for {key!r} must extend main"

    def test_main_prompt_has_safety_disclaimer(self) -> None:
        assert "medical" in MAIN_SYSTEM_PROMPT.lower()
        assert "financial" in MAIN_SYSTEM_PROMPT.lower()
        assert "legal" in MAIN_SYSTEM_PROMPT.lower()


class TestStarterPrompts:
    def test_all_five_systems_have_starters(self) -> None:
        systems = {"intelligence", "healing", "wealth", "creative", "perspective"}
        assert set(STARTER_PROMPTS.keys()) == systems

    def test_each_system_has_three_starters(self) -> None:
        for system, prompts in STARTER_PROMPTS.items():
            assert len(prompts) == 3, f"{system} should have 3 starter prompts"

    def test_starters_are_non_empty_strings(self) -> None:
        for system, prompts in STARTER_PROMPTS.items():
            for prompt in prompts:
                assert isinstance(prompt, str) and prompt.strip(), (
                    f"Empty starter prompt in {system}"
                )

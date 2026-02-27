"""Tests for the LLM client and narrative generator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from alchymine.llm.client import LLMBackend, LLMClient, LLMResponse
from alchymine.llm.narrative import (
    NarrativeGenerator,
    NarrativeResult,
    fill_template,
    flatten_engine_data,
    load_template,
)

# ─── LLM Client Tests ────────────────────────────────────────────


class TestLLMResponse:
    """Test the LLMResponse dataclass."""

    def test_response_creation(self):
        resp = LLMResponse(
            text="Hello world",
            backend="claude",
            model="claude-sonnet-4-20250514",
            input_tokens=10,
            output_tokens=5,
        )
        assert resp.text == "Hello world"
        assert resp.backend == "claude"
        assert resp.input_tokens == 10

    def test_response_defaults(self):
        resp = LLMResponse(text="hi", backend="none", model="none")
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0

    def test_response_is_frozen(self):
        resp = LLMResponse(text="hi", backend="none", model="none")
        with pytest.raises(AttributeError):
            resp.text = "changed"  # type: ignore[misc]


class TestLLMClientFallback:
    """Test LLM client fallback behavior."""

    def test_fallback_response_when_no_backend(self):
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            client = LLMClient()

        async def _run():
            return await client.generate("system", "user")

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.backend == "none"
        assert "unavailable" in result.text.lower()

    def test_forced_backend_none(self):
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            client = LLMClient()
        assert client._forced_backend == LLMBackend.NONE

    def test_default_no_forced_backend(self):
        with patch.dict("os.environ", {}, clear=False):
            env = dict(**{k: v for k, v in __import__("os").environ.items() if k != "LLM_BACKEND"})
        with patch.dict("os.environ", env, clear=True):
            client = LLMClient()
        assert client._forced_backend is None


class TestLLMClientClaude:
    """Test Claude backend with mocked API."""

    @pytest.fixture
    def mock_claude_response(self):
        """Mock anthropic.AsyncAnthropic.messages.create."""
        mock_block = type("Block", (), {"text": "Generated narrative text."})()
        mock_usage = type("Usage", (), {"input_tokens": 100, "output_tokens": 50})()
        return type("Response", (), {"content": [mock_block], "usage": mock_usage})()

    async def test_claude_generation(self, mock_claude_response):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            client = LLMClient()

        mock_create = AsyncMock(return_value=mock_claude_response)
        mock_anthropic = type("anthropic", (), {
            "AsyncAnthropic": lambda *a, **kw: type("Client", (), {
                "messages": type("Messages", (), {"create": mock_create})(),
            })(),
        })()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = await client._generate_claude("system", "user", 2048, 0.7)

        assert result.text == "Generated narrative text."
        assert result.backend == "claude"
        assert result.input_tokens == 100


# ─── Narrative Generator Tests ────────────────────────────────────


class TestLoadTemplate:
    """Test template loading."""

    def test_load_intelligence_template(self):
        template = load_template("intelligence")
        assert template["name"] == "intelligence_narrative"
        assert "system_prompt" in template
        assert "user_prompt" in template

    def test_load_healing_template(self):
        template = load_template("healing")
        assert template["system"] == "healing"
        assert "disclaimers" in template

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent_system")

    @pytest.mark.parametrize(
        "system",
        [
            "intelligence",
            "healing",
            "wealth",
            "creative",
            "perspective",
            "synthesis",
        ],
    )
    def test_all_templates_loadable(self, system):
        template = load_template(system)
        assert isinstance(template, dict)


class TestFillTemplate:
    """Test template variable substitution."""

    def test_basic_substitution(self):
        result = fill_template(
            "Hello {name}, your path is {path}.",
            {
                "name": "Maria",
                "path": "3",
            },
        )
        assert result == "Hello Maria, your path is 3."

    def test_missing_key_preserved(self):
        result = fill_template("Hello {name}, age {age}.", {"name": "Maria"})
        assert result == "Hello Maria, age {age}."

    def test_empty_data(self):
        result = fill_template("No variables here.", {})
        assert result == "No variables here."


class TestFlattenEngineData:
    """Test engine data flattening."""

    def test_flat_data_unchanged(self):
        data = {"life_path": 3, "sun_sign": "Pisces"}
        result = flatten_engine_data(data)
        assert result["life_path"] == 3
        assert result["sun_sign"] == "Pisces"

    def test_nested_dicts_flattened(self):
        data = {
            "numerology": {"life_path": 3, "expression": 6},
            "astrology": {"sun_sign": "Pisces"},
        }
        result = flatten_engine_data(data)
        assert result["life_path"] == 3
        assert result["sun_sign"] == "Pisces"

    def test_lists_become_sections(self):
        data = {
            "modalities": [
                {"name": "Breathwork", "description": "Conscious breathing"},
                {"name": "Meditation", "description": "Mindfulness practice"},
            ]
        }
        result = flatten_engine_data(data)
        assert "modalities_section" in result
        assert "Breathwork" in result["modalities_section"]
        assert "Meditation" in result["modalities_section"]

    def test_empty_list_produces_none(self):
        result = flatten_engine_data({"items": []})
        assert result["items_section"] == "(none)"


class TestNarrativeGenerator:
    """Test the narrative generator with mocked LLM."""

    @pytest.fixture
    def mock_client(self):
        client = LLMClient()
        client.generate = AsyncMock(
            return_value=LLMResponse(
                text="This is a warm, empowering narrative about your unique patterns.",
                backend="mock",
                model="mock-model",
            )
        )
        return client

    async def test_generate_intelligence(self, mock_client):
        gen = NarrativeGenerator(client=mock_client)
        result = await gen.generate(
            "intelligence",
            {
                "life_path": 3,
                "expression": 6,
                "soul_urge": 5,
                "personality_number": 1,
                "personal_year": 7,
                "maturity": 9,
                "calculation_system": "pythagorean",
                "sun_sign": "Pisces",
                "moon_sign": "Scorpio",
                "rising_sign": "Leo",
                "primary_archetype": "Creator",
                "secondary_archetype": "Sage",
                "shadow_archetype": "Trickster",
                "openness": 75,
                "conscientiousness": 55,
                "extraversion": 60,
                "agreeableness": 80,
                "neuroticism": 45,
                "attachment_style": "secure",
                "enneagram_type": 2,
                "enneagram_wing": 3,
            },
        )
        assert isinstance(result, NarrativeResult)
        assert result.system == "intelligence"
        assert result.narrative != ""
        assert result.ethics_passed
        mock_client.generate.assert_called_once()

    async def test_generate_with_nested_data(self, mock_client):
        gen = NarrativeGenerator(client=mock_client)
        result = await gen.generate(
            "intelligence",
            {
                "numerology": {"life_path": 3, "expression": 6},
                "astrology": {"sun_sign": "Pisces"},
            },
        )
        assert result.system == "intelligence"
        # Verify the prompt was filled with flattened data
        call_args = mock_client.generate.call_args
        assert "Pisces" in call_args.kwargs.get(
            "user_prompt", call_args[1] if len(call_args) > 1 else ""
        )

    async def test_generate_nonexistent_system_returns_empty(self, mock_client):
        gen = NarrativeGenerator(client=mock_client)
        result = await gen.generate("nonexistent", {})
        assert result.narrative == ""
        assert result.ethics_passed
        mock_client.generate.assert_not_called()

    async def test_ethics_violation_flagged(self):
        bad_client = LLMClient()
        bad_client.generate = AsyncMock(
            return_value=LLMResponse(
                text="You are destined to always succeed. The stars decree your path.",
                backend="mock",
                model="mock",
            )
        )
        gen = NarrativeGenerator(client=bad_client)
        result = await gen.generate("intelligence", {"life_path": 3})
        assert not result.ethics_passed
        assert len(result.ethics_violations) > 0

    async def test_disclaimers_from_template(self, mock_client):
        gen = NarrativeGenerator(client=mock_client)
        result = await gen.generate("healing", {"crisis_flag": False})
        assert len(result.disclaimers) >= 1
        assert any("medical" in d.lower() for d in result.disclaimers)

    async def test_generate_all(self, mock_client):
        gen = NarrativeGenerator(client=mock_client)
        results = await gen.generate_all(
            ["intelligence", "healing"],
            {"intelligence": {"life_path": 3}, "healing": {"crisis_flag": False}},
        )
        assert "intelligence" in results
        assert "healing" in results
        assert mock_client.generate.call_count == 2

    async def test_wealth_narrative_no_financial_data(self, mock_client):
        gen = NarrativeGenerator(client=mock_client)
        result = await gen.generate(
            "wealth",
            {
                "wealth_archetype": "Builder",
                "archetype_description": "Systematic wealth creator",
                "risk_tolerance": "moderate",
                "intention": "business",
            },
        )
        assert result.system == "wealth"
        # Verify no financial data in the prompt sent to LLM
        call_args = mock_client.generate.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "income" not in user_prompt.lower() or "income_range" not in user_prompt.lower()

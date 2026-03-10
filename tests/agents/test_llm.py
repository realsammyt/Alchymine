"""Tests for the LLM client, OllamaClient, fallback behavior, and narrative generator."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from alchymine.llm.client import (
    LLMBackend,
    LLMClient,
    LLMResponse,
    OllamaClient,
    OllamaModelInfo,
)
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

        result = asyncio.run(_run())
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
        mock_anthropic = type(
            "anthropic",
            (),
            {
                "AsyncAnthropic": lambda *a, **kw: type(
                    "Client",
                    (),
                    {
                        "messages": type("Messages", (), {"create": mock_create})(),
                    },
                )(),
            },
        )()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = await client._generate_claude("system", "user", 2048, 0.7)

        assert result.text == "Generated narrative text."
        assert result.backend == "claude"
        assert result.input_tokens == 100


# ─── OllamaClient Tests ──────────────────────────────────────────


class TestOllamaClient:
    """Test OllamaClient with mocked HTTP calls."""

    def test_default_config(self):
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"
        assert client.default_model == "llama3.2"

    def test_custom_config(self):
        client = OllamaClient(
            base_url="http://my-ollama:9999",
            default_model="mistral",
            timeout=60.0,
        )
        assert client.base_url == "http://my-ollama:9999"
        assert client.default_model == "mistral"

    async def test_generate_calls_api(self):
        """generate() should POST to /api/generate and return an LLMResponse."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=200,
            json={"response": "Test response from Ollama."},
            request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
        )
        mock_post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient.post", mock_post):
            result = await client.generate("Tell me about numerology")

        assert result.text == "Test response from Ollama."
        assert result.backend == "ollama"
        assert result.model == "llama3.2"

        # Verify the call was made correctly
        call_args = mock_post.call_args
        assert "/api/generate" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["model"] == "llama3.2"
        assert payload["stream"] is False

    async def test_generate_with_custom_model(self):
        """generate() should use the specified model."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=200,
            json={"response": "Mistral response."},
            request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
        )

        with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
            result = await client.generate("Test", model="mistral")

        assert result.model == "mistral"

    async def test_generate_with_system_prompt(self):
        """generate() should include system prompt when provided."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=200,
            json={"response": "OK"},
            request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
        )
        mock_post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient.post", mock_post):
            await client.generate("Test", system_prompt="Be helpful")

        payload = mock_post.call_args[1]["json"]
        assert payload["system"] == "Be helpful"

    async def test_generate_raises_on_http_error(self):
        """generate() should propagate HTTP errors."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
            request=httpx.Request("POST", "http://fake-ollama:11434/api/generate"),
        )

        with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.generate("Test")

    async def test_list_models(self):
        """list_models() should GET /api/tags and return model info."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=200,
            json={
                "models": [
                    {
                        "name": "llama3.2",
                        "size": 4000000000,
                        "digest": "abc123",
                        "modified_at": "2025-01-01T00:00:00Z",
                    },
                    {
                        "name": "mistral",
                        "size": 3500000000,
                        "digest": "def456",
                        "modified_at": "2025-01-02T00:00:00Z",
                    },
                ]
            },
            request=httpx.Request("GET", "http://fake-ollama:11434/api/tags"),
        )

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            models = await client.list_models()

        assert len(models) == 2
        assert models[0].name == "llama3.2"
        assert models[0].size == 4000000000
        assert models[1].name == "mistral"

    async def test_list_models_empty(self):
        """list_models() should handle an empty model list."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=200,
            json={"models": []},
            request=httpx.Request("GET", "http://fake-ollama:11434/api/tags"),
        )

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            models = await client.list_models()

        assert models == []

    async def test_is_available_true(self):
        """is_available() should return True when server responds 200."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=200,
            text="Ollama is running",
            request=httpx.Request("GET", "http://fake-ollama:11434"),
        )

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await client.is_available()

        assert result is True

    async def test_is_available_false_on_error(self):
        """is_available() should return False on connection error."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        with patch(
            "httpx.AsyncClient.get",
            AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
        ):
            result = await client.is_available()

        assert result is False

    async def test_is_available_false_on_non_200(self):
        """is_available() should return False when server returns non-200."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        mock_response = httpx.Response(
            status_code=503,
            text="Service Unavailable",
            request=httpx.Request("GET", "http://fake-ollama:11434"),
        )

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
            result = await client.is_available()

        assert result is False

    async def test_stream_generate(self):
        """stream_generate() should yield chunks from streaming response."""
        client = OllamaClient(base_url="http://fake-ollama:11434")

        # Build fake streaming response lines
        lines = [
            json.dumps({"response": "Hello ", "done": False}),
            json.dumps({"response": "world", "done": False}),
            json.dumps({"response": "", "done": True}),
        ]

        # Create a mock streaming context manager
        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_stream_response.aiter_lines = mock_aiter_lines

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
            chunks = []
            async for chunk in client.stream_generate("Test prompt"):
                chunks.append(chunk)

        assert chunks == ["Hello ", "world"]


class TestOllamaModelInfo:
    """Test the OllamaModelInfo dataclass."""

    def test_model_info_creation(self):
        info = OllamaModelInfo(
            name="llama3.2",
            size=4000000000,
            digest="abc123",
            modified_at="2025-01-01T00:00:00Z",
        )
        assert info.name == "llama3.2"
        assert info.size == 4000000000

    def test_model_info_defaults(self):
        info = OllamaModelInfo(name="test")
        assert info.size == 0
        assert info.digest == ""
        assert info.modified_at == ""


# ─── Fallback and Model Routing Tests ────────────────────────────


class TestLLMClientFallbackBehavior:
    """Test the fallback cascade: Claude → Ollama → graceful degradation."""

    async def test_claude_failure_falls_back_to_ollama(self):
        """If Claude fails, Ollama should be tried next."""
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "test-key", "LLM_BACKEND": ""},
            clear=False,
        ):
            env_copy = {k: v for k, v in __import__("os").environ.items() if k != "LLM_BACKEND"}
        with patch.dict("os.environ", env_copy, clear=True):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                client = LLMClient()

        # Make Claude fail
        client._generate_claude = AsyncMock(side_effect=Exception("Claude unavailable"))  # type: ignore[method-assign]

        # Make Ollama succeed
        ollama_response = LLMResponse(
            text="Ollama response",
            backend="ollama",
            model="llama3.2",
        )
        client._ollama_client.generate = AsyncMock(return_value=ollama_response)  # type: ignore[method-assign]

        result = await client.generate("system", "user")
        assert result.backend == "ollama"
        assert result.text == "Ollama response"
        assert client.last_backend == "ollama"

    async def test_both_fail_returns_fallback(self):
        """If both Claude and Ollama fail, graceful degradation is returned."""
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=False,
        ):
            env_copy = {k: v for k, v in __import__("os").environ.items() if k != "LLM_BACKEND"}
        with patch.dict("os.environ", env_copy, clear=True):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                client = LLMClient()

        client._generate_claude = AsyncMock(side_effect=Exception("Claude down"))  # type: ignore[method-assign]
        client._ollama_client.generate = AsyncMock(side_effect=Exception("Ollama down"))  # type: ignore[method-assign]

        result = await client.generate("system", "user")
        assert result.backend == "none"
        assert "unavailable" in result.text.lower()
        assert client.last_backend == "none"

    async def test_forced_ollama_skips_claude(self):
        """LLM_BACKEND=ollama should skip Claude entirely."""
        with patch.dict("os.environ", {"LLM_BACKEND": "ollama"}, clear=False):
            client = LLMClient()

        ollama_response = LLMResponse(
            text="Ollama only",
            backend="ollama",
            model="llama3.2",
        )
        client._ollama_client.generate = AsyncMock(return_value=ollama_response)  # type: ignore[method-assign]
        client._generate_claude = AsyncMock()  # type: ignore[method-assign]

        result = await client.generate("system", "user")
        assert result.backend == "ollama"
        client._generate_claude.assert_not_called()

    async def test_forced_claude_skips_ollama(self):
        """LLM_BACKEND=claude should skip Ollama even if Claude fails."""
        with patch.dict(
            "os.environ",
            {"LLM_BACKEND": "claude", "ANTHROPIC_API_KEY": "test-key"},
            clear=False,
        ):
            client = LLMClient()

        client._generate_claude = AsyncMock(side_effect=Exception("Claude down"))  # type: ignore[method-assign]
        client._ollama_client.generate = AsyncMock()  # type: ignore[method-assign]

        result = await client.generate("system", "user")
        # Should return fallback, not try Ollama
        assert result.backend == "none"
        client._ollama_client.generate.assert_not_called()

    async def test_last_backend_tracking(self):
        """The last_backend property should reflect the most recent call."""
        with patch.dict("os.environ", {"LLM_BACKEND": "none"}, clear=False):
            client = LLMClient()

        await client.generate("system", "user")
        assert client.last_backend == "none"


class TestLLMClientModelRouting:
    """Test that model selection and routing works correctly."""

    async def test_ollama_model_from_env(self):
        """OLLAMA_MODEL env var should be used as default model."""
        with patch.dict(
            "os.environ",
            {"OLLAMA_MODEL": "codellama", "LLM_BACKEND": "ollama"},
            clear=False,
        ):
            client = LLMClient()

        assert client._ollama_model == "codellama"
        assert client._ollama_client.default_model == "codellama"

    async def test_ollama_model_default(self):
        """Without OLLAMA_MODEL, the default should be llama3.2."""
        env_copy = {k: v for k, v in __import__("os").environ.items() if k != "OLLAMA_MODEL"}
        with patch.dict("os.environ", env_copy, clear=True):
            client = LLMClient()

        assert client._ollama_model == "llama3.2"

    async def test_generate_ollama_uses_ollama_client(self):
        """_generate_ollama should delegate to the OllamaClient."""
        with patch.dict("os.environ", {"LLM_BACKEND": "ollama"}, clear=False):
            client = LLMClient()

        ollama_response = LLMResponse(
            text="Delegated response",
            backend="ollama",
            model="llama3.2",
        )
        client._ollama_client.generate = AsyncMock(return_value=ollama_response)  # type: ignore[method-assign]

        result = await client._generate_ollama("system", "user", 2048, 0.7)
        assert result.text == "Delegated response"
        client._ollama_client.generate.assert_called_once_with(
            prompt="user",
            system_prompt="system",
            max_tokens=2048,
            temperature=0.7,
        )


class TestLLMClientStreamFallback:
    """Test stream_generate fallback behavior."""

    async def test_stream_fallback_to_ollama(self):
        """stream_generate should fall back to Ollama if Claude fails."""
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "test-key"},
            clear=False,
        ):
            env_copy = {k: v for k, v in __import__("os").environ.items() if k != "LLM_BACKEND"}
        with patch.dict("os.environ", env_copy, clear=True):
            with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
                client = LLMClient()

        # Make Claude streaming fail
        async def failing_claude(*args, **kwargs):
            raise Exception("Claude streaming down")
            yield  # noqa: E0305 — unreachable but makes this an async generator

        client._stream_claude = failing_claude  # type: ignore[assignment]

        # Make Ollama streaming succeed
        async def mock_ollama_stream(*args, **kwargs):
            for chunk in ["Ollama ", "streaming ", "works"]:
                yield chunk

        client._ollama_client.stream_generate = mock_ollama_stream  # type: ignore[assignment]

        chunks = []
        async for chunk in client.stream_generate("test"):
            chunks.append(chunk)

        assert "".join(chunks) == "Ollama streaming works"


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

    def test_flatten_healing_modalities_alias(self):
        """flatten_engine_data creates modalities_section alias from recommended_modalities."""
        data = {
            "recommended_modalities": [
                {
                    "modality": "Breathwork",
                    "skill_trigger": "anxiety relief",
                    "preference_score": 0.85,
                },
                {"modality": "Yoga", "skill_trigger": "stress reduction", "preference_score": 0.78},
            ],
        }
        flat = flatten_engine_data(data)
        assert "modalities_section" in flat
        assert "Breathwork" in flat["modalities_section"]

    def test_flatten_healing_crisis_section(self):
        """flatten_engine_data creates crisis_section from crisis_response dict."""
        data = {
            "crisis_response": {
                "severity": "high",
                "resources": [
                    {"name": "988 Suicide & Crisis Lifeline", "contact": "988"},
                ],
            },
        }
        flat = flatten_engine_data(data)
        assert "crisis_section" in flat
        assert "high" in flat["crisis_section"]
        assert "988" in flat["crisis_section"]

    def test_flatten_healing_no_crisis(self):
        """No crisis -> crisis_section says no crisis detected."""
        data = {"crisis_flag": False}
        flat = flatten_engine_data(data)
        assert "crisis_section" in flat
        assert "no crisis" in flat["crisis_section"].lower()


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

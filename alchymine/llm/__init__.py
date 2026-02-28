"""LLM client module for Alchymine narrative generation.

Provides a unified interface to generate text using either the
Claude API (recommended) or an Ollama fallback for self-hosted
deployments.
"""

from __future__ import annotations

from alchymine.llm.client import LLMClient, LLMResponse, OllamaClient, OllamaModelInfo

__all__ = ["LLMClient", "LLMResponse", "OllamaClient", "OllamaModelInfo"]

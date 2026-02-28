"""MCP (Model Context Protocol) servers for Alchymine.

Exposes engine capabilities as MCP tools for Claude and other LLMs.
Each system has its own server module:

  - intelligence_server — Numerology, astrology, personality, biorhythm
  - healing_server      — Crisis detection, modality matching, breathwork
  - wealth_server       — Wealth archetypes, lever priorities, debt strategies
  - creative_server     — Guilford assessment, style fingerprint, projects
  - perspective_server  — Bias detection, Kegan stages, decision frameworks
"""

from .base import MCPServer, ResourceDefinition, ToolDefinition

__all__ = [
    "MCPServer",
    "ResourceDefinition",
    "ToolDefinition",
]

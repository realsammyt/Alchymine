"""Creative MCP server — Guilford assessment, style fingerprint, projects.

Exposes the Creative Development system's deterministic engines
as MCP tools for Claude and other LLMs.
"""

from __future__ import annotations

from alchymine.engine.creative import (
    assess_guilford,
    suggest_projects,
)
from alchymine.engine.creative.assessment import assess_creative_dna
from alchymine.engine.creative.style import generate_style_fingerprint
from alchymine.engine.profile import CreativeDNA, GuilfordScores

from .base import MCPServer

server = MCPServer(name="alchymine-creative", version="1.0.0")


# ─── Tool: assess_guilford ──────────────────────────────────────────────


@server.tool(
    name="assess_guilford",
    description=(
        "Score divergent thinking from assessment responses using Guilford's "
        "six components: fluency, flexibility, originality, elaboration, "
        "sensitivity, and redefinition. Each scored 0-100."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "responses": {
                "type": "object",
                "description": (
                    "Assessment responses. Either component names directly "
                    "(e.g., {fluency: 75, flexibility: 60, ...}) or individual "
                    "question IDs ({fluency_1: 70, fluency_2: 80, ...})."
                ),
            },
        },
        "required": ["responses"],
    },
)
def assess_guilford_tool(responses: dict) -> dict:
    """Score Guilford divergent thinking components."""
    scores = assess_guilford(responses)
    return {
        "fluency": scores.fluency,
        "flexibility": scores.flexibility,
        "originality": scores.originality,
        "elaboration": scores.elaboration,
        "sensitivity": scores.sensitivity,
        "redefinition": scores.redefinition,
    }


# ─── Tool: generate_style_fingerprint ───────────────────────────────────


@server.tool(
    name="generate_style_fingerprint",
    description=(
        "Generate a unified creative style profile from Guilford scores "
        "and Creative DNA dimensions. Returns style summary, dominant "
        "components, one-sentence style description, and overall score."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guilford_scores": {
                "type": "object",
                "description": (
                    "Guilford component scores (0-100). Keys: fluency, "
                    "flexibility, originality, elaboration, sensitivity, redefinition"
                ),
            },
            "creative_dna": {
                "type": "object",
                "description": (
                    "Creative DNA dimensions. Keys: structure_vs_improvisation (0-1), "
                    "collaboration_vs_solitude (0-1), convergent_vs_divergent (0-1), "
                    "primary_sensory_mode (visual|verbal|kinesthetic|musical), "
                    "creative_peak (morning|evening)"
                ),
            },
        },
        "required": ["guilford_scores"],
    },
)
def generate_style_fingerprint_tool(
    guilford_scores: dict, creative_dna: dict | None = None
) -> dict:
    """Generate a unified creative style profile."""
    guilford = GuilfordScores(**guilford_scores)

    if creative_dna is not None:
        dna = CreativeDNA(**creative_dna)
    else:
        dna = assess_creative_dna({})

    return generate_style_fingerprint(guilford, dna)


# ─── Tool: suggest_projects ─────────────────────────────────────────────


@server.tool(
    name="suggest_projects",
    description=(
        "Suggest creative projects based on a user's Guilford scores "
        "and creative orientation. Returns project titles, descriptions, "
        "types, and suggested mediums."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "guilford_scores": {
                "type": "object",
                "description": (
                    "Guilford scores (0-100). Keys: fluency, flexibility, "
                    "originality, elaboration, sensitivity, redefinition"
                ),
            },
            "skill_level": {
                "type": "string",
                "description": "Skill level: beginner, intermediate, or advanced",
            },
        },
        "required": ["guilford_scores"],
    },
)
def suggest_projects_tool(guilford_scores: dict, skill_level: str = "beginner") -> list[dict]:
    """Suggest creative projects based on the user's profile."""
    guilford = GuilfordScores(**guilford_scores)
    dna = assess_creative_dna({})
    style = generate_style_fingerprint(guilford, dna)
    return suggest_projects(style, skill_level)


# ─── Resource: system info ──────────────────────────────────────────────


@server.resource(
    uri="alchymine://creative/info",
    name="Creative System Info",
    description="Metadata about the Creative MCP server and its available tools.",
)
def creative_info() -> dict:
    """Return metadata about the Creative system."""
    return {
        "name": server.name,
        "version": server.version,
        "tools": [t["name"] for t in server.list_tools()],
        "description": (
            "Creative Development system — Guilford divergent thinking "
            "assessment, creative style fingerprinting, and project "
            "suggestions. All calculations are deterministic."
        ),
    }

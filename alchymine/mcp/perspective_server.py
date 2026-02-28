"""Perspective MCP server — bias detection, Kegan stages, decision frameworks.

Exposes the Perspective Enhancement system's deterministic engines
as MCP tools for Claude and other LLMs.
"""

from __future__ import annotations

from alchymine.engine.perspective.biases import detect_biases
from alchymine.engine.perspective.frameworks import (
    pros_cons_analysis,
    six_thinking_hats,
    weighted_decision_matrix,
)
from alchymine.engine.perspective.kegan import assess_kegan_stage, stage_description

from .base import MCPServer

server = MCPServer(name="alchymine-perspective", version="1.0.0")


# ─── Tool: detect_biases ────────────────────────────────────────────────


@server.tool(
    name="detect_biases",
    description=(
        "Identify potential cognitive biases in reasoning text using "
        "keyword/pattern matching against a catalog of 20 known biases. "
        "Returns bias types, descriptions, matched phrases, confidence, "
        "and academic sources. This is a reflective aid, not a diagnostic tool."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Free-text reasoning to analyse for cognitive biases",
            },
        },
        "required": ["text"],
    },
)
def detect_biases_tool(text: str) -> list[dict]:
    """Detect cognitive biases in reasoning text."""
    return detect_biases(text)


# ─── Tool: assess_kegan_stage ────────────────────────────────────────────


@server.tool(
    name="assess_kegan_stage",
    description=(
        "Assess developmental stage using Kegan's constructive-developmental "
        "framework. Requires scores (1-5) on at least 2 of 5 dimensions: "
        "self_awareness, perspective_taking, relationship_to_authority, "
        "conflict_tolerance, systems_thinking. Returns stage with description, "
        "strengths, and growth edges."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "responses": {
                "type": "object",
                "description": (
                    "Dimension scores (1-5). Keys: self_awareness, "
                    "perspective_taking, relationship_to_authority, "
                    "conflict_tolerance, systems_thinking. At least 2 required."
                ),
            },
        },
        "required": ["responses"],
    },
)
def assess_kegan_stage_tool(responses: dict) -> dict:
    """Assess Kegan developmental stage from dimension scores."""
    stage = assess_kegan_stage(responses)
    desc = stage_description(stage)
    return {
        "stage": stage.value,
        "stage_number": desc["stage_number"],
        "name": desc["name"],
        "description": desc["description"],
        "strengths": desc["strengths"],
        "growth_edges": desc["growth_edges"],
        "source": desc["source"],
        "methodology": desc["methodology"],
    }


# ─── Tool: apply_framework ──────────────────────────────────────────────


@server.tool(
    name="apply_framework",
    description=(
        "Apply a structured decision framework to a problem. Supported "
        "frameworks: 'weighted_matrix' (multi-criteria scoring), "
        "'pros_cons' (structured pros/cons), 'six_hats' (De Bono's "
        "Six Thinking Hats). Each returns analysis with methodology attribution."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "framework_type": {
                "type": "string",
                "description": "Framework: weighted_matrix, pros_cons, or six_hats",
            },
            "decision": {
                "type": "string",
                "description": "The decision or problem being analysed",
            },
            "options": {
                "type": "object",
                "description": (
                    "Framework-specific data. "
                    "For weighted_matrix: {options: [str], criteria: [{name, weight, scores}]}. "
                    "For pros_cons: {pros: [str], cons: [str]}. "
                    "For six_hats: {perspectives: {colour: thinking}}."
                ),
            },
        },
        "required": ["framework_type", "decision", "options"],
    },
)
def apply_framework_tool(framework_type: str, decision: str, options: dict) -> dict:
    """Apply a decision framework to a problem."""
    if framework_type == "weighted_matrix":
        return weighted_decision_matrix(
            options=options.get("options", []),
            criteria=options.get("criteria", []),
        )
    elif framework_type == "pros_cons":
        return pros_cons_analysis(
            option=decision,
            pros=options.get("pros", []),
            cons=options.get("cons", []),
        )
    elif framework_type == "six_hats":
        return six_thinking_hats(
            problem=decision,
            perspectives=options.get("perspectives", {}),
        )
    else:
        raise ValueError(
            f"Unknown framework: {framework_type}. Valid: weighted_matrix, pros_cons, six_hats"
        )


# ─── Resource: system info ──────────────────────────────────────────────


@server.resource(
    uri="alchymine://perspective/info",
    name="Perspective System Info",
    description="Metadata about the Perspective MCP server and its available tools.",
)
def perspective_info() -> dict:
    """Return metadata about the Perspective system."""
    return {
        "name": server.name,
        "version": server.version,
        "tools": [t["name"] for t in server.list_tools()],
        "description": (
            "Perspective Enhancement system — cognitive bias detection, "
            "Kegan developmental stage assessment, and structured decision "
            "frameworks. All calculations are deterministic. Bias detection "
            "is a reflective aid, not a diagnostic tool."
        ),
    }

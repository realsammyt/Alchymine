"""Intelligence MCP server — numerology, astrology, personality, biorhythm.

Exposes the Personalized Intelligence system's deterministic engines
as MCP tools for Claude and other LLMs.
"""

from __future__ import annotations

from datetime import date

from alchymine.engine.astrology import approximate_sun_degree, approximate_sun_sign
from alchymine.engine.biorhythm import calculate_biorhythm
from alchymine.engine.numerology import calculate_pythagorean_profile
from alchymine.engine.personality.big_five import score_big_five
from alchymine.engine.personality.enneagram import score_enneagram

from .base import MCPServer

server = MCPServer(name="alchymine-intelligence", version="1.0.0")


# ─── Tool: calculate_numerology ──────────────────────────────────────────


@server.tool(
    name="calculate_numerology",
    description=(
        "Calculate a full Pythagorean numerology profile from a person's "
        "name and birth date. Returns life path, expression, soul urge, "
        "personality, personal year/month, and maturity numbers."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Full legal name"},
            "birth_date": {
                "type": "string",
                "description": "Birth date in YYYY-MM-DD format",
            },
        },
        "required": ["name", "birth_date"],
    },
)
def calculate_numerology(name: str, birth_date: str) -> dict:
    """Calculate a full Pythagorean numerology profile."""
    bd = date.fromisoformat(birth_date)
    profile = calculate_pythagorean_profile(name, bd)
    return {
        "life_path": profile.life_path,
        "expression": profile.expression,
        "soul_urge": profile.soul_urge,
        "personality": profile.personality,
        "personal_year": profile.personal_year,
        "personal_month": profile.personal_month,
        "maturity": profile.maturity,
        "is_master_number": profile.is_master_number,
    }


# ─── Tool: calculate_astrology ──────────────────────────────────────────


@server.tool(
    name="calculate_astrology",
    description=(
        "Calculate sun sign and ecliptic degree from a birth date. "
        "Uses date-based approximation (accurate to within 1 day at sign boundaries)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "birth_date": {
                "type": "string",
                "description": "Birth date in YYYY-MM-DD format",
            },
        },
        "required": ["birth_date"],
    },
)
def calculate_astrology(birth_date: str) -> dict:
    """Calculate sun sign and degree from a birth date."""
    bd = date.fromisoformat(birth_date)
    sun_sign = approximate_sun_sign(bd)
    sun_degree = approximate_sun_degree(bd)
    return {
        "sun_sign": sun_sign,
        "sun_degree": sun_degree,
    }


# ─── Tool: assess_personality ────────────────────────────────────────────


@server.tool(
    name="assess_personality",
    description=(
        "Score Big Five personality traits (mini-IPIP, 20 items) and "
        "Enneagram type (9 items). Returns trait scores on a 0-100 scale "
        "and Enneagram primary type + wing."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "big_five_responses": {
                "type": "object",
                "description": (
                    "20 mini-IPIP responses: keys bf_e1..bf_e4, bf_a1..bf_a4, "
                    "bf_c1..bf_c4, bf_n1..bf_n4, bf_o1..bf_o4. Values 1-5."
                ),
            },
            "enneagram_responses": {
                "type": "object",
                "description": ("9 Enneagram responses: keys enn_1..enn_9. Values 1-5."),
            },
        },
        "required": ["big_five_responses", "enneagram_responses"],
    },
)
def assess_personality(
    big_five_responses: dict[str, int], enneagram_responses: dict[str, int]
) -> dict:
    """Score Big Five and Enneagram from assessment responses."""
    big_five = score_big_five(big_five_responses)
    primary_type, wing = score_enneagram(enneagram_responses)
    return {
        "big_five": {
            "openness": big_five.openness,
            "conscientiousness": big_five.conscientiousness,
            "extraversion": big_five.extraversion,
            "agreeableness": big_five.agreeableness,
            "neuroticism": big_five.neuroticism,
        },
        "enneagram": {
            "primary_type": primary_type,
            "wing": wing,
        },
    }


# ─── Tool: calculate_biorhythm ──────────────────────────────────────────


@server.tool(
    name="calculate_biorhythm",
    description=(
        "Calculate biorhythm cycle values (physical, emotional, intellectual) "
        "for a given target date. Returns sine values (-1 to 1), percentages "
        "(0-100), and critical-day flags. Evidence rating: LOW."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "birth_date": {
                "type": "string",
                "description": "Birth date in YYYY-MM-DD format",
            },
            "target_date": {
                "type": "string",
                "description": "Target date in YYYY-MM-DD format",
            },
        },
        "required": ["birth_date", "target_date"],
    },
)
def calculate_biorhythm_tool(birth_date: str, target_date: str) -> dict:
    """Calculate biorhythm cycles for a target date."""
    bd = date.fromisoformat(birth_date)
    td = date.fromisoformat(target_date)
    result = calculate_biorhythm(bd, td)
    return {
        "physical": result.physical,
        "emotional": result.emotional,
        "intellectual": result.intellectual,
        "physical_percentage": result.physical_percentage,
        "emotional_percentage": result.emotional_percentage,
        "intellectual_percentage": result.intellectual_percentage,
        "days_alive": result.days_alive,
        "is_physical_critical": result.is_physical_critical,
        "is_emotional_critical": result.is_emotional_critical,
        "is_intellectual_critical": result.is_intellectual_critical,
        "target_date": result.target_date.isoformat(),
        "evidence_rating": result.evidence_rating,
        "methodology_note": result.methodology_note,
    }


# ─── Resource: system info ──────────────────────────────────────────────


@server.resource(
    uri="alchymine://intelligence/info",
    name="Intelligence System Info",
    description="Metadata about the Intelligence MCP server and its available tools.",
)
def intelligence_info() -> dict:
    """Return metadata about the Intelligence system."""
    return {
        "name": server.name,
        "version": server.version,
        "tools": [t["name"] for t in server.list_tools()],
        "description": (
            "Personalized Intelligence system — numerology, astrology, "
            "personality assessment, and biorhythm calculations. "
            "All calculations are deterministic."
        ),
    }

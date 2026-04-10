"""Healing MCP server — crisis detection, modality matching, breathwork.

Exposes the Ethical Healing system's deterministic engines
as MCP tools for Claude and other LLMs.

CRITICAL: Crisis detection must always be available. The detect_crisis
tool is the highest-priority tool in this server.
"""

from __future__ import annotations

from alchymine.engine.healing import detect_crisis, get_breathwork_pattern, match_modalities
from alchymine.engine.healing.skills import (
    SkillNotFoundError,
    SkillRegistry,
    get_default_yaml_dir,
)
from alchymine.engine.profile import (
    ArchetypeType,
    BigFiveScores,
    Intention,
    PracticeDifficulty,
)

from .base import MCPServer

server = MCPServer(name="alchymine-healing", version="1.0.0")

# Module-level skill registry, loaded lazily on first tool call.
_skill_registry: SkillRegistry | None = None


def _get_skill_registry() -> SkillRegistry:
    """Return the lazily-initialised skill registry."""
    global _skill_registry
    if _skill_registry is None:
        reg = SkillRegistry()
        reg.load_directory(get_default_yaml_dir())
        _skill_registry = reg
    return _skill_registry


# ─── Tool: detect_crisis ────────────────────────────────────────────────


@server.tool(
    name="detect_crisis",
    description=(
        "Scan free-text input for crisis-related keywords. Returns severity "
        "level, matched keywords, crisis resources (hotlines), and disclaimers. "
        "Returns null if no crisis indicators are detected. "
        "CRITICAL: This tool must be called on any user text that may "
        "contain crisis indicators."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Free-text input to scan for crisis keywords",
            },
        },
        "required": ["text"],
    },
)
def detect_crisis_tool(text: str) -> dict | None:
    """Scan text for crisis keywords."""
    result = detect_crisis(text)
    if result is None:
        return None
    return {
        "severity": result.severity.value,
        "matched_keywords": list(result.matched_keywords),
        "resources": [
            {"name": r.name, "contact": r.contact, "description": r.description}
            for r in result.resources
        ],
        "disclaimers": list(result.disclaimers),
    }


# ─── Tool: match_modalities ─────────────────────────────────────────────


@server.tool(
    name="match_modalities",
    description=(
        "Match and rank healing modalities for a user profile based on "
        "archetype, Big Five personality traits, and intention. Returns "
        "a ranked list of healing preferences with scores."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "archetype": {
                "type": "string",
                "description": (
                    "Primary Jungian archetype. One of: creator, sage, explorer, "
                    "mystic, ruler, lover, hero, caregiver, jester, innocent, rebel, everyman"
                ),
            },
            "big_five": {
                "type": "object",
                "description": (
                    "Big Five scores (0-100 each). Keys: openness, conscientiousness, "
                    "extraversion, agreeableness, neuroticism"
                ),
            },
            "intention": {
                "type": "string",
                "description": (
                    "Primary intention. One of: career, love, purpose, money, "
                    "health, family, business, legacy"
                ),
            },
        },
        "required": ["archetype", "big_five", "intention"],
    },
)
def match_modalities_tool(archetype: str, big_five: dict, intention: str) -> list[dict]:
    """Match healing modalities for a user profile."""
    archetype_type = ArchetypeType(archetype)
    big_five_scores = BigFiveScores(**big_five)
    intention_enum = Intention(intention)

    results = match_modalities(
        archetype_primary=archetype_type,
        archetype_secondary=None,
        big_five=big_five_scores,
        intentions=[intention_enum],
    )
    return [
        {
            "modality": r.modality,
            "skill_trigger": r.skill_trigger,
            "preference_score": r.preference_score,
            "difficulty_level": r.difficulty_level.value,
        }
        for r in results
    ]


# ─── Tool: get_breathwork ───────────────────────────────────────────────


@server.tool(
    name="get_breathwork",
    description=(
        "Select a breathwork pattern based on difficulty level and intention. "
        "Returns timing parameters (inhale, hold, exhale, hold empty), cycle "
        "count, and description."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "difficulty": {
                "type": "string",
                "description": (
                    "Maximum difficulty level. One of: foundation, developing, "
                    "established, advanced, intensive"
                ),
            },
            "intention": {
                "type": "string",
                "description": (
                    "Optional intention hint (e.g., 'calm', 'energy', 'focus', "
                    "'sleep', 'resilience', 'balance', 'stress', 'clarity')"
                ),
            },
        },
        "required": ["difficulty"],
    },
)
def get_breathwork_tool(difficulty: str, intention: str | None = None) -> dict:
    """Select a breathwork pattern."""
    diff = PracticeDifficulty(difficulty)
    pattern = get_breathwork_pattern(difficulty=diff, intention=intention)
    return {
        "name": pattern.name,
        "inhale_seconds": pattern.inhale_seconds,
        "hold_seconds": pattern.hold_seconds,
        "exhale_seconds": pattern.exhale_seconds,
        "hold_empty_seconds": pattern.hold_empty_seconds,
        "cycles": pattern.cycles,
        "difficulty": pattern.difficulty.value,
        "description": pattern.description,
    }


# ─── Tool: list_skills ──────────────────────────────────────────────────


@server.tool(
    name="list_skills",
    description=(
        "List all available healing skills, optionally filtered by modality. "
        "Returns a list of skill summaries (name, title, modality, evidence "
        "rating, duration). Use run_skill to get full details and guided steps."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "modality": {
                "type": "string",
                "description": (
                    "Optional: filter by modality (e.g., 'breathwork', 'somatic', "
                    "'language', 'nature'). Omit to list all skills."
                ),
            },
        },
        "required": [],
    },
)
def list_skills_tool(modality: str | None = None) -> list[dict]:
    """List healing skills from the SkillRegistry."""
    registry = _get_skill_registry()
    if modality is not None:
        skills = registry.list_by_modality(modality)
    else:
        skills = registry.list_all()
    return [
        {
            "name": s.name,
            "title": s.title,
            "modality": s.modality,
            "evidence_rating": s.evidence_rating,
            "duration_minutes": s.duration_minutes,
        }
        for s in skills
    ]


# ─── Tool: run_skill ───────────────────────────────────────────────────


@server.tool(
    name="run_skill",
    description=(
        "Retrieve a healing skill by name and return its full practice card "
        "including guided steps, contraindications, and evidence rating. "
        "The caller should present the steps to the user sequentially."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": (
                    "The skill slug, e.g. 'breathwork-box-breathing' or "
                    "'somatic-grounding-5-4-3-2-1'."
                ),
            },
        },
        "required": ["name"],
    },
)
def run_skill_tool(name: str) -> dict:
    """Return the full practice card for a single healing skill.

    Raises
    ------
    ValueError
        If the skill name is not found in the registry.
    """
    registry = _get_skill_registry()
    try:
        skill = registry.get(name)
    except SkillNotFoundError as exc:
        raise ValueError(f"Skill not found: {name}") from exc
    return {
        "name": skill.name,
        "title": skill.title,
        "modality": skill.modality,
        "description": skill.description,
        "steps": list(skill.steps),
        "evidence_rating": skill.evidence_rating,
        "contraindications": list(skill.contraindications),
        "duration_minutes": skill.duration_minutes,
    }


# ─── Resource: system info ──────────────────────────────────────────────


@server.resource(
    uri="alchymine://healing/info",
    name="Healing System Info",
    description="Metadata about the Healing MCP server and its available tools.",
)
def healing_info() -> dict:
    """Return metadata about the Healing system."""
    return {
        "name": server.name,
        "version": server.version,
        "tools": [t["name"] for t in server.list_tools()],
        "description": (
            "Ethical Healing system — crisis detection, modality matching, "
            "and breathwork pattern selection. Crisis detection is the "
            "highest-priority tool. All calculations are deterministic."
        ),
        "ethics_note": (
            "First, Do No Harm. Crisis detection must be run on any text "
            "that may contain crisis indicators before other processing."
        ),
    }

"""Project suggestions — deterministic project idea generation and scoping.

All functions are deterministic (pure). No LLM calls.
"""

from __future__ import annotations

# ─── Project Database ────────────────────────────────────────────────────

# Each project template is keyed by dominant Guilford component and skill level.
# Structure: {component: {skill_level: [project_dicts]}}

_PROJECT_TEMPLATES: dict[str, dict[str, list[dict]]] = {
    "fluency": {
        "beginner": [
            {
                "title": "100 Ideas Challenge",
                "description": "Generate 100 ideas on a single theme in one sitting to build idea-generation muscle.",
                "type": "brainstorming",
                "medium": "any",
            },
            {
                "title": "Daily Sketch Journal",
                "description": "Sketch one new concept per day for 30 days without judgment.",
                "type": "visual",
                "medium": "drawing",
            },
        ],
        "intermediate": [
            {
                "title": "Rapid Prototyping Sprint",
                "description": "Create 5 rough prototypes of a product idea in one week.",
                "type": "design",
                "medium": "mixed",
            },
            {
                "title": "Flash Fiction Collection",
                "description": "Write 10 flash fiction pieces (under 500 words each) in different genres.",
                "type": "writing",
                "medium": "verbal",
            },
        ],
        "advanced": [
            {
                "title": "Innovation Lab",
                "description": "Run a structured brainstorming session producing 50+ viable solutions to a real problem.",
                "type": "facilitation",
                "medium": "collaborative",
            },
        ],
    },
    "flexibility": {
        "beginner": [
            {
                "title": "Genre Swap Exercise",
                "description": "Take a familiar story and retell it in 3 different genres.",
                "type": "writing",
                "medium": "verbal",
            },
            {
                "title": "Material Exploration",
                "description": "Create the same design using 5 different materials or tools.",
                "type": "design",
                "medium": "mixed",
            },
        ],
        "intermediate": [
            {
                "title": "Cross-Discipline Mashup",
                "description": "Combine techniques from two unrelated creative fields into one piece.",
                "type": "mixed-media",
                "medium": "mixed",
            },
        ],
        "advanced": [
            {
                "title": "Constraint-Based Portfolio",
                "description": "Complete 7 creative works, each with a radically different constraint.",
                "type": "portfolio",
                "medium": "mixed",
            },
        ],
    },
    "originality": {
        "beginner": [
            {
                "title": "Unusual Uses Challenge",
                "description": "Find 20 novel uses for a common household object.",
                "type": "brainstorming",
                "medium": "any",
            },
        ],
        "intermediate": [
            {
                "title": "Surrealist Collaboration",
                "description": "Create a series of works using exquisite corpse or cut-up technique.",
                "type": "experimental",
                "medium": "mixed",
            },
            {
                "title": "Concept Album",
                "description": "Produce a 5-track concept album exploring an unconventional theme.",
                "type": "music",
                "medium": "musical",
            },
        ],
        "advanced": [
            {
                "title": "Experimental Short Film",
                "description": "Write, produce, and edit a 5-minute experimental film.",
                "type": "film",
                "medium": "visual",
            },
        ],
    },
    "elaboration": {
        "beginner": [
            {
                "title": "Detail Deep Dive",
                "description": "Take a simple sketch and develop it into a fully detailed illustration.",
                "type": "visual",
                "medium": "drawing",
            },
        ],
        "intermediate": [
            {
                "title": "World-Building Document",
                "description": "Create a detailed fictional world with geography, culture, and history.",
                "type": "writing",
                "medium": "verbal",
            },
        ],
        "advanced": [
            {
                "title": "Architectural Model",
                "description": "Design and build a detailed scale model of an imagined structure.",
                "type": "design",
                "medium": "kinesthetic",
            },
        ],
    },
    "sensitivity": {
        "beginner": [
            {
                "title": "Problem-Spotting Walk",
                "description": "Take a walk and document 10 design problems you notice in your environment.",
                "type": "observation",
                "medium": "any",
            },
        ],
        "intermediate": [
            {
                "title": "Community Needs Map",
                "description": "Interview 5 people and map unmet creative needs in your community.",
                "type": "research",
                "medium": "verbal",
            },
        ],
        "advanced": [
            {
                "title": "Design Thinking Sprint",
                "description": "Run a full empathize-define-ideate-prototype-test cycle on a real problem.",
                "type": "design-thinking",
                "medium": "mixed",
            },
        ],
    },
    "redefinition": {
        "beginner": [
            {
                "title": "Upcycle Project",
                "description": "Transform a discarded object into something beautiful or useful.",
                "type": "craft",
                "medium": "kinesthetic",
            },
        ],
        "intermediate": [
            {
                "title": "Remix Challenge",
                "description": "Take an existing creative work (with permission) and transform its meaning through remixing.",
                "type": "remix",
                "medium": "mixed",
            },
        ],
        "advanced": [
            {
                "title": "Adaptive Reuse Proposal",
                "description": "Design a plan to repurpose an abandoned space for creative community use.",
                "type": "design",
                "medium": "mixed",
            },
        ],
    },
}

# ─── Scope Estimation Data ────────────────────────────────────────────────

_SCOPE_ESTIMATES: dict[str, dict] = {
    "brainstorming": {
        "hours_min": 1,
        "hours_max": 3,
        "sessions": 1,
        "difficulty": "beginner",
        "materials": "notebook or whiteboard",
    },
    "writing": {
        "hours_min": 5,
        "hours_max": 20,
        "sessions": 5,
        "difficulty": "intermediate",
        "materials": "word processor",
    },
    "visual": {
        "hours_min": 3,
        "hours_max": 15,
        "sessions": 3,
        "difficulty": "intermediate",
        "materials": "drawing supplies or digital tools",
    },
    "design": {
        "hours_min": 10,
        "hours_max": 40,
        "sessions": 8,
        "difficulty": "intermediate",
        "materials": "design software or physical materials",
    },
    "music": {
        "hours_min": 10,
        "hours_max": 50,
        "sessions": 10,
        "difficulty": "intermediate",
        "materials": "instrument or DAW software",
    },
    "film": {
        "hours_min": 20,
        "hours_max": 80,
        "sessions": 15,
        "difficulty": "advanced",
        "materials": "camera, editing software",
    },
    "mixed-media": {
        "hours_min": 5,
        "hours_max": 25,
        "sessions": 5,
        "difficulty": "intermediate",
        "materials": "varied — depends on chosen media",
    },
    "experimental": {
        "hours_min": 5,
        "hours_max": 30,
        "sessions": 5,
        "difficulty": "intermediate",
        "materials": "varies",
    },
    "observation": {
        "hours_min": 1,
        "hours_max": 3,
        "sessions": 1,
        "difficulty": "beginner",
        "materials": "notebook or phone camera",
    },
    "research": {
        "hours_min": 5,
        "hours_max": 15,
        "sessions": 5,
        "difficulty": "intermediate",
        "materials": "recording device, notebook",
    },
    "design-thinking": {
        "hours_min": 15,
        "hours_max": 40,
        "sessions": 8,
        "difficulty": "advanced",
        "materials": "post-its, whiteboard, prototyping materials",
    },
    "facilitation": {
        "hours_min": 5,
        "hours_max": 15,
        "sessions": 3,
        "difficulty": "advanced",
        "materials": "facilitation supplies, meeting space",
    },
    "craft": {
        "hours_min": 3,
        "hours_max": 10,
        "sessions": 2,
        "difficulty": "beginner",
        "materials": "found objects, basic tools",
    },
    "remix": {
        "hours_min": 5,
        "hours_max": 20,
        "sessions": 4,
        "difficulty": "intermediate",
        "materials": "editing software appropriate to medium",
    },
    "portfolio": {
        "hours_min": 30,
        "hours_max": 80,
        "sessions": 15,
        "difficulty": "advanced",
        "materials": "varied — depends on chosen media",
    },
}

# Valid skill levels
_VALID_SKILL_LEVELS = {"beginner", "intermediate", "advanced"}


# ─── Public API ───────────────────────────────────────────────────────────


def suggest_projects(style: dict, skill_level: str) -> list[dict]:
    """Generate project ideas based on a style fingerprint and skill level.

    Parameters
    ----------
    style:
        A style fingerprint dict as returned by
        ``generate_style_fingerprint()``. Must contain a
        ``dominant_components`` key with a list of Guilford component names.
    skill_level:
        One of "beginner", "intermediate", or "advanced".

    Returns
    -------
    list[dict]
        List of project suggestion dicts, each containing:
        title, description, type, medium, skill_level.
    """
    level = skill_level.lower()
    if level not in _VALID_SKILL_LEVELS:
        level = "beginner"

    dominant = style.get("dominant_components", [])
    if not dominant:
        dominant = ["fluency"]  # safe default

    projects: list[dict] = []
    seen_titles: set[str] = set()

    for component in dominant:
        component_projects = _PROJECT_TEMPLATES.get(component, {})
        level_projects = component_projects.get(level, [])

        for proj in level_projects:
            if proj["title"] not in seen_titles:
                enriched = {**proj, "skill_level": level}
                projects.append(enriched)
                seen_titles.add(proj["title"])

    # If no projects found for the exact level, fall back to beginner
    if not projects and level != "beginner":
        return suggest_projects(style, "beginner")

    return projects


def estimate_project_scope(project_type: str) -> dict:
    """Estimate time and effort for a project type.

    Parameters
    ----------
    project_type:
        Type string from a project suggestion (e.g., "writing", "design").

    Returns
    -------
    dict
        Keys: hours_min, hours_max, sessions, difficulty, materials.
        Returns defaults for unrecognized types.
    """
    ptype = project_type.lower()
    if ptype in _SCOPE_ESTIMATES:
        return dict(_SCOPE_ESTIMATES[ptype])

    # Default scope for unknown types
    return {
        "hours_min": 5,
        "hours_max": 20,
        "sessions": 4,
        "difficulty": "intermediate",
        "materials": "varies",
    }

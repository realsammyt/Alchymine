"""Kegan developmental stage assessment — deterministic scoring.

Robert Kegan's model of adult psychological development describes five
stages of increasing capacity for self-awareness and perspective-taking:

  Stage 1 — Impulsive: subject to impulses and perceptions
  Stage 2 — Imperial: subject to needs, interests, desires
  Stage 3 — Socialized: subject to interpersonal relationships and mutuality
  Stage 4 — Self-Authoring: subject to authorship, identity, ideology
  Stage 5 — Self-Transforming: subject to the dialectic, inter-individuality

Assessment uses a scored questionnaire mapping. All calculations are
deterministic. No LLM calls.

Attribution:
  Robert Kegan — "The Evolving Self" (1982) and
  "In Over Our Heads: The Mental Demands of Modern Life" (1994)

Ethical note:
  Kegan stages describe developmental capacity, not intelligence or
  worth. Every stage has strengths. The assessment is a reflective tool,
  not a judgement. Language must empower growth, never limit identity.
"""

from __future__ import annotations

from alchymine.engine.profile import KeganStage

# ─── Stage Metadata ──────────────────────────────────────────────────────

_STAGE_DESCRIPTIONS: dict[KeganStage, dict] = {
    KeganStage.IMPULSIVE: {
        "stage_number": 1,
        "name": "Impulsive",
        "description": (
            "At this stage, one is embedded in immediate impulses, perceptions, "
            "and reflexes. The world is experienced through direct sensory input "
            "and fantasy. Actions tend to be reactive rather than reflective."
        ),
        "strengths": [
            "Spontaneity and presence in the moment",
            "Vivid sensory experience",
            "Unfiltered emotional expression",
        ],
        "growth_edges": [
            "Developing the ability to delay gratification",
            "Beginning to recognise that others have separate perspectives",
            "Building cause-and-effect understanding",
        ],
        "source": "Kegan, R. (1982). The Evolving Self.",
    },
    KeganStage.IMPERIAL: {
        "stage_number": 2,
        "name": "Imperial",
        "description": (
            "At this stage, one's own needs, interests, and desires are the "
            "organising principle. Others are understood instrumentally — in terms "
            "of what they can provide. There is a clearer sense of self as separate "
            "from the environment."
        ),
        "strengths": [
            "Clear sense of personal needs and goals",
            "Self-reliance and independence",
            "Ability to pursue concrete objectives",
            "Strong practical intelligence",
        ],
        "growth_edges": [
            "Moving from transactional to mutual relationships",
            "Understanding that others have internal experiences as complex as one's own",
            "Developing empathy beyond self-interest",
        ],
        "source": "Kegan, R. (1982). The Evolving Self.",
    },
    KeganStage.SOCIALIZED: {
        "stage_number": 3,
        "name": "Socialized",
        "description": (
            "At this stage, one is embedded in interpersonal relationships and "
            "shared expectations. Identity is largely defined by important "
            "relationships and the group. There is deep capacity for empathy "
            "and connection, but difficulty distinguishing one's own voice from "
            "the expectations of others."
        ),
        "strengths": [
            "Deep empathy and attunement to others",
            "Strong relational skills and loyalty",
            "Capacity for genuine collaboration",
            "Orientation toward community and belonging",
        ],
        "growth_edges": [
            "Developing an internal authority separate from external validation",
            "Learning to hold one's own perspective even when it differs from the group",
            "Tolerating conflict without losing connection",
        ],
        "source": "Kegan, R. (1994). In Over Our Heads.",
    },
    KeganStage.SELF_AUTHORING: {
        "stage_number": 4,
        "name": "Self-Authoring",
        "description": (
            "At this stage, one has developed an internal compass — a self-authored "
            "system of values, beliefs, and identity. One can take responsibility for "
            "inner states, mediate between competing values, and maintain perspective "
            "independent of others' expectations."
        ),
        "strengths": [
            "Clear internal value system and personal authority",
            "Ability to self-reflect and take ownership of choices",
            "Capacity to hold multiple perspectives while maintaining one's own",
            "Strategic thinking and long-term planning",
        ],
        "growth_edges": [
            "Recognising the limits of one's own ideology or framework",
            "Becoming open to fundamental transformation of one's value system",
            "Holding paradox and contradiction without needing resolution",
        ],
        "source": "Kegan, R. (1994). In Over Our Heads.",
    },
    KeganStage.SELF_TRANSFORMING: {
        "stage_number": 5,
        "name": "Self-Transforming",
        "description": (
            "At this stage, one can see the limits of any single system of meaning — "
            "including one's own. There is capacity to hold multiple ideologies and "
            "frameworks simultaneously, embracing paradox and seeking deeper patterns. "
            "Identity is understood as fluid, interconnected, and evolving."
        ),
        "strengths": [
            "Comfort with paradox, ambiguity, and complexity",
            "Ability to hold and integrate multiple meaning-making systems",
            "Deep systemic awareness and inter-connectedness",
            "Capacity for genuine dialogue across differences",
        ],
        "growth_edges": [
            "Maintaining groundedness and practical action amid complexity",
            "Communicating across developmental perspectives",
            "Balancing systemic awareness with personal well-being",
        ],
        "source": "Kegan, R. (1994). In Over Our Heads.",
    },
}


# ─── Stage Assessment ────────────────────────────────────────────────────

# Assessment dimensions and their mapping to stages.
# Each response key maps to one dimension; values are scored 1-5.
# The assessment is deliberately simplified — a full Subject-Object
# Interview (SOI) requires a trained interviewer.

_DIMENSION_WEIGHTS: dict[str, dict[KeganStage, float]] = {
    "self_awareness": {
        KeganStage.IMPULSIVE: 1.0,
        KeganStage.IMPERIAL: 2.0,
        KeganStage.SOCIALIZED: 3.0,
        KeganStage.SELF_AUTHORING: 4.0,
        KeganStage.SELF_TRANSFORMING: 5.0,
    },
    "perspective_taking": {
        KeganStage.IMPULSIVE: 1.0,
        KeganStage.IMPERIAL: 1.5,
        KeganStage.SOCIALIZED: 3.0,
        KeganStage.SELF_AUTHORING: 4.0,
        KeganStage.SELF_TRANSFORMING: 5.0,
    },
    "relationship_to_authority": {
        KeganStage.IMPULSIVE: 1.0,
        KeganStage.IMPERIAL: 2.0,
        KeganStage.SOCIALIZED: 3.5,
        KeganStage.SELF_AUTHORING: 4.5,
        KeganStage.SELF_TRANSFORMING: 5.0,
    },
    "conflict_tolerance": {
        KeganStage.IMPULSIVE: 1.0,
        KeganStage.IMPERIAL: 2.0,
        KeganStage.SOCIALIZED: 2.5,
        KeganStage.SELF_AUTHORING: 4.0,
        KeganStage.SELF_TRANSFORMING: 5.0,
    },
    "systems_thinking": {
        KeganStage.IMPULSIVE: 1.0,
        KeganStage.IMPERIAL: 1.5,
        KeganStage.SOCIALIZED: 2.5,
        KeganStage.SELF_AUTHORING: 3.5,
        KeganStage.SELF_TRANSFORMING: 5.0,
    },
}

VALID_DIMENSIONS = frozenset(_DIMENSION_WEIGHTS.keys())

# Stage order for scoring
_STAGE_ORDER: list[KeganStage] = [
    KeganStage.IMPULSIVE,
    KeganStage.IMPERIAL,
    KeganStage.SOCIALIZED,
    KeganStage.SELF_AUTHORING,
    KeganStage.SELF_TRANSFORMING,
]


def assess_kegan_stage(responses: dict) -> KeganStage:
    """Determine developmental stage from assessment responses.

    Args:
        responses: Dict mapping dimension keys to scores (1-5).
            Valid keys: self_awareness, perspective_taking,
            relationship_to_authority, conflict_tolerance, systems_thinking.
            At least two dimensions must be provided.

    Returns:
        KeganStage enum value representing the assessed stage.

    Raises:
        ValueError: If fewer than 2 valid dimensions provided or scores
            are out of range.
    """
    # Validate responses
    valid_responses: dict[str, float] = {}
    for key, value in responses.items():
        if key in VALID_DIMENSIONS:
            if not isinstance(value, (int, float)):
                raise ValueError(f"Score for '{key}' must be numeric, got {type(value).__name__}")
            if value < 1 or value > 5:
                raise ValueError(f"Score for '{key}' must be between 1 and 5, got {value}")
            valid_responses[key] = float(value)

    if len(valid_responses) < 2:
        raise ValueError(
            f"At least 2 valid dimensions required. "
            f"Valid dimensions: {sorted(VALID_DIMENSIONS)}. "
            f"Provided: {sorted(valid_responses.keys())}"
        )

    # Score each stage by computing the sum of absolute differences
    # between the user's response and each stage's expected score
    # for each dimension. The stage with the lowest total distance wins.
    stage_distances: dict[KeganStage, float] = {}

    for stage in _STAGE_ORDER:
        total_distance = 0.0
        for dim, user_score in valid_responses.items():
            expected = _DIMENSION_WEIGHTS[dim][stage]
            total_distance += abs(user_score - expected)
        stage_distances[stage] = total_distance

    # Find the stage with the minimum distance
    best_stage = min(stage_distances, key=lambda s: stage_distances[s])

    return best_stage


# ─── Stage Description ───────────────────────────────────────────────────


def stage_description(stage: KeganStage) -> dict:
    """Return a comprehensive description of a Kegan developmental stage.

    Args:
        stage: KeganStage enum value.

    Returns:
        Dict with:
            - stage: KeganStage value
            - stage_number: 1-5
            - name: human-readable name
            - description: what the stage means
            - strengths: list of strengths at this stage
            - growth_edges: areas for potential growth
            - source: academic attribution
            - methodology: attribution string
    """
    if stage not in _STAGE_DESCRIPTIONS:
        raise ValueError(f"Invalid stage: {stage}")

    info = _STAGE_DESCRIPTIONS[stage]

    return {
        "stage": stage,
        "stage_number": info["stage_number"],
        "name": info["name"],
        "description": info["description"],
        "strengths": info["strengths"],
        "growth_edges": info["growth_edges"],
        "source": info["source"],
        "methodology": (
            "Robert Kegan's constructive-developmental framework "
            "(The Evolving Self, 1982; In Over Our Heads, 1994). "
            "Stages describe increasing complexity in how people "
            "construct meaning, not intelligence or worth. Every stage "
            "has genuine strengths. Growth is supported, never forced."
        ),
    }


# ─── Growth Pathway ──────────────────────────────────────────────────────

_GROWTH_PRACTICES: dict[KeganStage, dict] = {
    KeganStage.IMPULSIVE: {
        "target_stage": KeganStage.IMPERIAL,
        "practices": [
            "Practice pausing before reacting — notice the impulse without acting on it immediately.",
            "Keep a simple journal of cause-and-effect observations.",
            "Set one small goal each day and track progress.",
            "Practise naming emotions when they arise.",
        ],
        "supportive_environments": [
            "Structured routines with clear expectations",
            "Safe relationships with consistent boundaries",
            "Low-pressure opportunities for choice-making",
        ],
        "timeframe": "This transition typically unfolds over months to years with consistent practice.",
    },
    KeganStage.IMPERIAL: {
        "target_stage": KeganStage.SOCIALIZED,
        "practices": [
            "Practise active listening — summarise what others say before responding.",
            "Reflect on how your actions affect other people's feelings.",
            "Engage in collaborative projects where mutual success depends on cooperation.",
            "Ask others about their experience, even when it differs from yours.",
        ],
        "supportive_environments": [
            "Collaborative teams with shared goals",
            "Mentoring relationships",
            "Community participation and service",
        ],
        "timeframe": "This transition typically unfolds over months to years with consistent practice.",
    },
    KeganStage.SOCIALIZED: {
        "target_stage": KeganStage.SELF_AUTHORING,
        "practices": [
            "Identify beliefs you hold because of others' expectations versus your own conviction.",
            "Practise stating your opinion before asking others what they think.",
            "Write a personal values statement and review it monthly.",
            "Sit with the discomfort of disagreeing with someone you respect.",
            "Make one decision per week based solely on your own criteria.",
        ],
        "supportive_environments": [
            "Environments that encourage independent thinking",
            "Leadership roles with genuine autonomy",
            "Reflective practices (journaling, coaching, therapy)",
        ],
        "timeframe": "This transition typically unfolds over months to years with consistent practice.",
    },
    KeganStage.SELF_AUTHORING: {
        "target_stage": KeganStage.SELF_TRANSFORMING,
        "practices": [
            "Seek out perspectives that genuinely challenge your worldview.",
            "Practise holding two contradictory ideas without needing to resolve them.",
            "Explore traditions or frameworks very different from your own.",
            "Notice where your identity system creates blind spots.",
            "Engage in dialogue where the goal is understanding, not persuasion.",
        ],
        "supportive_environments": [
            "Diverse communities with multiple meaning-making systems",
            "Contemplative or mindfulness practices",
            "Cross-cultural experiences and dialogue",
        ],
        "timeframe": "This transition typically unfolds over years of sustained reflection and engagement.",
    },
    KeganStage.SELF_TRANSFORMING: {
        "target_stage": None,
        "practices": [
            "Continue to practise groundedness and presence amid complexity.",
            "Serve as a bridge between different perspectives and communities.",
            "Mentor others in their developmental journeys without prescribing outcomes.",
            "Explore the intersection of personal growth and systemic change.",
            "Maintain practices that support well-being alongside depth of awareness.",
        ],
        "supportive_environments": [
            "Communities engaged in systemic and collective transformation",
            "Inter-traditional dialogue spaces",
            "Service-oriented projects with emergent design",
        ],
        "timeframe": "At this stage, growth is an ongoing, open-ended process of deepening and integration.",
    },
}


def growth_pathway(current: KeganStage) -> dict:
    """Suggest development practices for growing beyond the current stage.

    Args:
        current: The user's current KeganStage.

    Returns:
        Dict with:
            - current_stage: the input stage
            - target_stage: the next stage (or None if at Stage 5)
            - practices: list of suggested growth practices
            - supportive_environments: conditions that support the transition
            - timeframe: realistic timeframe note
            - encouragement: empowering framing of the growth journey
            - methodology: attribution string
    """
    if current not in _GROWTH_PRACTICES:
        raise ValueError(f"Invalid stage: {current}")

    info = _GROWTH_PRACTICES[current]
    target = info["target_stage"]

    if target is not None:
        encouragement = (
            f"Your current stage ({current.value}) has genuine strengths — "
            f"the goal is not to 'leave' this stage behind, but to expand your "
            f"capacity so that you can access its strengths while also drawing on "
            f"the capabilities of the {target.value} stage. Growth is additive, "
            f"not replacement."
        )
    else:
        encouragement = (
            "At the self-transforming stage, growth continues as an open-ended "
            "process of deepening integration and expanding awareness. Your "
            "capacity for holding complexity is itself a gift to others."
        )

    return {
        "current_stage": current,
        "target_stage": target,
        "practices": info["practices"],
        "supportive_environments": info["supportive_environments"],
        "timeframe": info["timeframe"],
        "encouragement": encouragement,
        "methodology": (
            "Growth pathway based on Robert Kegan's constructive-developmental "
            "framework. Practices are informed by developmental coaching literature "
            "and the Subject-Object Interview tradition. Growth between stages is "
            "supported, never forced — each person's timeline is their own."
        ),
    }

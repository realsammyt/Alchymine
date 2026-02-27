"""Cognitive bias detection and debiasing — deterministic pattern matching.

Identifies cognitive biases in reasoning text using keyword/pattern matching.
No LLM calls — all detection is rule-based and reproducible.

Attribution:
  - Daniel Kahneman — "Thinking, Fast and Slow" (2011)
  - Amos Tversky & Daniel Kahneman — heuristics and biases research programme
  - Wikipedia's "List of cognitive biases" (community-maintained reference)

Ethical note:
  Bias detection is presented as a reflective aid, not a diagnostic tool.
  Identifying a bias pattern does not mean the user's reasoning is wrong —
  it means there may be a blind spot worth examining.
"""

from __future__ import annotations

import re


# ─── Cognitive Bias Catalog ──────────────────────────────────────────────

COGNITIVE_BIASES: dict[str, dict] = {
    "confirmation_bias": {
        "name": "Confirmation Bias",
        "description": (
            "Tendency to search for, interpret, and recall information "
            "that confirms pre-existing beliefs."
        ),
        "keywords": [
            "i knew it", "proves my point", "as i expected",
            "i always thought", "confirms what i", "just as i said",
            "this supports my", "see i was right", "told you so",
            "exactly what i predicted",
        ],
        "source": "Kahneman & Tversky, heuristics and biases research",
    },
    "anchoring_bias": {
        "name": "Anchoring Bias",
        "description": (
            "Over-reliance on the first piece of information encountered "
            "when making decisions."
        ),
        "keywords": [
            "first impression", "initially i thought", "my first instinct",
            "the original price", "starting point", "baseline was",
            "originally it was", "compared to the first",
        ],
        "source": "Tversky & Kahneman (1974)",
    },
    "sunk_cost_fallacy": {
        "name": "Sunk Cost Fallacy",
        "description": (
            "Continuing a behaviour or endeavour because of previously "
            "invested resources rather than future value."
        ),
        "keywords": [
            "already invested", "too much time", "come this far",
            "can't give up now", "already spent", "wasted if i stop",
            "too late to quit", "put so much into", "after all the effort",
            "already committed",
        ],
        "source": "Arkes & Blumer (1985)",
    },
    "availability_heuristic": {
        "name": "Availability Heuristic",
        "description": (
            "Overestimating the likelihood of events that come easily to mind, "
            "often because they are recent or emotionally vivid."
        ),
        "keywords": [
            "i just saw", "happened recently", "heard about someone",
            "it's everywhere", "so many people", "everyone is",
            "in the news", "i keep seeing", "all the time",
        ],
        "source": "Tversky & Kahneman (1973)",
    },
    "dunning_kruger_effect": {
        "name": "Dunning-Kruger Effect",
        "description": (
            "Overestimating one's competence in areas where one has "
            "limited knowledge or experience."
        ),
        "keywords": [
            "how hard can it be", "i could do that easily",
            "it's not that complicated", "anyone could",
            "simple enough", "obvious solution", "i don't need help",
            "i already know everything",
        ],
        "source": "Kruger & Dunning (1999)",
    },
    "bandwagon_effect": {
        "name": "Bandwagon Effect",
        "description": (
            "Adopting beliefs or behaviours because many others do so."
        ),
        "keywords": [
            "everyone is doing", "most people think", "the trend is",
            "popular opinion", "majority believes", "going with the crowd",
            "nobody else is worried", "everyone agrees",
        ],
        "source": "Leibenstein (1950)",
    },
    "status_quo_bias": {
        "name": "Status Quo Bias",
        "description": (
            "Preference for the current state of affairs, even when "
            "change would be beneficial."
        ),
        "keywords": [
            "why change", "it's always been", "worked before",
            "if it ain't broke", "comfortable with", "used to this",
            "no need to change", "things are fine", "better the devil you know",
        ],
        "source": "Samuelson & Zeckhauser (1988)",
    },
    "framing_effect": {
        "name": "Framing Effect",
        "description": (
            "Drawing different conclusions from the same information "
            "depending on how it is presented."
        ),
        "keywords": [
            "depends on how you look", "way it was presented",
            "sounds better when", "the way they put it",
            "phrased differently", "framed as", "spin on it",
        ],
        "source": "Tversky & Kahneman (1981)",
    },
    "negativity_bias": {
        "name": "Negativity Bias",
        "description": (
            "Giving more weight to negative experiences or information "
            "than positive ones of equal magnitude."
        ),
        "keywords": [
            "worst case", "what could go wrong", "the problem is",
            "everything is terrible", "nothing works", "always bad",
            "can't see anything good", "only see the negative",
            "doomed", "never going to work",
        ],
        "source": "Baumeister et al. (2001)",
    },
    "optimism_bias": {
        "name": "Optimism Bias",
        "description": (
            "Believing that negative events are less likely to happen "
            "to oneself than to others."
        ),
        "keywords": [
            "that won't happen to me", "i'm different",
            "it'll work out", "nothing bad will happen",
            "i'm lucky", "can't fail", "guaranteed success",
            "no risk for me",
        ],
        "source": "Sharot (2011)",
    },
    "hindsight_bias": {
        "name": "Hindsight Bias",
        "description": (
            "Believing, after an event, that one would have predicted "
            "or expected the outcome."
        ),
        "keywords": [
            "i knew it all along", "saw it coming", "should have known",
            "was obvious", "predictable", "could have told you",
            "everyone knew", "hindsight",
        ],
        "source": "Fischhoff (1975)",
    },
    "halo_effect": {
        "name": "Halo Effect",
        "description": (
            "Letting an overall positive impression of a person, brand, "
            "or product influence judgements about their specific attributes."
        ),
        "keywords": [
            "they're great so", "can do no wrong", "everything they do is",
            "because they're successful", "trust them completely",
            "amazing at everything", "if they say so",
        ],
        "source": "Thorndike (1920)",
    },
    "loss_aversion": {
        "name": "Loss Aversion",
        "description": (
            "Feeling losses more intensely than equivalent gains, "
            "leading to risk-averse behaviour."
        ),
        "keywords": [
            "can't afford to lose", "don't want to risk",
            "what if i lose", "scared of losing", "too much to lose",
            "protect what i have", "losing is worse", "rather not risk",
        ],
        "source": "Kahneman & Tversky (1979, Prospect Theory)",
    },
    "recency_bias": {
        "name": "Recency Bias",
        "description": (
            "Placing disproportionate weight on recent events or data "
            "while underweighting historical patterns."
        ),
        "keywords": [
            "just happened", "lately", "recently",
            "last week", "past few days", "this morning",
            "just yesterday", "most recent",
        ],
        "source": "Serial position effect research",
    },
    "attribution_error": {
        "name": "Fundamental Attribution Error",
        "description": (
            "Attributing others' behaviour to their character while "
            "attributing one's own behaviour to circumstances."
        ),
        "keywords": [
            "they're just", "that's who they are", "they always",
            "typical of them", "it's their nature", "they chose to",
            "because they're lazy", "they don't care",
        ],
        "source": "Ross (1977)",
    },
    "planning_fallacy": {
        "name": "Planning Fallacy",
        "description": (
            "Underestimating the time, costs, and risks of future actions "
            "while overestimating their benefits."
        ),
        "keywords": [
            "should only take", "quick project", "won't take long",
            "easy to do", "just a few days", "be done in no time",
            "straightforward", "piece of cake",
        ],
        "source": "Kahneman & Tversky (1979)",
    },
    "survivorship_bias": {
        "name": "Survivorship Bias",
        "description": (
            "Focusing on successful examples while overlooking failures, "
            "leading to false conclusions about what causes success."
        ),
        "keywords": [
            "look at the successful", "they made it so",
            "worked for them", "follow their example",
            "if they can", "success stories show",
            "the winners all", "successful people",
        ],
        "source": "Wald (1943) — WWII aircraft survivorship analysis",
    },
    "authority_bias": {
        "name": "Authority Bias",
        "description": (
            "Placing excessive trust in the opinions of authority figures "
            "regardless of the domain or evidence."
        ),
        "keywords": [
            "the expert said", "according to the authority",
            "doctor recommended", "professor says", "boss told me",
            "because they're the expert", "authority on this",
        ],
        "source": "Milgram (1963)",
    },
    "choice_overload": {
        "name": "Choice Overload",
        "description": (
            "Difficulty making a decision when presented with too many "
            "options, leading to decision fatigue or avoidance."
        ),
        "keywords": [
            "too many options", "can't decide", "overwhelmed by choices",
            "so many possibilities", "paralysed by", "don't know which",
            "too much to choose", "decision fatigue",
        ],
        "source": "Iyengar & Lepper (2000)",
    },
    "zero_risk_bias": {
        "name": "Zero-Risk Bias",
        "description": (
            "Preferring to eliminate a small risk entirely rather than "
            "achieving a larger overall risk reduction."
        ),
        "keywords": [
            "completely safe", "zero risk", "no risk at all",
            "100% guaranteed", "totally eliminate", "absolutely certain",
            "no chance of failure", "risk free",
        ],
        "source": "Baron et al. (1993)",
    },
}


# ─── Detection ───────────────────────────────────────────────────────────


def detect_biases(reasoning_text: str) -> list[dict]:
    """Identify potential cognitive biases in a piece of reasoning text.

    Uses keyword/phrase pattern matching against the COGNITIVE_BIASES
    catalog. This is a reflective aid — detection of a pattern does NOT
    mean the reasoning is invalid, only that a blind spot may be present.

    Args:
        reasoning_text: Free-text reasoning to analyse.

    Returns:
        List of dicts, each with:
            - bias_type: key from COGNITIVE_BIASES
            - bias_name: human-readable name
            - description: what the bias is
            - matched_phrases: which keywords triggered detection
            - confidence: rough confidence based on number of matches
            - source: academic attribution
    """
    if not reasoning_text or not reasoning_text.strip():
        return []

    text_lower = reasoning_text.lower()
    detected: list[dict] = []

    for bias_key, bias_info in COGNITIVE_BIASES.items():
        matched_phrases = []
        for keyword in bias_info["keywords"]:
            # Use word-boundary-aware matching for short keywords
            pattern = re.escape(keyword)
            if re.search(pattern, text_lower):
                matched_phrases.append(keyword)

        if matched_phrases:
            # Confidence: more matches = higher confidence, capped at 1.0
            confidence = min(len(matched_phrases) / 3.0, 1.0)
            confidence = round(confidence, 2)

            detected.append({
                "bias_type": bias_key,
                "bias_name": bias_info["name"],
                "description": bias_info["description"],
                "matched_phrases": matched_phrases,
                "confidence": confidence,
                "source": bias_info["source"],
            })

    # Sort by confidence descending
    detected.sort(key=lambda x: x["confidence"], reverse=True)

    return detected


# ─── Debiasing Strategies ────────────────────────────────────────────────

_DEBIASING_STRATEGIES: dict[str, dict] = {
    "confirmation_bias": {
        "strategies": [
            "Actively seek disconfirming evidence before concluding.",
            "Ask: 'What would change my mind?'",
            "Consult someone who holds the opposite view.",
            "Use a pre-mortem: imagine the decision failed and work backwards.",
        ],
        "reframe": (
            "Your existing beliefs may have merit, but testing them against "
            "counter-evidence strengthens your position regardless of the outcome."
        ),
    },
    "anchoring_bias": {
        "strategies": [
            "Generate your own estimate before looking at external anchors.",
            "Consider multiple reference points, not just the first one.",
            "Ask: 'Would I reach the same conclusion with a different starting point?'",
        ],
        "reframe": (
            "First impressions are data, not destiny. Expanding your reference "
            "points leads to more calibrated judgements."
        ),
    },
    "sunk_cost_fallacy": {
        "strategies": [
            "Ask: 'If I were starting fresh today, would I make this same choice?'",
            "Separate past investment from future value.",
            "Set clear exit criteria before beginning any project.",
            "Reframe quitting as 'reallocating resources to better opportunities'.",
        ],
        "reframe": (
            "Honouring past effort does not require continuing down an "
            "unproductive path. Pivoting is a sign of adaptive intelligence."
        ),
    },
    "availability_heuristic": {
        "strategies": [
            "Look up base rates and actual statistics before estimating probability.",
            "Ask: 'Am I judging frequency by what comes to mind most easily?'",
            "Consider whether recent or vivid events are distorting your estimates.",
        ],
        "reframe": (
            "Vivid examples grab attention, but patterns emerge from data. "
            "Checking the numbers empowers more grounded decisions."
        ),
    },
    "dunning_kruger_effect": {
        "strategies": [
            "Seek feedback from people with more experience in the domain.",
            "List what you don't know before listing what you do.",
            "Try to explain the topic in detail — gaps become visible.",
        ],
        "reframe": (
            "Recognising the limits of your knowledge is a strength. "
            "Experts consistently report feeling less certain, not more."
        ),
    },
    "bandwagon_effect": {
        "strategies": [
            "Evaluate the evidence independently before checking popular opinion.",
            "Ask: 'Would I believe this if no one else did?'",
            "Look for base-rate data rather than anecdotal majority claims.",
        ],
        "reframe": (
            "Popularity is information, not proof. Your independent evaluation "
            "adds value to any collective decision."
        ),
    },
    "status_quo_bias": {
        "strategies": [
            "Imagine you don't currently have the thing — would you choose it?",
            "List the hidden costs of not changing.",
            "Run a small experiment or pilot before committing fully.",
        ],
        "reframe": (
            "Stability has value, but so does growth. Evaluating the status quo "
            "as one option among many leads to better-informed choices."
        ),
    },
    "framing_effect": {
        "strategies": [
            "Restate the problem in multiple frames (gains vs. losses, percentages vs. absolutes).",
            "Ask: 'Would my decision change if the information were presented differently?'",
            "Focus on absolute outcomes rather than relative framing.",
        ],
        "reframe": (
            "Recognising that framing influences you is the first step to "
            "seeing through it. Re-framing is a perspective superpower."
        ),
    },
    "negativity_bias": {
        "strategies": [
            "For every risk identified, list one comparable opportunity.",
            "Ask: 'Am I giving negative information more weight than it deserves?'",
            "Use structured pros/cons analysis to balance perspective.",
        ],
        "reframe": (
            "Caution is valuable, but over-weighting negatives can lead to "
            "paralysis. Balance the picture to make empowered decisions."
        ),
    },
    "optimism_bias": {
        "strategies": [
            "Use a pre-mortem: imagine the plan failed and identify likely causes.",
            "Research base rates for similar endeavours.",
            "Build contingency plans for realistic downside scenarios.",
        ],
        "reframe": (
            "Optimism fuels action, and tempering it with preparation makes "
            "success more sustainable."
        ),
    },
    "hindsight_bias": {
        "strategies": [
            "Record predictions before outcomes are known.",
            "Ask: 'What evidence did I actually have at the time?'",
            "Review decision logs rather than relying on memory.",
        ],
        "reframe": (
            "Hindsight clarity is an illusion. Good decisions are evaluated "
            "by the process used, not just the outcome."
        ),
    },
    "halo_effect": {
        "strategies": [
            "Evaluate specific attributes independently of overall impression.",
            "Seek evidence for each claim separately.",
            "Ask: 'Would I believe this if it came from someone I didn't admire?'",
        ],
        "reframe": (
            "Admiration is earned, but it does not transfer across domains. "
            "Evaluating specifics honours both the person and the truth."
        ),
    },
    "loss_aversion": {
        "strategies": [
            "Reframe potential losses as the cost of a learning opportunity.",
            "Calculate the expected value including both upside and downside.",
            "Ask: 'Am I avoiding this because of potential loss or actual evidence?'",
        ],
        "reframe": (
            "The pain of loss is real, but risk-avoidance has its own cost — "
            "missed opportunities. Balanced analysis helps you decide when risk is worthwhile."
        ),
    },
    "recency_bias": {
        "strategies": [
            "Zoom out to longer time horizons before drawing conclusions.",
            "Weight recent and historical data equally in your analysis.",
            "Ask: 'Would I reach the same conclusion using data from a year ago?'",
        ],
        "reframe": (
            "Recent events are vivid, but patterns reveal themselves over "
            "longer time frames. Expanding the window strengthens your view."
        ),
    },
    "attribution_error": {
        "strategies": [
            "Consider situational factors that may explain others' behaviour.",
            "Ask: 'What circumstances might lead me to act the same way?'",
            "Practice perspective-taking before judging character.",
        ],
        "reframe": (
            "Behaviour is shaped by context as much as character. Considering "
            "circumstances leads to more accurate and compassionate understanding."
        ),
    },
    "planning_fallacy": {
        "strategies": [
            "Use reference class forecasting: how long did similar projects actually take?",
            "Add a buffer of 50-100% to your initial time estimate.",
            "Break projects into smaller tasks and estimate each independently.",
        ],
        "reframe": (
            "Underestimating complexity is human. Building in buffers is not "
            "pessimism — it is experienced planning."
        ),
    },
    "survivorship_bias": {
        "strategies": [
            "Actively research failures, not just successes.",
            "Ask: 'How many tried this and didn't succeed?'",
            "Look for selection effects in the data you're considering.",
        ],
        "reframe": (
            "Success stories are inspiring, but learning from failures provides "
            "more actionable information. Both perspectives matter."
        ),
    },
    "authority_bias": {
        "strategies": [
            "Check whether the authority's expertise applies to this specific domain.",
            "Look for independent sources that corroborate or challenge the claim.",
            "Ask: 'What is the evidence, separate from who said it?'",
        ],
        "reframe": (
            "Expertise is valuable, but critical evaluation of claims — "
            "regardless of source — is the foundation of sound judgement."
        ),
    },
    "choice_overload": {
        "strategies": [
            "Set decision criteria before reviewing options.",
            "Eliminate options that don't meet minimum thresholds first.",
            "Limit yourself to comparing your top 3 options in detail.",
            "Set a decision deadline to prevent indefinite deliberation.",
        ],
        "reframe": (
            "Having many options is a sign of abundance. Structured evaluation "
            "transforms overwhelm into clarity."
        ),
    },
    "zero_risk_bias": {
        "strategies": [
            "Compare total risk reduction across options, not just whether one risk reaches zero.",
            "Ask: 'Am I paying a premium for certainty that isn't worth the cost?'",
            "Accept that all decisions carry some residual risk.",
        ],
        "reframe": (
            "Perfect safety is rarely achievable or efficient. Reducing the "
            "most significant risks first usually produces better outcomes."
        ),
    },
}


def suggest_debiasing(bias_type: str) -> dict:
    """Return debiasing strategies for a given bias type.

    Args:
        bias_type: Key from COGNITIVE_BIASES (e.g., 'confirmation_bias').

    Returns:
        Dict with:
            - bias_type: the input key
            - bias_name: human-readable name
            - strategies: list of actionable debiasing strategies
            - reframe: a constructive reframe of the bias pattern
            - methodology: attribution string

    Raises:
        ValueError: If bias_type is not in the catalog.
    """
    if bias_type not in COGNITIVE_BIASES:
        raise ValueError(
            f"Unknown bias type '{bias_type}'. "
            f"Valid types: {sorted(COGNITIVE_BIASES.keys())}"
        )

    bias_info = COGNITIVE_BIASES[bias_type]
    debiasing = _DEBIASING_STRATEGIES.get(bias_type, {})

    return {
        "bias_type": bias_type,
        "bias_name": bias_info["name"],
        "strategies": debiasing.get("strategies", []),
        "reframe": debiasing.get(
            "reframe",
            "Consider examining this pattern from multiple angles to strengthen your reasoning.",
        ),
        "methodology": (
            "Debiasing strategies drawn from cognitive psychology research, "
            "primarily Kahneman & Tversky's heuristics and biases programme "
            "and related work. Strategies are presented as reflective aids, "
            "not prescriptions."
        ),
    }

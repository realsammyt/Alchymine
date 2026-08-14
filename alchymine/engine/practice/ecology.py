"""The deterministic ecology recommender.

A pure function of (registry, the user's practice-log rows, ecology
state, ``now``). No LLM, no network, no RNG, not even a seeded one:
"why am I seeing this?" has to be answerable from data the user can see,
and a seed that resets on process restart makes it unanswerable. Variety
comes from the log changing, which is the honest source.

``now`` is injected rather than read, so a test pins the clock without
patching anything.

The shape of the work, in the order this module performs it:

1. **Eligibility** (design section 5.1) narrows every mounted practice
   to the ones that are offerable today.
2. **Scoring** (5.2) gives each survivor four terms in [0, 1], summed
   with configured weights.
3. **Tie-breaking** (5.4) puts the survivors in a total order, so the
   output is a pure function of the inputs.
4. **Selection** (5.3) round-robins across purposes in ascending share,
   which is what stops a plain top-N returning five practices of one
   kind.
5. **The stable-day rule** (5.6) replays yesterday's answer when the day
   and the mounted packs have not changed, so completing one practice at
   9am does not reshuffle the other four at 9:05.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import Any

from .loader import PracticeRegistry
from .purposes import PURPOSE_ORDER
from .schema import PracticeDefinition

logger = logging.getLogger(__name__)

# The protocol's three slots. Position matters: a practice's three
# ``daily_prompts`` map onto these in order, which is what turns slot
# assignment from an editorial judgement into a schema constraint.
PROTOCOL_SLOTS: tuple[str, ...] = ("morning", "day", "evening")

# Fewer than 3 is not a protocol, more than 7 is a to-do list. The
# column comment on ``ecology_state.protocol_size`` says the same; this
# is where it is enforced, because a stored 99 must not become a 99-item
# protocol on the strength of a bad write.
PROTOCOL_SIZE_MIN = 3
PROTOCOL_SIZE_MAX = 7

# How far the four weights may drift from 1.0 before they are normalized
# and the drift is logged.
WEIGHT_SUM_TOLERANCE = 0.01

# Scores are quantized before they enter the sort key. Two practices
# whose terms are mathematically equal produce bit-identical floats here,
# but a future term that does not could separate them by 1e-17 and
# silently bypass the documented tie-break chain. Rounding keeps the
# chain in charge of ties.
_SCORE_PRECISION = 9

# Stand-in for "never completed" in the sort key, so a practice with no
# completions sorts as the stalest thing there is.
_NEVER_COMPLETED_DAYS = 10**9

# Bumped whenever the stored payload shape changes. An envelope this
# build cannot read is recomputed rather than raised: a user whose stored
# row predates a deploy gets a fresh protocol, not a 500.
ENVELOPE_VERSION = 1

# Every reason string this module can emit, keyed by the id that ships
# alongside it so the frontend can style on the id rather than parse the
# prose. Draft copy, pending sign-off.
REASON_TEMPLATES: Mapping[str, str] = {
    "balance": "You have not logged much {purpose} practice recently.",
    "staleness": "It has been {days} {day_word} since you last did this one.",
    "never_practiced": "You have not tried this one yet.",
    "progression": "This follows on from {prerequisite}.",
    "featured": "This is a suggested starting point.",
}


# ─── Inputs ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PracticeLogRow:
    """The plaintext columns of one ``practice_log`` row.

    Deliberately not the ORM model. The recommender reads five columns
    and none of them is user-authored text, so the encrypted
    ``reflection`` and ``self_check_response`` never come near this code
    or the query that feeds it.

    ``day_key`` rather than ``occurred_at`` carries every date decision
    here: it is the user's *local* calendar day, so "days since you last
    did this" means what the user means by it, in every timezone.
    """

    pack_id: str
    practice_slug: str
    primary_purpose: str
    status: str
    day_key: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.pack_id, self.practice_slug)


@dataclass(frozen=True, slots=True)
class EcologyStateInput:
    """The per-user recommender state, as the engine reads it.

    ``last_recommended_at`` is deliberately absent. It is a UTC instant
    and the stable-day rule compares *local* days, so the day the last
    protocol belonged to is carried inside the envelope instead. The
    column is still written, for operators reading the table.
    """

    protocol_size: int = PROTOCOL_SIZE_MAX - 2
    active_pack_ids: tuple[str, ...] | None = None
    rotation_cursor: int = 0
    last_recommendation: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EcologySettings:
    """Weights and windows, injected so a test does not read the environment."""

    weight_balance: float = 0.40
    weight_staleness: float = 0.30
    weight_progression: float = 0.20
    weight_featured: float = 0.10
    staleness_full_days: int = 14
    balance_window_days: int = 28
    decline_threshold: int = 3
    protocol_default_size: int = 5


def default_ecology_settings() -> EcologySettings:
    """Build settings from the application configuration."""
    from alchymine.config import get_settings

    settings = get_settings()
    return EcologySettings(
        weight_balance=settings.practice_weight_balance,
        weight_staleness=settings.practice_weight_staleness,
        weight_progression=settings.practice_weight_progression,
        weight_featured=settings.practice_weight_featured,
        staleness_full_days=settings.practice_staleness_full_days,
        balance_window_days=settings.practice_balance_window_days,
        decline_threshold=settings.practice_decline_threshold,
        protocol_default_size=settings.practice_protocol_default_size,
    )


# ─── Outputs ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ScoredPractice:
    """One eligible practice with its four terms and its reason.

    The terms are the raw [0, 1] values, not the weighted contributions,
    so a test can assert on the term without knowing the weighting.
    """

    pack_id: str
    practice: PracticeDefinition
    purpose: str
    balance_term: float
    staleness_term: float
    progression_term: float
    featured_term: float
    score: float
    purpose_share: float
    days_since_last_completion: int | None
    reason: str
    reason_template: str


@dataclass(frozen=True, slots=True)
class Recommendation:
    """What one call to :func:`recommend_today` produced.

    ``payload`` is the wire shape. ``envelope`` is what belongs in
    ``ecology_state.last_recommendation``: the payload plus the two facts
    the stable-day rule needs to decide whether it is still current.
    """

    payload: dict[str, Any]
    envelope: dict[str, Any]
    rotation_cursor: int
    recomputed: bool


@dataclass(frozen=True, slots=True)
class PracticeSummary:
    """The rhythm figures behind ``GET /practice/summary``."""

    days_practiced_last_7: int
    last_7: list[bool] = field(default_factory=list)
    by_purpose: dict[str, int] = field(default_factory=dict)
    total_completed: int = 0


# ─── Weights ────────────────────────────────────────────────────────────


@lru_cache(maxsize=32)
def _resolve_weights(
    balance: float, staleness: float, progression: float, featured: float
) -> tuple[float, float, float, float]:
    """Return the four weights, normalized if they do not sum to 1.0.

    A typo in an env var should not take the app down, which is the same
    posture ``get_plan_allowance_cents()`` takes. It should be loud
    though, so the drift is logged at ERROR.

    The cache is what makes "logged once" true: a given weighting logs on
    its first use and never again, rather than once per request.
    """
    total = balance + staleness + progression + featured

    if abs(total - 1.0) <= WEIGHT_SUM_TOLERANCE:
        return (balance, staleness, progression, featured)

    if total <= 0:
        logger.error(
            "Practice recommender weights sum to %.4f, which cannot be normalized. "
            "Falling back to the defaults (0.40/0.30/0.20/0.10). Check "
            "PRACTICE_WEIGHT_BALANCE, PRACTICE_WEIGHT_STALENESS, "
            "PRACTICE_WEIGHT_PROGRESSION and PRACTICE_WEIGHT_FEATURED.",
            total,
        )
        return (0.40, 0.30, 0.20, 0.10)

    logger.error(
        "Practice recommender weights sum to %.4f rather than 1.0 "
        "(balance=%.4f staleness=%.4f progression=%.4f featured=%.4f). "
        "Normalizing by the sum so the ratios are preserved. Check the "
        "PRACTICE_WEIGHT_* environment variables.",
        total,
        balance,
        staleness,
        progression,
        featured,
    )
    return (balance / total, staleness / total, progression / total, featured / total)


# ─── Log aggregation ────────────────────────────────────────────────────


def _parse_day(value: str) -> date | None:
    """Parse a ``day_key``, or return ``None`` if it is not one.

    Every row reaching here was written through a route that validates
    the shape, so ``None`` means a row was written by something else.
    Skipping it keeps one malformed row from taking a user's whole
    protocol down.
    """
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning("Ignoring practice_log row with unparseable day_key %r", value)
        return None


@dataclass(frozen=True, slots=True)
class _LogFacts:
    """Everything the scorer needs, derived from the rows in one pass."""

    completed_today: frozenset[tuple[str, str]]
    last_completion: Mapping[tuple[str, str], date]
    window_completions_by_purpose: Mapping[str, int]
    window_completions_total: int
    window_skips: Mapping[tuple[str, str], int]
    window_completions: Mapping[tuple[str, str], int]


def _gather(log: Sequence[PracticeLogRow], *, today: date, window_days: int) -> _LogFacts:
    """Aggregate *log* into the counts eligibility and scoring read.

    The window is *window_days* calendar days ending today, inclusive, so
    a 28-day window covers today and the 27 days before it.
    """
    window_start = today - timedelta(days=max(window_days, 1) - 1)

    completed_today: set[tuple[str, str]] = set()
    last_completion: dict[tuple[str, str], date] = {}
    by_purpose: Counter[str] = Counter()
    window_skips: Counter[tuple[str, str]] = Counter()
    window_completions: Counter[tuple[str, str]] = Counter()
    window_total = 0

    for row in log:
        day = _parse_day(row.day_key)
        if day is None:
            continue

        in_window = window_start <= day <= today

        if row.status == "completed":
            previous = last_completion.get(row.key)
            if previous is None or day > previous:
                last_completion[row.key] = day
            if day == today:
                completed_today.add(row.key)
            if in_window:
                by_purpose[row.primary_purpose] += 1
                window_completions[row.key] += 1
                window_total += 1
        elif row.status == "skipped" and in_window:
            window_skips[row.key] += 1

    return _LogFacts(
        completed_today=frozenset(completed_today),
        last_completion=last_completion,
        window_completions_by_purpose=by_purpose,
        window_completions_total=window_total,
        window_skips=window_skips,
        window_completions=window_completions,
    )


# ─── Eligibility and scoring ────────────────────────────────────────────


def _is_eligible(
    pack_id: str,
    practice: PracticeDefinition,
    facts: _LogFacts,
    *,
    decline_threshold: int,
) -> bool:
    """Apply the four eligibility rules of design section 5.1."""
    key = (pack_id, practice.slug)

    # Rule 2: every prerequisite completed at least once, ever. This is
    # the invariant the whole builds_on graph exists to protect.
    for prerequisite in practice.builds_on:
        if (pack_id, prerequisite) not in facts.last_completion:
            return False

    # Rule 3: not already completed today. A *skip* does not close a
    # practice for the day; only finishing it does.
    if key in facts.completed_today:
        return False

    # Rule 4: declined. Repeated skips with nothing completed in the same
    # window means the user has answered, so stop asking for a while.
    if (
        facts.window_skips.get(key, 0) >= decline_threshold
        and facts.window_completions.get(key, 0) == 0
    ):
        return False

    return True


def _reason_for(
    practice: PracticeDefinition,
    *,
    purpose: str,
    contributions: Sequence[tuple[str, float]],
    days_since: int | None,
    has_history: bool,
    prerequisite_title: str | None,
) -> tuple[str, str]:
    """Return ``(reason, template_id)`` for one scored practice.

    The reason names whichever term contributed most, which is what
    makes it answerable: the user can see the same fact the scorer saw.
    A term only gets to explain a practice when it actually says
    something about it, so three guards apply.

    *balance* needs history. With an empty log every share is zero by
    construction rather than by neglect, so "you have not practiced this
    much" would be describing the absence of data, not a pattern.

    *progression* needs a prerequisite. A root has nothing to follow on
    from.

    *staleness* needs a previous completion. A practice you have never
    done scores maximum staleness by convention, not by evidence, so it
    does not get to call itself stale. Something more specific explains
    it, and when nothing does, the fallback says plainly that you have
    not tried it yet.
    """
    for name, contribution in contributions:
        if contribution <= 0:
            continue
        if name == "balance" and has_history:
            return (REASON_TEMPLATES["balance"].format(purpose=purpose), "balance")
        if name == "staleness" and days_since is not None:
            return (
                REASON_TEMPLATES["staleness"].format(
                    days=days_since, day_word="day" if days_since == 1 else "days"
                ),
                "staleness",
            )
        if name == "progression" and prerequisite_title is not None:
            return (
                REASON_TEMPLATES["progression"].format(prerequisite=prerequisite_title),
                "progression",
            )
        if name == "featured" and practice.featured:
            return (REASON_TEMPLATES["featured"], "featured")

    if days_since is not None:
        return (
            REASON_TEMPLATES["staleness"].format(
                days=days_since, day_word="day" if days_since == 1 else "days"
            ),
            "staleness",
        )
    return (REASON_TEMPLATES["never_practiced"], "never_practiced")


def rank_practices(
    registry: PracticeRegistry,
    log: Sequence[PracticeLogRow],
    state: EcologyStateInput,
    *,
    today: str,
    settings: EcologySettings | None = None,
) -> list[ScoredPractice]:
    """Score every eligible practice and return them in total order.

    The ordering is the tie-break chain of design section 5.4:
    score desc, purpose share asc, days since last completion desc,
    ``order`` asc, then ``(pack_id, slug)``. The last key is total, so
    the result is a pure function of the arguments.
    """
    settings = settings or default_ecology_settings()
    today_date = date.fromisoformat(today)
    return _rank(
        registry,
        state,
        _gather(log, today=today_date, window_days=settings.balance_window_days),
        today_date=today_date,
        settings=settings,
    )


def _rank(
    registry: PracticeRegistry,
    state: EcologyStateInput,
    facts: _LogFacts,
    *,
    today_date: date,
    settings: EcologySettings,
) -> list[ScoredPractice]:
    """Score and order, given facts already aggregated.

    Split out so :func:`recommend_today` aggregates the log once rather
    than once for the ranking and again for the purpose running order.
    """
    w_balance, w_staleness, w_progression, w_featured = _resolve_weights(
        settings.weight_balance,
        settings.weight_staleness,
        settings.weight_progression,
        settings.weight_featured,
    )

    denominator = max(1, facts.window_completions_total)
    has_history = facts.window_completions_total > 0
    full_days = max(1, settings.staleness_full_days)
    active = state.active_pack_ids

    scored: list[ScoredPractice] = []
    for pack_id, practice in registry.list_practices():
        # Rule 1: the pack is mounted and the user has it switched on.
        if active is not None and pack_id not in active:
            continue
        if not _is_eligible(pack_id, practice, facts, decline_threshold=settings.decline_threshold):
            continue

        purpose = practice.primary_purpose
        share = facts.window_completions_by_purpose.get(purpose, 0) / denominator

        last = facts.last_completion.get((pack_id, practice.slug))
        # Floored at zero. Every day_key is client-supplied, so a user who
        # crosses a date line or whose clock runs fast can leave a row
        # dated after the day being computed. Zero is the honest reading
        # of "you did this already"; a negative count would render as
        # "-1 days" and subtract from the staleness term.
        days_since = max(0, (today_date - last).days) if last is not None else None

        balance_term = 1.0 - share
        staleness_term = 1.0 if days_since is None else min(1.0, days_since / full_days)
        # A practice with prerequisites is the unlocked next step in a
        # thread the user already started. Eligibility guarantees they
        # are met, so reaching here means it is genuinely unlocked.
        progression_term = 1.0 if practice.builds_on else 0.5
        featured_term = 1.0 if practice.featured else 0.0

        contributions = [
            ("balance", w_balance * balance_term),
            ("staleness", w_staleness * staleness_term),
            ("progression", w_progression * progression_term),
            ("featured", w_featured * featured_term),
        ]
        score = sum(value for _, value in contributions)
        # Named, not slugged: the reason is prose the user reads, and the
        # loader guarantees a within-pack edge resolves.
        prerequisite_title = (
            registry.get(pack_id, practice.builds_on[0]).title if practice.builds_on else None
        )
        reason, template_id = _reason_for(
            practice,
            purpose=purpose,
            # Ties between equal contributions fall to this fixed order,
            # so the emitted reason is as deterministic as the ranking.
            contributions=sorted(contributions, key=lambda pair: -pair[1]),
            days_since=days_since,
            has_history=has_history,
            prerequisite_title=prerequisite_title,
        )

        scored.append(
            ScoredPractice(
                pack_id=pack_id,
                practice=practice,
                purpose=purpose,
                balance_term=balance_term,
                staleness_term=staleness_term,
                progression_term=progression_term,
                featured_term=featured_term,
                score=score,
                purpose_share=share,
                days_since_last_completion=days_since,
                reason=reason,
                reason_template=template_id,
            )
        )

    scored.sort(key=_rank_key)
    return scored


def _rank_key(scored: ScoredPractice) -> tuple[float, float, int, int, str, str]:
    days = (
        _NEVER_COMPLETED_DAYS
        if scored.days_since_last_completion is None
        else scored.days_since_last_completion
    )
    return (
        -round(scored.score, _SCORE_PRECISION),
        scored.purpose_share,
        -days,
        scored.practice.order,
        scored.pack_id,
        scored.practice.slug,
    )


# ─── Selection ──────────────────────────────────────────────────────────


def _purpose_running_order(
    facts_by_purpose: Mapping[str, int], total: int, rotation_cursor: int
) -> list[str]:
    """Order the five purposes most-neglected first, then rotate.

    The rotation is what keeps a small protocol from showing the same
    two purposes forever when the shares are level: at N=3 the cursor
    moves which three get picked, day to day.
    """
    denominator = max(1, total)
    ordered = sorted(
        PURPOSE_ORDER,
        key=lambda purpose: (
            facts_by_purpose.get(purpose, 0) / denominator,
            PURPOSE_ORDER.index(purpose),
        ),
    )
    offset = rotation_cursor % len(ordered)
    return ordered[offset:] + ordered[:offset]


def _select(
    scored: Sequence[ScoredPractice], running_order: Sequence[str], size: int
) -> list[ScoredPractice]:
    """Round-robin across purposes until *size* are chosen or the pool empties.

    One practice per purpose per pass, in the running order, then wrap.
    That is what makes the balance invariant hold: with N at least as
    large as the number of purposes that have anything eligible, the
    first pass alone covers every one of them.
    """
    buckets: dict[str, list[ScoredPractice]] = {purpose: [] for purpose in running_order}
    for candidate in scored:
        bucket = buckets.get(candidate.purpose)
        if bucket is not None:
            bucket.append(candidate)

    chosen: list[ScoredPractice] = []
    cursors = dict.fromkeys(running_order, 0)
    while len(chosen) < size:
        took_any = False
        for purpose in running_order:
            index = cursors[purpose]
            bucket = buckets[purpose]
            if index >= len(bucket):
                continue
            chosen.append(bucket[index])
            cursors[purpose] = index + 1
            took_any = True
            if len(chosen) == size:
                return chosen
        if not took_any:
            break
    return chosen


# ─── The stable-day rule ────────────────────────────────────────────────


def compute_pack_fingerprint(
    registry: PracticeRegistry, active_pack_ids: Sequence[str] | None
) -> str:
    """Fingerprint the pack set a recommendation was computed against.

    Covers the pack ids *and* their content versions. A revised pack can
    change what is eligible, so a stored protocol computed against the
    old one is stale for the same reason a removed pack makes it stale.

    An active id naming a pack that is not mounted contributes nothing,
    so unmounting a pack the user opted into is itself a change.
    """
    identity = sorted(
        [manifest.pack_id, manifest.version]
        for manifest in registry.list_packs()
        if active_pack_ids is None or manifest.pack_id in active_pack_ids
    )
    encoded = json.dumps(identity, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:32]


def _replayable_payload(
    stored: Mapping[str, Any] | None, *, day_key: str, fingerprint: str
) -> dict[str, Any] | None:
    """Return the stored payload when it is still current, else ``None``.

    Anything unreadable, from any cause, returns ``None`` and triggers a
    recomputation. A stored envelope is only ever written by this module,
    so a shape this build cannot read means a deploy moved underneath it;
    a fresh protocol is the right answer, not an exception.
    """
    if not isinstance(stored, Mapping):
        return None
    if stored.get("envelope_version") != ENVELOPE_VERSION:
        return None
    if stored.get("day_key") != day_key or stored.get("pack_fingerprint") != fingerprint:
        return None
    payload = stored.get("payload")
    if not isinstance(payload, Mapping):
        return None
    return dict(payload)


# ─── The entry point ────────────────────────────────────────────────────


def recommend_today(
    registry: PracticeRegistry,
    log: Sequence[PracticeLogRow],
    *,
    state: EcologyStateInput,
    now: datetime,
    day_key: str,
    refresh: bool = False,
    settings: EcologySettings | None = None,
) -> Recommendation:
    """Return today's protocol for one user.

    Parameters
    ----------
    registry:
        Every mounted pack. Which of them count is ``state.active_pack_ids``.
    log:
        The user's practice-log rows. Callers pass every completed row
        ever (prerequisites and staleness both reach past the window)
        plus every row inside the balance window.
    state:
        The stored recommender state, including the last emitted envelope.
    now:
        Injected, and the only clock this module reads.
    day_key:
        The user's local calendar day. The server does not derive it: an
        evening practice in Auckland belongs to the Auckland day.
    refresh:
        Recompute even when the stable-day rule would replay.
    """
    settings = settings or default_ecology_settings()
    fingerprint = compute_pack_fingerprint(registry, state.active_pack_ids)

    if not refresh:
        replayed = _replayable_payload(
            state.last_recommendation, day_key=day_key, fingerprint=fingerprint
        )
        if replayed is not None:
            return Recommendation(
                payload=replayed,
                envelope=dict(state.last_recommendation or {}),
                rotation_cursor=state.rotation_cursor,
                recomputed=False,
            )

    size = min(PROTOCOL_SIZE_MAX, max(PROTOCOL_SIZE_MIN, state.protocol_size))
    today_date = date.fromisoformat(day_key)
    facts = _gather(log, today=today_date, window_days=settings.balance_window_days)

    scored = _rank(registry, state, facts, today_date=today_date, settings=settings)
    running_order = _purpose_running_order(
        facts.window_completions_by_purpose,
        facts.window_completions_total,
        state.rotation_cursor,
    )
    chosen = _select(scored, running_order, size)

    payload = _build_payload(chosen, day_key=day_key, now=now, protocol_size=size)
    envelope = {
        "envelope_version": ENVELOPE_VERSION,
        "day_key": day_key,
        "pack_fingerprint": fingerprint,
        "payload": payload,
    }

    return Recommendation(
        payload=payload,
        envelope=envelope,
        # Kept inside the purpose count rather than growing without
        # bound: it is only ever read modulo that count, and a column
        # that climbs forever eventually overflows an Integer.
        rotation_cursor=(state.rotation_cursor + 1) % len(PURPOSE_ORDER),
        recomputed=True,
    )


def _build_payload(
    chosen: Sequence[ScoredPractice], *, day_key: str, now: datetime, protocol_size: int
) -> dict[str, Any]:
    """Render the chosen practices as the wire shape of design section 5.7.

    The three slots hold the same practices in the same order, each with
    that slot's prompt. The protocol is N practices rendered three times,
    not three different protocols, which is why every practice carries
    exactly three ``daily_prompts``.

    The score is deliberately absent. ``reason`` is the user-facing
    answer to "why am I seeing this?", and a number next to it invites
    reading the protocol as a leaderboard.
    """
    items = [
        {
            "pack_id": scored.pack_id,
            "slug": scored.practice.slug,
            "title": scored.practice.title,
            "purpose": scored.purpose,
            "purposes": list(scored.practice.purposes),
            "category": scored.practice.category,
            "duration_minutes": scored.practice.duration_minutes,
            "reason": scored.reason,
            "reason_template": scored.reason_template,
        }
        for scored in chosen
    ]
    slots = {
        slot: [
            {
                "pack_id": scored.pack_id,
                "slug": scored.practice.slug,
                "prompt": scored.practice.daily_prompts[index],
            }
            for scored in chosen
        ]
        for index, slot in enumerate(PROTOCOL_SLOTS)
    }
    return {
        "day_key": day_key,
        "generated_at": now.astimezone(UTC).isoformat(),
        "protocol_size": protocol_size,
        "items": items,
        "slots": slots,
    }


# ─── The rhythm summary ─────────────────────────────────────────────────


def summarize_practice(log: Sequence[PracticeLogRow], *, today: str) -> PracticeSummary:
    """Return the figures behind the rhythm display.

    ``last_7`` is oldest first: index 0 is six days ago and index 6 is
    *today*, so a caller renders it left to right without reversing it.
    A day is marked when at least one practice was completed on it, so
    two completions on one day count once. Only completions count: a
    skip is not a smaller success, it is a different thing.

    ``by_purpose`` and ``total_completed`` are all-time, and
    ``by_purpose`` is zero-filled across all five purposes so the caller
    has one shape rather than a map that grows as the user broadens.
    """
    today_date = date.fromisoformat(today)
    window = [today_date - timedelta(days=offset) for offset in range(6, -1, -1)]
    practiced: set[date] = set()
    by_purpose: dict[str, int] = dict.fromkeys(PURPOSE_ORDER, 0)
    total = 0

    for row in log:
        if row.status != "completed":
            continue
        day = _parse_day(row.day_key)
        if day is None:
            continue
        total += 1
        if row.primary_purpose in by_purpose:
            by_purpose[row.primary_purpose] += 1
        if day in window:
            practiced.add(day)

    last_7 = [day in practiced for day in window]
    return PracticeSummary(
        days_practiced_last_7=sum(last_7),
        last_7=last_7,
        by_purpose=by_purpose,
        total_completed=total,
    )

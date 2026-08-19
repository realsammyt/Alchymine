"""Practice endpoints: the library views, the practice log, the journey.

Auth is required on every route but no plan gate is applied: nothing
here costs money, and gating the retention loop would defeat the loop.
There are no LLM calls on any path in this module.

The registry is built at application startup, so the library handlers
never touch the filesystem. The log handlers read it too, because the
registry is the only thing that knows whether a practice exists and
what capacity it develops.

``GET /journey/timeseries`` lives here rather than in a router of its
own because it reads exactly what this module writes: the practice log,
and the loops closed against it. Nothing else in the app owns that pair,
and a second module reading it would need its own copy of the day-axis
rule the fold depends on.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.api.auth import get_current_user
from alchymine.api.deps import get_db_session
from alchymine.db import repository
from alchymine.db.models import EcologyState, PracticeLogEntry
from alchymine.engine.practice import (
    PackManifest,
    PackNotFoundError,
    PracticeDefinition,
    PracticeNotFoundError,
    PracticeRegistry,
    get_practice_registry,
)
from alchymine.engine.practice.ecology import (
    EcologySettings,
    EcologyStateInput,
    PracticeLogRow,
    Recommendation,
    default_ecology_settings,
    recommend_today,
    summarize_practice,
)
from alchymine.engine.practice.journey import (
    JOURNEY_WINDOW_DEFAULT,
    JOURNEY_WINDOW_MAX,
    JOURNEY_WINDOW_MIN,
    JourneyRow,
    build_journey_series,
    loop_shift_value,
)
from alchymine.engine.practice.purposes import system_for_purpose

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_day_key(value: str) -> str:
    """Reject anything that is not a real ``YYYY-MM-DD`` calendar date.

    The regex alone would let ``2026-13-01`` through, and
    ``date.fromisoformat`` alone would accept ISO week dates like
    ``2026-W33-5``, which are the same length. Both together pin the one
    shape the column is documented to hold.

    The pairing is also load-bearing in a less obvious way: pydantic v2
    compiles the pattern with a Unicode-aware regex engine, so ``\\d``
    matches Arabic-Indic and fullwidth digits; ``fromisoformat`` is
    ASCII-only and is what rejects them. Do not collapse this to one
    check.
    """
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("must be a real calendar date in YYYY-MM-DD form") from exc
    return value


DayKey = Annotated[
    str,
    StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    AfterValidator(_validate_day_key),
]

# The three the log accepts. ``started`` exists so a user who opens a
# practice and stops halfway has somewhere honest to put that.
LogStatus = Literal["completed", "skipped", "started"]

# The protocol's three slots plus the escape hatch for a practice done
# outside the protocol entirely.
ProtocolSlot = Literal["morning", "day", "evening", "unscheduled"]


# ─────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────


class PracticeResponse(BaseModel):
    """A practice plus the two facts that only the registry knows.

    The definition is nested rather than flattened so the wire shape
    cannot drift from the schema: adding a field to
    :class:`PracticeDefinition` surfaces here without a second edit.
    """

    model_config = ConfigDict(frozen=True)

    pack_id: str = Field(..., description="The pack this practice belongs to")
    progression_depth: int = Field(
        ..., description="Longest path from a root in the pack's builds_on graph; a root is 0"
    )
    practice: PracticeDefinition


class PackResponse(BaseModel):
    """A pack manifest, including its license and attribution."""

    model_config = ConfigDict(frozen=True)

    manifest: PackManifest
    practice_count: int


class PracticeLogCreate(BaseModel):
    """A request to log one practice event.

    Note what is absent. There is no ``user_id``: the owner is the
    authenticated subject, never a value the client chooses. There is no
    ``primary_purpose``, ``purposes`` or ``category`` either; those are
    read off the registry definition, so a client cannot file a somatic
    practice under reflection and skew what the recommender sees. Extra
    keys are ignored rather than rejected, so sending them is harmless.
    """

    pack_id: str = Field(..., min_length=1, max_length=64)
    practice_slug: str = Field(..., min_length=1, max_length=64)
    day_key: DayKey = Field(
        ...,
        description="The user's local calendar day, YYYY-MM-DD. Stored exactly as sent.",
    )
    status: LogStatus = "completed"
    protocol_slot: ProtocolSlot | None = None
    occurred_at: datetime | None = Field(
        None, description="When it happened. Defaults to the moment the row is written."
    )
    duration_minutes: int | None = Field(
        None,
        ge=0,
        le=1440,
        description="How long it actually took. A sanity bound, not a rule about practice.",
    )
    reflection: str | None = Field(None, max_length=5000)
    self_check_response: str | None = Field(None, max_length=5000)


class PracticeLogResponse(BaseModel):
    """One practice-log row, returned to its owner.

    ``reflection`` and ``self_check_response`` are encrypted at rest and
    echoed in plaintext here, which is safe because every route that
    builds this model has already scoped the row to the caller.
    """

    id: str
    user_id: str
    pack_id: str
    practice_slug: str
    primary_purpose: str
    purposes: list[str]
    category: str
    status: str
    protocol_slot: str | None
    duration_minutes: int | None
    occurred_at: datetime
    day_key: str
    created_at: datetime | None
    reflection: str | None
    self_check_response: str | None


class PracticeLogListResponse(BaseModel):
    """A page of the caller's own practice log."""

    entries: list[PracticeLogResponse]
    total: int
    page: int
    per_page: int


class IntegrationCreate(BaseModel):
    """A request to close the loop on one logged practice.

    Note what is absent, again. There is no ``user_id`` and no
    ``purpose``: the owner is the authenticated subject and the purpose
    is read off the practice_log row. A client that could name the
    purpose could credit its practice to whichever pillar it liked, and
    the dashboard would show that instead of what happened.

    Everything except ``practice_log_id`` is optional, so a user who
    logs a practice and writes nothing still has a valid loop.
    """

    model_config = ConfigDict(extra="ignore")

    practice_log_id: str = Field(..., min_length=1, max_length=36)
    intention_entry_id: str | None = Field(None, max_length=36)
    reflection_entry_id: str | None = Field(None, max_length=36)
    capacity_delta: int | None = Field(
        None,
        ge=-2,
        le=2,
        description=(
            "The user's own read on whether the capacity moved, -2 to +2. "
            "A self-report, not a measurement, and never required."
        ),
    )
    note: str | None = Field(None, max_length=5000)


class IntegrationResponse(BaseModel):
    """One integration entry, returned to its owner.

    ``note`` is encrypted at rest and echoed in plaintext here, which is
    safe because the only route that builds this model has already
    scoped every id in the request to the caller.
    """

    id: str
    user_id: str
    practice_log_id: str | None
    intention_entry_id: str | None
    reflection_entry_id: str | None
    purpose: str
    capacity_delta: int | None
    note: str | None
    created_at: datetime | None


class ProtocolItem(BaseModel):
    """One practice in today's protocol, with the line that explains it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pack_id: str
    slug: str
    title: str
    summary: str = Field(
        ...,
        description="One line saying what the practice is, so the card is readable "
        "without opening the library",
    )
    purpose: str = Field(..., description="The capacity this develops, for the chip")
    purposes: list[str]
    category: str
    duration_minutes: int
    reason: str = Field(..., description="Why this practice, in one deterministic sentence")
    reason_template: str = Field(
        ...,
        description="The template the reason came from, so the client styles on an id "
        "rather than parsing the prose",
    )


class ProtocolSlotEntry(BaseModel):
    """One practice as it appears in one slot, carrying that slot's prompt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pack_id: str
    slug: str
    prompt: str


class TodayResponse(BaseModel):
    """Today's protocol.

    ``slots`` holds the same practices three times over, once per slot,
    each with that slot's prompt. It is one protocol rendered three
    times, not three protocols, which is why every practice carries
    exactly three ``daily_prompts``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    day_key: str
    generated_at: str
    protocol_size: int
    items: list[ProtocolItem]
    slots: dict[str, list[ProtocolSlotEntry]]


class PracticeSummaryResponse(BaseModel):
    """The rhythm figures, with no counter that resets to zero.

    ``last_7`` is oldest first: index 0 is six days before ``day_key``
    and index 6 is ``day_key`` itself, so a client renders it left to
    right without reversing anything.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    day_key: str
    days_practiced_last_7: int
    last_7: list[bool]
    by_purpose: dict[str, int]
    total_completed: int


class JourneyDayResponse(BaseModel):
    """One column of the journey chart.

    ``average_shift`` is ``null`` rather than 0.0 on a day with no
    closed loops. Zero is a real self-report meaning "nothing moved",
    and a day nobody wrote about is not that.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    day_key: str
    completed: int = Field(..., description="Practices completed on this day")
    purposes: list[str] = Field(
        ..., description="The distinct capacities practiced, in fixed display order"
    )
    loops: int = Field(..., description="Integration loops closed against this day's practices")
    average_shift: float | None = Field(
        None, description="Mean recorded shift for those loops, null when there were none"
    )


class JourneyTotalsResponse(BaseModel):
    """The figures under the chart.

    The first three describe the window. The two anchors do not: they
    reach back through the whole log, because "practicing since March"
    is the line that makes a thirty-day chart mean something and is
    unanswerable from thirty days of rows.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    days_practiced: int
    completed: int
    loops_closed: int
    first_practice_day: str | None = Field(
        None, description="The user's earliest logged practice day, or null if there is none"
    )
    first_loop_day: str | None = Field(
        None, description="The practice day of the earliest closed loop, or null"
    )


class JourneyTimeseriesResponse(BaseModel):
    """The journey series: what the user did, day by day.

    ``days`` is always exactly ``window_days`` long and oldest first, so
    a client renders it left to right without reversing anything and a
    day with nothing on it is a gap rather than a missing column.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    day_key: str = Field(..., description="The window's last day, as the caller sent it")
    start_day: str
    window_days: int
    days: list[JourneyDayResponse]
    by_purpose: dict[str, int] = Field(
        ..., description="Completions per capacity inside the window, zero-filled across all five"
    )
    totals: JourneyTotalsResponse


# ─────────────────────────────────────────────────────────────────────
# Dependency
# ─────────────────────────────────────────────────────────────────────


def registry_dependency() -> PracticeRegistry:
    """FastAPI dependency returning the process-global registry."""
    return get_practice_registry()


def ecology_settings_dependency() -> EcologySettings:
    """FastAPI dependency returning the recommender's weights and windows.

    A dependency rather than a direct read so a test can pin the
    weighting for one route without reaching into the environment.
    """
    return default_ecology_settings()


def _state_input(state: EcologyState) -> EcologyStateInput:
    """Adapt the stored row to what the engine reads.

    ``active_pack_ids`` is a JSON column, so a value that is not a list
    of strings is treated as "no opt-in subset" rather than trusted. The
    closed direction here is *wider*: an unreadable subset should show
    the user their whole library, not an empty protocol.
    """
    active = state.active_pack_ids
    packs = tuple(str(entry) for entry in active) if isinstance(active, list) and active else None
    stored = state.last_recommendation if isinstance(state.last_recommendation, dict) else None
    return EcologyStateInput(
        protocol_size=state.protocol_size,
        active_pack_ids=packs,
        rotation_cursor=state.rotation_cursor,
        last_recommendation=stored,
    )


async def _load_recommender_log(
    session: AsyncSession, user_id: str, *, today: str, settings: EcologySettings
) -> list[PracticeLogRow]:
    """Read the plaintext log columns and adapt them to the engine's row type.

    The mapping lives here rather than in the repository so the ``db``
    package keeps having no dependency on ``engine``.
    """
    window_start = date.fromisoformat(today) - timedelta(
        days=max(settings.balance_window_days, 1) - 1
    )
    rows = await repository.list_recommender_log_rows(
        session, user_id, window_start_day=window_start.isoformat()
    )
    return [
        PracticeLogRow(
            pack_id=row.pack_id,
            practice_slug=row.practice_slug,
            primary_purpose=row.primary_purpose,
            status=row.status,
            day_key=row.day_key,
        )
        for row in rows
    ]


def _recommend(
    registry: PracticeRegistry,
    log: list[PracticeLogRow],
    state: EcologyState,
    *,
    now: datetime,
    today: str,
    refresh: bool,
    settings: EcologySettings,
) -> Recommendation:
    return recommend_today(
        registry,
        log,
        state=_state_input(state),
        now=now,
        day_key=today,
        refresh=refresh,
        settings=settings,
    )


TodayQuery = Annotated[
    DayKey,
    Query(
        description=(
            "The caller's local calendar day, YYYY-MM-DD. Required, and not "
            "derived server-side: the server is in UTC and the user is not, so "
            "an evening practice in Auckland would land on the wrong day."
        )
    ),
]


def _to_response(
    registry: PracticeRegistry, pack_id: str, practice: PracticeDefinition
) -> PracticeResponse:
    return PracticeResponse(
        pack_id=pack_id,
        progression_depth=registry.progression_depth(pack_id, practice.slug),
        practice=practice,
    )


def _resolve_practice(registry: PracticeRegistry, pack_id: str, slug: str) -> PracticeDefinition:
    """Return the definition being logged, or raise a 400 naming the gap.

    A log row pointing at a practice that does not exist is unreadable
    later: nothing can tell you what capacity it developed or what the
    user was actually doing. The registry is the only place that knows,
    so the check happens here rather than at read time.

    400 rather than 404: the route exists and the request reached it.
    What is wrong is the body.
    """
    try:
        return registry.get(pack_id, slug)
    except PackNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No mounted pack has the id '{pack_id}'. "
                "See /api/v1/practices/packs for what is mounted."
            ),
        ) from exc
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Pack '{pack_id}' has no practice '{slug}'. "
                f"See /api/v1/practices?pack_id={pack_id} for what it carries."
            ),
        ) from exc


def _log_to_response(entry: PracticeLogEntry) -> PracticeLogResponse:
    purposes = entry.purposes if isinstance(entry.purposes, list) else []
    return PracticeLogResponse(
        id=entry.id,
        user_id=entry.user_id,
        pack_id=entry.pack_id,
        practice_slug=entry.practice_slug,
        primary_purpose=entry.primary_purpose,
        purposes=purposes,
        category=entry.category,
        status=entry.status,
        protocol_slot=entry.protocol_slot,
        duration_minutes=entry.duration_minutes,
        occurred_at=entry.occurred_at,
        day_key=entry.day_key,
        created_at=entry.created_at,
        reflection=entry.reflection,
        self_check_response=entry.self_check_response,
    )


# ─────────────────────────────────────────────────────────────────────
# Routes
#
# Literal paths are registered before parameterized siblings, so
# /practices/packs cannot be captured by /practices/{pack_id}/{slug}.
# ─────────────────────────────────────────────────────────────────────


@router.get("/practices", response_model=list[PracticeResponse])
async def list_practices(
    purpose: str | None = Query(None, description="Filter by one of the five purposes"),
    category: str | None = Query(None, description="Filter by practice category"),
    pack_id: str | None = Query(None, description="Filter to a single pack"),
    registry: PracticeRegistry = Depends(registry_dependency),
    _user: dict = Depends(get_current_user),
) -> list[PracticeResponse]:
    """List every practice in every mounted pack.

    Filters narrow the result. A value that matches nothing returns an
    empty list rather than an error, so the caller has one shape to
    handle instead of two.
    """
    return [
        _to_response(registry, item_pack_id, practice)
        for item_pack_id, practice in registry.list_practices(
            purpose=purpose, category=category, pack_id=pack_id
        )
    ]


@router.get("/practices/packs", response_model=list[PackResponse])
async def list_packs(
    registry: PracticeRegistry = Depends(registry_dependency),
    _user: dict = Depends(get_current_user),
) -> list[PackResponse]:
    """List the mounted pack manifests, with license and attribution."""
    return [
        PackResponse(
            manifest=manifest,
            practice_count=registry.practice_count(manifest.pack_id),
        )
        for manifest in registry.list_packs()
    ]


# ── The practice log ────────────────────────────────────────────────
#
# Declared above /practices/{pack_id}/{slug} so no future rename of the
# library prefix can let the pattern swallow these. Both routes derive
# the owner from the token: there is no user_id in the body and no
# user_id query parameter, so there is no shape of request that reads or
# writes somebody else's log.


@router.post("/practice/log", status_code=201, response_model=PracticeLogResponse)
async def create_practice_log(
    entry: PracticeLogCreate,
    registry: PracticeRegistry = Depends(registry_dependency),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeLogResponse:
    """Log one practice event and return the created row.

    The practice has to exist in a mounted pack. Its purposes and
    category come from that definition, denormalized onto the row so it
    stays readable after the pack is unmounted or revised.

    ``day_key`` is stored exactly as sent. It is the user's local
    calendar day, and only the client knows what that is.
    """
    definition = _resolve_practice(registry, entry.pack_id, entry.practice_slug)

    created = await repository.create_practice_log_entry(
        session,
        user_id=current_user["sub"],
        pack_id=entry.pack_id,
        practice_slug=definition.slug,
        primary_purpose=definition.primary_purpose,
        purposes=list(definition.purposes),
        category=definition.category,
        day_key=entry.day_key,
        occurred_at=entry.occurred_at or datetime.now(UTC),
        status=entry.status,
        protocol_slot=entry.protocol_slot,
        duration_minutes=entry.duration_minutes,
        reflection=entry.reflection,
        self_check_response=entry.self_check_response,
    )
    return _log_to_response(created)


@router.get("/practice/log", response_model=PracticeLogListResponse)
async def list_practice_log(
    from_day: DayKey | None = Query(
        None, alias="from", description="Earliest local day to include, inclusive"
    ),
    to_day: DayKey | None = Query(
        None, alias="to", description="Latest local day to include, inclusive"
    ),
    status: LogStatus | None = Query(None, description="Filter to one status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeLogListResponse:
    """Return a page of the caller's own practice log, newest first.

    The range filters on ``day_key``, the user's local day, so "the last
    seven days" means the same thing here as it does on the rhythm
    display. Both bounds are inclusive and either may be omitted.
    """
    entries, total = await repository.list_practice_log_entries(
        session,
        current_user["sub"],
        from_day=from_day,
        to_day=to_day,
        status=status,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    return PracticeLogListResponse(
        entries=[_log_to_response(row) for row in entries],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/practice/today", response_model=TodayResponse)
async def practice_today(
    today: TodayQuery,
    refresh: bool = Query(
        False, description="Recompute even when the stable-day rule would replay"
    ),
    registry: PracticeRegistry = Depends(registry_dependency),
    settings: EcologySettings = Depends(ecology_settings_dependency),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TodayResponse:
    """Return today's protocol: N practices, each rendered in three slots.

    Deterministic. There is no LLM on this path and no randomness, so the
    same log on the same day produces the same protocol, and ``reason``
    is answerable from what the user can already see.

    The result is stable within a day: completing one practice at 9am
    does not reshuffle the other four at 9:05. Pass ``refresh=true`` to
    recompute anyway. A new day or a change to the mounted packs
    recomputes on its own.
    """
    user_id = current_user["sub"]
    state = await repository.get_or_create_ecology_state(session, user_id)
    log = await _load_recommender_log(session, user_id, today=today, settings=settings)
    now = datetime.now(UTC)

    result = _recommend(
        registry, log, state, now=now, today=today, refresh=refresh, settings=settings
    )
    try:
        response = TodayResponse.model_validate(result.payload)
    except ValidationError:
        # A stored payload this build cannot read means a deploy moved
        # underneath it. Recompute rather than 500: the user wants a
        # protocol, not an incident.
        logger.warning(
            "Stored practice recommendation for a user did not match the current "
            "payload shape. Recomputing.",
        )
        result = _recommend(
            registry, log, state, now=now, today=today, refresh=True, settings=settings
        )
        response = TodayResponse.model_validate(result.payload)

    if result.recomputed:
        await repository.update_ecology_recommendation(
            session,
            user_id,
            rotation_cursor=result.rotation_cursor,
            last_recommendation=result.envelope,
            last_recommended_at=now,
        )
    return response


@router.get("/practice/summary", response_model=PracticeSummaryResponse)
async def practice_summary(
    today: TodayQuery,
    current_user: dict = Depends(get_current_user),
    settings: EcologySettings = Depends(ecology_settings_dependency),
    session: AsyncSession = Depends(get_db_session),
) -> PracticeSummaryResponse:
    """Return the rhythm figures for the seven days ending *today*.

    A day counts when at least one practice was completed on it, so two
    completions on one day count once, and a skip counts as neither. No
    number here resets to zero and nothing compares the caller to anyone
    else: the display this feeds is a record, not a scoreboard.
    """
    log = await _load_recommender_log(session, current_user["sub"], today=today, settings=settings)
    summary = summarize_practice(log, today=today)
    return PracticeSummaryResponse(
        day_key=today,
        days_practiced_last_7=summary.days_practiced_last_7,
        last_7=summary.last_7,
        by_purpose=summary.by_purpose,
        total_completed=summary.total_completed,
    )


# DRAFT copy, awaiting Tyler's sign-off. Three things it has to do:
# say the save did not land, say the earlier writing is safe, and give
# the user a way to keep what they just typed. It stays quiet about it
# because a full note is not an emergency, and it never repeats the
# refused text back, which would only put it somewhere else.
NOTE_FULL_DETAIL = (
    "This entry's note is full. Your earlier notes are saved. This new text was not "
    "added, so copy it somewhere safe if you want to keep it."
)


@router.post(
    "/practice/integration",
    status_code=201,
    response_model=IntegrationResponse,
    responses={
        200: {"description": "This completion already had an entry, and the save merged into it."},
        422: {"description": "The note would pass this entry's total cap, so nothing was written."},
    },
)
async def create_integration(
    entry: IntegrationCreate,
    response: Response,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> IntegrationResponse:
    """Link an intention, an experience and a reflection, and record the shift.

    Two writes, both scoped to the caller: the link row, and exactly one
    derived ``outcome_metrics`` row so the change lands on the dashboard
    the user already reads.

    One completion is one record. The completed practice card offers the
    self-check and the integration reading side by side and both save
    here against the same ``practice_log_id``, so this route saves
    rather than creates: a second call merges into the row the first one
    wrote and answers 200 instead of 201. Merge semantics are the
    repository's (:func:`~alchymine.db.repository.upsert_integration_entry`);
    what matters here is that nothing the user wrote is dropped by
    saving twice.

    Every id in the body is checked against the caller first, and a row
    belonging to somebody else answers 404 rather than 403. A 403 would
    confirm the row exists, which turns this endpoint into an existence
    oracle over another user's practice log and journal.

    The derived row goes through the repository rather than
    ``POST /outcomes/activity``: that path drops its metadata, writes
    process-global dicts, and takes a client-supplied ``user_id``.

    One entry's note is the merge of every save against that completion,
    so it carries a total cap on top of the per-request 5000. A note
    that would pass it answers 422 and writes nothing, rather than
    storing a truncated version of what the user wrote.
    """
    user_id = current_user["sub"]

    log_entry = await repository.get_practice_log_entry(session, entry.practice_log_id, user_id)
    if log_entry is None:
        raise HTTPException(status_code=404, detail="Practice log entry not found")

    for entry_id in (entry.intention_entry_id, entry.reflection_entry_id):
        if entry_id is None:
            continue
        if await repository.get_journal_entry_for_user(session, entry_id, user_id) is None:
            raise HTTPException(status_code=404, detail="Journal entry not found")

    try:
        stored, created = await repository.upsert_integration_entry(
            session,
            user_id=user_id,
            practice_log_id=log_entry.id,
            purpose=log_entry.primary_purpose,
            intention_entry_id=entry.intention_entry_id,
            reflection_entry_id=entry.reflection_entry_id,
            capacity_delta=entry.capacity_delta,
            note=entry.note,
        )
    except repository.IntegrationNoteFull as exc:
        raise HTTPException(status_code=422, detail=NOTE_FULL_DETAIL) from exc

    # One row per completion, not one per save. The value is read off
    # the stored row rather than off this request, so the reading stands
    # whichever prompt the user filled in first and a later note-only
    # save does not walk it back. The rule for an absent self-report
    # lives in :func:`loop_shift_value`, shared with the journey series:
    # if the two had their own copies and one changed, the dashboard and
    # the journey would report different numbers for the same loop.
    await repository.record_outcome_metric(
        session,
        user_id=user_id,
        system=system_for_purpose(log_entry.primary_purpose),
        metric_name="practice_integration",
        value=loop_shift_value(stored.capacity_delta),
        period="daily",
        metric_id=repository.derived_metric_id(stored.id, "practice_integration"),
    )

    if not created:
        response.status_code = 200

    return IntegrationResponse(
        id=stored.id,
        user_id=stored.user_id,
        practice_log_id=stored.practice_log_id,
        intention_entry_id=stored.intention_entry_id,
        reflection_entry_id=stored.reflection_entry_id,
        purpose=stored.purpose,
        capacity_delta=stored.capacity_delta,
        note=stored.note,
        created_at=stored.created_at,
    )


@router.get("/journey/timeseries", response_model=JourneyTimeseriesResponse, tags=["journey"])
async def journey_timeseries(
    today: TodayQuery,
    days: int = Query(
        JOURNEY_WINDOW_DEFAULT,
        ge=JOURNEY_WINDOW_MIN,
        le=JOURNEY_WINDOW_MAX,
        description=(
            "How many days the window covers, ending on 'today'. Bounded here "
            "rather than clamped: a caller asking for a year should find out "
            "it cannot have one."
        ),
    ),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> JourneyTimeseriesResponse:
    """Return the caller's practice and integration history as a series.

    Read-only, deterministic, and scoped to the caller: the owner comes
    from the token, so there is no shape of request that reads somebody
    else's journey. No plan gate, matching the rest of the practice
    layer and the dashboard, and no LLM anywhere on the path.

    A user with no history gets a full zero-filled window rather than an
    empty body. "You have not started yet" is a state the page renders,
    not a failure it handles.

    Two reads, both bounded. The series comes from one query scoped to
    the window; the anchors in ``totals`` are scalar aggregates over an
    index, which is how "practicing since March" is answerable without
    loading March.
    """
    user_id = current_user["sub"]
    window_start = date.fromisoformat(today) - timedelta(days=days - 1)

    rows = await repository.list_journey_rows(session, user_id, from_day=window_start.isoformat())
    first_practice_day, first_loop_day = await repository.get_journey_anchors(session, user_id)

    series = build_journey_series(
        [
            JourneyRow(
                day_key=row.day_key,
                primary_purpose=row.primary_purpose,
                status=row.status,
                has_loop=row.integration_id is not None,
                capacity_delta=row.capacity_delta,
            )
            for row in rows
        ],
        today=today,
        window_days=days,
    )

    return JourneyTimeseriesResponse(
        day_key=today,
        start_day=series.start_day,
        window_days=series.window_days,
        days=[
            JourneyDayResponse(
                day_key=point.day_key,
                completed=point.completed,
                purposes=list(point.purposes),
                loops=point.loops,
                average_shift=point.average_shift,
            )
            for point in series.days
        ],
        by_purpose=series.by_purpose,
        totals=JourneyTotalsResponse(
            days_practiced=series.days_practiced,
            completed=series.total_completed,
            loops_closed=series.total_loops,
            first_practice_day=first_practice_day,
            first_loop_day=first_loop_day,
        ),
    )


@router.get("/practices/{pack_id}/{slug}", response_model=PracticeResponse)
async def get_practice(
    pack_id: str,
    slug: str,
    registry: PracticeRegistry = Depends(registry_dependency),
    _user: dict = Depends(get_current_user),
) -> PracticeResponse:
    """Return one practice by its qualified id."""
    try:
        practice = registry.get(pack_id, slug)
    except PackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pack not found: {pack_id}") from exc
    except PracticeNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Practice not found: {pack_id}/{slug}"
        ) from exc
    return _to_response(registry, pack_id, practice)

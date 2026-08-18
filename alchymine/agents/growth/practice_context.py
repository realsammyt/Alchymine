"""The practice coach's view of the user's own practice data.

Deterministic. No LLM, no scoring, no interpretation: this module reads
a fixed set of plaintext columns and renders them as a short labelled
block. Everything interpretive is the coach's job, and everything
private stays out of its reach.

**The data rail.** ``practice_log.reflection``,
``practice_log.self_check_response`` and ``integration_entries.note``
are encrypted at rest and are never selected here. The query that feeds
this module (``repository.list_practice_context_rows``) names its five
columns explicitly for that reason. So a reflection can only reach an
LLM if the user types it into the chat box themselves, which is their
call to make rather than ours.

**Where the block goes.** Appended to the *user message* at call time,
after the prompt-cache breakpoint, never to the system prompt. The
assembled system prompt is the stable cacheable prefix of every chat
turn (``llm.client._system_payload``); a block that changes daily would
invalidate that prefix daily. Only the user's raw text is persisted to
``chat_messages``, so the block is not part of the conversation history
either.

**The day boundary.** ``day_key`` is the user's *local* calendar day and
the chat request carries no local day, so the window is anchored to the
UTC date and the stored protocol is accepted one day either side of it.
A user in Auckland or Honolulu is a day out from UTC, not seven, and the
alternative is telling half the world their protocol is stale.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db import repository
from alchymine.engine.practice import (
    PackNotFoundError,
    PracticeNotFoundError,
    get_practice_registry,
)

logger = logging.getLogger(__name__)

# The rhythm surface reports seven days, and the coach saying something
# different about the same week would read as a second opinion.
WINDOW_DAYS = 7

# How far the stored protocol's day_key may sit from the UTC date and
# still count as today. See the module docstring.
_PROTOCOL_DAY_TOLERANCE = 1

_HEADER = "Practice context (from this user's own practice log):"

# Said plainly because the model cannot tell an absent column from an
# empty one, and a coach that assumes it has already read the reflection
# will never ask about it.
_FOOTER = (
    "You cannot see what they wrote in their reflections or self-checks. Ask them if it matters."
)


def _title_for(pack_id: str, slug: str) -> str:
    """Return the practice's display title, falling back to its slug.

    A log row outlives its pack: an external mount can be removed, and a
    pack can drop a practice in a new version. Neither is a reason to
    fail the whole block, and the slug still names the thing the user
    did.
    """
    try:
        return get_practice_registry().get(pack_id, slug).title
    except (PackNotFoundError, PracticeNotFoundError):
        return slug
    except Exception:  # pragma: no cover - a broken mount is not a chat failure
        logger.exception("Practice registry unreadable while building coach context")
        return slug


def _mounted_pack_ids() -> frozenset[str] | None:
    """Return the mounted pack ids, or ``None`` when they cannot be read.

    ``None`` means "unknown", and an unknown mount set filters nothing.
    A registry this process cannot read is a deployment problem, not a
    reason to hand the coach a protocol line with holes in it.
    """
    try:
        return frozenset(manifest.pack_id for manifest in get_practice_registry().list_packs())
    except Exception:  # pragma: no cover - a broken mount is not a chat failure
        logger.exception("Practice registry unreadable while building coach context")
        return None


def _protocol_titles(stored: Mapping[str, Any] | None, *, anchor_day: str) -> list[str]:
    """Return today's protocol titles from the stored envelope, if current.

    Entries naming a pack that is no longer mounted are dropped. The
    envelope is a *copy* of pack content rather than a reference to it,
    and unmounting a pack is how a license is revoked, so a title from a
    pack this process does not have must not reach the model. Startup
    clears those rows outright (``db.pack_envelopes``); this is the
    second line of defense for the case where that purge could not run.
    An entry naming no pack at all is kept: there is nothing to revoke it
    against.

    Anything unreadable returns an empty list rather than raising. The
    envelope is written by the recommender and read here; a shape this
    build does not recognise means a deploy moved underneath it, and the
    right answer is a block without a protocol line, not a 500 on the
    chat endpoint.
    """
    if not isinstance(stored, Mapping):
        return []
    payload = stored.get("payload")
    if not isinstance(payload, Mapping):
        return []

    day_key = payload.get("day_key") or stored.get("day_key")
    if not isinstance(day_key, str) or not _within_tolerance(day_key, anchor_day):
        return []

    items = payload.get("items")
    if not isinstance(items, list):
        return []

    mounted = _mounted_pack_ids()
    titles: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        pack_id = item.get("pack_id")
        if mounted is not None and isinstance(pack_id, str) and pack_id not in mounted:
            continue
        title = item.get("title") or item.get("slug")
        if isinstance(title, str) and title:
            titles.append(title)
    return titles


def _within_tolerance(day_key: str, anchor_day: str) -> bool:
    try:
        stored_day = datetime.strptime(day_key, "%Y-%m-%d").date()
        anchor = datetime.strptime(anchor_day, "%Y-%m-%d").date()
    except ValueError:
        return False
    return abs((stored_day - anchor).days) <= _PROTOCOL_DAY_TOLERANCE


async def build_practice_context(session: AsyncSession, user_id: str) -> str | None:
    """Return the practice block for *user_id*, or ``None`` when there is none.

    ``None`` rather than an empty scaffold: a user asking their first
    practice question has nothing to summarise, and a block announcing
    that would spend tokens telling the model something it can infer
    from silence.

    Parameters
    ----------
    session:
        The request's database session.
    user_id:
        The authenticated subject. Rows are owner-filtered in SQL.
    """
    today = datetime.now(UTC).date()
    anchor_day = today.isoformat()
    from_day = (today - timedelta(days=WINDOW_DAYS - 1)).isoformat()

    rows = await repository.list_practice_context_rows(session, user_id, from_day=from_day)
    stored = await repository.get_stored_recommendation(session, user_id)

    completed = [row for row in rows if row.status == "completed"]
    protocol = _protocol_titles(stored, anchor_day=anchor_day)

    if not completed and not protocol:
        return None

    lines = [_HEADER]

    if completed:
        days = {row.day_key for row in completed}
        lines.append(f"- Practiced on {len(days)} of the last {WINDOW_DAYS} days.")

        counts = Counter(
            (_title_for(row.pack_id, row.practice_slug), row.primary_purpose) for row in completed
        )
        done = ", ".join(
            f"{title} ({purpose}) x{count}" for (title, purpose), count in counts.most_common()
        )
        lines.append(f"- Completed since {from_day}: {done}.")

        by_purpose = Counter(row.primary_purpose for row in completed)
        shares = ", ".join(f"{purpose} {count}" for purpose, count in by_purpose.most_common())
        lines.append(f"- By purpose: {shares}.")

    if protocol:
        lines.append(f"- Today's protocol: {', '.join(protocol)}.")

    lines.append(_FOOTER)
    return "\n".join(lines)

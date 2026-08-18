"""One integration entry per completion.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-18

0018 gave ``integration_entries`` no key beyond its primary key. The
completed practice card offers two prompts, the self-check and the
integration reading, and both save against the same ``practice_log``
row, so one practice produced two link rows and two derived
``outcome_metrics`` rows. Everything counting integrations read double.

This adds the key that makes one-row-per-completion a schema fact:
``(user_id, practice_log_id)``. Scoped to the user, so two people
practicing are never each other's conflict. Rows with a NULL
``practice_log_id`` are untouched, because NULLs do not compare equal on
either dialect; the route requires one, so those do not arise from the
API, but the column allows them and this migration does not narrow that.

A unique INDEX rather than a table constraint. Adding a constraint to an
existing table on SQLite means a batch rebuild: copy the table, copy the
rows, rebuild three foreign keys. ``CREATE UNIQUE INDEX`` is one
statement both dialects take, on a table already holding user writing.

IT REFUSES TO RUN ON A DATABASE THAT ALREADY HAS DUPLICATES, and it
deletes nothing. Merging historical rows would destroy user writing as a
side effect of a deploy, with no record of what went. The pre-check
raises with the counts and points at the cleanup script in issue #290
instead. For any database that has been serving this route, the deploy
order is CLEANUP FIRST, THEN MIGRATE.

``downgrade()`` drops the index and leaves every row where it is.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_integration_entries_user_practice_log"

_DUPLICATES = sa.text(
    "SELECT user_id, practice_log_id, COUNT(*) AS copies "
    "FROM integration_entries "
    "WHERE practice_log_id IS NOT NULL "
    "GROUP BY user_id, practice_log_id "
    "HAVING COUNT(*) > 1 "
    "ORDER BY copies DESC"
)


def _refuse_on_duplicates(conn) -> None:
    """Stop the deploy if the key would not hold. Change nothing.

    The operator gets the numbers and the next step, because the fix is
    a script somebody has to read and run, not something a migration
    should decide on their behalf at 2am.
    """
    duplicated = conn.execute(_DUPLICATES).all()
    if not duplicated:
        return

    extra_rows = sum(row.copies - 1 for row in duplicated)
    completions = "completion" if len(duplicated) == 1 else "completions"
    rows = "row" if extra_rows == 1 else "rows"
    raise RuntimeError(
        f"Migration 0019 stopped: integration_entries has more than one entry "
        f"for {len(duplicated)} {completions} ({extra_rows} {rows} above one). "
        "The unique key cannot be created until those are merged, and this "
        "migration will not merge them, because that means deleting rows "
        "holding what users wrote. Run the reviewed cleanup script from "
        "issue #290 first, then run this migration again. Deploy order on "
        "any database that has served POST /practice/integration is "
        "cleanup first, then migrate."
    )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if "integration_entries" not in set(inspector.get_table_names()):
        # 0018 has not run here. Nothing to key.
        return

    if INDEX_NAME in {ix["name"] for ix in inspector.get_indexes("integration_entries")}:
        # Replayed after a partially applied deploy, matching 0015, 0017
        # and 0018. The check below would pass anyway; skipping it keeps
        # the replay cheap on a large table.
        return

    _refuse_on_duplicates(conn)

    op.create_index(
        INDEX_NAME,
        "integration_entries",
        ["user_id", "practice_log_id"],
        unique=True,
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if "integration_entries" not in set(inspector.get_table_names()):
        return
    if INDEX_NAME in {ix["name"] for ix in inspector.get_indexes("integration_entries")}:
        op.drop_index(INDEX_NAME, table_name="integration_entries")

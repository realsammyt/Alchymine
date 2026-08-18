"""Tests for migration 0019, one integration entry per completion.

0018 left ``integration_entries`` with no key of its own beyond the
primary key, so the two prompts on a completed practice card wrote two
link rows for one completion and every count downstream read double.
0019 adds the unique key that makes one-row-per-completion a schema fact
rather than an application rule.

What these tests pin, and why each matters:

1. The key is ``(user_id, practice_log_id)``. Scoped to the user, so two
   people practicing are never each other's conflict, and scoped to the
   completion, so a week of practice is still a week of rows.
2. Rows with a NULL ``practice_log_id`` are left alone. The column is
   nullable and NULLs do not compare equal, on SQLite or on Postgres.
   Collapsing them would be a schema change nobody asked for.
3. The migration refuses to run when duplicates already exist, and
   deletes nothing. Historical cleanup is a reviewed, explicitly run
   script, not a side effect of a deploy. A migration that quietly
   merged rows would destroy user writing with no record of what went.
4. upgrade → downgrade → upgrade round trips, and a replayed upgrade is
   a no-op, matching 0018.

SQLite only, matching ``test_migration_0018_practice_layer.py``: the
repo has no Postgres test harness and CI stands up no database service.
The DDL is a plain ``CREATE UNIQUE INDEX``, which both dialects take
without a table rebuild.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

INDEX_NAME = "uq_integration_entries_user_practice_log"


def _alembic_config(async_url: str):
    """Build an Alembic Config pointed at *async_url*."""
    from alembic.config import Config

    import alchymine

    pkg_root = os.path.dirname(os.path.dirname(alchymine.__file__))
    cfg = Config(os.path.join(pkg_root, "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def db_at_0018(tmp_path, monkeypatch):
    """A SQLite database migrated to 0018, the state before this change.

    Yields ``(engine, cfg)`` so a test can seed rows, run the 0019
    upgrade against them and inspect what happened.
    """
    from alembic import command

    db_path = tmp_path / "integration_uniqueness.db"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", async_url)

    cfg = _alembic_config(async_url)
    command.upgrade(cfg, "0018")

    engine = create_engine(sync_url)
    yield engine, cfg
    engine.dispose()


@pytest.fixture
def db_at_0019(db_at_0018):
    """A SQLite database migrated all the way to 0019."""
    from alembic import command

    engine, cfg = db_at_0018
    command.upgrade(cfg, "0019")
    return engine, cfg


def _seed_user_and_log(engine, user_id: str = "u-1", log_id: str = "pl-1") -> None:
    """One user and one completed practice, the parents of a link row."""
    with engine.begin() as conn:
        conn.execute(text("INSERT OR IGNORE INTO users (id) VALUES (:u)"), {"u": user_id})
        conn.execute(
            text(
                "INSERT INTO practice_log "
                "(id, user_id, pack_id, practice_slug, primary_purpose, purposes, "
                " category, occurred_at, day_key) "
                "VALUES (:i, :u, 'p', 's', 'steadiness', '[]', 'reflection', "
                " '2026-08-14T09:00:00+00:00', '2026-08-14')"
            ),
            {"i": log_id, "u": user_id},
        )


def _insert_entry(engine, entry_id: str, user_id: str, log_id: str | None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO integration_entries (id, user_id, practice_log_id, purpose) "
                "VALUES (:i, :u, :p, 'steadiness')"
            ),
            {"i": entry_id, "u": user_id, "p": log_id},
        )


class TestRevisionChain:
    """0019 has to be the single head, following 0018."""

    def test_0019_is_the_only_head(self):
        """Two heads is a merge conflict that only shows up on deploy."""
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(_alembic_config("sqlite://"))

        heads = list(script.get_heads())
        assert heads == ["0019"], f"expected a single head 0019, got {heads}"
        assert script.get_revision("0019").down_revision == "0018"


class TestTheUniqueKey:
    def test_the_index_exists_and_is_unique(self, db_at_0019):
        engine, _ = db_at_0019

        indexes = {ix["name"]: ix for ix in inspect(engine).get_indexes("integration_entries")}
        assert INDEX_NAME in indexes, f"have {sorted(indexes)}"
        assert indexes[INDEX_NAME]["unique"]
        assert indexes[INDEX_NAME]["column_names"] == ["user_id", "practice_log_id"]

    def test_a_second_row_for_one_completion_is_refused(self, db_at_0019):
        """The bug this migration closes, stated as a constraint."""
        engine, _ = db_at_0019
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")

        with pytest.raises(IntegrityError):
            _insert_entry(engine, "ie-2", "u-1", "pl-1")

    def test_two_completions_are_two_rows(self, db_at_0019):
        """A week of practice is still a week of rows."""
        engine, _ = db_at_0019
        _seed_user_and_log(engine, "u-1", "pl-1")
        _seed_user_and_log(engine, "u-1", "pl-2")

        _insert_entry(engine, "ie-1", "u-1", "pl-1")
        _insert_entry(engine, "ie-2", "u-1", "pl-2")

        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM integration_entries")).scalar_one()
        assert count == 2

    def test_the_key_is_scoped_to_the_user(self, db_at_0019):
        """Two people are never each other's conflict."""
        engine, _ = db_at_0019
        _seed_user_and_log(engine, "u-1", "pl-1")
        _seed_user_and_log(engine, "u-2", "pl-2")

        _insert_entry(engine, "ie-1", "u-1", "pl-1")
        _insert_entry(engine, "ie-2", "u-2", "pl-2")

        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM integration_entries")).scalar_one()
        assert count == 2

    def test_rows_with_no_practice_log_are_left_alone(self, db_at_0019):
        """``practice_log_id`` is nullable and NULLs do not compare equal.

        The route requires one, so these do not arise from the API, but
        the column allows them and the migration must not start refusing
        a shape the schema permits.
        """
        engine, _ = db_at_0019
        _seed_user_and_log(engine)

        _insert_entry(engine, "ie-1", "u-1", None)
        _insert_entry(engine, "ie-2", "u-1", None)

        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM integration_entries")).scalar_one()
        assert count == 2


class TestDuplicatesStopTheDeploy:
    """Existing duplicates fail loudly. Nothing is deleted or merged."""

    def test_the_upgrade_raises_when_duplicates_exist(self, db_at_0018):
        from alembic import command

        engine, cfg = db_at_0018
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")
        _insert_entry(engine, "ie-2", "u-1", "pl-1")

        with pytest.raises(RuntimeError) as excinfo:
            command.upgrade(cfg, "0019")

        message = str(excinfo.value)
        assert "integration_entries" in message
        assert "1" in message, "the operator needs the count, not just the fact"

    def test_the_failure_message_names_the_cleanup(self, db_at_0018):
        """An operator reading this at 2am needs the next step in it."""
        from alembic import command

        engine, cfg = db_at_0018
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")
        _insert_entry(engine, "ie-2", "u-1", "pl-1")

        with pytest.raises(RuntimeError) as excinfo:
            command.upgrade(cfg, "0019")

        assert "cleanup" in str(excinfo.value).lower()

    def test_the_duplicate_rows_survive_the_failed_upgrade(self, db_at_0018):
        """Data deletion is a reviewed decision, never a deploy side effect."""
        from alembic import command

        engine, cfg = db_at_0018
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")
        _insert_entry(engine, "ie-2", "u-1", "pl-1")

        with pytest.raises(RuntimeError):
            command.upgrade(cfg, "0019")

        with engine.connect() as conn:
            ids = [
                row[0]
                for row in conn.execute(text("SELECT id FROM integration_entries ORDER BY id"))
            ]
        assert ids == ["ie-1", "ie-2"]

    def test_the_index_is_not_created_when_the_check_fails(self, db_at_0018):
        from alembic import command

        engine, cfg = db_at_0018
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")
        _insert_entry(engine, "ie-2", "u-1", "pl-1")

        with pytest.raises(RuntimeError):
            command.upgrade(cfg, "0019")

        names = {ix["name"] for ix in inspect(engine).get_indexes("integration_entries")}
        assert INDEX_NAME not in names

    def test_a_clean_database_upgrades(self, db_at_0018):
        """The pre-check passes when there is nothing to complain about."""
        from alembic import command

        engine, cfg = db_at_0018
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")

        command.upgrade(cfg, "0019")

        names = {ix["name"] for ix in inspect(engine).get_indexes("integration_entries")}
        assert INDEX_NAME in names


class TestIdempotency:
    """upgrade → downgrade → upgrade has to be a no-op round trip."""

    def test_the_round_trip_leaves_the_same_indexes(self, db_at_0018):
        from alembic import command

        engine, cfg = db_at_0018

        command.upgrade(cfg, "0019")
        first = {ix["name"] for ix in inspect(engine).get_indexes("integration_entries")}

        command.downgrade(cfg, "0018")
        after_downgrade = {ix["name"] for ix in inspect(engine).get_indexes("integration_entries")}
        assert INDEX_NAME not in after_downgrade

        command.upgrade(cfg, "0019")
        second = {ix["name"] for ix in inspect(engine).get_indexes("integration_entries")}

        assert first == second

    def test_the_downgrade_keeps_the_rows(self, db_at_0019):
        """Dropping the key must not drop what it was keying."""
        from alembic import command

        engine, cfg = db_at_0019
        _seed_user_and_log(engine)
        _insert_entry(engine, "ie-1", "u-1", "pl-1")

        command.downgrade(cfg, "0018")

        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM integration_entries")).scalar_one()
        assert count == 1

    def test_a_replayed_upgrade_does_not_fail(self, db_at_0019):
        """The partially-applied-migration case: the index already exists."""
        from alembic import command

        engine, cfg = db_at_0019

        command.stamp(cfg, "0018")
        command.upgrade(cfg, "0019")

        names = {ix["name"] for ix in inspect(engine).get_indexes("integration_entries")}
        assert INDEX_NAME in names

"""Tests for migration 0018 — the practice layer schema.

Three tables land here: ``practice_log`` (one row per logged practice
event), ``ecology_state`` (one row per user, recommender state) and
``integration_entries`` (the intention/experience/reflection link).

What these tests pin, and why each matters:

1. The migration is idempotent. ``upgrade`` → ``downgrade`` → ``upgrade``
   has to leave the same schema behind, because a partially applied
   migration replayed after a deploy is the normal failure mode, not the
   exotic one.
2. Primary keys are ``String(36)`` uuids on all three tables. 0017 needed
   a ``BigInteger``/``Integer`` SQLite variant for its autoincrement PKs;
   nothing here does, and adding one by pattern-match would change the
   key type on a table that joins ``journal_entries`` and
   ``outcome_metrics``.
3. The cascade asymmetry on ``integration_entries``. Deleting the
   practice_log row destroys the link (CASCADE) because the link has no
   meaning without the experience. Deleting a journal entry is a
   user-facing action and must leave the integration record standing
   (SET NULL). Getting this backwards silently deletes user history.
4. The three indexes the recommender reads exist. Without them slice 3
   table-scans practice_log on every /practice/today.

SQLite only, matching ``test_migration_0017_entitlements.py``: the repo
has no Postgres test harness and CI stands up no database service. The
migration is written dialect-agnostically (no server-side casts, no
Postgres-only types) so the same DDL applies on both.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text


def _alembic_config(async_url: str):
    """Build an Alembic Config pointed at *async_url*."""
    from alembic.config import Config

    import alchymine

    pkg_root = os.path.dirname(os.path.dirname(alchymine.__file__))
    cfg = Config(os.path.join(pkg_root, "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


PRACTICE_TABLES = ("practice_log", "ecology_state", "integration_entries")


@pytest.fixture
def db_at_0017(tmp_path, monkeypatch):
    """A SQLite database migrated to 0017 — the state main is in today.

    Yields ``(engine, cfg)`` so a test can run the 0018 upgrade against
    it and inspect what landed.
    """
    from alembic import command

    db_path = tmp_path / "practice_layer.db"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", async_url)

    cfg = _alembic_config(async_url)
    command.upgrade(cfg, "0017")

    engine = create_engine(sync_url)
    yield engine, cfg
    engine.dispose()


@pytest.fixture
def db_at_0018(db_at_0017):
    """A SQLite database migrated all the way to 0018."""
    from alembic import command

    engine, cfg = db_at_0017
    command.upgrade(cfg, "0018")
    return engine, cfg


class TestRevisionChain:
    """0018 follows 0017, on the one path the chain has."""

    def test_0018_sits_on_the_single_head_path(self):
        """Two heads is a merge conflict that only shows up on deploy.

        The head itself moves forward with every migration that lands,
        so what is pinned here is that there is exactly one of them and
        that 0018 is an ancestor of it, rather than a literal that needs
        editing whenever somebody adds a revision.
        """
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(_alembic_config("sqlite://"))

        heads = list(script.get_heads())
        assert len(heads) == 1, f"expected a single head, got {heads}"

        chain = {revision.revision for revision in script.walk_revisions("base", heads[0])}
        assert "0018" in chain, f"0018 is not on the path to {heads[0]}"
        assert script.get_revision("0018").down_revision == "0017"


class TestIdempotency:
    """upgrade → downgrade → upgrade has to be a no-op round trip."""

    def test_upgrade_downgrade_upgrade_leaves_the_same_tables(self, db_at_0017):
        from alembic import command

        engine, cfg = db_at_0017

        command.upgrade(cfg, "0018")
        after_first = set(inspect(engine).get_table_names())

        command.downgrade(cfg, "0017")
        after_downgrade = set(inspect(engine).get_table_names())
        for name in PRACTICE_TABLES:
            assert name not in after_downgrade, f"{name} survived the downgrade"

        command.upgrade(cfg, "0018")
        after_second = set(inspect(engine).get_table_names())

        assert after_first == after_second

    def test_columns_survive_the_round_trip(self, db_at_0017):
        """Not just the table names: the full column set has to match."""
        from alembic import command

        engine, cfg = db_at_0017

        command.upgrade(cfg, "0018")
        first = {
            table: {c["name"] for c in inspect(engine).get_columns(table)}
            for table in PRACTICE_TABLES
        }

        command.downgrade(cfg, "0017")
        command.upgrade(cfg, "0018")
        second = {
            table: {c["name"] for c in inspect(engine).get_columns(table)}
            for table in PRACTICE_TABLES
        }

        assert first == second

    def test_a_replayed_upgrade_does_not_fail(self, db_at_0018):
        """Stamp back and replay: the guards make the second run a no-op.

        This is the partially-applied-migration case. The tables already
        exist; ``create_table`` without an inspect guard would raise.
        """
        from alembic import command

        engine, cfg = db_at_0018

        command.stamp(cfg, "0017")
        command.upgrade(cfg, "0018")

        tables = set(inspect(engine).get_table_names())
        for name in PRACTICE_TABLES:
            assert name in tables


class TestPracticeLogTable:
    """Section 4.1 of the design."""

    def test_every_column_exists(self, db_at_0018):
        engine, _ = db_at_0018

        cols = {c["name"] for c in inspect(engine).get_columns("practice_log")}
        expected = {
            "id",
            "user_id",
            "pack_id",
            "practice_slug",
            "primary_purpose",
            "purposes",
            "category",
            "status",
            "protocol_slot",
            "duration_minutes",
            "occurred_at",
            "day_key",
            "created_at",
            "reflection",
            "self_check_response",
        }
        assert expected <= cols, f"missing practice_log columns: {expected - cols}"

    def test_primary_key_is_a_uuid_string_not_an_integer(self, db_at_0018):
        """Decision 10. A BigInteger PK here would break the uuid joins."""
        engine, _ = db_at_0018

        cols = {c["name"]: c for c in inspect(engine).get_columns("practice_log")}
        pk_type = str(cols["id"]["type"]).upper()
        assert "VARCHAR(36)" in pk_type or "CHAR(36)" in pk_type, pk_type
        assert "INT" not in pk_type

    def test_the_three_recommender_indexes_exist(self, db_at_0018):
        """Slice 3 reads all three. Without them /practice/today scans."""
        engine, _ = db_at_0018

        indexed = {tuple(ix["column_names"]) for ix in inspect(engine).get_indexes("practice_log")}
        for cols in [
            ("user_id", "day_key"),
            ("user_id", "primary_purpose", "occurred_at"),
            ("user_id", "pack_id", "practice_slug", "occurred_at"),
        ]:
            assert cols in indexed, f"index on {cols} missing; have {indexed}"

    def test_encrypted_columns_are_nullable_text(self, db_at_0018):
        """Fernet ciphertext is longer than plaintext, so these are TEXT."""
        engine, _ = db_at_0018

        cols = {c["name"]: c for c in inspect(engine).get_columns("practice_log")}
        for name in ("reflection", "self_check_response"):
            assert cols[name]["nullable"] is True
            assert "TEXT" in str(cols[name]["type"]).upper()

    def test_recommender_input_columns_are_not_text_blobs(self, db_at_0018):
        """Decision 11: what the recommender groups by stays plaintext.

        An encrypted ``primary_purpose`` cannot be grouped in SQL, which
        would move the whole recommender into Python over a full scan.
        """
        engine, _ = db_at_0018

        cols = {c["name"]: c for c in inspect(engine).get_columns("practice_log")}
        assert cols["primary_purpose"]["nullable"] is False
        assert cols["day_key"]["nullable"] is False
        assert "VARCHAR" in str(cols["day_key"]["type"]).upper()

    def test_user_id_cascades_on_delete(self, db_at_0018):
        engine, _ = db_at_0018

        fks = inspect(engine).get_foreign_keys("practice_log")
        user_fk = next(fk for fk in fks if fk["constrained_columns"] == ["user_id"])
        assert user_fk["referred_table"] == "users"
        assert user_fk["options"].get("ondelete", "").upper() == "CASCADE"

    def test_status_defaults_to_completed(self, db_at_0018):
        engine, _ = db_at_0018

        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id) VALUES ('u-status')"))
            conn.execute(
                text(
                    "INSERT INTO practice_log "
                    "(id, user_id, pack_id, practice_slug, primary_purpose, purposes, "
                    " category, occurred_at, day_key) "
                    "VALUES ('pl-1', 'u-status', 'p', 's', 'steadiness', '[]', "
                    " 'reflection', '2026-08-14T09:00:00+00:00', '2026-08-14')"
                )
            )

        with engine.connect() as conn:
            status = conn.execute(
                text("SELECT status FROM practice_log WHERE id = 'pl-1'")
            ).scalar_one()
        assert status == "completed"


class TestEcologyStateTable:
    """Section 4.2. One row per user; the PK is the FK."""

    def test_every_column_exists(self, db_at_0018):
        engine, _ = db_at_0018

        cols = {c["name"] for c in inspect(engine).get_columns("ecology_state")}
        expected = {
            "user_id",
            "protocol_size",
            "active_pack_ids",
            "last_recommended_at",
            "last_recommendation",
            "rotation_cursor",
            "created_at",
            "updated_at",
        }
        assert expected <= cols, f"missing ecology_state columns: {expected - cols}"

    def test_user_id_is_the_primary_key(self, db_at_0018):
        """One row per user is a schema fact, not an application rule."""
        engine, _ = db_at_0018

        pk = inspect(engine).get_pk_constraint("ecology_state")
        assert pk["constrained_columns"] == ["user_id"]

    def test_defaults_land_on_a_bare_insert(self, db_at_0018):
        engine, _ = db_at_0018

        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id) VALUES ('u-eco')"))
            conn.execute(text("INSERT INTO ecology_state (user_id) VALUES ('u-eco')"))

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT protocol_size, rotation_cursor FROM ecology_state WHERE user_id = :u"),
                {"u": "u-eco"},
            ).one()

        assert row[0] == 5
        assert row[1] == 0


class TestIntegrationEntriesTable:
    """Section 4.3, and the cascade asymmetry that guards user history."""

    def test_every_column_exists(self, db_at_0018):
        engine, _ = db_at_0018

        cols = {c["name"] for c in inspect(engine).get_columns("integration_entries")}
        expected = {
            "id",
            "user_id",
            "practice_log_id",
            "intention_entry_id",
            "reflection_entry_id",
            "purpose",
            "capacity_delta",
            "note",
            "created_at",
        }
        assert expected <= cols, f"missing integration_entries columns: {expected - cols}"

    def test_practice_log_link_cascades_but_journal_links_set_null(self, db_at_0018):
        """The asymmetry is deliberate and load-bearing.

        Deleting a journal entry is something a user does on purpose. It
        must not take the integration record with it.
        """
        engine, _ = db_at_0018

        fks = {
            fk["constrained_columns"][0]: fk
            for fk in inspect(engine).get_foreign_keys("integration_entries")
        }

        assert fks["practice_log_id"]["referred_table"] == "practice_log"
        assert fks["practice_log_id"]["options"].get("ondelete", "").upper() == "CASCADE"

        for column in ("intention_entry_id", "reflection_entry_id"):
            assert fks[column]["referred_table"] == "journal_entries"
            assert fks[column]["options"].get("ondelete", "").upper() == "SET NULL", (
                f"{column} must SET NULL: deleting a journal entry cannot destroy "
                "the integration record"
            )

    def test_the_two_indexes_exist(self, db_at_0018):
        engine, _ = db_at_0018

        indexed = {
            tuple(ix["column_names"]) for ix in inspect(engine).get_indexes("integration_entries")
        }
        for cols in [("user_id", "created_at"), ("user_id", "purpose", "created_at")]:
            assert cols in indexed, f"index on {cols} missing; have {indexed}"

    def test_note_is_nullable_text(self, db_at_0018):
        engine, _ = db_at_0018

        cols = {c["name"]: c for c in inspect(engine).get_columns("integration_entries")}
        assert cols["note"]["nullable"] is True
        assert "TEXT" in str(cols["note"]["type"]).upper()

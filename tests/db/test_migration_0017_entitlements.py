"""Tests for migration 0017 — the entitlement schema.

Three things have to hold for slice 1 of the unit-economics work to be safe
to deploy:

1. The seven new ``users`` columns land without a table rewrite (every one
   is nullable or carries a server_default).
2. Every row that already exists comes out on ``plan='beta'``. Every account
   on the system today arrived through an invite code, and the beta allowance
   is what keeps chat, art and reports working for them. If the data
   migration does not run, the whole invite cohort wakes up on the free
   allowance and slice 3 locks them out.
3. A signup created *after* the migration gets ``plan='free'`` from the
   column default, not ``'beta'``.

The ledger (``usage_records``) and the Stripe inbox (``billing_events``) are
created here too, so that the slices that write to them ship as a router and
a handler rather than a router, a handler and a migration on a live path.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def _alembic_config(async_url: str):
    """Build an Alembic Config pointed at *async_url*."""
    from alembic.config import Config

    import alchymine

    pkg_root = os.path.dirname(os.path.dirname(alchymine.__file__))
    cfg = Config(os.path.join(pkg_root, "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", async_url)
    return cfg


@pytest.fixture
def db_at_0016(tmp_path, monkeypatch):
    """A SQLite database migrated to 0016 — the state production is in today.

    Yields ``(engine, cfg)`` so a test can seed rows at 0016 and then run the
    0017 upgrade against them.
    """
    from alembic import command

    db_path = tmp_path / "entitlements.db"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", async_url)

    cfg = _alembic_config(async_url)
    command.upgrade(cfg, "0016")

    engine = create_engine(sync_url)
    yield engine, cfg
    engine.dispose()


class TestDataMigration:
    """The ``UPDATE users SET plan='beta'`` line is the load-bearing one."""

    def test_existing_users_become_beta(self, db_at_0016):
        """Rows that predate 0017 are the invite cohort and must land on beta."""
        from alembic import command

        engine, cfg = db_at_0016

        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id) VALUES ('legacy-1')"))
            conn.execute(text("INSERT INTO users (id) VALUES ('legacy-2')"))

        command.upgrade(cfg, "0017")

        with engine.connect() as conn:
            rows = conn.execute(text("SELECT id, plan, plan_status FROM users ORDER BY id")).all()

        assert rows == [
            ("legacy-1", "beta", "active"),
            ("legacy-2", "beta", "active"),
        ]

    def test_fresh_insert_defaults_to_free(self, db_at_0016):
        """A signup created after the migration gets the column default."""
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id) VALUES ('new-signup')"))

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT plan, plan_status, cancel_at_period_end FROM users WHERE id = :i"),
                {"i": "new-signup"},
            ).one()

        assert row[0] == "free"
        assert row[1] == "active"
        # SQLite keeps a boolean server_default as the literal text it was
        # given; Postgres parses it as a real boolean. Same convention the
        # is_admin / is_active columns have used since 0003.
        assert row[2] in (0, False, "false")

    def test_a_re_run_leaves_a_moved_account_alone(self, db_at_0016):
        """Re-running the upgrade must not re-grant beta to an upgraded account.

        The data migration is gated on having just created the ``plan``
        column. Without that gate, a partially-applied migration replayed
        after a deploy (or an ``alembic stamp`` back to 0016) would rewrite
        every deliberate plan change in the table.
        """
        from alembic import command

        engine, cfg = db_at_0016

        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id) VALUES ('legacy-1')"))

        command.upgrade(cfg, "0017")

        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET plan = 'pro' WHERE id = 'legacy-1'"))
            conn.execute(text("INSERT INTO users (id) VALUES ('new-signup')"))

        # Stamp back and replay: the schema is already at 0017, only the
        # version marker moves.
        command.stamp(cfg, "0016")
        command.upgrade(cfg, "0017")

        with engine.connect() as conn:
            plans = dict(conn.execute(text("SELECT id, plan FROM users")).all())

        assert plans["legacy-1"] == "pro", "a re-run must not drag an upgraded account back to beta"
        assert plans["new-signup"] == "free", "a post-migration signup must not be granted beta"

    def test_migration_is_safe_on_an_empty_table(self, db_at_0016):
        """No rows is not an error; the upgrade still completes."""
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM users")).scalar_one()
        assert count == 0


class TestUserColumns:
    """The seven entitlement columns from section 1.1 of the design."""

    def test_all_seven_columns_exist(self, db_at_0016):
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        cols = {c["name"] for c in inspect(engine).get_columns("users")}
        expected = {
            "plan",
            "plan_status",
            "stripe_customer_id",
            "stripe_subscription_id",
            "plan_period_end",
            "cancel_at_period_end",
            "trial_ends_at",
        }
        assert expected <= cols, f"missing entitlement columns: {expected - cols}"

    def test_stripe_identifier_columns_are_nullable_text(self, db_at_0016):
        """Fernet ciphertext is longer than plaintext, so these are TEXT."""
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        cols = {c["name"]: c for c in inspect(engine).get_columns("users")}
        for name in ("stripe_customer_id", "stripe_subscription_id"):
            assert cols[name]["nullable"] is True
            assert "TEXT" in str(cols[name]["type"]).upper()

    def test_downgrade_removes_the_entitlement_columns(self, db_at_0016):
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")
        command.downgrade(cfg, "0016")

        cols = {c["name"] for c in inspect(engine).get_columns("users")}
        assert "plan" not in cols
        assert "stripe_customer_id" not in cols

        tables = set(inspect(engine).get_table_names())
        assert "usage_records" not in tables
        assert "billing_events" not in tables


class TestUsageRecordsTable:
    """The cost ledger. One row per delivered paid call."""

    def test_table_has_every_ledger_column(self, db_at_0016):
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        cols = {c["name"] for c in inspect(engine).get_columns("usage_records")}
        expected = {
            "id",
            "created_at",
            "user_id",
            "scope",
            "surface",
            "meter",
            "provider",
            "model",
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "images",
            "cost_micros",
            "estimated",
            "period_key",
            "month_key",
            "request_id",
        }
        assert expected <= cols, f"missing ledger columns: {expected - cols}"

    def test_the_four_analytics_indexes_exist(self, db_at_0016):
        """/admin/usage table-scans within a month of launch without these."""
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        indexed = {tuple(ix["column_names"]) for ix in inspect(engine).get_indexes("usage_records")}
        for cols in [
            ("created_at",),
            ("user_id",),
            ("period_key", "surface"),
            ("user_id", "month_key"),
        ]:
            assert cols in indexed, f"index on {cols} missing; have {indexed}"

    def test_user_id_is_nullable_for_unattributed_spend(self, db_at_0016):
        """ON DELETE SET NULL keeps the aggregate honest after an erasure."""
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        cols = {c["name"]: c for c in inspect(engine).get_columns("usage_records")}
        assert cols["user_id"]["nullable"] is True


class TestBillingEventsTable:
    """Built now, zero writers until Stripe lands."""

    def test_table_has_every_column(self, db_at_0016):
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        cols = {c["name"] for c in inspect(engine).get_columns("billing_events")}
        expected = {
            "id",
            "stripe_event_id",
            "event_type",
            "user_id",
            "payload",
            "status",
            "error",
            "processed_at",
            "created_at",
        }
        assert expected <= cols, f"missing billing_events columns: {expected - cols}"

    def test_stripe_event_id_is_unique(self, db_at_0016):
        """The idempotency key. A duplicate webhook delivery must be rejected."""
        from alembic import command

        engine, cfg = db_at_0016
        command.upgrade(cfg, "0017")

        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO billing_events (stripe_event_id, event_type, status) "
                    "VALUES ('evt_1', 'checkout.session.completed', 'received')"
                )
            )

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO billing_events (stripe_event_id, event_type, status) "
                        "VALUES ('evt_1', 'checkout.session.completed', 'received')"
                    )
                )

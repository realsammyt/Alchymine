"""Tests for Alembic migration completeness.

Verifies that running all migrations on a fresh database produces the same
schema as the ORM models (i.e., no tables or columns are missing from the
migration chain).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.fixture
def fresh_migration_engine(tmp_path, monkeypatch):
    """Create a fresh SQLite DB, run all Alembic migrations, and return the engine."""
    db_path = tmp_path / "test_migrations.db"
    # Use aiosqlite driver for async Alembic env.py
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"

    # Override DATABASE_URL so env.py uses our test DB
    monkeypatch.setenv("DATABASE_URL", async_url)

    from alembic import command
    from alembic.config import Config

    import alchymine

    pkg_root = os.path.dirname(os.path.dirname(alchymine.__file__))
    ini_path = os.path.join(pkg_root, "alembic.ini")

    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", async_url)

    # Run all migrations on the fresh DB
    command.upgrade(cfg, "head")

    engine = create_engine(sync_url)
    yield engine
    engine.dispose()


@pytest.fixture
def orm_engine(tmp_path):
    """Create a fresh SQLite DB using ORM create_all() and return the engine."""
    db_path = tmp_path / "test_orm.db"
    url = f"sqlite:///{db_path}"

    engine = create_engine(url)

    from alchymine.db.base import Base

    # Ensure all models are imported
    import alchymine.db.models  # noqa: F401

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


class TestMigrationCompleteness:
    """Verify migration chain creates all required tables and columns."""

    def test_all_model_tables_exist_after_migration(
        self, fresh_migration_engine, orm_engine
    ):
        """Every table from ORM models must exist in the migrated schema."""
        orm_inspector = inspect(orm_engine)
        migration_inspector = inspect(fresh_migration_engine)

        orm_tables = set(orm_inspector.get_table_names())
        migration_tables = set(migration_inspector.get_table_names())

        # Exclude alembic's own version table
        migration_tables.discard("alembic_version")

        missing = orm_tables - migration_tables
        assert not missing, f"Tables missing from migrations: {missing}"

    def test_all_columns_exist_after_migration(
        self, fresh_migration_engine, orm_engine
    ):
        """Every column from ORM models must exist in the migrated schema."""
        orm_inspector = inspect(orm_engine)
        migration_inspector = inspect(fresh_migration_engine)

        migration_tables = set(migration_inspector.get_table_names())
        migration_tables.discard("alembic_version")

        missing_columns: list[str] = []
        for table in migration_tables:
            orm_cols = {c["name"] for c in orm_inspector.get_columns(table)}
            mig_cols = {c["name"] for c in migration_inspector.get_columns(table)}
            for col in orm_cols - mig_cols:
                missing_columns.append(f"{table}.{col}")

        assert not missing_columns, f"Columns missing from migrations: {missing_columns}"

    def test_migration_revision_chain_is_linear(self, fresh_migration_engine):
        """The alembic_version table should have exactly one head revision."""
        with fresh_migration_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = result.fetchall()

        assert len(rows) == 1, f"Expected 1 head revision, got {len(rows)}: {rows}"
        assert rows[0][0] == "0007", f"Expected head at 0007, got {rows[0][0]}"

    def test_reports_table_has_all_columns(self, fresh_migration_engine):
        """Reports table (added in migration 0006) has all expected columns."""
        inspector = inspect(fresh_migration_engine)
        cols = {c["name"] for c in inspector.get_columns("reports")}
        expected = {
            "id",
            "user_id",
            "report_type",
            "status",
            "user_input",
            "user_profile",
            "result",
            "html_content",
            "pdf_path",
            "pdf_data",
            "error",
            "created_at",
            "updated_at",
        }
        missing = expected - cols
        assert not missing, f"Reports columns missing: {missing}"

    def test_journal_entries_table_has_all_columns(self, fresh_migration_engine):
        """Journal entries table (added in migration 0006) has all expected columns."""
        inspector = inspect(fresh_migration_engine)
        cols = {c["name"] for c in inspector.get_columns("journal_entries")}
        expected = {
            "id",
            "user_id",
            "system",
            "entry_type",
            "title",
            "content",
            "tags",
            "mood_score",
            "created_at",
            "updated_at",
        }
        missing = expected - cols
        assert not missing, f"Journal entries columns missing: {missing}"

    def test_user_auth_columns_exist(self, fresh_migration_engine):
        """User table has auth columns added in migration 0006."""
        inspector = inspect(fresh_migration_engine)
        cols = {c["name"] for c in inspector.get_columns("users")}
        auth_cols = {
            "email",
            "password_hash",
            "password_reset_token",
            "password_reset_expires",
            "password_changed_at",
        }
        missing = auth_cols - cols
        assert not missing, f"User auth columns missing: {missing}"

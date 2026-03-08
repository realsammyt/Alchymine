"""Fix encrypted column type mismatches.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-07

Migration 0001 declared several encrypted columns with incorrect SQL types:

- ``intake_data.full_name``: String(200) → Text  (EncryptedString impl = Text)
- ``intake_data.birth_city``: String(200) → Text  (EncryptedString impl = Text)
- ``wealth_profiles.risk_tolerance``: String(50) → Text  (EncryptedString impl = Text)
- ``wealth_profiles.financial_distress_detected``: Boolean → Text  (EncryptedString)

Fernet ciphertext is always longer than the plaintext, so the backing column
must be Text (unbounded) rather than a length-limited String or Boolean.

On PostgreSQL, ``ALTER COLUMN ... TYPE TEXT`` is a safe, metadata-only change
for String → Text.  For Boolean → Text, existing rows will be cast.

On SQLite, column type changes are no-ops (dynamic typing), so we use
``batch_alter_table`` for schema compatibility.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_column_type(inspector: sa.Inspector, table: str, column: str) -> str:
    """Return the SQL type name for a column (e.g. 'TEXT', 'VARCHAR', 'BOOLEAN')."""
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return str(col["type"]).upper()
    return ""


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    inspector = inspect(conn)

    # ── intake_data: full_name String(200) → Text ─────────────────────
    if dialect_name == "postgresql":
        full_name_type = _get_column_type(inspector, "intake_data", "full_name")
        if "TEXT" not in full_name_type:
            op.alter_column(
                "intake_data",
                "full_name",
                type_=sa.Text(),
                existing_type=sa.String(200),
                existing_nullable=False,
            )

        birth_city_type = _get_column_type(inspector, "intake_data", "birth_city")
        if "TEXT" not in birth_city_type:
            op.alter_column(
                "intake_data",
                "birth_city",
                type_=sa.Text(),
                existing_type=sa.String(200),
                existing_nullable=True,
            )

        risk_type = _get_column_type(inspector, "wealth_profiles", "risk_tolerance")
        if "TEXT" not in risk_type:
            op.alter_column(
                "wealth_profiles",
                "risk_tolerance",
                type_=sa.Text(),
                existing_type=sa.String(50),
                existing_nullable=False,
                existing_server_default="moderate",
            )

        distress_type = _get_column_type(
            inspector, "wealth_profiles", "financial_distress_detected"
        )
        if "TEXT" not in distress_type:
            # Boolean → Text requires USING cast on PostgreSQL
            op.execute(
                "ALTER TABLE wealth_profiles "
                "ALTER COLUMN financial_distress_detected TYPE TEXT "
                "USING CASE WHEN financial_distress_detected THEN 'true' ELSE 'false' END"
            )
    else:
        # SQLite: use batch_alter_table for column type changes
        with op.batch_alter_table("intake_data") as batch_op:
            batch_op.alter_column(
                "full_name",
                type_=sa.Text(),
                existing_type=sa.String(200),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "birth_city",
                type_=sa.Text(),
                existing_type=sa.String(200),
                existing_nullable=True,
            )

        with op.batch_alter_table("wealth_profiles") as batch_op:
            batch_op.alter_column(
                "risk_tolerance",
                type_=sa.Text(),
                existing_type=sa.String(50),
                existing_nullable=False,
                existing_server_default="moderate",
            )
            batch_op.alter_column(
                "financial_distress_detected",
                type_=sa.Text(),
                existing_type=sa.Boolean(),
                existing_nullable=False,
                existing_server_default="0",
            )


def downgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        op.alter_column(
            "wealth_profiles",
            "financial_distress_detected",
            type_=sa.Boolean(),
            existing_type=sa.Text(),
            existing_nullable=False,
            postgresql_using="financial_distress_detected::boolean",
        )
        op.alter_column(
            "wealth_profiles",
            "risk_tolerance",
            type_=sa.String(50),
            existing_type=sa.Text(),
            existing_nullable=False,
            existing_server_default="moderate",
        )
        op.alter_column(
            "intake_data",
            "birth_city",
            type_=sa.String(200),
            existing_type=sa.Text(),
            existing_nullable=True,
        )
        op.alter_column(
            "intake_data",
            "full_name",
            type_=sa.String(200),
            existing_type=sa.Text(),
            existing_nullable=False,
        )
    else:
        with op.batch_alter_table("wealth_profiles") as batch_op:
            batch_op.alter_column(
                "financial_distress_detected",
                type_=sa.Boolean(),
                existing_type=sa.Text(),
                existing_nullable=False,
            )
            batch_op.alter_column(
                "risk_tolerance",
                type_=sa.String(50),
                existing_type=sa.Text(),
                existing_nullable=False,
            )

        with op.batch_alter_table("intake_data") as batch_op:
            batch_op.alter_column(
                "birth_city",
                type_=sa.String(200),
                existing_type=sa.Text(),
                existing_nullable=True,
            )
            batch_op.alter_column(
                "full_name",
                type_=sa.String(200),
                existing_type=sa.Text(),
                existing_nullable=False,
            )

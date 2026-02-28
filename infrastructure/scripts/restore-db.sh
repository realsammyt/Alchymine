#!/usr/bin/env bash
# ============================================================================
# Alchymine — PostgreSQL Database Restore
# Restores the Alchymine database from a backup created by backup-db.sh.
#
# Usage:
#   ./restore-db.sh <backup-file.sql.gz>
#
# Environment variables (from .env.production or defaults):
#   POSTGRES_USER  — database user (default: alchymine)
#   POSTGRES_DB    — database name (default: alchymine)
#   POSTGRES_HOST  — database host (default: db, for Docker network)
#   POSTGRES_PORT  — database port (default: 5432)
#
# WARNING: This will DROP and recreate the target database.
# ============================================================================
set -euo pipefail

# ── Argument validation ──────────────────────────────────────────────────────
if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    echo ""
    echo "Available backups:"
    BACKUP_DIR="$(dirname "$0")/../backups"
    if [ -d "${BACKUP_DIR}" ]; then
        ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "  (none found in ${BACKUP_DIR})"
    fi
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# ── Configuration ────────────────────────────────────────────────────────────
POSTGRES_USER="${POSTGRES_USER:-alchymine}"
POSTGRES_DB="${POSTGRES_DB:-alchymine}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

echo "=== Alchymine Database Restore ==="
echo "Database:    ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "Backup file: ${BACKUP_FILE}"
echo ""

# ── Safety confirmation ──────────────────────────────────────────────────────
echo "WARNING: This will DROP the database '${POSTGRES_DB}' and restore from backup."
echo "All existing data will be lost."
echo ""
read -p "Type 'yes' to confirm: " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Restoring..."

# ── Restore ──────────────────────────────────────────────────────────────────
if command -v docker &>/dev/null && docker ps --format '{{.Names}}' | grep -q "alchymine-db"; then
    echo "Restoring via Docker container..."

    # Drop and recreate the database
    docker exec alchymine-db psql -U "${POSTGRES_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
        -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};" \
        -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

    # Restore from backup
    gunzip -c "${BACKUP_FILE}" | docker exec -i alchymine-db pg_restore \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --verbose \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
    || true  # pg_restore may return non-zero for warnings

elif command -v psql &>/dev/null && command -v pg_restore &>/dev/null; then
    echo "Restoring via local tools..."

    # Drop and recreate the database
    psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
        -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};" \
        -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

    # Restore from backup
    gunzip -c "${BACKUP_FILE}" | pg_restore \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --verbose \
        --no-owner \
        --no-privileges \
        --clean \
        --if-exists \
    || true

else
    echo "ERROR: Neither Docker nor psql/pg_restore is available."
    exit 1
fi

echo ""
echo "=== Restore complete ==="
echo "Database '${POSTGRES_DB}' has been restored from: ${BACKUP_FILE}"
echo ""
echo "Next steps:"
echo "  1. Verify the application is working: curl http://localhost:8000/health"
echo "  2. Run any pending migrations: docker exec alchymine-api alembic upgrade head"

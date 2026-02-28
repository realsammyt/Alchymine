#!/usr/bin/env bash
# ============================================================================
# Alchymine — PostgreSQL Database Backup
# Creates a timestamped pg_dump of the Alchymine database.
#
# Usage:
#   ./backup-db.sh                     # Backs up to ./backups/
#   ./backup-db.sh /path/to/backups    # Backs up to specified directory
#
# Environment variables (from .env.production or defaults):
#   POSTGRES_USER     — database user (default: alchymine)
#   POSTGRES_DB       — database name (default: alchymine)
#   POSTGRES_HOST     — database host (default: db, for Docker network)
#   POSTGRES_PORT     — database port (default: 5432)
#   BACKUP_RETENTION  — days to keep backups (default: 30)
# ============================================================================
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
POSTGRES_USER="${POSTGRES_USER:-alchymine}"
POSTGRES_DB="${POSTGRES_DB:-alchymine}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_RETENTION="${BACKUP_RETENTION:-30}"

BACKUP_DIR="${1:-$(dirname "$0")/../backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

# ── Setup ────────────────────────────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"

echo "=== Alchymine Database Backup ==="
echo "Timestamp:  ${TIMESTAMP}"
echo "Database:   ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "Output:     ${BACKUP_FILE}"
echo ""

# ── Dump ─────────────────────────────────────────────────────────────────────
# Use docker exec if running inside the Docker network, or pg_dump directly
if command -v docker &>/dev/null && docker ps --format '{{.Names}}' | grep -q "alchymine-db"; then
    echo "Backing up via Docker container..."
    docker exec alchymine-db pg_dump \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --verbose \
        --format=custom \
        --no-owner \
        --no-privileges \
    | gzip > "${BACKUP_FILE}"
elif command -v pg_dump &>/dev/null; then
    echo "Backing up via local pg_dump..."
    pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --verbose \
        --format=custom \
        --no-owner \
        --no-privileges \
    | gzip > "${BACKUP_FILE}"
else
    echo "ERROR: Neither Docker nor pg_dump is available."
    exit 1
fi

# ── Verify ───────────────────────────────────────────────────────────────────
if [ -s "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo ""
    echo "Backup completed successfully."
    echo "File: ${BACKUP_FILE}"
    echo "Size: ${BACKUP_SIZE}"
else
    echo "ERROR: Backup file is empty or was not created."
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# ── Cleanup old backups ─────────────────────────────────────────────────────
if [ "${BACKUP_RETENTION}" -gt 0 ]; then
    echo ""
    echo "Cleaning up backups older than ${BACKUP_RETENTION} days..."
    DELETED=$(find "${BACKUP_DIR}" -name "${POSTGRES_DB}_*.sql.gz" -mtime +"${BACKUP_RETENTION}" -delete -print | wc -l)
    echo "Removed ${DELETED} old backup(s)."
fi

echo ""
echo "=== Backup complete ==="

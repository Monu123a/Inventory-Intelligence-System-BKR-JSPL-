#!/bin/bash
# scripts/backup_db.sh
set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_PATH="${BASE_DIR}/inventory.db"
BACKUP_DIR="${BASE_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/inventory_${TIMESTAMP}.db"

mkdir -p "${BACKUP_DIR}"

if [ ! -f "${DB_PATH}" ]; then
  echo "Error: Database file not found at ${DB_PATH}"
  exit 1
fi

echo "Starting atomic backup of ${DB_PATH} to ${BACKUP_FILE}..."
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"
echo "Backup completed successfully: ${BACKUP_FILE}"

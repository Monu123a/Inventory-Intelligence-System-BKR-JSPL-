#!/bin/bash
# scripts/restore_db.sh
set -e

if [ -z "$1" ]; then
  echo "Usage: ./restore_db.sh <backup_filename>"
  echo "Example: ./restore_db.sh inventory_20260810_120000.db"
  exit 1
fi

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_PATH="${BASE_DIR}/inventory.db"
BACKUP_DIR="${BASE_DIR}/backups"
BACKUP_FILE="${BACKUP_DIR}/$1"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Error: Backup file not found at ${BACKUP_FILE}"
  exit 1
fi

echo "WARNING: This will overwrite the live database at ${DB_PATH} with ${BACKUP_FILE}"
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

echo "Creating safety backup before restore..."
sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/safety_before_restore_$(date +%Y%m%d_%H%M%S).db'"

echo "Restoring database..."
cp "${BACKUP_FILE}" "${DB_PATH}"
echo "Restore completed successfully."

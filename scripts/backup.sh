#!/bin/bash
# Backs up Postgres and uploaded files. Run manually or via cron.
# Cron example (daily at 2am): 0 2 * * * /path/to/NURA/scripts/backup.sh

set -e

cd "$(dirname "$0")/.."

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting backup at $TIMESTAMP"

# Postgres
echo "[backup] Dumping Postgres..."
docker compose exec -T postgres pg_dump -U nura_user -d nura_db -Fc \
  > "$BACKUP_DIR/postgres_$TIMESTAMP.dump"
echo "[backup] Postgres dump saved: postgres_$TIMESTAMP.dump"

# Uploaded files
if [ -d "./uploads" ]; then
  echo "[backup] Archiving uploads..."
  tar -czf "$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz" uploads
  echo "[backup] Uploads archived: uploads_$TIMESTAMP.tar.gz"
fi

# Prune old backups
echo "[backup] Removing backups older than $KEEP_DAYS days..."
find "$BACKUP_DIR" -name "*.dump" -mtime +$KEEP_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$KEEP_DAYS -delete

echo "[backup] Done."

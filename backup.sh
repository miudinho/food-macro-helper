#!/usr/bin/env bash
# Spójny backup SQLite (online backup API – bezpieczny przy trybie WAL) + foods.json.
set -euo pipefail
NAME="${NAME:-macro-diet-app}"
DOCKER="${DOCKER:-sudo docker}"
OUT_DIR="${OUT_DIR:-./backups}"
TS="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

$DOCKER exec "$NAME" python -c "
import sqlite3
src = sqlite3.connect('/app/data/macro.db')
dst = sqlite3.connect('/tmp/macro_backup.db')
src.backup(dst); dst.close(); src.close()
"
$DOCKER cp "$NAME:/tmp/macro_backup.db" "$OUT_DIR/macro_${TS}.db"
$DOCKER cp "$NAME:/app/data/foods.json" "$OUT_DIR/foods_${TS}.json"
$DOCKER exec "$NAME" rm -f /tmp/macro_backup.db
chmod 600 "$OUT_DIR"/macro_"${TS}".db
echo "Backup: $OUT_DIR/macro_${TS}.db, $OUT_DIR/foods_${TS}.json"

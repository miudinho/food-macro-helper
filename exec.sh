#!/usr/bin/env bash
# Build + uruchomienie z trwałym wolumenem (SQLite + foods.json) i hardeningiem.
# foods.json z folderu tego skryptu jest przy każdym starcie synchronizowany do wolumenu.
set -euo pipefail

IMAGE="${IMAGE:-macro-diet-app}"
NAME="${NAME:-macro-diet-app}"
VOLUME="${VOLUME:-macro-data}"
PORT="${PORT:-8501}"
BIND_ADDR="${BIND_ADDR:-127.0.0.1}"   # 0.0.0.0 tylko za firewallem / reverse proxy
DOCKER="${DOCKER:-sudo docker}"
# overwrite = wolumen zastępowany plikiem z folderu (stary do foods.json.bak)
# merge     = produkty z pliku dopisywane/nadpisywane, dodane w UI zostają
# off       = tylko pierwszy start
FOODS_SYNC="${MACRO_FOODS_SYNC:-overwrite}"

cd "$(dirname "$0")"

$DOCKER build -t "$IMAGE" .
$DOCKER volume create "$VOLUME" >/dev/null

# Jednorazowy import starego stanu (user_selection.json) do wolumenu, jeśli istnieje
if [[ -f user_selection.json ]]; then
  $DOCKER run --rm --entrypoint sh \
    -v "$VOLUME:/app/data" -v "$(pwd)/user_selection.json:/import.json:ro" \
    "$IMAGE" -c '[ -f /app/data/macro.db ] || cp /import.json /app/data/user_selection.json'
fi

# foods.json z folderu skryptu -> kontener (tylko do odczytu)
FOODS_ARGS=()
if [[ -f foods.json ]]; then
  FOODS_ARGS=(-v "$(pwd)/foods.json:/seed/foods.json:ro" -e MACRO_FOODS_SEED=/seed/foods.json)
else
  echo "UWAGA: brak $(pwd)/foods.json - użyty zostanie plik z obrazu/wolumenu" >&2
fi

# Usuń poprzednią instancję o tej samej nazwie (dane zostają w wolumenie)
$DOCKER rm -f "$NAME" >/dev/null 2>&1 || true

exec $DOCKER run --rm --name "$NAME" \
  -p "${BIND_ADDR}:${PORT}:8501" \
  -v "$VOLUME:/app/data" \
  "${FOODS_ARGS[@]}" \
  -e MACRO_FOODS_SYNC="$FOODS_SYNC" \
  --read-only --tmpfs /tmp:size=64m,mode=1777 \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --pids-limit 256 --memory 512m --cpus 1 \
  --stop-timeout 15 \
  "$IMAGE"


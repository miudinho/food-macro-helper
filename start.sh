#!/usr/bin/env bash
# Wariant docker compose (zalecany): dane w wolumenie "macro-data".
set -euo pipefail
cd "$(dirname "$0")"
sudo docker compose up -d --build
sudo docker compose ps
echo "Aplikacja: http://127.0.0.1:8501  |  logi: sudo docker compose logs -f"

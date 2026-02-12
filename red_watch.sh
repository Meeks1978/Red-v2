#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8111/health"
NAME="red"

if curl -fsS --max-time 2 "$BASE" >/dev/null; then
  exit 0
fi

echo "[red-watch] health failed; dumping last logs + restarting..."
docker logs "$NAME" --tail 200 || true
docker restart "$NAME" || true
sleep 2
curl -fsS --max-time 3 "$BASE" >/dev/null && echo "[red-watch] recovered"
